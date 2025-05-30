#!/usr/bin/env python3
"""
update_det_shift.py

Update detector-shift datasets in an HDF5 file (.h5) using the detector-centre
coordinates stored in that file and the pixel resolution / frame-size
information taken from a CrystFEL .geom file.

Usage
-----
python update_det_shift.py <data.h5> <geometry.geom>
"""

import argparse
import h5py
import re
import sys
from pathlib import Path


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
_FLOAT = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

def _parse_geom(path):
    """Return (pixels_per_m, frame_size) read from a .geom file."""
    ppm = min_ss = max_ss = min_fs = max_fs = None
    with open(path, "r") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("res"):
                ppm = float(_FLOAT.search(s).group())
            elif s.startswith("p0/min_ss"):
                min_ss = int(_FLOAT.search(s).group())
            elif s.startswith("p0/max_ss"):
                max_ss = int(_FLOAT.search(s).group())
            elif s.startswith("p0/min_fs"):
                min_fs = int(_FLOAT.search(s).group())
            elif s.startswith("p0/max_fs"):
                max_fs = int(_FLOAT.search(s).group())

    if None in (ppm, min_ss, max_ss, min_fs, max_fs):
        raise ValueError(f"Missing required keys in {path}")

    fs_ss = max_ss - min_ss + 1
    fs_fs = max_fs - min_fs + 1
    if fs_ss != fs_fs:
        raise ValueError(
            f"Geometry describes a rectangular detector "
            f"(ss={fs_ss}, fs={fs_fs}).  "
            f"Adapt script if this is intentional."
        )

    return ppm, fs_ss


def _read_centres(h5_path):
    """Return (center_x, center_y) from entry/data/center_* in the HDF5 file."""
    with h5py.File(h5_path, "r") as f:
        cx = f["entry/data/center_x"][()]
        cy = f["entry/data/center_y"][()]
    # accept scalar or 1-element arrays
    cx = float(cx[0] if hasattr(cx, "__len__") else cx)
    cy = float(cy[0] if hasattr(cy, "__len__") else cy)
    return cx, cy


def _write_shifts(h5_path, dx_mm, dy_mm):
    """(Re)create det_shift_*_mm datasets with the supplied values."""
    with h5py.File(h5_path, "r+") as f:
        for name, val in {
            "entry/data/det_shift_x_mm": dx_mm,
            "entry/data/det_shift_y_mm": dy_mm,
        }.items():
            if name in f:
                del f[name]
            f.create_dataset(name, data=val, dtype="float64", maxshape=(None,))


# ----------------------------------------------------------------------
# Main routine
# ----------------------------------------------------------------------
def main(h5file, geomfile):
    ppm, frame = _parse_geom(geomfile)
    cx, cy = _read_centres(h5file)

    presumed = frame / 2.0
    dx_mm = -((cx - presumed) / ppm) * 1000.0
    dy_mm = -((cy - presumed) / ppm) * 1000.0

    _write_shifts(h5file, dx_mm, dy_mm)

    print(
        f"Updated {h5file}: det_shift_x_mm = {dx_mm:.6f}, "
        f"det_shift_y_mm = {dy_mm:.6f}"
    )


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # parser = argparse.ArgumentParser(
    #     description="Update detector-shift datasets in an HDF5 file."
    # )
    # parser.add_argument("h5file", type=Path, help="Input .h5 file")
    # parser.add_argument("geomfile", type=Path, help="Associated .geom file")
    # args = parser.parse_args()
    h5file="/home/bubl3932/files/simulations/cP_LTA/sim_003/sim.h5"
    geomfile="/home/bubl3932/files/simulations/cP_LTA/sim_003/7108314.geom"

    # if not args.h5file.exists():
    #     sys.exit(f"Error: {args.h5file} not found")
    # if not args.geomfile.exists():
    #     sys.exit(f"Error: {args.geomfile} not found")

    main(h5file, geomfile)
