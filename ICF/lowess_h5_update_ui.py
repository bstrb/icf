#!/usr/bin/env python3
import os
import re
import time
import numpy as np
import pandas as pd
import ipywidgets as widgets
import matplotlib.pyplot as plt
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output

# Import the LOWESS function.
from statsmodels.nonparametric.smoothers_lowess import lowess

# Custom module for updating H5 files.
from update_h5 import create_updated_h5

# We'll use a mutable container (list) for the shifted CSV path.
_shifted_csv_path = [None]

# ------------------------------------------------------------------------
# UI Section 2A: LOWESS-Fit & Shift
csv_file_chooser = FileChooser(os.getcwd())
csv_file_chooser.title = "Select CSV From Section 1"
csv_file_chooser.filter_pattern = "*.csv"

shift_x_widget = widgets.FloatText(value=0, description="Shift X:", layout=widgets.Layout(width="150px"))
shift_y_widget = widgets.FloatText(value=0, description="Shift Y:", layout=widgets.Layout(width="150px"))

lowess_frac_widget = widgets.FloatSlider(
    value=0.1, min=0.01, max=1.0, step=0.01,
    description="Lowess frac:",
    continuous_update=False,
    layout=widgets.Layout(width="300px")
)

process_csv_button = widgets.Button(description="Lowess & Save CSV", button_style="primary")
csv_output = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})

def on_process_csv_clicked(b):
    with csv_output:
        clear_output()

        input_csv = csv_file_chooser.selected
        if not input_csv:
            print("Please select a CSV from Section 1.")
            return

        # Read CSV
        try:
            df = pd.read_csv(input_csv)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return

        # Must contain these columns
        for col in ["frame_number", "data_index", "center_x", "center_y"]:
            if col not in df.columns:
                print(f"CSV must contain '{col}' column.")
                return

        # Sort by data_index for the smoothing
        df = df.sort_values("data_index").reset_index(drop=True)
        idx_all  = df["data_index"].values
        cx_all   = df["center_x"].values
        cy_all   = df["center_y"].values

        valid_mask = ~np.isnan(cx_all) & ~np.isnan(cy_all)
        idx_valid  = idx_all[valid_mask]
        cx_valid   = cx_all[valid_mask]
        cy_valid   = cy_all[valid_mask]

        frac_val = lowess_frac_widget.value

        if len(idx_valid) < 2:
            print("Too few valid points for a LOWESS fit. We'll leave all centers as-is.")
            df_smoothed = df.copy()
        else:
            min_idx, max_idx = idx_valid.min(), idx_valid.max()
            lowess_x = lowess(cx_valid, idx_valid, frac=frac_val, return_sorted=True)
            lowess_y = lowess(cy_valid, idx_valid, frac=frac_val, return_sorted=True)

            # Interpolate at all integer data_index in [min_idx..max_idx]
            all_idx = np.arange(min_idx, max_idx + 1)
            smoothed_x = np.interp(all_idx, lowess_x[:,0], lowess_x[:,1])
            smoothed_y = np.interp(all_idx, lowess_y[:,0], lowess_y[:,1])

            # Apply user shift
            shift_x = shift_x_widget.value
            shift_y = shift_y_widget.value
            smoothed_x += shift_x
            smoothed_y += shift_y

            # Build a lookup
            idx2sx = dict(zip(all_idx, smoothed_x))
            idx2sy = dict(zip(all_idx, smoothed_y))

            # Construct a new DataFrame with updated centers
            df_smoothed = df.copy()
            for i in range(len(df_smoothed)):
                di = df_smoothed.at[i, "data_index"]
                if min_idx <= di <= max_idx:
                    df_smoothed.at[i, "center_x"] = idx2sx[di]
                    df_smoothed.at[i, "center_y"] = idx2sy[di]

        # Plot the original vs. smoothed (for valid points)
        fig, axs = plt.subplots(1, 2, figsize=(12, 5))
        axs[0].plot(idx_valid, cx_valid, 'o--', label='Original X (valid)', markersize=4)
        axs[1].plot(idx_valid, cy_valid, 'o--', label='Original Y (valid)', markersize=4)

        s_cx_valid = df_smoothed.loc[valid_mask, "center_x"].values
        s_cy_valid = df_smoothed.loc[valid_mask, "center_y"].values

        axs[0].plot(idx_valid, s_cx_valid, 'o-', label='Smoothed X', markersize=4)
        axs[1].plot(idx_valid, s_cy_valid, 'o-', label='Smoothed Y', markersize=4)
        axs[0].set_title("Center X vs data_index")
        axs[1].set_title("Center Y vs data_index")
        axs[0].legend()
        axs[1].legend()
        plt.show()

        # Write final CSV
        _shifted_csv_path[0] = os.path.join(
            os.path.dirname(input_csv),
            f"centers_lowess_{frac_val:.2f}_shifted.csv"
        )
        df_smoothed.to_csv(_shifted_csv_path[0], index=False)
        print(f"Smoothed CSV saved:\n{_shifted_csv_path[0]}")

process_csv_button.on_click(on_process_csv_clicked)

lowess_ui = widgets.VBox([
    widgets.HTML("<h2>Section 2A: Lowess-Fit & Shift</h2>"),
    csv_file_chooser,
    widgets.HBox([shift_x_widget, shift_y_widget]),
    lowess_frac_widget,
    process_csv_button,
    csv_output
])

# ------------------------------------------------------------------------
# UI Section 2B: Update H5 with Smoothed Centers
image_file_chooser_h5 = FileChooser(os.getcwd())
image_file_chooser_h5.title = "Select H5 File to Update"
image_file_chooser_h5.filter_pattern = "*.h5"

update_h5_button = widgets.Button(description="Update H5 with Smoothed Centers", button_style="primary")
h5_output = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})

def on_update_h5_clicked(b):
    with h5_output:
        clear_output()
        if _shifted_csv_path[0] is None:
            print("No shifted CSV available. Please run the 'Lowess & Save CSV' step first.")
            return
        image_file = image_file_chooser_h5.selected
        if not image_file:
            print("Please select an H5 file to update.")
            return

        new_h5_path = os.path.join(
            os.path.dirname(image_file),
            os.path.splitext(os.path.basename(_shifted_csv_path[0]))[0] + '.h5'
        )

        try:
            create_updated_h5(image_file, new_h5_path, _shifted_csv_path[0])
            print(f"Updated H5 file created at:\n{new_h5_path}")
        except Exception as e:
            print("Error updating H5 file:", e)

update_h5_button.on_click(on_update_h5_clicked)

h5_ui = widgets.VBox([
    widgets.HTML("<h2>Section 2B: Update H5</h2>"),
    image_file_chooser_h5,
    update_h5_button,
    h5_output
])

# Combine the two sections.
csv_h5_ui = widgets.VBox([lowess_ui, h5_ui])

def get_ui():
    """
    Returns the combined Lowess-Fit & H5 Update UI as a widget.
    """
    return csv_h5_ui

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
