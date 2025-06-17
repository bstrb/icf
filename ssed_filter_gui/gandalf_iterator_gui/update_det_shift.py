#!/usr/bin/env python3
"""update_det_shift_qt.py – update *det_shift_[xy]_mm* in an HDF5 file

Adds **verbose debugging** so you can trace every step of the calculation when
`--debug` is supplied.  Run head‑less or via the PyQt 6 GUI.

```bash
# normal
python update_det_shift_qt.py data.h5 geom.geom

# verbose
python update_det_shift_qt.py data.h5 geom.geom --debug

# GUI (checkbox toggles debug)
python update_det_shift_qt.py --gui
```
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence, Tuple

import h5py
import numpy as np

# ----------------------------------------------------------------------------
# Helper utils
# ----------------------------------------------------------------------------
_FLOAT_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _dprint(enabled: bool, *msg) -> None:  # simple debug‑print wrapper
    if enabled:
        print("[debug]", *msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Geometry parsing
# ---------------------------------------------------------------------------

def parse_geom(path: Path | str, *, dbg: bool = False) -> Tuple[float, int]:
    """Return *(pixels_per_unit, frame_size_px)* from a CrystFEL *.geom* file.

    Robust against panel names like ``p0/`` which contain digits: we look
    **after the equal sign** so we don't accidentally capture the leading *0*
    in "p0/min_ss" etc.
    """

    ppm = min_ss = max_ss = min_fs = max_fs = None
    with open(path, "r", encoding="utf-8") as fh:
        for ln in fh:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue

            # Split once at '=' to avoid matching the digit in "p0" / "p1" etc.
            key, sep, val = s.partition("=")
            if not sep:
                continue  # no '=' on this line
            key = key.strip()
            val = val.strip()

            if key == "res":
                ppm = float(val.split()[0])
            elif key.endswith("min_ss"):
                min_ss = int(val.split()[0])
            elif key.endswith("max_ss"):
                max_ss = int(val.split()[0])
            elif key.endswith("min_fs"):
                min_fs = int(val.split()[0])
            elif key.endswith("max_fs"):
                max_fs = int(val.split()[0])

    if None in (ppm, min_ss, max_ss, min_fs, max_fs):
        raise ValueError(f"Missing required keys in {path}")

    frame_ss = max_ss - min_ss + 1
    frame_fs = max_fs - min_fs + 1
    if frame_ss != frame_fs:
        _dprint(dbg, "Non‑square panel detected (ss≠fs); using ss side only")
    frame_px = frame_ss

    _dprint(
        dbg,
        f"geom: res={ppm}, min_ss={min_ss}, max_ss={max_ss}, "
        f"min_fs={min_fs}, max_fs={max_fs}, frame_px={frame_px}",
    )
    return ppm, frame_px


# ---------------------------------------------------------------------------
# Centre reading
# ---------------------------------------------------------------------------

def read_centres(h5_path: Path | str, *, dbg: bool = False):
    """Return *(cx, cy)* arrays from entry/data/center_*"""
    with h5py.File(h5_path, "r") as f:
        cx = f["entry/data/center_x"][()]
        cy = f["entry/data/center_y"][()]

    cx = np.asarray(cx, dtype=np.float64).reshape(-1)
    cy = np.asarray(cy, dtype=np.float64).reshape(-1)
    if cx.shape != cy.shape:
        raise ValueError("center_x and center_y have different lengths")

    _dprint(dbg, f"centres: n={len(cx)}, cx[0..3]={cx[:3]}, cy[0..3]={cy[:3]}")
    return cx, cy


# ---------------------------------------------------------------------------
# Shift calculation
# ---------------------------------------------------------------------------

def calculate_shifts_mm(
    cx: Sequence[float],
    cy: Sequence[float],
    pixels_per_unit: float,
    frame_px: int,
    *,
    dbg: bool = False,
):
    """Convert pixel offsets → millimetres."""
    cx = np.asarray(cx, dtype=np.float64)
    cy = np.asarray(cy, dtype=np.float64)

    presumed = frame_px / 2.0  # geometric centre
    _dprint(dbg, f"presumed centre (px) = {presumed}")

    if pixels_per_unit > 500:  # px per metre
        px_to_mm = 1000.0 / pixels_per_unit
        unit_msg = "px/m → *1000 / res*"
    else:  # px per mm
        px_to_mm = 1.0 / pixels_per_unit
        unit_msg = "px/mm → *1 / res*"
    _dprint(dbg, f"conversion factor px→mm = {px_to_mm}  ({unit_msg})")

    diff_x = cx - presumed
    diff_y = cy - presumed
    dx_mm  = - diff_x * px_to_mm
    dy_mm  = - diff_y * px_to_mm

    _dprint(dbg, f"dx[0..3] px = {diff_x[:3]},  mm = {dx_mm[:3]}")
    _dprint(dbg, f"dy[0..3] px = {diff_y[:3]},  mm = {dy_mm[:3]}")

    return dx_mm, dy_mm


# ---------------------------------------------------------------------------
# HDF5 writing
# ---------------------------------------------------------------------------

def write_shifts(h5_path: Path | str, dx_mm, dy_mm, *, dbg: bool = False):
    with h5py.File(h5_path, "r+") as f:
        for name, arr in {
            "entry/data/det_shift_x_mm": np.asarray(dx_mm, dtype=np.float64),
            "entry/data/det_shift_y_mm": np.asarray(dy_mm, dtype=np.float64),
        }.items():
            if name in f:
                del f[name]
            f.create_dataset(name, data=arr, dtype="float64")
            _dprint(dbg, f"wrote dataset {name}  shape={arr.shape}")


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------

def cli(h5file: Path, geomfile: Path, *, debug: bool):
    ppm, frame_px       = parse_geom(geomfile, dbg=debug)
    cx, cy              = read_centres(h5file, dbg=debug)
    dx_mm, dy_mm        = calculate_shifts_mm(cx, cy, ppm, frame_px, dbg=debug)
    write_shifts(h5file, dx_mm, dy_mm, dbg=debug)

    print(
        f"Updated {h5file}: det_shift_x_mm/det_shift_y_mm ← {len(dx_mm)} vals "
        f"(range {dx_mm.min():.3f}…{dx_mm.max():.3f} mm)"
    )


# ---------------------------------------------------------------------------
# Optional PyQt6 GUI
# ---------------------------------------------------------------------------

def gui():  # pragma: no cover
    try:
        from PyQt6 import QtWidgets
    except ModuleNotFoundError:
        sys.exit("PyQt6 not installed – run `pip install pyqt6` or use CLI mode.")

    class Win(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Update det_shift_*_mm")
            self.resize(520, 180)
            lay = QtWidgets.QVBoxLayout(self)

            self.h5_edit   = QtWidgets.QLineEdit()
            self.geom_edit = QtWidgets.QLineEdit()
            self.debug_chk = QtWidgets.QCheckBox("Verbose debug output")

            for label, edit, filt in (
                ("HDF5 file",   self.h5_edit,   "HDF5 (*.h5 *.hdf5)"),
                ("Geometry file", self.geom_edit, "*.geom"),
            ):
                row = QtWidgets.QHBoxLayout()
                row.addWidget(QtWidgets.QLabel(label))
                row.addWidget(edit, 1)
                btn = QtWidgets.QPushButton("Browse…")
                row.addWidget(btn)
                lay.addLayout(row)

                def pick(*_, e=edit, flt=filt):
                    fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file", str(Path.cwd()), flt)
                    if fn:
                        e.setText(fn)
                btn.clicked.connect(pick)  # type: ignore[arg-type]

            lay.addWidget(self.debug_chk)
            run_btn = QtWidgets.QPushButton("Update shifts")
            lay.addWidget(run_btn)
            output = QtWidgets.QTextEdit(readOnly=True)
            lay.addWidget(output, 1)

            def run():
                h5  = Path(self.h5_edit.text().strip())
                geo = Path(self.geom_edit.text().strip())
                if not (h5.is_file() and geo.is_file()):
                    QtWidgets.QMessageBox.critical(self, "Error", "Select valid files")
                    return
                try:
                    cli(h5, geo, debug=self.debug_chk.isChecked())
                    output.append(f"✔ {h5.name} updated\n")
                except Exception as e:  # noqa: BLE001
                    QtWidgets.QMessageBox.critical(self, "Failure", str(e))

            run_btn.clicked.connect(run)  # type: ignore[arg-type]

    app = QtWidgets.QApplication(sys.argv[1:])
    w   = Win()
    w.show()
    app.exec()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Update det_shift_*_mm in HDF5 file")
    p.add_argument("h5file", type=Path, nargs="?", help="Input .h5 file")
    p.add_argument("geomfile", type=Path, nargs="?", help="CrystFEL .geom file")
    p.add_argument("--debug", action="store_true", help="Verbose prints to stderr")
    p.add_argument("--gui", action="store_true", help="Launch PyQt6 GUI")
    args = p.parse_args()

    if args.gui or args.h5file is None or args.geomfile is None:
        gui()
    else:
        cli(args.h5file, args.geomfile, debug=args.debug)
