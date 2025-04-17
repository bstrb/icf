#!/usr/bin/env python
"""
Refine detector beam‑centre using PEAK positions married to the nearest indexed
(h,k,l).  Runs each diffraction “chunk” in parallel and writes
refined_centers.csv + two diagnostic plots.
"""

import os
import re
import csv
import numpy as np
import matplotlib.pyplot as plt
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

# ══════════════════════════════════════════════════════════════════════
# Utility: match peaks to nearest reflection, with filters
# ══════════════════════════════════════════════════════════════════════
def match_peaks_to_reflections(
    peaks,
    reflections,
    intensity_threshold=300.0,
    max_match_radius_px=4.0,
    center=(512.0, 512.0),
    min_r_px=0.0,
    max_r_px=np.inf,
):
    """
    Return a list of (h, k, l, fs_peak, ss_peak) for peaks that:

      • have intensity ≥ `intensity_threshold`
      • lie between `min_r_px` and `max_r_px` from image centre
      • have an indexed reflection within `max_match_radius_px` pixels
    """
    refl_xy = np.array([(fs, ss) for (_, _, _, fs, ss) in reflections])
    if refl_xy.size == 0:
        return []

    tree = cKDTree(refl_xy)
    matched = []
    cx0, cy0 = center

    for fs_p, ss_p, inten in peaks:
        if inten < intensity_threshold:
            continue
        r = np.hypot(fs_p - cx0, ss_p - cy0)
        if not (min_r_px <= r <= max_r_px):
            continue

        dist, idx = tree.query((fs_p, ss_p), distance_upper_bound=max_match_radius_px)
        if np.isfinite(dist):  # neighbour within radius
            h, k, l, _, _ = reflections[idx]
            matched.append((h, k, l, fs_p, ss_p))

    return matched


# ══════════════════════════════════════════════════════════════════════
# 1) Parse geometry from header
# ══════════════════════════════════════════════════════════════════════
def parse_header_geometry(stream_text):
    """Extract wavelength, clen, res, pixel size from the geometry block."""
    geom = {}

    geom_block = re.search(
        r"----- Begin geometry file -----\s*(.*?)\s*----- End geometry file -----",
        stream_text,
        re.DOTALL,
    )
    if geom_block:
        block = geom_block.group(1)
        def _f(pat):  # helper
            m = re.search(pat, block)
            return float(m.group(1)) if m else None

        geom["wavelength_A"] = _f(r"wavelength\s*=\s*([\d.eE+-]+)\s*A")
        geom["clen_m"]      = _f(r"clen\s*=\s*([\d.eE+-]+)\s*m")
        geom["res"]         = _f(r"res\s*=\s*([\d.eE+-]+)")

    # Pixel size in mm
    geom["pixel_size_mm"] = 1000.0 / geom["res"] if geom.get("res") else 0.1
    return geom


# ══════════════════════════════════════════════════════════════════════
# 2) Parse one chunk
# ══════════════════════════════════════════════════════════════════════
def parse_stream_chunk(chunk):
    """
    Returns
        (evt_idx, astar, bstar, cstar, reflections, peaks)

    * reflections: list of (h,k,l, fs, ss)
    * peaks      : list of (fs, ss, intensity)
    """
    m_ev = re.search(r"Event:\s*//([0-9]+)", chunk)
    if not m_ev:
        return None
    evt_idx = int(m_ev.group(1))

    recips = {}
    for name, x, y, z in re.findall(
        r"(astar|bstar|cstar)\s*=\s*([+\-0-9.e]+)\s+([+\-0-9.e]+)\s+([+\-0-9.e]+)\s+nm\^-1",
        chunk,
    ):
        recips[name] = 0.1 * np.array([float(x), float(y), float(z)])

    if len(recips) != 3:
        return None

    # ------------------------------------------------ reflections
    refl_list = []
    refl_block = re.search(
        r"Reflections measured after indexing(.*?)End of reflections",
        chunk,
        re.DOTALL,
    )
    if refl_block:
        for ln in refl_block.group(1).strip().splitlines():
            if re.match(r"^\s*-?\d+", ln):
                parts = ln.split()
                if len(parts) >= 9:
                    h, k, l = map(int, parts[:3])
                    fs, ss = map(float, parts[7:9])
                    refl_list.append((h, k, l, fs, ss))

    # ------------------------------------------------ peaks
    peak_list = []
    peak_block = re.search(
        r"Peaks from peak search(.*?)End of peak list",
        chunk,
        re.DOTALL,
    )
    if peak_block:
        for ln in peak_block.group(1).strip().splitlines():
            parts = ln.split()
            if len(parts) >= 4 and parts[0][0].isdigit():
                fs_p, ss_p, inten = float(parts[0]), float(parts[1]), float(parts[3])
                peak_list.append((fs_p, ss_p, inten))

    return (
        evt_idx,
        recips["astar"],
        recips["bstar"],
        recips["cstar"],
        refl_list,
        peak_list,
    )


# ══════════════════════════════════════════════════════════════════════
# 3) Diffraction model + least‑squares
# ══════════════════════════════════════════════════════════════════════
def build_orientation_matrix(astar, bstar, cstar):
    return np.column_stack((astar, bstar, cstar))


def predict_fs_ss(h, k, l, R, k_in, dist_mm, px_mm, cx, cy):
    hkl = np.array([h, k, l])
    k_scat = k_in + R @ hkl
    kz = k_scat[2]
    if abs(kz) < 1e-12:
        return np.nan, np.nan

    t = dist_mm / kz
    fs = cx + (t * k_scat[0]) / px_mm
    ss = cy + (t * k_scat[1]) / px_mm
    return fs, ss


def residual_beam_center(params, reflections, R, k_in, dist_mm, px_mm):
    cx, cy = params
    res = []
    for h, k, l, fs_m, ss_m in reflections:
        fs_p, ss_p = predict_fs_ss(h, k, l, R, k_in, dist_mm, px_mm, cx, cy)
        if np.isfinite(fs_p) and np.isfinite(ss_p):
            res.extend([fs_p - fs_m, ss_p - ss_m])
    return np.asarray(res)


def refine_beam_center(
    astar,
    bstar,
    cstar,
    reflections,
    wavelength_A,
    clen_m,
    px_size_mm,
    guess_cx=512.0,
    guess_cy=512.0,
):
    R = build_orientation_matrix(astar, bstar, cstar)
    k_in = np.array([0.0, 0.0, 1.0 / wavelength_A])
    dist_mm = clen_m * 1000.0

    res = least_squares(
        residual_beam_center,
        x0=[guess_cx, guess_cy],
        args=(reflections, R, k_in, dist_mm, px_size_mm),
        method="lm",
        max_nfev=1000,
    )
    return tuple(res.x)


# ══════════════════════════════════════════════════════════════════════
# 4) Worker for one chunk
# ══════════════════════════════════════════════════════════════════════
def process_one_chunk(
    chunk,
    geom,
    inten_thr=300.0,
    match_radius_px=4.0,
    min_r=0.0,
    max_r=np.inf,
    guess_cx=512.0,
    guess_cy=512.0,
):
    parsed = parse_stream_chunk(chunk)
    if not parsed:
        return None

    evt_idx, astar, bstar, cstar, refls, peaks = parsed
    if not (refls and peaks):
        return None

    use_refs = match_peaks_to_reflections(
        peaks,
        refls,
        intensity_threshold=inten_thr,
        max_match_radius_px=match_radius_px,
        center=(guess_cx, guess_cy),
        min_r_px=min_r,
        max_r_px=max_r,
    )
    if not use_refs:
        return None

    cx_ref, cy_ref = refine_beam_center(
        astar,
        bstar,
        cstar,
        use_refs,
        geom["wavelength_A"],
        geom["clen_m"],
        geom["pixel_size_mm"],
        guess_cx,
        guess_cy,
    )
    return evt_idx, cx_ref, cy_ref


# ══════════════════════════════════════════════════════════════════════
# 5) Main driver
# ══════════════════════════════════════════════════════════════════════
def parse_stream_and_refine_multiproc(stream_file):
    with open(stream_file, "r") as fh:
        stream_text = fh.read()

    geom = parse_header_geometry(stream_text)
    print("Parsed geometry:", geom)

    chunks = re.findall(
        r"----- Begin chunk -----\s*(.*?)\s*----- End chunk -----",
        stream_text,
        re.DOTALL,
    )
    print(f"Found {len(chunks)} chunks in the stream file.")

    # Worker with proper keyword arguments!
    worker = partial(
        process_one_chunk,
        geom=geom,
        inten_thr=200.0,
        match_radius_px=2.0,
        min_r=50.0,
        max_r=500.0,
        guess_cx=512.0,
        guess_cy=512.0,
    )

    results = []
    with ProcessPoolExecutor() as ex:
        for out in tqdm(
            ex.map(worker, chunks), total=len(chunks), desc="Processing chunks"
        ):
            if out is not None:
                results.append(out)

    results.sort(key=lambda x: x[0])

    # ─── plots ────────────────────────────────────────────────────────
    if results:
        evt, cx, cy = zip(*results)
        plt.figure()
        plt.plot(evt, cx, marker="o")
        plt.xlabel("Event index")
        plt.ylabel("Refined centre X (px)")
        plt.title("Refined Beam Centre X vs. Event")
        plt.figure()
        plt.plot(evt, cy, marker="o")
        plt.xlabel("Event index")
        plt.ylabel("Refined centre Y (px)")
        plt.title("Refined Beam Centre Y vs. Event")
        plt.show()

    # ─── CSV ──────────────────────────────────────────────────────────
    csv_path = os.path.join(os.path.dirname(stream_file), "refined_centers.csv")
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["EventIndex", "RefinedCenterX", "RefinedCenterY"])
        writer.writerows(results)

    print(f"Results written to {csv_path}")
    return results


# ══════════════════════════════════════════════════════════════════════
# CLI entry‑point
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    stream_file = "/Users/xiaodong/Downloads/filtered_metrics.stream"
    parse_stream_and_refine_multiproc(stream_file)
