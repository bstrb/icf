#!/usr/bin/env python3
import os
import time
import h5py
import numpy as np
import pandas as pd
import ipywidgets as widgets
import matplotlib.pyplot as plt
from multiprocessing import Pool, set_start_method
from statsmodels.nonparametric.smoothers_lowess import lowess
from tqdm import tqdm
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output
import warnings
warnings.filterwarnings('ignore', message='invalid value encountered in subtract', category=RuntimeWarning)

# ------------------------------------------------------------------------
# Custom module imports
# ------------------------------------------------------------------------

from image_processing import process_single_image
from update_h5 import create_updated_h5

##############################################################################
# FORCE THE SPAWN METHOD AT TOP LEVEL
##############################################################################
try:
    set_start_method('spawn', force=True)
except RuntimeError:
    # If it's already set or you're in an interactive environment, you may get an error
    pass

# ------------------------------------------------------------------------
# SECTION 1: PROCESS IMAGES (Partial CSV) WITH CHUNKING
# ------------------------------------------------------------------------

def compute_centers_for_chunk(args):
    """
    Helper function for processing a chunk of frames.
    Args is a tuple:
      (frame_nums, data_indices, image_file, mask, n_wedges, n_rad_bins,
       xatol, fatol, verbose, xmin, xmax, ymin, ymax)
    Returns a list of tuples:
      [(frame_num, data_index, center_x, center_y), ...] for that chunk.
    """
    (frame_nums, data_indices, image_file, mask, n_wedges, n_rad_bins,
     xatol, fatol, verbose, xmin, xmax, ymin, ymax) = args
    results = []
    # Open the H5 file once for the entire chunk:
    with h5py.File(image_file, 'r') as f:
        images = f['/entry/data/images']
        for i, fn in enumerate(frame_nums):
            img = images[fn].astype(np.float32)
            cx, cy = process_single_image(img, mask, n_wedges, n_rad_bins, xatol, fatol, verbose)
            # If out-of-bounds or invalid, set centers to NaN:
            if not (np.isfinite(cx) and np.isfinite(cy) and xmin <= cx < xmax and ymin <= cy < ymax):
                cx, cy = np.nan, np.nan
            results.append((fn, data_indices[i], cx, cy))
    return results

def process_images_partial(
    image_file,
    mask,
    frame_interval=10,
    xatol=0.01,
    fatol=10,
    n_wedges=4,
    n_rad_bins=100,
    chunk_size=100,  # chunk size for processing frames
    xmin=0,
    xmax=9999999,
    ymin=0,
    ymax=9999999,
    verbose=False
):
    """
    Reads the H5 file to determine n_images.
    If /entry/data/index exists, that column is used; otherwise, it defaults to frame_number.
    Only frames that are first, last, or multiples of frame_interval are processed.
    These frames are grouped in chunks (default size 100) to avoid opening the file for every frame.
    Saves a partial CSV with only the processed frames.
    """
    with h5py.File(image_file, 'r') as f:
        n_images = f['/entry/data/images'].shape[0]
        index_dset = f.get('/entry/data/index')
        if index_dset is not None:
            data_index_all = index_dset[:]
        else:
            data_index_all = np.arange(n_images)

    # Determine which frames to process (physical frame_numbers)
    frames_to_process = sorted(set([0, n_images - 1]) | {i for i in range(n_images) if i % frame_interval == 0})
    
    # Group frames_to_process into chunks of size 'chunk_size'
    chunks = [frames_to_process[i:i+chunk_size] for i in range(0, len(frames_to_process), chunk_size)]
    
    # For each chunk, also extract corresponding data_index values.
    tasks = []
    for chunk in chunks:
        d_indices = [data_index_all[fn] for fn in chunk]
        tasks.append((
            chunk,           # list of frame numbers in this chunk
            d_indices,       # corresponding data_index values
            image_file,
            mask,
            n_wedges,
            n_rad_bins,
            xatol,
            fatol,
            verbose,
            xmin,
            xmax,
            ymin,
            ymax
        ))

    start_time = time.time()
    results = []
    with Pool() as pool:
        for chunk_result in tqdm(pool.imap(compute_centers_for_chunk, tasks), total=len(tasks), desc="Processing chunks"):
            results.extend(chunk_result)

    elapsed = time.time() - start_time
    print(f"Processed {len(frames_to_process)} frames in {elapsed:.1f}s.")

    # Build a DataFrame from the processed frames.
    df_part = pd.DataFrame(results, columns=["frame_number", "data_index", "center_x", "center_y"])
    df_part = df_part.sort_values("frame_number").reset_index(drop=True)

    # Save the partial CSV (only rows for frames that were processed)
    csv_file = os.path.join(
        os.path.dirname(image_file),
        f"partial_centers_xatol_{xatol}_interval_{frame_interval}.csv"
    )
    df_part.to_csv(csv_file, index=False)
    print(f"Partial CSV written with {len(df_part)} rows:\n{csv_file}")

# ------------------------------------------------------------------------
# SECTION 1: UI for Processing Images (Partial CSV)
# ------------------------------------------------------------------------
image_file_chooser = FileChooser(os.getcwd())
image_file_chooser.title = "Select H5 Image File"
image_file_chooser.filter_pattern = "*.h5"

mask_file_chooser = FileChooser(os.getcwd())
mask_file_chooser.title = "Select Mask H5 File"
mask_file_chooser.filter_pattern = "*.h5"

use_mask_checkbox = widgets.Checkbox(value=True, description="Use Mask")

xatol_widget = widgets.FloatText(value=0.01, description="xatol:", layout=widgets.Layout(width="120px"))
frame_interval_widget = widgets.IntText(value=10, description="Interval:", layout=widgets.Layout(width="120px"))
verbose_checkbox = widgets.Checkbox(value=False, description="Verbose")

xmin_widget = widgets.IntText(value=0, description="xmin:", layout=widgets.Layout(width="120px"))
xmax_widget = widgets.IntText(value=2048, description="xmax:", layout=widgets.Layout(width="120px"))
ymin_widget = widgets.IntText(value=0, description="ymin:", layout=widgets.Layout(width="120px"))
ymax_widget = widgets.IntText(value=2048, description="ymax:", layout=widgets.Layout(width="120px"))

process_images_button = widgets.Button(description="Process Images (Partial)", button_style="primary")
output_area = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})

def on_process_images_clicked(b):
    with output_area:
        clear_output()
        image_file = image_file_chooser.selected
        if not image_file:
            print("Please select an H5 image file.")
            return
        mask_file = mask_file_chooser.selected
        if not mask_file:
            print("Please select a mask H5 file.")
            return
        try:
            with h5py.File(mask_file, 'r') as f_mask:
                if use_mask_checkbox.value:
                    mask = f_mask['/mask'][:].astype(bool)
                else:
                    sample = f_mask['/mask'][0]
                    mask = np.ones_like(sample, dtype=bool)
        except Exception as e:
            print("Error loading mask file:", e)
            return

        xatol_val = xatol_widget.value
        frame_interval_val = frame_interval_widget.value
        verbose_val = verbose_checkbox.value
        xmin_val = xmin_widget.value
        xmax_val = xmax_widget.value
        ymin_val = ymin_widget.value
        ymax_val = ymax_widget.value

        print("Section 1: Processing images to create a PARTIAL CSV (only processed frames).")
        process_images_partial(
            image_file=image_file,
            mask=mask,
            frame_interval=frame_interval_val,
            xatol=xatol_val,
            fatol=10,
            n_wedges=4,
            n_rad_bins=100,
            chunk_size=100,
            xmin=xmin_val,
            xmax=xmax_val,
            ymin=ymin_val,
            ymax=ymax_val,
            verbose=verbose_val
        )
        print("Section 1: Done.")

process_images_button.on_click(on_process_images_clicked)

process_images_ui = widgets.VBox([
    widgets.HTML("<h2>Section 1: Process Images & Write PARTIAL CSV</h2>"),
    image_file_chooser,
    mask_file_chooser,
    use_mask_checkbox,
    widgets.HBox([xatol_widget, frame_interval_widget, verbose_checkbox]),
    widgets.HBox([xmin_widget, xmax_widget, ymin_widget, ymax_widget]),
    process_images_button,
    output_area
])

# ------------------------------------------------------------------------
# SECTION 2: LOWESS-FIT + CREATE FINAL CSV + UPDATE H5
# ------------------------------------------------------------------------
csv_file_chooser = FileChooser(os.getcwd())
csv_file_chooser.title = "Select PARTIAL CSV"
csv_file_chooser.filter_pattern = "*.csv"

shift_x_widget = widgets.FloatText(value=0, description="Shift X:", layout=widgets.Layout(width="150px"))
shift_y_widget = widgets.FloatText(value=0, description="Shift Y:", layout=widgets.Layout(width="150px"))

lowess_frac_widget = widgets.FloatSlider(
    value=0.1, min=0.01, max=1.0, step=0.01,
    description="Lowess frac:",
    continuous_update=False,
    layout=widgets.Layout(width="300px")
)

process_csv_button = widgets.Button(description="Lowess & Write FULL CSV", button_style="primary")
csv_output = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})
shifted_csv_path = None  # Global variable for final CSV path

def on_process_csv_clicked(b):
    global shifted_csv_path
    with csv_output:
        clear_output()
        partial_csv = csv_file_chooser.selected
        if not partial_csv:
            print("Please select the PARTIAL CSV from Section 1.")
            return

        try:
            df_part = pd.read_csv(partial_csv)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return

        # Ensure required columns
        for col in ["frame_number", "data_index", "center_x", "center_y"]:
            if col not in df_part.columns:
                print(f"CSV must contain '{col}' column.")
                return

        # Assume the partial CSV includes the first and last frame.
        # Let n_images = last frame_number + 1.
        n_images = int(df_part["frame_number"].max() + 1)
        print(f"Section 2: n_images = {n_images} (from max frame_number+1)")

        # We'll build a final DataFrame with n_images rows.
        # For frames processed in the partial CSV, we use their computed values.
        # For frames not processed, we set data_index = -1 and centers = NaN.
        df_final = pd.DataFrame({
            "frame_number": np.arange(n_images),
            "data_index": np.full(n_images, -1, dtype=int),
            "center_x": np.full(n_images, np.nan, dtype=float),
            "center_y": np.full(n_images, np.nan, dtype=float),
        })

        # Fill in rows from the partial CSV
        for _, row in df_part.iterrows():
            fn = int(row["frame_number"])
            df_final.at[fn, "data_index"] = row["data_index"]
            df_final.at[fn, "center_x"] = row["center_x"]
            df_final.at[fn, "center_y"] = row["center_y"]

        # Now, perform LOWESS on the valid rows in the partial CSV.
        valid_mask = (~df_part["center_x"].isna()) & (~df_part["center_y"].isna())
        idx_valid = df_part.loc[valid_mask, "data_index"].values
        cx_valid = df_part.loc[valid_mask, "center_x"].values
        cy_valid = df_part.loc[valid_mask, "center_y"].values

        frac_val = lowess_frac_widget.value
        if len(idx_valid) < 2:
            print("Too few valid points for LOWESS. Final CSV remains as partial values.")
        else:
            min_idx, max_idx = idx_valid.min(), idx_valid.max()
            lowess_x = lowess(cx_valid, idx_valid, frac=frac_val, return_sorted=True)
            lowess_y = lowess(cy_valid, idx_valid, frac=frac_val, return_sorted=True)
            all_idx = np.arange(min_idx, max_idx+1)
            smoothed_x = np.interp(all_idx, lowess_x[:,0], lowess_x[:,1])
            smoothed_y = np.interp(all_idx, lowess_y[:,0], lowess_y[:,1])
            shift_x = shift_x_widget.value
            shift_y = shift_y_widget.value
            smoothed_x += shift_x
            smoothed_y += shift_y
            idx2sx = dict(zip(all_idx, smoothed_x))
            idx2sy = dict(zip(all_idx, smoothed_y))
            # For each row in df_final whose data_index is in [min_idx, max_idx], update centers.
            for i in range(n_images):
                di = df_final.at[i, "data_index"]
                if (di != -1) and (di >= min_idx) and (di <= max_idx):
                    df_final.at[i, "center_x"] = idx2sx[di]
                    df_final.at[i, "center_y"] = idx2sy[di]

        # Plot a comparison for valid points from partial CSV vs final CSV
        valid_mask_final = (df_final["data_index"] != -1)
        if valid_mask_final.sum() > 0:
            fig, axs = plt.subplots(1, 2, figsize=(12, 5))
            axs[0].plot(df_part.loc[valid_mask, "data_index"], cx_valid, "o--", label="Partial X", markersize=4)
            axs[0].plot(df_final.loc[valid_mask_final, "data_index"], df_final.loc[valid_mask_final, "center_x"], "o-", label="Final X", markersize=4)
            axs[1].plot(df_part.loc[valid_mask, "data_index"], cy_valid, "o--", label="Partial Y", markersize=4)
            axs[1].plot(df_final.loc[valid_mask_final, "data_index"], df_final.loc[valid_mask_final, "center_y"], "o-", label="Final Y", markersize=4)
            axs[0].set_title("Center X vs data_index")
            axs[1].set_title("Center Y vs data_index")
            axs[0].legend()
            axs[1].legend()
            plt.show()

        shifted_csv_path = os.path.join(
            os.path.dirname(partial_csv),
            f"final_centers_lowess_{frac_val:.2f}.csv"
        )
        df_final.to_csv(shifted_csv_path, index=False)
        print(f"Section 2: Final CSV with {n_images} rows saved:\n{shifted_csv_path}")

process_csv_button.on_click(on_process_csv_clicked)

lowess_ui = widgets.VBox([
    widgets.HTML("<h2>Section 2A: LOWESS-Fit & Create Final CSV</h2>"),
    csv_file_chooser,
    widgets.HBox([shift_x_widget, shift_y_widget]),
    lowess_frac_widget,
    process_csv_button,
    csv_output
])

# ------------------------------------------------------------------------
# SECTION 2B: UPDATE H5
# ------------------------------------------------------------------------
image_file_chooser_h5 = FileChooser(os.getcwd())
image_file_chooser_h5.title = "Select H5 File to Update"
image_file_chooser_h5.filter_pattern = "*.h5"

update_h5_button = widgets.Button(description="Update H5 with Final CSV", button_style="primary")
h5_output = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})

def on_update_h5_clicked(b):
    with h5_output:
        clear_output()
        if shifted_csv_path is None:
            print("No final CSV available. Please run the LOWESS step first.")
            return
        h5_file = image_file_chooser_h5.selected
        if not h5_file:
            print("Please select an H5 file to update.")
            return
        new_h5_path = os.path.join(
            os.path.dirname(h5_file),
            os.path.splitext(os.path.basename(shifted_csv_path))[0] + ".h5"
        )
        try:
            create_updated_h5(h5_file, new_h5_path, shifted_csv_path)
            print(f"Updated H5 file created at:\n{new_h5_path}")
        except Exception as e:
            print("Error updating H5:", e)

update_h5_button.on_click(on_update_h5_clicked)

h5_ui = widgets.VBox([
    widgets.HTML("<h2>Section 2B: Update H5 with Final CSV</h2>"),
    image_file_chooser_h5,
    update_h5_button,
    h5_output
])

csv_h5_ui = widgets.VBox([lowess_ui, h5_ui])

# ------------------------------------------------------------------------
# FINAL COMBINED UI
# ------------------------------------------------------------------------
tab = widgets.Tab(children=[process_images_ui, csv_h5_ui])
tab.set_title(0, "Section 1: Process Images")
tab.set_title(1, "Section 2: LOWESS & H5 Update")
display(tab)

if __name__ == "__main__":
    # Optionally launch the UI or call your main function
    # e.g. something like:
    import IPython
    IPython.start_ipython(argv=[], user_ns=dict(globals(), **locals()))
