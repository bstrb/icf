import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

def indexing_heatmap(folder_path):
    os.chdir(folder_path)
    
    # Find all files with the ".stream" extension
    stream_files = glob.glob("*.stream")
    data = []
    
    for stream_file in stream_files:
        base_name = os.path.splitext(stream_file)[0]
        parts = base_name.rsplit("_", 2)
        x = float(parts[-2])
        y = float(parts[-1])
        
        # Count "num_reflections" lines
        event_count = 0
        with open(stream_file, "r") as f:
            for line in f:
                if line.startswith("num_reflections"):
                    event_count += 1
        
        data.append((x, y, event_count))
    
    df = pd.DataFrame(data, columns=["x", "y", "count"])

    # Create a scatter plot where each point's color = 'count'
    plt.figure()
    scatter = plt.scatter(
        df["x"], 
        df["y"], 
        c=df["count"],        # color by num_reflections count
        cmap="viridis",       # choose any built-in colormap you like
        alpha=0.9,            # make points slightly transparent if desired
        # edgecolors="black",   # optional: add borders around points
        s=150                  # marker size
    )

    # Add a colorbar to show the scale of 'num_reflections'
    cbar = plt.colorbar(scatter)
    cbar.set_label("Count of index results")

    plt.title("Number of index results at Each (x, y) File Coordinate")
    plt.xlabel("X coordinate")
    plt.ylabel("Y coordinate")
    plt.grid(True)  # Optional grid

    plt.show()

if __name__ == "__main__":
    input_folder = "/home/bubl3932/files/LTA_sim/simulation-45/xgandalf_iterations_max_radius_2_step_0.5"
    indexing_heatmap(input_folder)
