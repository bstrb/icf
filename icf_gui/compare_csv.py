import pandas as pd
import matplotlib.pyplot as plt

# Replace these file names with your CSV file paths.
csv_file1 = "/home/bubl3932/files/UOX1/UOX1_original/centers_xatol_0.01_frameinterval_10_lowess_0.10_shifted_0.5_-0.3/xgandalf_iterations_max_radius_1.8_step_0.5/refined_centers.csv"   # contains: EventIndex, RefinedCenterX, RefinedCenterY
csv_file2 = "/home/bubl3932/files/UOX1/centers_xatol_0.01_frameinterval_10_lowess_0.10_shifted_0.5_-0.3.csv"       # contains: data_index, center_x, center_y

# Read the CSV files into DataFrames.
df1 = pd.read_csv(csv_file1)
df2 = pd.read_csv(csv_file2)

# ----------------------------
# Plot X coordinates vs. Index
# ----------------------------
plt.figure()
plt.plot(df1["EventIndex"], df1["RefinedCenterX"], marker='o', linestyle='-', label="RefinedCenterX")
plt.plot(df2["data_index"], df2["center_x"], marker='o', linestyle='-', label="center_x")
plt.xlabel("Index")
plt.ylabel("X Coordinate")
plt.title("X Coordinate vs. Index")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# ----------------------------
# Plot Y coordinates vs. Index
# ----------------------------
plt.figure()
plt.plot(df1["EventIndex"], df1["RefinedCenterY"], marker='o', linestyle='-', label="RefinedCenterY")
plt.plot(df2["data_index"], df2["center_y"], marker='o', linestyle='-', label="center_y")
plt.xlabel("Index")
plt.ylabel("Y Coordinate")
plt.title("Y Coordinate vs. Index")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
