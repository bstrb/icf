# ICFTOTAL.py

import numpy as np
from scipy.optimize import minimize
import numba

def center_of_mass_initial_guess(image, mask):
    """
    Compute a rough center-of-mass (CoM) for the image using valid pixels only.
    Returns (cx, cy).
    """
    rows, cols = np.indices(image.shape)
    valid_intensity = image[mask]
    valid_rows = rows[mask]
    valid_cols = cols[mask]
    total_intensity = np.sum(valid_intensity)
    if total_intensity == 0:
        # Default to geometric center
        return (image.shape[1] / 2.0, image.shape[0] / 2.0)
    cx = np.sum(valid_cols * valid_intensity) / total_intensity
    cy = np.sum(valid_rows * valid_intensity) / total_intensity
    return (cx, cy)


@numba.njit
def compute_bin_medians(wedge_vals, bin_indices, n_bins):
    """
    Given wedge_vals and bin_indices, compute the median per bin.
    Any bin with no values or any NaN => np.nan for that bin.
    """
    result = np.empty(n_bins, dtype=np.float64)
    for bin_i in range(n_bins):
        count = 0
        any_nan = False
        # First pass: count values & check NaNs
        for j in range(wedge_vals.shape[0]):
            if bin_indices[j] == bin_i:
                if np.isnan(wedge_vals[j]):
                    any_nan = True
                count += 1
        if count == 0 or any_nan:
            result[bin_i] = np.nan
        else:
            # Collect and sort values
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
                mid = count // 2
                result[bin_i] = 0.5 * (tmp[mid - 1] + tmp[mid])
    return result


def build_symmetric_mask_fast(image_shape, global_mask, center_yx):
    """
    Fast approach for ensuring mirrored pixels are both valid or both invalid.
    center_yx = (cy, cx).
    Returns a 2D boolean mask.
    """
    rows, cols = image_shape
    cy, cx = center_yx

    y_indices, x_indices = np.indices(image_shape)
    y_flat = y_indices.ravel()
    x_flat = x_indices.ravel()
    N = y_flat.size

    global_valid = global_mask.ravel()
    sym_valid = np.zeros_like(global_valid, dtype=np.bool_)

    # Round mirror coords
    mirror_x = np.round(2.0*cx - x_flat).astype(np.int32)
    mirror_y = np.round(2.0*cy - y_flat).astype(np.int32)

    # Flattened mirror index
    mirror_index = np.full(N, -1, dtype=np.int64)
    for i in range(N):
        mx = mirror_x[i]
        my = mirror_y[i]
        if (0 <= mx < cols) and (0 <= my < rows):
            mirror_index[i] = my * cols + mx

    # Single pass to mark pairs
    for i in range(N):
        j = mirror_index[i]
        if j < 0:
            continue  # out of range => exclude
        if j > i:
            if global_valid[i] and global_valid[j]:
                sym_valid[i] = True
                sym_valid[j] = True
        elif j == i:
            # Pixel is its own mirror (exactly on the center)
            if global_valid[i]:
                sym_valid[i] = True
        # if j < i, it was handled already

    return sym_valid.reshape(image_shape)


def compute_wedge_radial_profiles(image, mask, base_center, center,
                                  dx_base, dy_base,
                                  n_wedges=8, n_rad_bins=200,
                                  r_min=0, r_max=None):
    """
    Compute radial profiles for image wedges using a shifted center.
    Returns (wedge_profiles, r_centers).
    """
    shift = (center[0] - base_center[0], center[1] - base_center[1])
    new_dx = dx_base - shift[0]
    new_dy = dy_base - shift[1]
    r = np.sqrt(new_dx**2 + new_dy**2)
    theta = np.arctan2(new_dy, new_dx)

    if r_max is None:
        r_max = min(image.shape) / 2.0
    r_edges = np.linspace(r_min, r_max, n_rad_bins + 1)

    wedge_profiles = []
    wedge_step = 2*np.pi / n_wedges

    for w in range(n_wedges):
        angle_min = -np.pi + w * wedge_step
        angle_max = -np.pi + (w + 1) * wedge_step
        wedge_mask = (theta >= angle_min) & (theta < angle_max) & mask
        r_wedge = r[wedge_mask]
        wedge_vals = image[wedge_mask]
        bin_indices = np.digitize(r_wedge, r_edges) - 1
        profile = compute_bin_medians(wedge_vals, bin_indices, n_rad_bins)
        wedge_profiles.append(profile)

    r_centers = 0.5 * (r_edges[:-1] + r_edges[1:])
    return wedge_profiles, r_centers


def center_asymmetry_metric(candidate_center, image, global_mask,
                            base_center, dx_base, dy_base,
                            n_wedges=4, n_rad_bins=100, debug=False):
    """
    Compute the asymmetry metric with mirrored-pixel exclusion:
    - Build symmetric mask
    - Compute wedge profiles
    - Compare opposite wedges
    """
    # Because code typically uses (cx, cy), but mask-building uses (cy, cx),
    # we swap the candidate_center here:
    cy_cx = (candidate_center[1], candidate_center[0])
    sym_mask = build_symmetric_mask_fast(image.shape, global_mask, cy_cx)

    wedge_profiles, _ = compute_wedge_radial_profiles(
        image, sym_mask,
        base_center, candidate_center,
        dx_base, dy_base,
        n_wedges=n_wedges, n_rad_bins=n_rad_bins
    )

    half = n_wedges // 2
    total_diff = 0.0
    count = 0
    for i in range(half):
        p1 = wedge_profiles[i]
        p2 = wedge_profiles[i + half]
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
                            xatol=1e-1, fatol=1e-1,
                            verbose=True, skip_tol=3.0):
    """
    Main entry point for refining the diffraction center.
    """
    if initial_center is None:
        initial_center = center_of_mass_initial_guess(image, mask)
    if verbose:
        print("Starting center refinement with initial center:", initial_center)

    rows, cols = np.indices(image.shape)
    dx_base = cols - initial_center[0]
    dy_base = rows - initial_center[1]

    # Evaluate metric at the initial center
    initial_metric = center_asymmetry_metric(
        initial_center, image, mask,
        initial_center, dx_base, dy_base,
        n_wedges=n_wedges, n_rad_bins=n_rad_bins, debug=verbose
    )
    if verbose:
        print("Metric at initial center:", initial_metric)

    # Skip if below threshold
    if initial_metric < skip_tol:
        if verbose:
            print("Initial center metric is below threshold; skipping optimization.")
        return initial_center

    x0 = np.array(initial_center, dtype=float)
    if verbose:
        print("Initial center (x0):", x0)

    res = minimize(
        center_asymmetry_metric,
        x0,
        args=(image, mask, initial_center, dx_base, dy_base, n_wedges, n_rad_bins, verbose),
        method='Nelder-Mead',
        options={'xatol': xatol, 'fatol': fatol, 'maxiter': 300}
    )
    refined_center = res.x
    if verbose:
        print("Final refined center:", refined_center)

    return tuple(refined_center)
