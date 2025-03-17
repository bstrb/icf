# image_processing.py
import numpy as np
import h5py

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
