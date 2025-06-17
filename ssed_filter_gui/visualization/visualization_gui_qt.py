#!/usr/bin/env python3
"""
visualization_gui_qt.py – Indexing‑rate visualizer (PyQt 6)

Qt 6 replacement for the original Tkinter helper that inspects a folder of
Gandalf *.stream* files (with out‑of‑center filenames) and plots the indexing
rate vs. x/y shift.  All heavy lifting (parsing + matplotlib figures) remains
in `visualization.indexing_histograms.plot_indexing_rate`; this script just
provides a more modern, resizable GUI.

Run with:
    python visualization_gui_qt.py

Requirements:
    pip install pyqt6 matplotlib   # (+ your existing project libs)

If you prefer LGPL bindings substitute `PySide6` – the widget API is identical.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ‑‑ project‑specific import: remains unchanged
from indexing_histograms import plot_indexing_rate


class VisualizerWindow(QWidget):
    """Main window for selecting a *.stream* folder and launching plots."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Indexing‑rate Visualizer")
        self.setMinimumSize(640, 360)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        desc = (
            "Select a folder with indexing output *.stream* files produced by\n"
            "Gandalf runs with shifted centers.  When you click *Generate\n"
            "Visualizations* we will:\n\n"
            "  • Parse x/y shift from filenames.\n"
            "  • Compute indexing‑rate = (num_reflections / num_peaks) × 100.\n"
            "  • Show a 3‑D bar chart + 2‑D scatter/heat‑map of that rate."
        )

        desc_lbl = QLabel(desc, wordWrap=True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        desc_lbl.setFont(QFont("SansSerif", 10))

        # ── folder chooser row ───────────────────────────────────────────
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Stream File Folder:")
        self.folder_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)

        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(browse_btn)

        # ── run button ───────────────────────────────────────────────────
        run_btn = QPushButton("Generate Visualizations")
        run_btn.setStyleSheet("QPushButton { background-color: lightblue; }")
        run_btn.clicked.connect(self._generate_plots)

        # ── main layout ──────────────────────────────────────────────────
        vbox = QVBoxLayout(self)
        vbox.addWidget(desc_lbl)
        vbox.addLayout(folder_layout)
        vbox.addStretch(1)
        vbox.addWidget(run_btn)

    # ------------------------------------------------------------------
    # Slots / callbacks
    # ------------------------------------------------------------------
    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder", os.getcwd())
        if path:
            self.folder_edit.setText(path)

    def _generate_plots(self) -> None:
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.critical(self, "Error", "Please select an output folder.")
            return
        if not os.path.isdir(folder):
            QMessageBox.critical(self, "Error", f"Folder does not exist:\n{folder}")
            return

        print("Generating visualizations for output folder:", folder)
        try:
            plot_indexing_rate(folder, save_path=os.path.join(folder, "indexing_rate_plots.png"))
            print("Visualization completed successfully.")
        except Exception as exc:
            print("Error during visualization:", exc)
            QMessageBox.critical(self, "Error", f"Visualization failed:\n{exc}")


# ----------------------------------------------------------------------
# entry‑point
# ----------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> None:  # pragma: no cover
    app = QApplication(argv or sys.argv)
    win = VisualizerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
