#!/usr/bin/env python3
import os
import time
import h5py
import numpy as np
import pandas as pd
import ipywidgets as widgets
import matplotlib.pyplot as plt
from multiprocessing import Pool
from tqdm import tqdm
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output

import warnings
warnings.filterwarnings('ignore', message='invalid value encountered in subtract', category=RuntimeWarning)

# ------------------------------------------------------------------------
# Custom modules (adjust or remove if not needed):
from image_processing import process_single_image

# ------------------------------------------------------------------------
# HELPER FUNCTION (TOP LEVEL, so it's picklable)
def compute_center_for_frame(args):
    """
    Helper function for multiprocessing.
    Loads one frame from the H5, calls process_single_image, returns (frame_num, center_x, center_y).
    If the center is invalid or out-of-bounds, it returns NaN.
    """
    (frame_num, image_file, mask, n_wedges, n_rad_bins,
     xatol, fatol, verbose, xmin, xmax, ymin, ymax) = args

    # Load the image for this frame
    with h5py.File(image_file, 'r') as f:
        img = f['/entry/data/images'][frame_num].astype(np.float32)

    # Run the center-finding function
    cx, cy = process_single_image(img, mask, n_wedges, n_rad_bins, xatol, fatol, verbose)

    # If out-of-bounds or invalid => NaN
    if not (np.isfinite(cx) and np.isfinite(cy) and
            xmin <= cx < xmax and ymin <= cy < ymax):
        cx, cy = np.nan, np.nan

    return frame_num, cx, cy

# ------------------------------------------------------------------------
# FUNCTION TO PROCESS IMAGES (ONE ROW PER FRAME)
def process_images_no_chunk(
    image_file,
    mask,
    frame_interval=10,
    xatol=0.01,
    fatol=10,
    n_wedges=4,
    n_rad_bins=100,
    xmin=0,
    xmax=9999999,
    ymin=0,
    ymax=9999999,
    verbose=False
):
    """
    Creates a CSV with exactly one row per frame_number (0..n_images-1),
    while only physically loading frames you want to process:
      - first (0),
      - last (n_images-1),
      - multiples of frame_interval.
      
    If '/entry/data/index' exists, store it in 'data_index';
    otherwise, 'data_index = frame_number'.

    The resulting CSV has columns [frame_number, data_index, center_x, center_y],
    length == n_images. Unprocessed frames remain NaN for center_x, center_y.
    """
    # 1) Determine how many frames, plus read /entry/data/index if present
    with h5py.File(image_file, 'r') as f:
        n_images = f['/entry/data/images'].shape[0]
        index_dset = f.get('/entry/data/index')
        if index_dset is not None:
            data_index_all = index_dset[:]
        else:
            data_index_all = np.arange(n_images)

    # 2) Create a DataFrame with n_images rows, initialized to NaN centers
    df = pd.DataFrame({
        "frame_number": np.arange(n_images),
        "data_index": data_index_all,
        "center_x": np.full(n_images, np.nan, dtype=float),
        "center_y": np.full(n_images, np.nan, dtype=float),
    })

    # 3) Identify frames we actually process
    frames_to_process = set([0, n_images - 1]) | {
        i for i in range(n_images) if i % frame_interval == 0
    }
    frames_to_process = sorted(frames_to_process)

    # 4) Build argument tuples for multiprocessing
    tasks = []
    for fn in frames_to_process:
        tasks.append((
            fn,         # frame_num
            image_file, # pass path, not data
            mask,
            n_wedges, n_rad_bins,
            xatol, fatol,
            verbose,
            xmin, xmax, ymin, ymax
        ))

    # 5) Parallel center-finding
    start_time = time.time()
    with Pool() as pool:
        results = list(
            tqdm(
                pool.imap(compute_center_for_frame, tasks),
                total=len(tasks),
                desc="Processing frames"
            )
        )

    # 6) Place the results back into df
    for (fn, cx, cy) in results:
        df.at[fn, "center_x"] = cx
        df.at[fn, "center_y"] = cy

    # 7) Write CSV
    csv_file = os.path.join(
        os.path.dirname(image_file),
        f"centers_xatol_{xatol}_frameinterval_{frame_interval}.csv"
    )
    df.to_csv(csv_file, index=False)

    elapsed = time.time() - start_time
    print(f"Created CSV with {len(df)} rows in {elapsed:.1f}s:\n{csv_file}")

# ------------------------------------------------------------------------
# UI for Section 1: Process Images
image_file_chooser = FileChooser(os.getcwd())
image_file_chooser.title = "Select H5 Image File"
image_file_chooser.filter_pattern = "*.h5"

mask_file_chooser = FileChooser(os.getcwd())
mask_file_chooser.title = "Select Mask H5 File"
mask_file_chooser.filter_pattern = "*.h5"

use_mask_checkbox = widgets.Checkbox(value=True, description="Use Mask")

xatol_widget = widgets.FloatText(value=0.01, description="xatol:", layout=widgets.Layout(width="140px"))
frame_interval_widget = widgets.IntText(value=10, description="Interval:", layout=widgets.Layout(width="140px"))
verbose_checkbox = widgets.Checkbox(value=False, description="Verbose")

xmin_widget = widgets.IntText(value=462, description="xmin:", layout=widgets.Layout(width="140px"))
xmax_widget = widgets.IntText(value=562, description="xmax:", layout=widgets.Layout(width="140px"))
ymin_widget = widgets.IntText(value=462, description="ymin:", layout=widgets.Layout(width="140px"))
ymax_widget = widgets.IntText(value=562, description="ymax:", layout=widgets.Layout(width="140px"))

process_images_button = widgets.Button(description="Process Images", button_style="primary")
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
                    # If not using a mask, create an array of all True values.
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

        print("Processing images to create a CSV with one row per frame...")
        process_images_no_chunk(
            image_file=image_file,
            mask=mask,
            frame_interval=frame_interval_val,
            xatol=xatol_val,
            fatol=10,
            n_wedges=4,
            n_rad_bins=100,
            xmin=xmin_val,
            xmax=xmax_val,
            ymin=ymin_val,
            ymax=ymax_val,
            verbose=verbose_val
        )
        print("Done.")

process_images_button.on_click(on_process_images_clicked)

process_images_ui = widgets.VBox([
    widgets.HTML("<h2>Section 1: Process Images (One Row Per Frame)</h2>"),
    image_file_chooser,
    mask_file_chooser,
    use_mask_checkbox,
    widgets.HBox([xatol_widget, frame_interval_widget, verbose_checkbox]),
    widgets.HBox([xmin_widget, xmax_widget, ymin_widget, ymax_widget]),
    process_images_button,
    output_area
])

def get_ui():
    """
    Returns the Process Images UI as a widget.
    """
    return process_images_ui

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
