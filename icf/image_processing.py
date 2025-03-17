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

def process_single_image(img, mask, n_wedges, n_rad_bins, xatol, fatol, verbose):
    """
    Process a single image:
      - Compute the center-of-mass initial guess.
      - Refine the diffraction center.
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

def process_images_chunked(
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
    verbose=False,
    chunk_size=1000  # New parameter for chunking tasks
):
    """
    Creates a CSV with one row per frame with a valid computed center.
    Only the frames specified (first, last, and every frame_interval) are processed.
    
    Introduces chunking in the multiprocessing call to reduce inter-process 
    communication overhead by grouping tasks.
    
    If '/entry/data/index' exists, it's stored in 'data_index';
    otherwise, 'data_index = frame_number'.
    """
    # 1) Determine number of frames and read '/entry/data/index' if present else raise error.

    with h5py.File(image_file, 'r') as f:
        n_images = f['/entry/data/images'].shape[0]
        index_dset = f.get('/entry/data/index')
        if index_dset is not None:
            data_index_all = index_dset[:]
        else:
            raise ValueError("Dataset '/entry/data/index' is required for correct processing but was not found in the file.")

    # 2) Create a DataFrame with n_images rows, initialized with NaN centers.
    df = pd.DataFrame({
        "frame_number": np.arange(n_images),
        "data_index": data_index_all,
        "center_x": np.full(n_images, np.nan, dtype=float),
        "center_y": np.full(n_images, np.nan, dtype=float),
    })

    # 3) Identify frames to process: first (0), last (n_images-1), and multiples of frame_interval.
    frames_to_process = set([0, n_images - 1]) | {i for i in range(n_images) if i % frame_interval == 0}
    frames_to_process = sorted(frames_to_process)

    # 4) Build argument tuples for multiprocessing.
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

    # 5) Parallel center-finding with chunking.
    start_time = time.time()
    with Pool() as pool:
        results = list(
            tqdm(
                pool.imap(compute_center_for_frame, tasks, chunksize=chunk_size),
                total=len(tasks),
                desc="Processing frames"
            )
        )

    # 6) Place the results back into the DataFrame.
    for (fn, cx, cy) in results:
        df.at[fn, "center_x"] = cx
        df.at[fn, "center_y"] = cy

    # 7) Filter DataFrame to only include frames with found centers (non-NaN values).
    df_found = df.dropna(subset=["center_x", "center_y"])

    # 8) Write CSV with only found centers.
    csv_file = os.path.join(
        os.path.dirname(image_file),
        f"centers_xatol_{xatol}_frameinterval_{frame_interval}.csv"
    )
    df_found.to_csv(csv_file, index=False)

    elapsed = time.time() - start_time
    print(f"Created CSV with {len(df_found)} found centers in {elapsed:.1f}s:\n{csv_file}")