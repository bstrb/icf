# chunk_processing.py
import numpy as np
import h5py
from image_processing import process_single_image

def compute_centers_for_chunk(args):
    (frame_nums, data_indices, image_file, mask, n_wedges, n_rad_bins,
     xatol, fatol, verbose, xmin, xmax, ymin, ymax) = args

    results = []
    with h5py.File(image_file, 'r') as f:
        images = f['/entry/data/images']
        for i, fn in enumerate(frame_nums):
            img = images[fn].astype(np.float32)
            cx, cy = process_single_image(img, mask, n_wedges, n_rad_bins, xatol, fatol, verbose)
            if not (np.isfinite(cx) and np.isfinite(cy) and xmin <= cx < xmax and ymin <= cy < ymax):
                cx, cy = np.nan, np.nan
            results.append((fn, data_indices[i], cx, cy))
    return results
