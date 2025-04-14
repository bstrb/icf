#!/usr/bin/env python3
import os
import sys
import signal
import glob
import shutil
import atexit
import tempfile

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
        lower_line = line.strip().lower()
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


def main():
    # We keep parameters in a dictionary so we can easily re-run or tweak.
    params = {
        "geom_file": "/home/bubl3932/files/MFM300_VIII/MFM300_VIII_spot2_20250408_1511/MFM.geom",
        "cell_file": "/home/bubl3932/files/MFM300_VIII/MFM300_VIII_spot2_20250408_1511/MFM.cell",
        "input_folder": "/home/bubl3932/files/MFM300_VIII/MFM300_VIII_spot2_20250408_1511",
        "output_base": "MFM300",
        "threads": 24,
        "max_radius": 0,
        "step": 1,
        "peakfinder_method": "cxi",    # or peakfinder9, peakfinder8
        "peakfinder_params": [],       # list of strings
        "advanced_flags": [],
        "other_flags": ["--min-peaks=50",
                        "--tolerance=10,10,10,5",
                        "--xgandalf-sampling-pitch=5",
                        "--xgandalf-grad-desc-iterations=1",
                        "--xgandalf-tolerance=0.02",
                        "--int-radius=2,5,10",
                        "--no-revalidate",
                        "--no-half-pixel-shift",
                        "--no-refine",
                        "--no-non-hits-in-stream"],
        # Optional geometry overrides
        "override_wavelength": None,
        "override_adu": None,
        "override_clen": None,
        "override_res": None,
        "override_corner_x": None,
        "override_corner_y": None,
    }


    # We'll do a simple loop so you can run multiple times without re-entering everything.
    # Press Ctrl+C or type 'n' to exit.

    while True:
        print("\n==========================================")
        print(" Enter or confirm the parameters below.")
        print(" (Press Enter to keep the current/previous value.)")
        print("==========================================\n")

        # Prompt user for each main parameter, reusing existing values if blank
        # Geometry file
        # val = input(f"Geometry File (.geom) [current: {params['geom_file']}]: ").strip()
        # if val:
        #     params["geom_file"] = val

        # val = input(f"Cell File (.cell) [current: {params['cell_file']}]: ").strip()
        # if val:
        #     params["cell_file"] = val

        # val = input(f"Input Folder [current: {params['input_folder']}]: ").strip()
        # if val:
        #     params["input_folder"] = val

        # val = input(f"Output Base [current: {params['output_base']}]: ").strip()
        # if val:
        #     params["output_base"] = val

        # val = input(f"Threads [current: {params['threads']}]: ").strip()
        # if val:
        #     try:
        #         params["threads"] = int(val)
        #     except:
        #         print("Invalid threads, keeping old value.")

        # val = input(f"Max Radius [current: {params['max_radius']}]: ").strip()
        # if val:
        #     try:
        #         params["max_radius"] = float(val)
        #     except:
        #         print("Invalid float, keeping old value.")

        # val = input(f"Step [current: {params['step']}]: ").strip()
        # if val:
        #     try:
        #         params["step"] = float(val)
        #     except:
        #         print("Invalid float, keeping old value.")

        # val = input(f"Peakfinder method (cxi, peakfinder9, peakfinder8) [current: {params['peakfinder_method']}]: ").strip()
        # if val:
        #     if val in ["cxi", "peakfinder9", "peakfinder8"]:
        #         params["peakfinder_method"] = val
        #     else:
        #         print("Unrecognized method, keeping old value.")

        # # We'll let user type a single line for "peakfinder_params" space-separated
        # val = input("Peakfinder params (space-separated) or blank to keep current:\n"
        #             f"Current: {params['peakfinder_params']}\n> ").strip()
        # if val:
        #     params["peakfinder_params"] = val.split()

        # val = input("Advanced flags (space-separated) or blank to keep current:\n"
        #             f"Current: {params['advanced_flags']}\n> ").strip()
        # if val:
        #     params["advanced_flags"] = val.split()

        # val = input("Other flags (space-separated) or blank to keep current:\n"
        #             f"Current: {params['other_flags']}\n> ").strip()
        # if val:
        #     params["other_flags"] = val.split()

        # Optional geometry overrides (one by one)
        # If user enters something, we store it; if blank, keep previous; if "none", we set to None
        def float_or_none(prompt, current):
            v = input(f"{prompt} [current: {current}] (enter 'none' to unset): ").strip()
            if v.lower() == "none":
                return None
            if v == "":
                return current
            try:
                return float(v)
            except:
                print("Invalid float, ignoring.")
                return current

        params["override_wavelength"] = float_or_none("Override wavelength (A)", params["override_wavelength"])
        # params["override_adu"] = float_or_none("Override adu_per_photon", params["override_adu"])
        params["override_clen"] = float_or_none("Override clen (m)", params["override_clen"])
        # params["override_res"] = float_or_none("Override res", params["override_res"])
        # params["override_corner_x"] = float_or_none("Override p0/corner_x", params["override_corner_x"])
        # params["override_corner_y"] = float_or_none("Override p0/corner_y", params["override_corner_y"])

        print("\nGot these parameters:")
        for k, v in params.items():
            print(f"  {k}: {v}")
        print()

        # Confirm all required files/folders exist (if user gave them)
        # (You can add more robust checks if you prefer.)
        if not os.path.isfile(params["geom_file"]):
            print(f"ERROR: Geometry file not found: {params['geom_file']}")
        if not os.path.isfile(params["cell_file"]):
            print(f"ERROR: Cell file not found: {params['cell_file']}")
        if not os.path.isdir(params["input_folder"]):
            print(f"ERROR: Input folder not found: {params['input_folder']}")

        # Ask user if we should run with these parameters now
        do_run = input("Run indexing now with these parameters? (y/n) [y] ").strip().lower()
        if do_run == "" or do_run == "y":
            # Build the combined flags
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

        again = input("Do you want to run or edit parameters again? (y/n) [n] ").strip().lower()
        if again != "y":
            print("Exiting.")
            break


if __name__ == "__main__":
    main()
