"""
plot_indexing_rate.py
~~~~~~~~~~~~~~~~~~~~~
High-resolution 3-D surface + 2-D heat-map visualisation of indexing
rate, tailored for poster-sized outputs but safe to embed in a Qt GUI.

Usage
-----
>>> from plot_indexing_rate import plot_indexing_rate
>>> fig = plot_indexing_rate("/path/to/streams",
...                          save_path="indexing_rate.png")  # 300 dpi PNG
>>> # or just display inside your Qt canvas: fig = plot_indexing_rate(dir)

Matplotlib ≥ 3.6 will use the `roll` argument for a perfect 90 ° CCW
rotation.  Older versions fall back to `invert_xaxis()`, producing the
same visual orientation.
"""

from __future__ import annotations

import glob
import os
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import tri
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 – side-effect import


def plot_indexing_rate(
    folder_path: str,
    *,
    title: str = "Indexing rate vs beam shift",
    dpi: int = 300,
    scatter_points: bool = False,
    save_path: Optional[str] = None,
    cmap: str | mpl.colors.Colormap = "viridis",
) -> mpl.figure.Figure:
    """
    Create a 3-D surface + square 2-D heat-map of indexing rate.

    Parameters
    ----------
    folder_path
        Directory containing ``*.stream`` files named “…_<x>_<y>.stream”.
    title
        Main figure title.
    dpi
        Figure resolution (poster-ready ≥ 300).
    scatter_points
        Overlay raw (x, y) points on the heat-map.
    save_path
        If given, figure is saved at *dpi* and closed instead of shown.
    cmap
        Colormap shared by both panels.

    Returns
    -------
    matplotlib.figure.Figure
        The created figure (convenient for embedding in Qt widgets).
    """
    # ------------------------------------------------------------------ #
    # 1 .  Parse *.stream files
    # ------------------------------------------------------------------ #
    pattern = os.path.join(folder_path, "*.stream")
    records: list[tuple[float, float, float]] = []

    for path in glob.glob(pattern):
        base = os.path.splitext(os.path.basename(path))[0]
        try:
            x, y = map(float, base.rsplit("_", 2)[-2:])
        except ValueError:
            continue  # ignore files not following “…_<x>_<y>.stream”

        hits = tots = 0
        with open(path) as fh:
            for line in fh:
                if line.startswith("num_reflections"):
                    hits += 1
                elif line.startswith("num_peaks"):
                    tots += 1
        perc = 100 * hits / tots if tots else 0
        records.append((x, y, perc))

    if not records:
        raise RuntimeError(f"No valid *.stream files found in {folder_path!r}")

    df = pd.DataFrame(records, columns=["x", "y", "rate"])

    # ------------------------------------------------------------------ #
    # 2 .  Poster-friendly styling context
    # ------------------------------------------------------------------ #
    with mpl.rc_context(
        {
            "figure.dpi": dpi,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "font.size": 12,
            "axes.linewidth": 1.2,
            "savefig.bbox": "tight",
        }
    ):
        fig = plt.figure(figsize=(12, 5))
        gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.30)

        cmap_obj = plt.get_cmap(cmap)
        norm = mpl.colors.Normalize(df.rate.min(), df.rate.max())
        tri_obj = tri.Triangulation(df.x, df.y)

        # ----------------------- 3-D surface panel ---------------------- #
        ax3d = fig.add_subplot(gs[0], projection="3d")
        surf = ax3d.plot_trisurf(
            tri_obj,
            df.rate,
            cmap=cmap_obj,
            norm=norm,
            edgecolor="none",
            linewidth=0.1,
            antialiased=True,
        )
        
        # ax3d.invert_xaxis()              # visual equivalent fallback
        
        # 90° counter-clockwise rotation in the x-y plane
        ax3d.view_init(azim=ax3d.azim + 90)      # keep current elevation

        ax3d.set(
            xlabel="X shift / px",
            ylabel="Y shift / px",
            # zlabel="Indexing rate / %",
            zlabel=" ",
            title="3-D rate surface",
        )

        for axis in (ax3d.xaxis, ax3d.yaxis, ax3d.zaxis):
            axis.pane.set_alpha(0.10)

        cb3d = fig.colorbar(surf, ax=ax3d, shrink=0.85, pad=0.08, aspect=18)
        cb3d.set_label("Indexing rate / %")

        # ----------------------- 2-D heat-map panel --------------------- #
        ax2d = fig.add_subplot(gs[1])

        xi = np.linspace(df.x.min(), df.x.max(), 200)
        yi = np.linspace(df.y.min(), df.y.max(), 200)
        Xi, Yi = np.meshgrid(xi, yi)

        # Interpolate onto grid (SciPy preferred; fallback to mpl)
        try:
            from scipy.interpolate import griddata

            Zi = griddata(
                points=df[["x", "y"]].values,
                values=df["rate"].values,
                xi=(Xi, Yi),
                method="linear",
            )
        except Exception:
            interp = tri.LinearTriInterpolator(tri_obj, df.rate)
            Zi = interp(Xi, Yi)

        hm = ax2d.pcolormesh(Xi, Yi, Zi, cmap=cmap_obj, norm=norm, shading="auto")

        # ✨ enforce a square aspect (1 : 1 data units)
        ax2d.set_aspect("equal", adjustable="box")

        ct = ax2d.contour(
            Xi, Yi, Zi, levels=8, colors="k", linewidths=0.4, alpha=0.6
        )
        ax2d.clabel(ct, fmt="%.0f", fontsize=8)

        if scatter_points:
            ax2d.scatter(
                df.x, df.y, s=15, c="white", edgecolors="black", zorder=3
            )

        ax2d.set(
            xlabel="X shift / px",
            ylabel="Y shift / px",
            title="Heat-map (top view)",
        )

        fig.colorbar(hm, ax=ax2d, shrink=0.95, pad=0.04).set_label(
            "Indexing rate / %"
        )

        # -------------------------- layout / output -------------------- #
        fig.suptitle(title, y=0.98, fontsize=18)
        plt.tight_layout(rect=[0, 0, 1, 0.97])

        if save_path:
            fig.savefig(save_path, dpi=dpi)
            plt.close(fig)
        else:
            plt.show()

    return fig
