#!/usr/bin/env python3
"""
Auto-grid heat-maps of dynamical-scattering metrics
→ Works head-less (Agg backend), no column renaming tricks.
→ List as many metrics as you like; figure size adapts.
→ Saves a 400 dpi PNG next to the CSV.
"""

# ── 0. Head-less backend & style knobs ─────────────────────────
import matplotlib
matplotlib.use("Agg")          # no Qt / Wayland needed
import math, os, re, sys
import numpy as np, pandas as pd, matplotlib.pyplot as plt

DPI, CMAP = 400, "viridis"     # PNG resolution & colour map
TITLE_FS, LABEL_FS, TICK_FS, CBAR_FS = 18, 14, 12, 12
SUPERTITLE_FS, MAX_COLS = 22, 3   # wrap grid after N columns
COL_W, ROW_H = 6, 5               # inches per subplot
# ───────────────────────────────────────────────────────────────

# 1 ── CSV path & loading  (same as your working script) ───────
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

# 2 ── Tell the script which metrics to plot ───────────────────
metrics = [
    "weighted_rmsd", "length_deviation", "angle_deviation",
    "fraction_outliers", "peak_ratio", "percentage_unindexed",
]
titles  = [
    "Mean weighted RMSD", "Mean length deviation", "Mean angle deviation",
    "Fraction of outliers", "Peak ratio", "Percentage unindexed",
]

# 3 ── Verify that the columns exist & contain numbers ─────────
good_metrics, good_titles = [], []
for m, t in zip(metrics, titles):
    if m not in df.columns:
        print(f"⚠︎  Column ‘{m}’ not found → skipped", file=sys.stderr)
        continue
    series = pd.to_numeric(df[m], errors="coerce")
    if series.notna().any():
        df[m] = series           # ensure numeric dtype
        good_metrics.append(m)
        good_titles.append(t)
    else:
        print(f"⚠︎  Column ‘{m}’ is all-NaN → skipped", file=sys.stderr)

if not good_metrics:
    sys.exit("Nothing to plot – no listed metric contains finite data.")

# 4 ── Adaptive grid size ──────────────────────────────────────
n_cols  = min(MAX_COLS, len(good_metrics))
n_rows  = math.ceil(len(good_metrics) / n_cols)
figsize = (COL_W * n_cols, ROW_H * n_rows)

fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, dpi=DPI,
                         constrained_layout=True)
axes = np.atleast_1d(axes).ravel()

# 5 ── Plot loop ───────────────────────────────────────────────
for ax, metric, title in zip(axes, good_metrics, good_titles):
    z = (
        df.groupby(["x", "y"])[metric]
          .mean()
          .reset_index()
          .pivot(index="y", columns="x", values=metric)
          .dropna(how="all").dropna(how="all", axis=1)
    )

    im = ax.imshow(
        z.values, cmap=CMAP, origin="lower", aspect="equal",
        extent=[z.columns.min(), z.columns.max(),
                z.index.min(), z.index.max()]
    )
    ax.set_title(title, fontsize=TITLE_FS, pad=8)
    ax.set_xlabel("x shift (pixels)", fontsize=LABEL_FS)
    ax.set_ylabel("y shift (pixels)", fontsize=LABEL_FS)
    ax.tick_params(labelsize=TICK_FS)

    cb = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
    cb.ax.tick_params(labelsize=CBAR_FS)

# hide any extra blank axes (if metrics < rows*cols)
for ax in axes[len(good_metrics):]:
    ax.set_visible(False)

if SUPERTITLE_FS:
    fig.suptitle("Indexing-quality metrics (mean per x-y shift)",
                 fontsize=SUPERTITLE_FS, y=1.02)

# 6 ── Save & done ─────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(csv_path), "iqm_mean_heatmaps_2.png")
fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
print(f"✔  Saved high-resolution image → {out_path}")
