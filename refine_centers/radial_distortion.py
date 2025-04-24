#!/usr/bin/env python3
"""
radial_distortion.py
====================

Compute the radial difference between peaks reported by the peak search and
indexed reflections in a Cheetah/CrystFEL *.stream* file and create a scatter
plot of the distortion.

For every peak the script finds the spatially‑nearest indexed reflection in the
same event.  A peak contributes to the plot **only if its nearest reflection is
within a user‑defined direct‑space distance Δ (pixels)**.  For the accepted
pairs we calculate the radii (pixel distance from a common origin) and plot

    Δr = r_peak − r_reflection   versus   r_reflection

The result is useful for diagnosing isotropic magnification (barrel/
pincushion) distortion in diffraction images.

Usage
-----
    python radial_distortion.py hits.stream                         # default Δ = 3 px
    python radial_distortion.py hits.stream -d 2.0 --cx 512 --cy 512  # custom Δ and beam centre

Optional arguments
------------------
    -d, --max‑dist Δ     keep a peak only if its nearest reflection is ≤ Δ pixels (default 3)
    -o, --out PNG        save the figure instead of showing it
    --csv CSV            also write a two‑column CSV (r_reflection, Δr)
    --cx, --cy FLOAT     beam centre in pixels (defaults 0, 0)
    -p, --pattern REGEX  event delimiter regex (default "^Image filename:")
    -n, --max‑peaks INT  stop after this many events (for testing)

Requires **numpy** and **matplotlib**.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Iterable, Optional

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# Parsing helpers
# -----------------------------------------------------------------------------

def _parse_peaks(block: str) -> List[Tuple[float, float]]:
    """Return list of (fs, ss) peaks from a chunk."""
    m = re.search(r"Peaks from peak search(.*?)End of peak list", block, re.S)
    if not m:
        return []
    peaks = []
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if re.match(r"^[0-9]", line):
            parts = line.split()
            peaks.append((float(parts[0]), float(parts[1])))
    return peaks


def _parse_reflections(block: str) -> List[Tuple[float, float]]:
    """Return list of (fs, ss) reflections from a chunk."""
    m = re.search(
        r"Reflections measured after indexing(.*?)End of reflections", block, re.S
    )
    if not m:
        return []
    refls = []
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        # first token is h index (may be negative)
        if re.match(r"^[0-9\-]", line):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    fs = float(parts[-3])
                    ss = float(parts[-2])
                    refls.append((fs, ss))
                except ValueError:
                    continue
    return refls


def _radial_diffs(
    peaks: Iterable[Tuple[float, float]],
    refls: Iterable[Tuple[float, float]],
    cx: float,
    cy: float,
    max_xy_dist: Optional[float] = None,
):
    """Yield tuples (r_reflection, delta_r) with an optional distance filter.

    A peak contributes only if the Euclidean distance to its closest reflection
    is ≤ max_xy_dist (if that value is not None).
    """
    refls = np.asarray(refls, dtype=float)
    if refls.size == 0:
        return

    # Shift reflections once for speed
    refls_shifted = refls - np.array([[cx, cy]])
    r_refl = np.hypot(refls_shifted[:, 0], refls_shifted[:, 1])

    for fs_p, ss_p in peaks:
        u, v = fs_p - cx, ss_p - cy
        r_peak = np.hypot(u, v)

        # Squared distances to every reflection
        d2 = (refls_shifted[:, 0] - u) ** 2 + (refls_shifted[:, 1] - v) ** 2
        i_min = int(np.argmin(d2))

        # Reject if the nearest reflection is farther than the threshold
        if max_xy_dist is not None and d2[i_min] > max_xy_dist ** 2:
            continue

        yield r_refl[i_min], r_peak - r_refl[i_min]


# -----------------------------------------------------------------------------
# Main driver
# -----------------------------------------------------------------------------

def process_stream(
    text: str,
    cx: float = 0.0,
    cy: float = 0.0,
    event_pattern: str = r"^Image filename:",
    max_events: Optional[int] = None,
    max_xy_dist: Optional[float] = None,
):
    """Return two numpy arrays (r_reflection, delta_r) for the whole file."""
    event_re = re.compile(event_pattern, re.M)
    # Split but keep delimiter by using finditer indices
    indices = [m.start() for m in event_re.finditer(text)] + [None]
    r_list: List[float] = []
    d_list: List[float] = []

    for i, start in enumerate(indices[:-1]):
        end = indices[i + 1]
        chunk = text[start:end]
        peaks = _parse_peaks(chunk)
        refls = _parse_reflections(chunk)
        for r_ref, d in _radial_diffs(peaks, refls, cx, cy, max_xy_dist):
            r_list.append(r_ref)
            d_list.append(d)
        if max_events is not None and i + 1 >= max_events:
            break
    return np.asarray(r_list), np.asarray(d_list)


# -----------------------------------------------------------------------------
# CLI entry‑point
# -----------------------------------------------------------------------------


def main(argv=None):
    
    stream_file = "/home/bubl3932/files/MFM300_VIII/simulation-2/xgandalf_iterations_max_radius_0_step_1/MFM300_0_0.stream"
    # Treat zero or negative as 'no filter'
    max_xy_dist = 1

    text = Path(stream_file).read_text()

    r_ref, delta = process_stream(
        text,
        cx=502.5,
        cy=510.5,
        max_events=1000,
        max_xy_dist=max_xy_dist,
    )

    if r_ref.size == 0:
        sys.exit("No peaks/reflections passed the distance filter – "
                 "check Δ or the stream content.")


    # ─── Plot ───────────────────────────────────────────────────────────────
    plt.figure(figsize=(6, 4))
    plt.scatter(r_ref, delta, s=8, alpha=0.7)
    plt.axhline(0, ls="--", lw=0.8)
    plt.xlabel("Reflection radius, r_ref (px)")
    plt.ylabel("Δr = r_peak − r_ref (px)")
    plt.title("Radial distortion")
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
