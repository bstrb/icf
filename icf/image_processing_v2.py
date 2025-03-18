# image_processing.py

import os
import time
import h5py
import numpy as np
import pandas as pd
from tqdm import tqdm
from multiprocessing import Pool

from ICFTOTAL import center_of_mass_initial_guess, find_diffraction_center

def compute_center_for_frame(args):
    """
    Helper function for multiprocessing.
    Loads one frame from the H5 file, processes it, and returns (frame_num, center_x, center_y).
    If the computed center is invalid or out-of-bounds, returns NaN values.
    """
    (frame_num, image_file, mask, n_wedges, n_rad_bins,
     xatol, fatol, verbose, xmin, xmax, ymin, ymax) = args

    with h5py.File(image_file, 'r') as f:
        img = f['/entry/data/images'][frame_num].astype(np.float32)

    cx, cy = process_single_image(img, mask, n_wedges, n_rad_bins, xatol, fatol, verbose, xmin, xmax, ymin, ymax)

    if not (np.isfinite(cx) and np.isfinite(cy) and
            xmin <= cx < xmax and ymin <= cy < ymax):
        cx, cy = np.nan, np.nan

    return frame_num, cx, cy

def process_single_image(img, mask, n_wedges, n_rad_bins, xatol, fatol, verbose, xmin, xmax, ymin, ymax):
    """
    Process a single image: get an initial center-of-mass guess and then refine it.
    """
    init_center = center_of_mass_initial_guess(img, mask)
    refined_center = find_diffraction_center(
        img, mask,
        initial_center=init_center,
        n_wedges=n_wedges,
        n_rad_bins=n_rad_bins,
        xatol=xatol,
        fatol=fatol,
        verbose=verbose
    )
    return refined_center

def process_images_apply_async(
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
    Processes the specified frames from the H5 image file in parallel using apply_async
    (without chunking) so that the progress bar is updated for every computed center.
    Results are stored in a CSV in the same folder as the image file.
    """
    # 1) Open the H5 file to get the number of images and index dataset.
    with h5py.File(image_file, 'r') as f:
        n_images = f['/entry/data/images'].shape[0]
        index_dset = f.get('/entry/data/index')
        if index_dset is not None:
            data_index_all = index_dset[:]
        else:
            raise ValueError("Dataset '/entry/data/index' is required but not found.")

    # 2) Create a DataFrame to store centers.
    df = pd.DataFrame({
        "frame_number": np.arange(n_images),
        "data_index": data_index_all,
        "center_x": np.full(n_images, np.nan, dtype=float),
        "center_y": np.full(n_images, np.nan, dtype=float),
    })

    # 3) Identify which frames to process.
    frames_to_process = set([0, n_images - 1]) | {i for i in range(n_images) if i % frame_interval == 0}
    frames_to_process = sorted(frames_to_process)

    # 4) Build a list of tasks.
    tasks = []
    for fn in frames_to_process:
        tasks.append((
            fn,         # frame number
            image_file, # image file path
            mask,
            n_wedges, n_rad_bins,
            xatol, fatol,
            verbose,
            xmin, xmax, ymin, ymax
        ))

    # 5) Create a tqdm progress bar.
    pbar = tqdm(total=len(tasks), desc="Processing frames", unit="frame")

    # 6) Define a callback to update the progress bar and DataFrame.
    def update_callback(result):
        frame_num, cx, cy = result
        df.at[frame_num, "center_x"] = cx
        df.at[frame_num, "center_y"] = cy
        pbar.update(1)

    # 7) Process each task individually using apply_async.
    with Pool() as pool:
        async_results = [pool.apply_async(compute_center_for_frame, args=(task,), callback=update_callback)
                         for task in tasks]
        # Wait for all tasks to finish.
        [res.get() for res in async_results]

    pbar.close()

    # 8) Filter the DataFrame and write out the CSV.
    df_found = df.dropna(subset=["center_x", "center_y"])
    csv_file = os.path.join(
        os.path.dirname(image_file),
        f"centers_xatol_{xatol}_frameinterval_{frame_interval}.csv"
    )
    df_found.to_csv(csv_file, index=False)
    print(f"Created CSV with {len(df_found)} found centers in {time.time()} seconds:\n{csv_file}")
