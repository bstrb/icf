import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the CSV file (change the filename as needed)
input_file = "/Users/xiaodong/Downloads/normalized_metrics.csv"
df = pd.read_csv(input_file)

# Remove rows with event header info
df = df[~df['stream_file'].str.startswith('Event number:')].copy()

# Function to extract x and y coordinates from stream filename.
def extract_coords(filename):
    try:
        base = filename.replace('.stream', '')
        parts = base.split('_')
        return float(parts[1]), float(parts[2])
    except Exception:
        return np.nan, np.nan

# Create 'x' and 'y' columns.
df[['x', 'y']] = df['stream_file'].apply(lambda s: pd.Series(extract_coords(s)))

# List of metrics to plot.
metrics = ['weighted_rmsd', 'fraction_outliers', 'length_deviation',
           'angle_deviation', 'peak_ratio', 'percentage_unindexed']

# Create a subplot grid.
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

for i, metric in enumerate(metrics):
    # Group data by x and y and calculate the mean for the current metric.
    # grouped = df.groupby(['x', 'y'])[metric].mean().reset_index()
    # Group data by x and y and calculate the mean for the current metric.
    grouped = df.groupby(['x', 'y'])[metric].median().reset_index()
    # Pivot the data to get a grid.
    heatmap_data = grouped.pivot(index='y', columns='x', values=metric)
    # Sort the y index so lower values are at the bottom.
    heatmap_data = heatmap_data.sort_index()
    
    # Plot the heatmap in the appropriate subplot.
    im = axes[i].imshow(heatmap_data, origin='lower',
                        extent=[heatmap_data.columns.min(), heatmap_data.columns.max(), 
                                heatmap_data.index.min(), heatmap_data.index.max()],
                        aspect='auto')
    axes[i].set_title(f'Mean {metric}')
    axes[i].set_xlabel('x coordinate')
    axes[i].set_ylabel('y coordinate')
    # Add a colorbar for each heatmap.
    fig.colorbar(im, ax=axes[i], fraction=0.046, pad=0.04)

plt.tight_layout()
plt.show()
