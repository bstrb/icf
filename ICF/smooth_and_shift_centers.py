#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import h5py

# Lowess from statsmodels
from statsmodels.nonparametric.smoothers_lowess import lowess

# Your custom function for updating .h5 (should be defined in update_h5.py)
from update_h5 import create_updated_h5

def lowess_fit_shift(csv_file, shift_x=0, shift_y=0, lowess_frac=0.1):
    """
    Reads a CSV file with columns 'frame_number', 'center_x', 'center_y',
    applies a Lowess fit to smooth the center coordinates, interpolates to fill
    missing frames, applies a shift, plots the results, and saves the new CSV.
    Returns the path to the newly created CSV.
    """
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

    # Ensure required columns are present.
    for col in ['frame_number', 'center_x', 'center_y']:
        if col not in df.columns:
            print(f"CSV must contain '{col}' column.")
            return None

    # Sort by frame number (in case it isn't already).
    df = df.sort_values('frame_number').reset_index(drop=True)
    frames = df['frame_number'].values
    original_x = df['center_x'].values
    original_y = df['center_y'].values

    # Fit Lowess for X and Y.
    lowess_x = lowess(endog=original_x, exog=frames, frac=lowess_frac, return_sorted=True)
    lowess_y = lowess(endog=original_y, exog=frames, frac=lowess_frac, return_sorted=True)

    # Create a full range of frames (fill in missing frames).
    min_frame = frames.min()
    max_frame = frames.max()
    all_frames = np.arange(min_frame, max_frame + 1)

    # Interpolate the Lowess results for every integer frame.
    smoothed_x = np.interp(all_frames, lowess_x[:, 0], lowess_x[:, 1])
    smoothed_y = np.interp(all_frames, lowess_y[:, 0], lowess_y[:, 1])

    # Apply shifts.
    smoothed_x += shift_x
    smoothed_y += shift_y

    # Create output DataFrame.
    output_df = pd.DataFrame({
        'frame_number': all_frames,
        'center_x': smoothed_x,
        'center_y': smoothed_y
    })

    # Plot original vs. smoothed data.
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))

    axs[0].plot(frames, original_x, 'o--', label='Original X', markersize=4)
    axs[0].plot(all_frames, smoothed_x, 'o-', label='Lowess + shift X', markersize=4)
    axs[0].set_title('Center X')
    axs[0].legend()
    axs[0].set_ylim(min(smoothed_x) - 1, max(smoothed_x) + 1)

    axs[1].plot(frames, original_y, 'o--', label='Original Y', markersize=4)
    axs[1].plot(all_frames, smoothed_y, 'o-', label='Lowess + shift Y', markersize=4)
    axs[1].set_title('Center Y')
    axs[1].legend()
    axs[1].set_ylim(min(smoothed_y) - 1, max(smoothed_y) + 1)

    plt.show()

    # Define the output CSV path.
    output_csv = os.path.join(
        os.path.dirname(csv_file),
        f"centers_lowess_{lowess_frac:.2f}_shifted_{shift_x}_{shift_y}.csv"
    )
    output_df.to_csv(output_csv, index=False)
    print(f"Created CSV with smoothed centers for every frame:\n{output_csv}")
    return output_csv

def update_h5_with_csv(h5_file, shifted_csv_path):
    """
    Updates the given H5 file using the shifted CSV centers.
    The new H5 file is saved in the same directory as the original H5 file.
    """
    new_h5_path = os.path.join(
        os.path.dirname(h5_file),
        os.path.splitext(os.path.basename(h5_file))[0] + os.path.basename(shifted_csv_path)
    )
    try:
        create_updated_h5(h5_file, new_h5_path, shifted_csv_path)
        print(f"Updated H5 file created at:\n{new_h5_path}")
    except Exception as e:
        print("Error updating H5 file:", e)

if __name__ == '__main__':
    # -------------------------
    # Example: Lowess-Fit Centers in CSV (fill missing frames) + Shift
    # -------------------------
    # Adjust the parameters as needed.
    csv_file = "/path/to/your/input_centers.csv"  # Replace with your CSV file path.
    shift_x = 0      # Adjust shift for X coordinate.
    shift_y = 0      # Adjust shift for Y coordinate.
    lowess_frac = 0.1  # Lowess smoothing fraction.
    
    shifted_csv = lowess_fit_shift(csv_file, shift_x=shift_x, shift_y=shift_y, lowess_frac=lowess_frac)
    if shifted_csv is None:
        print("Error processing CSV file.")
        exit(1)
    
    # -------------------------
    # Example: Update H5 with New Centers
    # -------------------------
    h5_file = "/path/to/your/input_file.h5"  # Replace with your H5 file path.
    
    update_h5_with_csv(h5_file, shifted_csv)
