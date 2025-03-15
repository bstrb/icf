# image_processing.py

from ICFTOTAL import center_of_mass_initial_guess, find_diffraction_center

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
