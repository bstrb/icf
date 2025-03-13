import os
import h5py
import numpy as np
import pandas as pd
import time
from multiprocessing import Pool
from tqdm import tqdm

from image_processing import process_single_image

def load_chunk(image_file, start, end):
    """
    Load a chunk of images from the H5 file.
    Slicing the dataset loads only the required subset.
    """
    with h5py.File(image_file, 'r') as f:
        images = f['/entry/data/images']
        chunk = images[start:end].astype(np.float32)
    return chunk

def process_images(image_file, mask, n_wedges=4, n_rad_bins=100, xatol=0.01, fatol=10, chunk_size=1000, frame_interval=10, verbose=False):
    # Open the image file to determine the total number of images.
    with h5py.File(image_file, 'r') as f_img:
        n_images = f_img['/entry/data/images'].shape[0]

    # Compute total frames that will be processed:
    # Always include the first (0) and the last (n_images - 1) frames and any frame where index % frame_interval == 0.
    valid_indices = set([0, n_images - 1]) | {i for i in range(n_images) if i % frame_interval == 0}
    total_centers = len(valid_indices)

    # Define output CSV file path.
    csv_file = os.path.join(os.path.dirname(image_file), f"centers_xatol_{xatol}_frameinterval_{frame_interval}.csv")
    if os.path.exists(csv_file):
        os.remove(csv_file)
    header_written = False
    start_time = time.time()

    # Initialize tqdm progress bar.
    pbar = tqdm(total=total_centers, desc="Calculating centers")

    # Create a multiprocessing Pool.
    with Pool() as pool:
        for start_idx in range(0, n_images, chunk_size):
            end_idx = min(start_idx + chunk_size, n_images)
            # Determine which global frame indices in this chunk to process.
            chunk_frame_indices = [
                i for i in range(start_idx, end_idx)
                if (i == 0 or i == n_images - 1 or (i % frame_interval == 0))
            ]
            if not chunk_frame_indices:
                continue  # Skip this chunk if no frames meet the criteria.

            current_chunk = load_chunk(image_file, start_idx, end_idx)

            # Prepare arguments for each selected image.
            args = [
                (current_chunk[i - start_idx], mask, n_wedges, n_rad_bins, xatol, fatol, verbose)
                for i in chunk_frame_indices
            ]

            # Process selected images in parallel.
            results = pool.starmap(process_single_image, args)

            # Write results incrementally.
            df_chunk = pd.DataFrame(
                [[i, res[0], res[1]] for i, res in zip(chunk_frame_indices, results)],
                columns=["frame_number", "center_x", "center_y"]
            )
            mode = "w" if not header_written else "a"
            df_chunk.to_csv(csv_file, index=False, mode=mode, header=not header_written)
            header_written = True

            # Update progress bar by the number of frames processed in this chunk.
            pbar.update(len(chunk_frame_indices))
            if verbose:
                print(f"Processed frames {chunk_frame_indices[0]} to {chunk_frame_indices[-1]} from chunk {start_idx} to {end_idx}")

    pbar.close()
    elapsed = time.time() - start_time
    print("Processing complete in {:.1f}s".format(elapsed))
    print("CSV file written to:", csv_file)

if __name__ == '__main__':
    # Parameters – adjust these as needed.
    image_file = "/Users/xiaodong/Desktop/UOX-data/UOX1_sub/UOX1_sub.h5"
    mask_file = "/Users/xiaodong/mask/pxmask.h5"
    use_mask = True

    # Load mask from file (or construct one) as needed.
    with h5py.File(mask_file, 'r') as f_mask:
        if use_mask:
            mask = f_mask['/mask'][:].astype(bool)
        else:
            mask_dataset = f_mask['/mask']
            sample_mask = mask_dataset[0]
            mask = np.ones_like(sample_mask, dtype=bool)
    
    xatol = 0.01
    frame_interval = 15  # Calculate centers for every 100th frame (always including first and last).
    
    process_images(image_file, mask, xatol=xatol, frame_interval=frame_interval)

