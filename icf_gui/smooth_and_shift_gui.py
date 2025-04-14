# smooth_and_shift_import.py - GUI for smoothing and shifting center data using LOWESS.
#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog

from statsmodels.nonparametric.smoothers_lowess import lowess

# Custom modules for updating H5 files.
# from update_h5_pb import create_updated_h5_pb
from create_updated_h5_pb import create_updated_h5_pb
from extract_geom_values import extract_geom_values

# Global containers.
shifted_csv_path = [None]      # To store the path to the saved smoothed CSV.
global_smoothed_df = [None]      # To store the computed DataFrame from preview.

def get_ui(parent):
    """
    Creates and returns a Frame containing the LOWESS/H5 Update GUI.
    
    The interface is split into two sections:
      - Section 2A: LOWESS-Fit & Shift (with buttons for preview and saving the smoothed CSV)
      - Section 2B: Update H5 with Smoothed Centers.
    """
    frame = tk.Frame(parent)
    
    # --- Section 2A: LOWESS-Fit & Shift ---
    frame_2a = tk.LabelFrame(frame, text="Section 2A: Lowess-Fit & Shift", padx=10, pady=10)
    frame_2a.pack(fill="both", expand=True, padx=10, pady=5)
    
    # CSV selection.
    tk.Label(frame_2a, text="CSV File (from Section 1):").grid(row=0, column=0, sticky="w")
    csv_path_var = tk.StringVar(frame)
    csv_entry = tk.Entry(frame_2a, textvariable=csv_path_var, width=50)
    csv_entry.grid(row=0, column=1, padx=5)
    tk.Button(frame_2a, text="Browse", command=lambda: csv_path_var.set(
        filedialog.askopenfilename(
            title="Select CSV File with Center Data",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=os.getcwd()
        )
    )).grid(row=0, column=2, padx=5)
    
    # Shift parameters.
    tk.Label(frame_2a, text="Shift X:").grid(row=1, column=0, sticky="w")
    shift_x_var = tk.StringVar(frame, value="0")
    tk.Entry(frame_2a, textvariable=shift_x_var, width=10).grid(row=1, column=1, sticky="w", padx=5)
    
    tk.Label(frame_2a, text="Shift Y:").grid(row=1, column=2, sticky="w")
    shift_y_var = tk.StringVar(frame, value="0")
    tk.Entry(frame_2a, textvariable=shift_y_var, width=10).grid(row=1, column=3, sticky="w", padx=5)
    
    # LOWESS fraction slider.
    lowess_frac_var = tk.DoubleVar(frame, value=0.10)
    lowess_scale = tk.Scale(frame_2a, from_=0.01, to=1.0, resolution=0.01, orient=tk.HORIZONTAL,
                            variable=lowess_frac_var, label="Lowess frac:", length=300)
    lowess_scale.grid(row=2, column=0, columnspan=4, pady=5)
    
    # Buttons for preview and saving.
    tk.Button(frame_2a, text="Preview LOWESS & Plot", command=lambda: preview_lowess()).grid(row=3, column=0, columnspan=2, pady=5)
    tk.Button(frame_2a, text="Save Smoothed CSV", command=lambda: save_smoothed_csv()).grid(row=3, column=2, columnspan=2, pady=5)
    
    # --- Section 2B: Update H5 with Smoothed Centers ---
    frame_2b = tk.LabelFrame(frame, text="Section 2B: Update H5 with Smoothed Centers", padx=10, pady=10)
    frame_2b.pack(fill="both", expand=True, padx=10, pady=5)
    
    # H5 file selection.
    tk.Label(frame_2b, text="H5 File to Update:").grid(row=0, column=0, sticky="w")
    h5_path_var = tk.StringVar(frame)
    h5_entry = tk.Entry(frame_2b, textvariable=h5_path_var, width=50)
    h5_entry.grid(row=0, column=1, padx=5)
    tk.Button(frame_2b, text="Browse", command=lambda: h5_path_var.set(
        filedialog.askopenfilename(
            title="Select H5 File to Update",
            filetypes=[("H5 Files", "*.h5")],
            initialdir=os.getcwd()
        )
    )).grid(row=0, column=2, padx=5)

    # GEOM file selection.
    tk.Label(frame_2b, text="Geometry File needed for H5 Update:").grid(row=1, column=0, sticky="w")
    geom_path_var = tk.StringVar(frame)
    geom_entry = tk.Entry(frame_2b, textvariable=geom_path_var, width=50)
    geom_entry.grid(row=1, column=1, padx=5)
    tk.Button(frame_2b, text="Browse", command=lambda: geom_path_var.set(
        filedialog.askopenfilename(
            title="Select geom File to Update",
            filetypes=[("geom Files", "*.geom")],
            initialdir=os.getcwd()
        )
    )).grid(row=1, column=2, padx=5)
    
    # New: Smoothed CSV file selection.
    tk.Label(frame_2b, text="Smoothed CSV File:").grid(row=2, column=0, sticky="w")
    smoothed_csv_path_var = tk.StringVar(frame)
    smoothed_csv_entry = tk.Entry(frame_2b, textvariable=smoothed_csv_path_var, width=50)
    smoothed_csv_entry.grid(row=2, column=1, padx=5)
    tk.Button(frame_2b, text="Browse", command=lambda: smoothed_csv_path_var.set(
        filedialog.askopenfilename(
            title="Select Smoothed CSV File",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=os.getcwd()
        )
    )).grid(row=2, column=2, padx=5)
    
    # Progress bar checkbox.
    pb_var = tk.BooleanVar(frame, value=False)
    tk.Checkbutton(frame_2b, text="Enable Progress Bar", variable=pb_var).grid(row=3, column=0, columnspan=2, sticky="w")
    
    # Update H5 button.
    tk.Button(frame_2b, text="Update H5 with Smoothed Centers", command=lambda: update_h5_file()).grid(row=4, column=0, columnspan=3, pady=5)
    
    # --- Internal function definitions ---
    def preview_lowess():
        print("-" * 60)
        csv_file = csv_path_var.get()
        if not csv_file:
            print("Please select a CSV file from Section 1.")
            return
        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return
        # Check for required columns.
        for col in ["frame_number", "data_index", "center_x", "center_y"]:
            if col not in df.columns:
                print(f"CSV must contain '{col}' column.")
                return
        # Sort by data_index.
        df = df.sort_values("data_index").reset_index(drop=True)
        data_idx = df["data_index"].values
        cx = df["center_x"].values
        cy = df["center_y"].values
        # Identify valid points.
        valid_mask = ~np.isnan(cx) & ~np.isnan(cy)
        valid_data_idx = data_idx[valid_mask]
        valid_cx = cx[valid_mask]
        valid_cy = cy[valid_mask]
        frac_val = lowess_frac_var.get()
        try:
            shift_x_val = float(shift_x_var.get())
            shift_y_val = float(shift_y_var.get())
        except Exception as e:
            print(f"Error reading shift values: {e}")
            return
        if len(valid_data_idx) < 2:
            print("Too few valid points for a LOWESS fit. We'll leave all centers as-is.")
            smoothed_df = df.copy()
        else:
            lowess_x = lowess(valid_cx, valid_data_idx, frac=frac_val, return_sorted=True)
            lowess_y = lowess(valid_cy, valid_data_idx, frac=frac_val, return_sorted=True)
            min_idx, max_idx = int(data_idx.min()), int(data_idx.max())
            all_idx = np.arange(min_idx, max_idx + 1)
            smoothed_x = np.interp(all_idx, lowess_x[:, 0], lowess_x[:, 1])
            smoothed_y = np.interp(all_idx, lowess_y[:, 0], lowess_y[:, 1])
            smoothed_x += shift_x_val
            smoothed_y += shift_y_val
            smoothed_df = pd.DataFrame({
                "data_index": all_idx,
                "center_x": smoothed_x,
                "center_y": smoothed_y
            })
        global_smoothed_df[0] = smoothed_df
        plt.close('all')
        fig, axs = plt.subplots(1, 2, figsize=(12, 5))
        axs[0].plot(valid_data_idx, valid_cx, 'o--', label='Original X (valid)', markersize=4)
        axs[1].plot(valid_data_idx, valid_cy, 'o--', label='Original Y (valid)', markersize=4)
        axs[0].plot(smoothed_df["data_index"], smoothed_df["center_x"], 'o-', label='Smoothed X (full)', markersize=4)
        axs[1].plot(smoothed_df["data_index"], smoothed_df["center_y"], 'o-', label='Smoothed Y (full)', markersize=4)
        axs[0].set_title("Center X vs. data_index")
        axs[1].set_title("Center Y vs. data_index")
        axs[0].legend()
        axs[1].legend()
        plt.tight_layout()
        plt.show()
        print("Preview complete. If satisfied, click 'Save Smoothed CSV' to create the CSV file.")
    
    def save_smoothed_csv():
        if global_smoothed_df[0] is None:
            print("No smoothed data available. Please run the 'Preview LOWESS & Plot' first.")
            return
        csv_file = csv_path_var.get()
        frac_val = lowess_frac_var.get()
        try:
            shift_x_val = float(shift_x_var.get())
            shift_y_val = float(shift_y_var.get())
        except Exception as e:
            print(f"Error reading shift values: {e}")
            return
        base_name = os.path.splitext(os.path.basename(csv_file))[0]
        out_path = os.path.join(
            os.path.dirname(csv_file),
            f"{base_name}_lowess_{frac_val:.2f}_shifted_{shift_x_val}_{shift_y_val}.csv"
        )
        try:
            global_smoothed_df[0].to_csv(out_path, index=False)
            shifted_csv_path[0] = out_path
            # Automatically update the Smoothed CSV field in Section 2B.
            smoothed_csv_path_var.set(out_path)
            print(f"Smoothed CSV saved:\n{out_path}")
        except Exception as e:
            print(f"Error saving CSV: {e}")
    
    def update_h5_file():
        print("-" * 60)
        # Use the CSV from the Smoothed CSV field.
        csv_file = smoothed_csv_path_var.get()
        if not csv_file:
            print("No smoothed CSV available. Please save the smoothed CSV first (Section 2A) or select one using the browse button.")
            return
        h5_file = h5_path_var.get()
        if not h5_file:
            print("Please select an H5 file to update.")
            return
        geom_file = geom_path_var.get()
        if not geom_file:
            print("Please select a GEOM file needed for H5 update.")
            return
        try:
            res_val, max_ss_val = extract_geom_values(geom_file)
            print(f"Extracted values from GEOM: res={res_val}, max_ss={max_ss_val}")
        except Exception as e:
            print(f"Error extracting values from GEOM: {e}")
            return

        base_name = os.path.splitext(os.path.basename(csv_file))[0]
        subfolder_path = os.path.join(os.path.dirname(h5_file), base_name)
        os.makedirs(subfolder_path, exist_ok=True)
        new_h5_path = os.path.join(subfolder_path, base_name + '.h5')
        try:
            if pb_var.get():
                create_updated_h5_pb(h5_file, new_h5_path, csv_file, use_progress=True, framesize=max_ss_val+1, pixels_per_meter=res_val)
            else:
                create_updated_h5_pb(h5_file, new_h5_path, csv_file, use_progress=False, framesize=max_ss_val+1, pixels_per_meter=res_val)
            print(f"Updated H5 file created at:\n{new_h5_path}")
        except Exception as e:
            print(f"Error updating H5 file: {e}")
    
    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Lowess H5 Update")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
