import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ──────────────────────────────────────────────────────────────
# 1. Load and pre-clean the CSV
# ──────────────────────────────────────────────────────────────
csv_path = "/home/bubl3932/files/MFM300_VIII/MFM_spot3_streams/normalized_metrics.csv"
df = pd.read_csv(csv_path)

# strip the header rows that contain only "Event number: …"
df = df[~df['stream_file'].str.startswith('Event number:')].copy()

# ──────────────────────────────────────────────────────────────
# 2. Robust coordinate extraction
# ──────────────────────────────────────────────────────────────
def extract_coords(fname):
    """
    Return (x, y) from a stream filename such as
    MFM300_Al_check_0.0_-0.5.stream  →  (0.0, -0.5)

    Works with or without the .stream suffix; returns (nan, nan) if
    it cannot find two numbers.
    """
    nums = re.findall(r'(-?\d+(?:\.\d+)?)', os.path.basename(fname))
    if len(nums) >= 2:
        return float(nums[-2]), float(nums[-1])
    return np.nan, np.nan

df[['x', 'y']] = df['stream_file'].apply(lambda s: pd.Series(extract_coords(s)))
df.dropna(subset=['x', 'y'], inplace=True)

# ──────────────────────────────────────────────────────────────
# 3. Plot heat-maps of each metric
# ──────────────────────────────────────────────────────────────
metrics = [
    'weighted_rmsd', 'fraction_outliers', 'length_deviation',
    'angle_deviation', 'peak_ratio', 'percentage_unindexed'
]

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

for ax, metric in zip(axes, metrics):
    # median value at each (x, y) location
    z = (
        df.groupby(['x', 'y'])[metric]
          .median()
          .reset_index()
          .pivot(index='y', columns='x', values=metric)
          .sort_index()            # y low → bottom
          .sort_index(axis=1)      # x low → left
    )

    im = ax.imshow(
        z.values,
        origin='lower',
        aspect='auto',
        extent=[
            z.columns.min(), z.columns.max(),
            z.index.min(),   z.index.max()
        ]
    )

    ax.set_title(f'Median {metric}')
    ax.set_xlabel('x coordinate')
    ax.set_ylabel('y coordinate')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

plt.tight_layout()
plt.show()
