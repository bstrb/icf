import os
import h5py
import numpy as np
import pandas as pd
from multiprocessing import Pool
from tqdm import tqdm

# Import the center-finding code
from icf_src import center_of_mass_initial_guess, find_diffraction_center

###############################################################################
# Global variables in each worker (populated by worker_init)
images_dset = None
global_mask = None

# Optional: store n_wedges, n_rad_bins, etc. if you like
n_wedges_global = 4
n_rad_bins_global = 100
xatol_global = 0.01
fatol_global = 10
verbose_global = False
xmin_global = 0
xmax_global = 1024
ymin_global = 0
ymax_global = 1024

###############################################################################
def worker_init(h5_path, mask_array,
                n_wedges, n_rad_bins, xatol, fatol,
                verbose, xmin, xmax, ymin, ymax):
    """
    Called once per worker process.  
    We open the HDF5 file in read-only mode and store relevant globals.
    """
    global images_dset, global_mask
    global n_wedges_global, n_rad_bins_global
    global xatol_global, fatol_global, verbose_global
    global xmin_global, xmax_global, ymin_global, ymax_global

    # Open the file (SWMR if available), read-only
    # If your HDF5 build doesn't support swmr=True, you can omit it
    file_obj = h5py.File(h5_path, 'r', swmr=True)
    images_dset = file_obj['/entry/data/images']  # store handle to dataset

    # Store mask in global variable
    global_mask = mask_array

    # Store other parameters
    n_wedges_global = n_wedges
    n_rad_bins_global = n_rad_bins
    xatol_global = xatol
    fatol_global = fatol
    verbose_global = verbose
    xmin_global, xmax_global = xmin, xmax
    ymin_global, ymax_global = ymin, ymax


def process_one_frame(frame_num):
    """
    Each worker uses this to process a single frame, returning (frame_num, cx, cy).
    """
    global images_dset, global_mask
    global n_wedges_global, n_rad_bins_global
    global xatol_global, fatol_global, verbose_global
    global xmin_global, xmax_global
    global ymin_global, ymax_global

    # Load the image from the globally opened dataset
    img = images_dset[frame_num].astype(np.float32)

    # 1) Compute center-of-mass guess
    init_center = center_of_mass_initial_guess(img, global_mask)

    # 2) Check if guess is out-of-bounds
    cx_guess, cy_guess = init_center
    if not (xmin_global <= cx_guess < xmax_global and
            ymin_global <= cy_guess < ymax_global):
        return (frame_num, np.nan, np.nan)

    # 3) Refine
    refined_center = find_diffraction_center(
        img,
        global_mask,
        initial_center=init_center,
        n_wedges=n_wedges_global,
        n_rad_bins=n_rad_bins_global,
        xatol=xatol_global,
        fatol=fatol_global,
        verbose=verbose_global,
        skip_tol=3.0   # or some other threshold
    )

    cx, cy = refined_center
    # 4) Check final validity
    if not (xmin_global <= cx < xmax_global and ymin_global <= cy < ymax_global):
        return (frame_num, np.nan, np.nan)

    return (frame_num, cx, cy)


def process_images_apply_async(
    image_file,
    mask,
    frame_interval=10,
    n_wedges=4,
    n_rad_bins=100,
    xatol=0.01,
    fatol=10,
    xmin=0,
    xmax=1024,
    ymin=0,
    ymax=1024,
    verbose=False
):
    """
    Multiprocessing routine using an initializer for each worker.
    Reads frames from image_file, finds centers, writes to CSV.
    """
    # 1) Open H5 file on main process just to get total frames & index
    with h5py.File(image_file, 'r') as f:
        n_images = f['/entry/data/images'].shape[0]
        index_dset = f.get('/entry/data/index')
        if index_dset is not None:
            data_index_all = index_dset[:]
        else:
            raise ValueError("'/entry/data/index' not found.")

    # 2) Prepare a DataFrame
    df = pd.DataFrame({
        "frame_number": np.arange(n_images),
        "data_index": data_index_all,
        "center_x": np.full(n_images, np.nan, dtype=float),
        "center_y": np.full(n_images, np.nan, dtype=float),
    })

    # 3) Determine which frames to process
    frames_to_process = set([0, n_images - 1]) | {i for i in range(n_images) if i % frame_interval == 0}
    frames_to_process = sorted(frames_to_process)

    # 4) Create a Pool with our worker_init
    #    Each worker: opens the file, sets global_mask, etc.
    with Pool(
        processes=None,  # or a fixed number if you prefer
        initializer=worker_init,
        initargs=(
            image_file,
            mask,
            n_wedges, n_rad_bins,
            xatol, fatol,
            verbose,
            xmin, xmax,
            ymin, ymax
        )
    ) as pool:

        # 5) Use imap_unordered for efficient scheduling
        results_iter = pool.imap_unordered(process_one_frame, frames_to_process)

        # 6) Collect results in a progress bar
        for (frame_num, cx, cy) in tqdm(results_iter,
                                        total=len(frames_to_process),
                                        desc="Processing frames",
                                        unit="frame"):
            df.at[frame_num, "center_x"] = cx
            df.at[frame_num, "center_y"] = cy

    # 7) Keep only the processed frames, write CSV
    df = df[df["frame_number"].isin(frames_to_process)]
    csv_file = os.path.join(
        os.path.dirname(image_file),
        f"centers_xatol_{xatol}_frameinterval_{frame_interval}.csv"
    )
    df.to_csv(csv_file, index=False)
    print(f"Saved {len(df)} centers to:\n{csv_file}")
