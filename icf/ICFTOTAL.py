import numpy as np
from scipy.optimize import minimize
import numba

def center_of_mass_initial_guess(image, mask):
    """
    Compute a rough center-of-mass (CoM) for the image using valid pixels only.
    This will serve as our initial guess for the diffraction center.
    """
    rows, cols = np.indices(image.shape)
    valid_intensity = image[mask]
    valid_rows = rows[mask]
    valid_cols = cols[mask]
    total_intensity = np.sum(valid_intensity)
    if total_intensity == 0:
        return (image.shape[1] / 2.0, image.shape[0] / 2.0)
    cx = np.sum(valid_cols * valid_intensity) / total_intensity
    cy = np.sum(valid_rows * valid_intensity) / total_intensity
    return (cx, cy)

@numba.njit

def compute_bin_medians(wedge_vals, bin_indices, n_bins):
    result = np.empty(n_bins, dtype=np.float64)
    for bin_i in range(n_bins):
        count = 0
        for j in range(wedge_vals.shape[0]):
            if bin_indices[j] == bin_i:
                count += 1
        if count == 0:
            result[bin_i] = np.nan
        else:
            tmp = np.empty(count, dtype=np.float64)
            k = 0
            for j in range(wedge_vals.shape[0]):
                if bin_indices[j] == bin_i:
                    tmp[k] = wedge_vals[j]
                    k += 1
            tmp.sort()
            if count % 2 == 1:
                result[bin_i] = tmp[count // 2]
            else:
                result[bin_i] = 0.5 * (tmp[count // 2 - 1] + tmp[count // 2])
    return result

def compute_wedge_radial_profiles(image, mask, base_center, center,
                                  dx_base, dy_base,
                                  n_wedges=8, n_rad_bins=200, r_max=None):
    """
    Compute wedge profiles using precomputed differences from a fixed base center,
    with the effective center provided.

    The effective center is used to compute a candidate shift relative to the base_center,
    i.e.:
        shift = (center[0] - base_center[0], center[1] - base_center[1])
    Then, the new dx and dy arrays are computed as:
        new_dx = dx_base - shift[0]  -->  cols - (base_center[0] + shift[0]) = cols - center[0]
        new_dy = dy_base - shift[1]  -->  rows - center[1]

    Parameters:
      image : 2D array-like
          The image data.
      mask : 2D boolean array-like
          A mask selecting valid pixels.
      base_center : tuple of floats
          The center used to precompute dx_base and dy_base.
      center : tuple of floats
          The effective center for which the wedge profiles are computed.
      dx_base, dy_base : 2D array-like
          Precomputed differences using base_center.
      n_wedges : int, optional
          Number of angular wedges.
      n_rad_bins : int, optional
          Number of radial bins.
      r_max : float, optional
          Maximum radial distance to consider. If None, defaults to half the smallest image dimension.

    Returns:
      wedge_profiles : list
          List of radial profiles (one per wedge).
      r_centers : 1D array
          The radial bin centers.
    """
    # Compute the shift relative to the base_center.
    shift = (center[0] - base_center[0], center[1] - base_center[1])
    new_dx = dx_base - shift[0]  # Equivalent to: cols - center[0]
    new_dy = dy_base - shift[1]  # Equivalent to: rows - center[1]
    r = np.sqrt(new_dx**2 + new_dy**2)
    theta = np.arctan2(new_dy, new_dx)
    
    if r_max is None:
        r_max = min(image.shape) / 2.0
    r_edges = np.linspace(0, r_max, n_rad_bins + 1)
    
    wedge_profiles = []
    wedge_step = 2 * np.pi / n_wedges
    for w in range(n_wedges):
        angle_min = -np.pi + w * wedge_step
        angle_max = -np.pi + (w + 1) * wedge_step
        wedge_mask = (theta >= angle_min) & (theta < angle_max) & mask
        r_wedge = r[wedge_mask]
        wedge_vals = image[wedge_mask]
        bin_indices = np.digitize(r_wedge, r_edges) - 1  # bins 0 to n_rad_bins-1
        profile = compute_bin_medians(wedge_vals, bin_indices, n_rad_bins)
        wedge_profiles.append(profile)
        
    r_centers = 0.5 * (r_edges[:-1] + r_edges[1:])
    return wedge_profiles, r_centers

def center_asymmetry_metric(candidate_center, image, mask, base_center, dx_base, dy_base,
                            n_wedges=4, n_rad_bins=100, debug=False):
    """
    Compute the asymmetry metric for a given candidate center relative to a fixed base_center.
    The image is split into n_wedges, and the radial median profiles for opposite wedges are compared.
    The metric is the average squared difference between the two profiles.
    """
    wedge_profiles, _ = compute_wedge_radial_profiles(image, mask, base_center, candidate_center,
                                                      dx_base, dy_base,
                                                      n_wedges=n_wedges, n_rad_bins=n_rad_bins)
    half = n_wedges // 2
    total_diff = 0.0
    count = 0
    for i in range(half):
        p1 = wedge_profiles[i]
        p2 = wedge_profiles[i + half]
        # Only consider points where both wedges have valid (non-NaN) values
        valid = ~np.isnan(p1) & ~np.isnan(p2)
        if np.any(valid):
            diff = p1[valid] - p2[valid]
            total_diff += np.sum(diff**2)
            count += np.sum(valid)
    metric_val = total_diff / count if count > 0 else np.inf
    if debug:
        print(f"Candidate center: {candidate_center}, Metric: {metric_val}")
    return metric_val

def find_diffraction_center(image, mask, initial_center=None,
                            n_wedges=4, n_rad_bins=100,
                            xatol = 1e-1, fatol = 1e-1,
                            verbose=True, skip_tol=3.0):
    """
    Refine the diffraction center by optimizing the asymmetry metric.
    If the metric at the initial center is already below skip_tol,
    the initial center is returned immediately.
    """
    if initial_center is None:
        initial_center = center_of_mass_initial_guess(image, mask)
    if verbose:
        print("Starting center refinement with initial center:", initial_center)
    
    # Precompute dx_base and dy_base using the fixed initial_center (base_center).
    rows, cols = np.indices(image.shape)
    dx_base = cols - initial_center[0]
    dy_base = rows - initial_center[1]
    
    # Evaluate metric at the initial center.
    initial_metric = center_asymmetry_metric(initial_center, image, mask,
                                             initial_center, dx_base, dy_base,
                                             n_wedges, n_rad_bins, debug=verbose)
    if verbose:
        print("Metric at initial center:", initial_metric)
    if initial_metric < skip_tol:
        if verbose:
            print("Initial center metric is below threshold; skipping optimization.")
        return initial_center

    # Otherwise, perform the optimization.
    x0 = np.array(initial_center)
    if verbose:
        print("Initial center:", x0)
    res = minimize(center_asymmetry_metric, x0,
                   args=(image, mask, initial_center, dx_base, dy_base, n_wedges, n_rad_bins, verbose),
                   method='Nelder-Mead',
                   options={'xatol': xatol, 'fatol': fatol, 'maxiter': 100})
    refined_center = res.x
    if verbose:
        print("Final refined center:", refined_center)
    
    return tuple(refined_center)
