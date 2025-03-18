#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import ipywidgets as widgets
import matplotlib.pyplot as plt
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output

# We'll use statsmodels' LOWESS.
from statsmodels.nonparametric.smoothers_lowess import lowess

# Custom module for updating H5 files (you already have it).
from update_h5 import create_updated_h5
from update_h5_pb import create_updated_h5_pb

# Mutable container for storing the path to the shifted CSV.
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

        # Sort by data_index for consistent processing
        df = df.sort_values("data_index").reset_index(drop=True)

        # Extract columns as arrays
        data_idx = df["data_index"].values
        cx = df["center_x"].values
        cy = df["center_y"].values

        # Identify valid points (non-missing centers)
        valid_mask = ~np.isnan(cx) & ~np.isnan(cy)
        valid_data_idx = data_idx[valid_mask]
        valid_cx = cx[valid_mask]
        valid_cy = cy[valid_mask]

        frac_val = lowess_frac_widget.value
        shift_x = shift_x_widget.value
        shift_y = shift_y_widget.value

        # If we don't have enough valid points, don't bother fitting.
        if len(valid_data_idx) < 2:
            print("Too few valid points for a LOWESS fit. We'll leave all centers as-is.")
            # Just output the original CSV but note that it won't fill missing endpoints.
            df_smoothed = df.copy()
        else:
            # Perform LOWESS on the valid points
            lowess_x = lowess(valid_cx, valid_data_idx, frac=frac_val, return_sorted=True)
            lowess_y = lowess(valid_cy, valid_data_idx, frac=frac_val, return_sorted=True)

            # We want to fill *every* integer data_index from min to max.
            min_idx, max_idx = data_idx.min(), data_idx.max()
            all_idx = np.arange(min_idx, max_idx + 1)

            # Interpolate the LOWESS results at each integer data_index
            smoothed_x = np.interp(all_idx, lowess_x[:, 0], lowess_x[:, 1])
            smoothed_y = np.interp(all_idx, lowess_y[:, 0], lowess_y[:, 1])

            # Apply user shifts
            smoothed_x += shift_x
            smoothed_y += shift_y

            # Create a new DataFrame that has *one row per integer data_index*:
            df_smoothed = pd.DataFrame({
                "data_index": all_idx,
                "center_x": smoothed_x,
                "center_y": smoothed_y
            })

        # ---------------------------
        # Plot old vs. new data
        fig, axs = plt.subplots(1, 2, figsize=(12, 5))

        # Original valid data
        axs[0].plot(valid_data_idx, valid_cx, 'o--', label='Original X (valid)', markersize=4)
        axs[1].plot(valid_data_idx, valid_cy, 'o--', label='Original Y (valid)', markersize=4)

        # Full-range smoothed data
        axs[0].plot(df_smoothed["data_index"], df_smoothed["center_x"], 'o-', label='Smoothed X (full)', markersize=4)
        axs[1].plot(df_smoothed["data_index"], df_smoothed["center_y"], 'o-', label='Smoothed Y (full)', markersize=4)

        axs[0].set_title("Center X vs. data_index")
        axs[1].set_title("Center Y vs. data_index")
        axs[0].legend()
        axs[1].legend()
        plt.show()
        # ---------------------------

        # Save the smoothed CSV
        base_name = os.path.splitext(os.path.basename(input_csv))[0]
        out_path = os.path.join(
            os.path.dirname(input_csv),
            f"{base_name}_lowess_{frac_val:.2f}_shifted_{shift_x}_{shift_y}.csv"
        )
        df_smoothed.to_csv(out_path, index=False)
        _shifted_csv_path[0] = out_path
        print(f"Smoothed CSV saved:\n{out_path}")

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

with_pb=widgets.Checkbox(value=False,description='Enable Progress Bar' )

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

        # Extract the base name (without extension) from _shifted_csv_path[0]
        base_name = os.path.splitext(os.path.basename(_shifted_csv_path[0]))[0]

        # Create a subfolder in the image file's directory named with the base_name
        subfolder_path = os.path.join(os.path.dirname(image_file), base_name)
        os.makedirs(subfolder_path, exist_ok=True)

        # Create the new H5 file path inside the subfolder with the same base name
        new_h5_path = os.path.join(subfolder_path, base_name + '.h5')

        try:
            if with_pb.value:
                create_updated_h5_pb(image_file, new_h5_path, _shifted_csv_path[0])
                print(f"Updated H5 file created at:\n{new_h5_path}")
            else:
                create_updated_h5(image_file, new_h5_path, _shifted_csv_path[0])
                print(f"Updated H5 file created at:\n{new_h5_path}")
        except Exception as e:
            print("Error updating H5 file:", e)

update_h5_button.on_click(on_update_h5_clicked)

h5_ui = widgets.VBox([
    widgets.HTML("<h2>Section 2B: Update H5</h2>"),
    image_file_chooser_h5,
    with_pb,  # Include the progress bar checkbox here.
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

