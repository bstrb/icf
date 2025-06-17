#!/usr/bin/env python3
"""
Generate three publication-quality heat-maps of dynamical scattering
electron-diffraction metrics from a single CSV.

∙ Keeps the original hard-coded `csv_path`
∙ Adds one-line “STYLE” settings for figure & text sizing
∙ Uses Matplotlib’s constrained-layout engine for clean spacing
∙ Saves a high-resolution PNG you can drag straight onto a poster
"""
# ──────────────────────────────────────────────────────────────
# 0. Style settings –- tweak here only
# ──────────────────────────────────────────────────────────────
FIG_SIZE       = (18, 6)   # inches  – overall figure (width, height)
DPI            = 400       # dots per inch for PNG export
CMAP           = "viridis" # any Matplotlib colormap
TITLE_FS       = 18        # subplot title font-size
LABEL_FS       = 14        # axis-label font-size
TICK_FS        = 12        # tick-label font-size
CBAR_FS        = 12        # colour-bar tick-label font-size
SUPERTITLE_FS  = 20        # big title on top; set None to disable

# ──────────────────────────────────────────────────────────────
# 1. Load and tidy the CSV (identical to your logic)
# ──────────────────────────────────────────────────────────────
import os, re, numpy as np, pandas as pd, matplotlib.pyplot as plt

csv_path = (
    "/home/bubl3932/files/MFM300_VIII/"
    "MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524/"
    "MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524_2038/"
    "xgandalf_iterations_max_radius_1.0_step_0.1/normalized_metrics.csv"
)

df = pd.read_csv(csv_path)
df = df[~df["stream_file"].str.startswith("Event number:")].copy()

def extract_coords(fname):
    nums = re.findall(r"(-?\d+(?:\.\d+)?)", os.path.basename(fname))
    return (float(nums[-2]), float(nums[-1])) if len(nums) >= 2 else (np.nan, np.nan)

df[["x", "y"]] = df["stream_file"].apply(lambda s: pd.Series(extract_coords(s)))
df.dropna(subset=["x", "y"], inplace=True)

# ──────────────────────────────────────────────────────────────
# 2. Plot
# ──────────────────────────────────────────────────────────────
metrics = ["weighted_rmsd", "length_deviation", "angle_deviation"]
titles  = ["Mean weighted RMSD", "Mean length deviation", "Mean angle deviation"]

fig, axes = plt.subplots(
    nrows=1, ncols=3, figsize=FIG_SIZE, dpi=DPI, constrained_layout=True
)

for ax, metric, title in zip(axes, metrics, titles):
    # pivot to x-by-y grid of mean metric values
    z = (
        df.groupby(["x", "y"])[metric]
          .mean()
          .reset_index()
          .pivot(index="y", columns="x", values=metric)
          .sort_index()
          .sort_index(axis=1)
    )
    im = ax.imshow(
        z.values,
        origin="lower",
        cmap=CMAP,
        extent=[z.columns.min(), z.columns.max(), z.index.min(), z.index.max()],
        aspect="equal"  # squares look better on posters
    )

    # axis formatting
    ax.set_title(title, fontsize=TITLE_FS, pad=8)
    ax.set_xlabel("x shift (pixels)", fontsize=LABEL_FS)
    ax.set_ylabel("y shift (pixels)", fontsize=LABEL_FS)
    ax.tick_params(labelsize=TICK_FS)

    # colour-bar
    cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cbar.ax.tick_params(labelsize=CBAR_FS)

# optional overall caption
if SUPERTITLE_FS:
    fig.suptitle("Indexing Quality Metrics",
                 fontsize=SUPERTITLE_FS, y=1.03)

# save and show
out_path = os.path.join(os.path.dirname(csv_path), "iqm_mean_heatmap.png")
fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
plt.show()
print(f"Saved high-resolution image → {out_path}")