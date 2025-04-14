#!/usr/bin/env python3
import os
import sys
import signal
import glob
import shutil
import atexit
import tempfile
import re
import time

# -------------------------------------------------------------------
# 1) Replace the stub below with your real import:
from gandalf_interations.gandalf_radial_iterator import gandalf_iterator

# -------------------------------------------------------------------

def cleanup_temp_dirs():
    """Remove all directories in the current working directory that start with 'indexamajig'."""
    for d in glob.glob("indexamajig*"):
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"Removed temporary directory: {d}")

atexit.register(cleanup_temp_dirs)

def signal_handler(sig, frame):
    """Handle Ctrl+C / SIGINT or SIGTERM to clean up and exit."""
    cleanup_temp_dirs()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

INDEXING_FLAGS = [
    "--indexing=xgandalf",
    "--integration=rings",
]

def parse_geometry_file(geom_path):
    """
    Parses the .geom file to extract known parameters:
      wavelength, adu_per_photon, clen, res, p0/corner_x, p0/corner_y
    Returns a dict { 'wavelength': <float or None>,
                     'adu_per_photon': <float or None>,
                     'clen': <float or None>,
                     'res': <float or None>,
                     'corner_x': <float or None>,
                     'corner_y': <float or None> }
    """
    results = {
        'wavelength': None,
        'adu_per_photon': None,
        'clen': None,
        'res': None,
        'corner_x': None,
        'corner_y': None,
    }
    if not os.path.isfile(geom_path):
        print(f"WARNING: geometry file not found: {geom_path}")
        return results

    with open(geom_path, 'r') as f:
        lines = f.readlines()

    # We'll do naive text matching plus a simple float parse
    # Example lines:
    # wavelength  = 0.019687 A
    # adu_per_photon = 5
    # clen = 0.295 m
    # res = 17857.14285714286
    # p0/corner_x = -512
    # p0/corner_y = -512

    # Regex patterns
    # We capture a possible float, ignoring trailing units like 'A' or 'm'.
    pat_map = {
        'wavelength': re.compile(r'^\s*wavelength\s*=\s*([\d.]+)', re.IGNORECASE),
        'adu_per_photon': re.compile(r'^\s*adu_per_photon\s*=\s*([\d.]+)', re.IGNORECASE),
        'clen': re.compile(r'^\s*clen\s*=\s*([\d.]+)', re.IGNORECASE),
        'res': re.compile(r'^\s*res\s*=\s*([\d.]+)', re.IGNORECASE),
        'corner_x': re.compile(r'^\s*p0/corner_x\s*=\s*([\-\d.]+)', re.IGNORECASE),
        'corner_y': re.compile(r'^\s*p0/corner_y\s*=\s*([\-\d.]+)', re.IGNORECASE),
    }

    for line in lines:
        test = line.strip().lower()
        for key, rgx in pat_map.items():
            m = rgx.match(test)
            if m:
                try:
                    results[key] = float(m.group(1))
                except ValueError:
                    results[key] = None
                break

    return results

def create_temp_geometry(
    original_geom_path,
    wavelength=None,
    adu_per_photon=None,
    clen=None,
    res=None,
    corner_x=None,
    corner_y=None
):
    """
    Create a temporary geometry file from `original_geom_path`, overriding any
    parameters that are not None. Returns the path to a new temp .geom file.
    """
    # Read original lines
    with open(original_geom_path, "r") as f:
        lines = f.readlines()

    # Build a dict of overrides => line text
    overrides = {}
    if wavelength is not None:
        overrides["wavelength"] = f"wavelength  = {wavelength} A\n"
    if adu_per_photon is not None:
        overrides["adu_per_photon"] = f"adu_per_photon = {adu_per_photon}\n"
    if clen is not None:
        overrides["clen"] = f"clen = {clen} m\n"
    if res is not None:
        overrides["res"] = f"res = {res}\n"
    if corner_x is not None:
        overrides["p0/corner_x"] = f"p0/corner_x = {corner_x}\n"
    if corner_y is not None:
        overrides["p0/corner_y"] = f"p0/corner_y = {corner_y}\n"

    replaced = {k: False for k in overrides}

    def line_starts_with_param(line_text, param_key):
        return line_text.strip().lower().startswith(param_key)

    new_lines = []
    for line in lines:
        replaced_this_line = False
        for k, v in overrides.items():
            if line_starts_with_param(line, k):
                new_lines.append(v)
                replaced[k] = True
                replaced_this_line = True
                break
        if not replaced_this_line:
            new_lines.append(line)

    # Append any not-found keys
    for k, was_replaced in replaced.items():
        if not was_replaced:
            new_lines.append(overrides[k])

    # Make a temp directory for the new geometry file
    temp_dir = tempfile.mkdtemp(prefix="geom_tmp_")
    temp_geom_path = os.path.join(temp_dir, "modified_geometry.geom")

    with open(temp_geom_path, "w") as out:
        out.writelines(new_lines)

    return temp_geom_path


def prompt_float_override(name, geometry_value, current_override):
    """
    Prompts the user to override a geometry parameter (float).
    - `name`: e.g. "wavelength"
    - `geometry_value`: the float value parsed from the geometry file (None if not found)
    - `current_override`: the user's last override (None if none)
    
    We show them something like:
      "wavelength? Geometry file shows 0.019. Current override: None
       Enter new float, or press enter to keep existing, or 'none' to remove override."
    
    Returns the new override float or None if no override.
    """
    geom_str = "N/A" if geometry_value is None else str(geometry_value)
    over_str = "None" if current_override is None else str(current_override)
    msg = (
        f"{name}?\n"
        f"  Geometry file: {geom_str}\n"
        f"  Current override: {over_str}\n"
        f"Enter a new float to override, press Enter to keep, or type 'none' to remove override: "
    )
    ans = input(msg).strip().lower()
    if ans == "":
        # keep existing override
        return current_override
    if ans == "none":
        # remove override
        return None
    # attempt to parse
    try:
        val = float(ans)
        return val
    except ValueError:
        print("Invalid float, ignoring input. Keeping old override.")
        return current_override


def main():
    # 1) Hard-coded defaults for main parameters
    #    (You can prompt for these if you want, but here we keep them pre-set.)
    params = {
        "geom_file":  "/home/bubl3932/files/MFM300_VIII/MFM300_VIII_spot2_20250408_1511/MFM.geom",
        "cell_file":  "/home/bubl3932/files/MFM300_VIII/MFM300_VIII_spot2_20250408_1511/MFM.cell",
        "input_folder": "/home/bubl3932/files/MFM300_VIII/MFM300_VIII_spot2_20250408_1511",
        "output_base": "MFM300_clen_0.297x1",
        "threads": 24,
        "max_radius": 0,
        "step": 1,
        "peakfinder_method": "cxi",   # or "peakfinder9" or "peakfinder8"
        "peakfinder_params": [],
        "advanced_flags": [],
        "other_flags": [
            "--min-peaks=50",
            "--tolerance=10,10,10,5",
            "--xgandalf-sampling-pitch=5",
            "--xgandalf-grad-desc-iterations=1",
            "--xgandalf-tolerance=0.02",
            "--int-radius=2,5,10",
            "--no-revalidate",
            "--no-half-pixel-shift",
            "--no-refine",
            "--no-non-hits-in-stream"
        ],
        # 2) The overrides
        "override_wavelength": 0.019687*1,
        "override_adu": None,
        "override_clen": 0.297/1,
        # "override_clen": 0.295/0.85,
        "override_res": None,
        "override_corner_x": None,
        "override_corner_y": None,
    }

    # We'll let you loop, so you can run multiple times without re-entering everything.
    while True:
        print("\n==========================================")
        print("   Current indexing parameters:")
        print("==========================================\n")
        print(f" Geometry File: {params['geom_file']}")
        print(f" Cell File:     {params['cell_file']}")
        print(f" Input Folder:  {params['input_folder']}")
        print(f" Output Base:   {params['output_base']}")
        print(f" Threads:       {params['threads']}")
        print(f" Max Radius:    {params['max_radius']}")
        print(f" Step:          {params['step']}")
        print(f" Peakfinder:    {params['peakfinder_method']}")
        print(f" Other flags:   {params['other_flags']}")
        
        # 3) Parse geometry file to see what's currently in it
        geom_values = parse_geometry_file(params["geom_file"])
        
        # 4) Prompt to override geometry parameters, showing geometry’s value
        params["override_wavelength"] = prompt_float_override(
            "wavelength", geom_values["wavelength"], params["override_wavelength"]
        )
        params["override_adu"] = prompt_float_override(
            "adu_per_photon", geom_values["adu_per_photon"], params["override_adu"]
        )
        params["override_clen"] = prompt_float_override(
            "clen", geom_values["clen"], params["override_clen"]
        )
        params["override_res"] = prompt_float_override(
            "res", geom_values["res"], params["override_res"]
        )
        params["override_corner_x"] = prompt_float_override(
            "p0/corner_x", geom_values["corner_x"], params["override_corner_x"]
        )
        params["override_corner_y"] = prompt_float_override(
            "p0/corner_y", geom_values["corner_y"], params["override_corner_y"]
        )

        print("\n=== Geometry Overrides Now ===")
        for k in ["override_wavelength","override_adu","override_clen","override_res","override_corner_x","override_corner_y"]:
            print(f"  {k}: {params[k]}")
        print()

        # Quick checks
        if not os.path.isfile(params["geom_file"]):
            print(f"ERROR: Geometry file not found: {params['geom_file']}")
        if not os.path.isfile(params["cell_file"]):
            print(f"ERROR: Cell file not found: {params['cell_file']}")
        if not os.path.isdir(params["input_folder"]):
            print(f"ERROR: Input folder not found: {params['input_folder']}")

        # 5) Ask user if we should run with these parameters now
        do_run = input("Run indexing now? (y/n) [y] ").strip().lower()
        if do_run == "" or do_run == "y":
            # Combine flags
            method_defaults = {
                "cxi": ["--peaks=cxi"],
                "peakfinder9": [
                    "--peaks=peakfinder9",
                    "--min-snr=1",
                    "--min-snr-peak-pix=6",
                    "--min-sig=9",
                    "--min-peak-over-neighbour=5",
                    "--local-bg-radius=5"
                ],
                "peakfinder8": [
                    "--peaks=peakfinder8",
                    "--threshold=45",
                    "--min-snr=3",
                    "--min-pix-count=3",
                    "--max-pix-count=500",
                    "--local-bg-radius=9",
                    "--min-res=30",
                    "--max-res=500"
                ]
            }
            combined_flags = list(method_defaults.get(params["peakfinder_method"], []))
            combined_flags.extend(params["peakfinder_params"])
            combined_flags.extend(params["advanced_flags"])
            combined_flags.extend(params["other_flags"])
            combined_flags.extend(INDEXING_FLAGS)

            # Check if we have any geometry overrides
            need_override = any([
                params["override_wavelength"] is not None,
                params["override_adu"] is not None,
                params["override_clen"] is not None,
                params["override_res"] is not None,
                params["override_corner_x"] is not None,
                params["override_corner_y"] is not None
            ])

            if need_override:
                try:
                    updated_geom_file = create_temp_geometry(
                        params["geom_file"],
                        wavelength=params["override_wavelength"],
                        adu_per_photon=params["override_adu"],
                        clen=params["override_clen"],
                        res=params["override_res"],
                        corner_x=params["override_corner_x"],
                        corner_y=params["override_corner_y"]
                    )
                    geom_to_use = updated_geom_file
                    print(f"Using overridden geometry file: {geom_to_use}")
                except Exception as exc:
                    print("ERROR creating temporary geometry file:", exc)
                    continue
            else:
                geom_to_use = params["geom_file"]

            print("\n=== Starting gandalf_iterator ===")
            print("Geometry File:", geom_to_use)
            print("Cell File:", params["cell_file"])
            print("Input Folder:", params["input_folder"])
            print("Output Base:", params["output_base"])
            print("Threads:", params["threads"])
            print("Max Radius:", params["max_radius"])
            print("Step:", params["step"])
            print("Combined Flags:", combined_flags)
            print("==================================\n")

            try:
                gandalf_iterator(
                    geom_to_use,
                    params["cell_file"],
                    params["input_folder"],
                    params["output_base"],
                    params["threads"],
                    max_radius=params["max_radius"],
                    step=params["step"],
                    extra_flags=combined_flags
                )
            except KeyboardInterrupt:
                print("\nIndexing interrupted by user (Ctrl-C).")
            except Exception as e:
                print("\nERROR during indexing:", e)
        else:
            print("Skipping run...")

        again = input("Do you want to loop again (edit overrides / re-run)? (y/n) [n] ").strip().lower()
        if again != "y":
            print("Exiting.")
            break


if __name__ == "__main__":
    main()
