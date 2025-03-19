#!/usr/bin/env python3
import h5py
import pandas as pd
import os
import time
import logging
from tqdm import tqdm
from multiprocessing import Process
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_copy_h5_entry(original_h5_path: str, new_h5_path: str) -> None:
    """
    Copy the entire 'entry' group from the source file to the destination file
    using h5py.File.copy. This function is meant to be run in a separate process.
    
    Parameters:
        original_h5_path (str): Path to the original HDF5 file.
        new_h5_path (str): Path where the new HDF5 file will be created.
    """
    with h5py.File(original_h5_path, 'r') as src, h5py.File(new_h5_path, 'w') as dst:
        dst.copy(src["entry"], "entry")

def create_updated_h5_pb(
    original_h5_path: str,
    new_h5_path: str,
    csv_path: str,
    use_progress: bool = True,
    framesize: int = 1024,
    pixels_per_meter: float = 17857.14285714286
) -> None:
    """
    Create a new HDF5 file by copying the original file's structure,
    updating datasets based on CSV data, and recalculating detector shifts.
    This version runs the copy in a separate process so that progress can be
    monitored via file size changes.
    
    Parameters:
        original_h5_path (str): Path to the original HDF5 file.
        new_h5_path (str): Path where the updated HDF5 file will be created.
        csv_path (str): Path to the CSV file with updated center coordinates.
        use_progress (bool): Whether to display a progress bar during the copy.
        framesize (int): Frame size used for recalculating shifts.
        pixels_per_meter (float): Conversion factor from pixels to meters.
    """
    # Overwrite protection: do not overwrite an existing file.
    if os.path.exists(new_h5_path):
        logging.error(f"File {new_h5_path} already exists. Exiting to avoid overwrite.")
        raise FileExistsError(f"File {new_h5_path} already exists.")

    # 1. Read CSV data and validate required columns.
    try:
        df: pd.DataFrame = pd.read_csv(csv_path)
    except Exception as e:
        logging.exception("Failed to read CSV file.")
        raise e
    required_cols = ['data_index', 'center_x', 'center_y']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"CSV file must contain columns: {required_cols}")

    # 2. Retrieve the HDF5 index from the original file.
    try:
        with h5py.File(original_h5_path, 'r') as src:
            h5_index = src['entry/data/index'][()]
    except Exception as e:
        logging.exception("Failed to open original HDF5 file or access 'entry/data/index'.")
        raise e

    # 3. Filter CSV data based on the HDF5 index.
    df_filtered: pd.DataFrame = df[df['data_index'].isin(h5_index)].copy()
    df_filtered.set_index('data_index', inplace=True)
    df_filtered = df_filtered.reindex(h5_index)
    if df_filtered.isnull().values.any():
        raise ValueError("Not all indices in the HDF5 file were found in the CSV file.")

    center_x = df_filtered['center_x'].values
    center_y = df_filtered['center_y'].values

    # 4. Copy the original HDF5 file structure to a new file using a separate process.
    try:
        if use_progress:
            original_size = os.path.getsize(original_h5_path)
            with tqdm(total=original_size, unit='B', unit_scale=True, unit_divisor=1024,
                      desc="Copying HDF5 file",
                      bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                # Launch the copy in a separate process.
                copy_process = Process(target=process_copy_h5_entry, args=(original_h5_path, new_h5_path))
                copy_process.start()
                # Poll the new file's size until the copy process is done.
                while copy_process.is_alive():
                    try:
                        new_size = os.path.getsize(new_h5_path)
                    except Exception:
                        new_size = 0
                    pbar.n = new_size
                    pbar.refresh()
                    time.sleep(1)
                # Ensure progress bar reaches 100%
                pbar.n = original_size
                pbar.refresh()
                copy_process.join()
        else:
            # If not using progress, perform the copy in the current process.
            with h5py.File(original_h5_path, 'r') as src, h5py.File(new_h5_path, 'w') as dst:
                dst.copy(src["entry"], "entry")
    except Exception as e:
        logging.exception("Failed to copy HDF5 file structure.")
        raise e

    # 5. Update center coordinates and detector shifts in the new file.
    try:
        with h5py.File(new_h5_path, 'r+') as dst:
            # Remove and update center datasets.
            for dset in ['entry/data/center_x', 'entry/data/center_y']:
                if dset in dst:
                    del dst[dset]
            dst.create_dataset('entry/data/center_x', data=center_x, dtype='float64')
            dst.create_dataset('entry/data/center_y', data=center_y, dtype='float64')

            # Recalculate detector shifts.
            presumed_center = framesize / 2.0
            det_shift_x_mm = -((center_x - presumed_center) / pixels_per_meter) * 1000
            det_shift_y_mm = -((center_y - presumed_center) / pixels_per_meter) * 1000

            for dset in ['entry/data/det_shift_x_mm', 'entry/data/det_shift_y_mm']:
                if dset in dst:
                    del dst[dset]
            dst.create_dataset('entry/data/det_shift_x_mm', data=det_shift_x_mm, dtype='float64')
            dst.create_dataset('entry/data/det_shift_y_mm', data=det_shift_y_mm, dtype='float64')
    except Exception as e:
        logging.exception("Failed to update center coordinates or detector shifts.")
        raise e

    logging.info(f"New HDF5 file created: {new_h5_path}")
    logging.info("Center coordinates and detector shifts have been updated.")

if __name__ == '__main__':
    # Define file paths (modify as needed).
    original_h5_path: str = "/Users/xiaodong/Desktop/UOX-data/UOX1/deiced_UOX1_min_15_peak.h5"
    new_h5_path: str = "/Users/xiaodong/Desktop/UOX-data/UOX1/deiced_UOX1_min_15_peak_UPDATED.h5"
    csv_path: str = "/Users/xiaodong/Desktop/UOX-data/UOX1/centers_xatol_0.01_frameinterval_10_lowess_0.10_shifted_0.5_-0.3.csv"
    
    try:
        # Toggle progress bar usage by setting use_progress to True or False.
        create_updated_h5_pb(original_h5_path, new_h5_path, csv_path, use_progress=True)
    except Exception as e:
        logging.error("An error occurred during processing.")
