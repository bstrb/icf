#!/usr/bin/env python3
import h5py
import pandas as pd

def create_updated_h5(original_h5_path, new_h5_path, csv_path, framesize=1024, pixels_per_meter=17857.14285714286):
    """
    Create a new HDF5 file by copying the original file's structure,
    update the center_x and center_y datasets using CSV data (only for rows
    whose 'data_index' matches the entries in entry/data/index), and recalculate
    detector shifts (det_shift_x_mm and det_shift_y_mm).

    Parameters
    ----------
    original_h5_path : str
        Path to the original HDF5 file.
    new_h5_path : str
        Path where the updated HDF5 file will be created.
    csv_path : str
        Path to the CSV file containing updated centers. The CSV must contain
        the columns: data_index, center_x, and center_y.
    framesize : int, optional
        Size of the frame (assumed square) used for recalculating shifts (default is 1024).
    pixels_per_meter : float, optional
        Conversion factor from pixels to meters (default is 17857.14285714286).
    """
    # 1. Read CSV data and ensure required columns exist
    df = pd.read_csv(csv_path)
    required_cols = ['data_index', 'center_x', 'center_y']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"CSV file must contain columns: {required_cols}")

    # 2. Open the original HDF5 file and read the 'entry/data/index' dataset
    with h5py.File(original_h5_path, 'r') as src:
        h5_index = src['entry/data/index'][()]

    # 3. Filter CSV to keep only rows with matching data_index, and reindex
    df_filtered = df[df['data_index'].isin(h5_index)].copy()
    # Set data_index as the index for alignment
    df_filtered.set_index('data_index', inplace=True)
    # Reorder rows to match the order in the HDF5 file
    df_filtered = df_filtered.reindex(h5_index)
    if df_filtered.isnull().values.any():
        raise ValueError("Not all indices in the HDF5 file were found in the CSV file.")

    # Extract centers in the order of the HDF5 index
    center_x = df_filtered['center_x'].values
    center_y = df_filtered['center_y'].values

    # 4. Copy the original HDF5 file structure into a new file
    with h5py.File(original_h5_path, 'r') as src, h5py.File(new_h5_path, 'w') as dst:
        src.copy('entry', dst)

    # 5. Reopen the new file in read-write mode to update datasets
    with h5py.File(new_h5_path, 'r+') as dst:
        # Remove and recreate center_x and center_y datasets
        for dset in ['entry/data/center_x', 'entry/data/center_y']:
            if dset in dst:
                del dst[dset]
        dst.create_dataset('entry/data/center_x', data=center_x, dtype='float64')
        dst.create_dataset('entry/data/center_y', data=center_y, dtype='float64')

        # 6. Compute the new detector shifts
        presumed_center = framesize / 2.0
        det_shift_x_mm = -((center_x - presumed_center) / pixels_per_meter) * 1000
        det_shift_y_mm = -((center_y - presumed_center) / pixels_per_meter) * 1000

        # Remove and recreate detector shift datasets
        for dset in ['entry/data/det_shift_x_mm', 'entry/data/det_shift_y_mm']:
            if dset in dst:
                del dst[dset]
        dst.create_dataset('entry/data/det_shift_x_mm', data=det_shift_x_mm, dtype='float64')
        dst.create_dataset('entry/data/det_shift_y_mm', data=det_shift_y_mm, dtype='float64')

    print(f"New HDF5 file created: {new_h5_path}")
    print("Center coordinates and detector shifts have been updated.")

if __name__ == '__main__':
    # Modify these paths as needed
    original_h5_path = "/home/bubl3932/files/UOX1/UOX1_original/UOX1_sub/UOX1_subset.h5"
    new_h5_path = "/home/bubl3932/files/UOX1/UOX1_original/UOX1_sub/UOX1_subset_UPDATED.h5"
    csv_path = "/home/bubl3932/files/UOX1/UOX1_original/UOX1_sub/filtered_centers.csv"
    
    create_updated_h5(original_h5_path, new_h5_path, csv_path)
