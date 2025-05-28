#!/usr/bin/env python3
"""
ssed_calc_metrics_qt.py – Metrics Processing GUI (PyQt 6)

A drop‑in Qt 6 replacement for *ssed_calc_metrics.py*.  The UI lets the user
pick a folder containing `.stream` files, adjust WRMSD / indexing tolerances,
and run `process_indexing_metrics`.  All heavy‑lifting remains in
`calc_metrics.process_indexing_metrics` – only the front‑end is new.

Usage
-----
```bash
pip install pyqt6   # or pyside6
python ssed_calc_metrics_qt.py
```

If you run on a head‑less node without `$DISPLAY`, set
`QT_QPA_PLATFORM=offscreen` or start under `xvfb-run`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
    QDoubleSpinBox,
)

# ──────────────────────────────────────────────────────────────────────────────
# domain logic (unchanged)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from calc_metrics.process_indexing_metrics import process_indexing_metrics  # type: ignore
except ModuleNotFoundError as exc:  # helpful error if module is missing
    raise ModuleNotFoundError("calc_metrics.process_indexing_metrics not found – check PYTHONPATH") from exc


# ──────────────────────────────────────────────────────────────────────────────
# Qt 6 main window
# ──────────────────────────────────────────────────────────────────────────────

class MetricsWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Metrics Processing GUI (Qt 6)")
        self.setMinimumSize(600, 300)

        layout = QGridLayout(self)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)
        row = 0

        # Explanation (multiline label with word‑wrap)
        explanation = (
            "Processes stream files from multiple indexing iterations to evaluate key metrics on frame quality.\n\n"
            "Evaluated metrics: weighted RMSD, fraction outliers, length & angle deviation, peak ratio, % indexed.\n\n"
            "Parameters:\n  • WRMSD tolerance (σ units) – default 2.0\n  • Indexing tolerance (pixels) – default 4.0"
        )
        expl_label = QLabel(explanation)
        expl_label.setWordWrap(True)
        expl_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(expl_label, row, 0, 1, 4)
        row += 1

        # Folder selector
        self.folder_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)

        layout.addWidget(QLabel("Stream file folder:"), row, 0)
        layout.addWidget(self.folder_edit, row, 1, 1, 2)
        layout.addWidget(browse_btn, row, 3)
        row += 1

        # Tolerances
        self.wrmsd_spin = QDoubleSpinBox()
        self.wrmsd_spin.setRange(0.0, 100.0)
        self.wrmsd_spin.setDecimals(2)
        self.wrmsd_spin.setValue(2.0)

        self.idx_tol_spin = QDoubleSpinBox()
        self.idx_tol_spin.setRange(0.0, 100.0)
        self.idx_tol_spin.setDecimals(2)
        self.idx_tol_spin.setValue(4.0)

        layout.addWidget(QLabel("WRMSD tolerance:"), row, 0)
        layout.addWidget(self.wrmsd_spin, row, 1)
        layout.addWidget(QLabel("Indexing tolerance:"), row, 2)
        layout.addWidget(self.idx_tol_spin, row, 3)
        row += 1

        # Process button
        process_btn = QPushButton("Process metrics")
        process_btn.setStyleSheet("background-color: lightblue;")
        process_btn.clicked.connect(self._process_metrics)
        layout.addWidget(process_btn, row, 0, 1, 4)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 0)

    # ──────────────────────────────────────────────────────────────────────
    # slots
    # ──────────────────────────────────────────────────────────────────────

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select stream file folder", str(Path.cwd()))
        if path:
            self.folder_edit.setText(path)

    def _process_metrics(self) -> None:
        folder = self.folder_edit.text().strip()
        if not folder or not Path(folder).is_dir():
            QMessageBox.critical(self, "Error", "Please select a valid stream file folder.")
            return

        wrmsd_tol = float(self.wrmsd_spin.value())
        idx_tol = float(self.idx_tol_spin.value())

        print("Processing metrics for", folder)
        print("  WRMSD tolerance:", wrmsd_tol)
        print("  Indexing tolerance:", idx_tol)
        try:
            process_indexing_metrics(folder, wrmsd_tolerance=wrmsd_tol, indexing_tolerance=idx_tol)
            QMessageBox.information(self, "Done", "Metrics processed successfully – see console for details.")
        except Exception as exc:
            print("Error while processing metrics:", exc)
            QMessageBox.critical(self, "Error", f"An error occurred:\n{exc}")


# ──────────────────────────────────────────────────────────────────────────────
# entry‑point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # fallback to offscreen platform if no display (HPC / CI)
    if not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QApplication(sys.argv)
    win = MetricsWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
