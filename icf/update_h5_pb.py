#!/usr/bin/env python3
import h5py
import pandas as pd
import os
import time
import threading
import logging
from tqdm import tqdm
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def monitor_progress(original_h5_path: str, new_h5_path: str, progress_bar: tqdm, stop_event: threading.Event) -> None:
    """
    Monitor the progress of the HDF5 file copy by checking the new file's size.
    
    Parameters:
        original_h5_path (str): Path to the original HDF5 file.
        new_h5_path (str): Path to the new HDF5 file.
        progress_bar (tqdm): A tqdm progress bar instance.
        stop_event (threading.Event): An event to signal when to stop monitoring.
    """
    try:
        while not stop_event.is_set():
            try:
                new_size = os.path.getsize(new_h5_path)
            except Exception:
                new_size = 0
            progress_bar.n = new_size
            progress_bar.refresh()
            time.sleep(1)
    finally:
        # Ensure the progress bar is fully updated at the end.
        progress_bar.n = progress_bar.total
        progress_bar.refresh()

def copy_h5_entry(src: h5py.File, dst: h5py.File) -> None:
    """
    Copy the entire 'entry' group from the source file to the destination file
    using h5py.File.copy.
    
    Parameters:
        src (h5py.File): Source HDF5 file.
        dst (h5py.File): Destination HDF5 file.
    """
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

    # 4. Copy the original HDF5 file structure to a new file.
    try:
        if use_progress:
            original_size = os.path.getsize(original_h5_path)
            with h5py.File(original_h5_path, 'r') as src, h5py.File(new_h5_path, 'w') as dst:
                with tqdm(total=original_size, unit='B', unit_scale=True, unit_divisor=1024,
                          desc="Copying HDF5 file",
                          bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
                    stop_event = threading.Event()
                    monitor_thread = threading.Thread(
                        target=monitor_progress,
                        args=(original_h5_path, new_h5_path, pbar, stop_event)
                    )
                    monitor_thread.start()
                    try:
                        copy_h5_entry(src, dst)
                    except Exception as e:
                        logging.exception("Error during HDF5 file copy.")
                        raise e
                    finally:
                        # Ensure thread cleanup.
                        stop_event.set()
                        monitor_thread.join()
        else:
            with h5py.File(original_h5_path, 'r') as src, h5py.File(new_h5_path, 'w') as dst:
                copy_h5_entry(src, dst)
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
