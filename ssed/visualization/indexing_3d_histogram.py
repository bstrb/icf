import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # enables 3D plotting
import matplotlib.colors as mcolors

def plot3d_indexing_rate(folder_path):
    os.chdir(folder_path)
    
    # Find all files with the ".stream" extension
    stream_files = glob.glob("*.stream")
    data = []
    
    for stream_file in stream_files:
        base_name = os.path.splitext(stream_file)[0]
        parts = base_name.rsplit("_", 2)
        x = float(parts[-2])
        y = float(parts[-1])
        
        # Count occurrences of "num_reflections"
        event_count = 0
        with open(stream_file, "r") as f:
            for line in f:
                if line.startswith("num_reflections"):
                    event_count += 1
        
        data.append((x, y, event_count))
    
    df = pd.DataFrame(data, columns=["x", "y", "count"])
    
    # Create figure and 3D axis with a larger size
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Normalize count values for the colormap
    norm = mcolors.Normalize(vmin=df["count"].min(), vmax=df["count"].max())
    cmap = plt.cm.viridis
    
    # Define bar widths (adjust based on your data scale)
    dx = dy = 0.07
    z_base = 0  # bars start at z = 0
    
    # Plot each bar individually with a color corresponding to its height
    for _, row in df.iterrows():
        x_val = row["x"]
        y_val = row["y"]
        dz = row["count"]
        color = cmap(norm(dz))
        ax.bar3d(x_val, y_val, z_base, dx, dy, dz,
                 color=color, shade=True, alpha=0.95)#, edgecolor='k')
    
    # Add a colorbar for reference
    mappable = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array(df["count"])
    cbar = fig.colorbar(mappable, ax=ax, pad=0.1)
    cbar.set_label("Count of index results")
    
    # Set labels and title
    ax.set_xlabel("X coordinate")
    ax.set_ylabel("Y coordinate")
    ax.set_zlabel("Count of index results")
    ax.set_title("3D Bar Plot of indexing rate at Each (x, y) Coordinate")
    
    # Adjust the viewing angle for a better perspective
    ax.view_init(elev=25, azim=135)
    
    # Optionally, remove background fill from panes for a cleaner look
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    
    plt.show()

if __name__ == "__main__":
    plot3d_indexing_rate("/home/bubl3932/files/LTA_sim/simulation-45/xgandalf_iterations_max_radius_2_step_0.5")
