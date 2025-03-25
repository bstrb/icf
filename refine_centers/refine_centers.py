import re
import os
import numpy as np
import csv
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

#########################################
# 1) PARSE GEOMETRY FROM HEADER
#########################################
def parse_header_geometry(stream_text):
    """
    Extract wavelength, clen, and res from the geometry file block.
    Returns a dict, e.g.:
    {
        'wavelength_A': float,
        'clen_m': float,
        'res': float,
        'pixel_size_mm': float
    }
    """
    geom = {}

    # Find the geometry block
    geom_block_pat = re.compile(
        r'----- Begin geometry file -----\s*(.*?)\s*----- End geometry file -----',
        re.DOTALL
    )
    m_geom_block = geom_block_pat.search(stream_text)
    if m_geom_block:
        block = m_geom_block.group(1)

        # Regex for lines like:
        #   wavelength  = 0.019687 A
        #   clen = 1.885 m
        #   res = 17857.14285714286
        wl_pat = re.compile(r'wavelength\s*=\s*([\d.eE+-]+)\s*A')
        cl_pat = re.compile(r'clen\s*=\s*([\d.eE+-]+)\s*m')
        res_pat = re.compile(r'res\s*=\s*([\d.eE+-]+)')

        m_wl = wl_pat.search(block)
        m_cl = cl_pat.search(block)
        m_res = res_pat.search(block)

        if m_wl:
            geom['wavelength_A'] = float(m_wl.group(1))
        if m_cl:
            geom['clen_m'] = float(m_cl.group(1))
        if m_res:
            geom['res'] = float(m_res.group(1))  # pixels per meter

    # Compute pixel size (mm)
    # If 'res' is px/m, then 1 px = (1/res) m => multiply by 1000 for mm
    # e.g., res=17857 px/m => pixel_size_m=1/17857 => pixel_size_mm=1000/17857=~0.056 mm
    if 'res' in geom:
        geom['pixel_size_mm'] = 1000.0 / geom['res']
    else:
        geom['pixel_size_mm'] = 0.1  # fallback or guess

    return geom

#########################################
# 2) PARSE ONE CHUNK
#########################################
def parse_stream_chunk(chunk):
    """
    Extract:
      - event index
      - astar, bstar, cstar (nm^-1 -> A^-1)
      - reflections: (h, k, l, fs, ss)
    Returns (evt_idx, astar, bstar, cstar, refl_list).
    """
    # Event index
    event_pat = re.compile(r"Event:\s*//(\d+)")
    m_ev = event_pat.search(chunk)
    if not m_ev:
        return None
    evt_idx = int(m_ev.group(1))

    # Reciprocal vectors in nm^-1, e.g.
    #   astar = -0.0466028 +0.0578149 +0.1018047 nm^-1
    # We’ll convert nm^-1 -> A^-1 by multiplying by 0.1
    vec_pat = re.compile(
        r'(astar|bstar|cstar)\s*=\s*([+\-0-9.e]+)\s+([+\-0-9.e]+)\s+([+\-0-9.e]+)\s+nm\^-1'
    )
    recips = {}
    for name, x, y, z in vec_pat.findall(chunk):
        xx = float(x)*0.1
        yy = float(y)*0.1
        zz = float(z)*0.1
        recips[name] = np.array([xx, yy, zz], dtype=float)
    if len(recips) < 3:
        return None

    # Reflection block
    refl_block_pat = re.compile(
        r"Reflections measured after indexing(.*?)End of reflections",
        re.DOTALL
    )
    m_refl_block = refl_block_pat.search(chunk)
    if not m_refl_block:
        return None

    block_text = m_refl_block.group(1)

    # Lines typically start with h,k,l => first col is numeric
    refl_line_pat = re.compile(r'^\s*-?\d+', re.MULTILINE)
    raw_lines = block_text.strip().splitlines()

    refl_list = []
    for line_str in raw_lines:
        if refl_line_pat.match(line_str.strip()):
            parts = line_str.split()
            if len(parts) < 9:
                continue
            try:
                h = int(parts[0])
                k = int(parts[1])
                l = int(parts[2])
                fs_meas = float(parts[7])
                ss_meas = float(parts[8])
                refl_list.append((h, k, l, fs_meas, ss_meas))
            except:
                pass

    return (
        evt_idx,
        recips['astar'], 
        recips['bstar'], 
        recips['cstar'], 
        refl_list
    )

#########################################
# 3) DIFFRACTION MODEL
#########################################
def build_orientation_matrix(astar, bstar, cstar):
    """
    Simple orientation matrix: columns = [astar, bstar, cstar].
    In real usage, you might incorporate a rotation matrix from indexing.
    """
    return np.column_stack((astar, bstar, cstar))

def predict_fs_ss(h, k, l, R, k_in, dist_mm, px_mm, cx, cy):
    """
    Predict the (fs, ss) for reflection (h,k,l).
      - R: 3x3 orientation matrix
      - k_in: incident wave vector (0,0,k)
      - dist_mm: distance to detector plane (mm)
      - px_mm: pixel size (mm)
      - cx, cy: beam center in pixel units
    """
    hkl = np.array([h, k, l], dtype=float)
    G_lab = R @ hkl
    k_scat = k_in + G_lab  # scattered wave vector

    kz = k_scat[2]
    if abs(kz) < 1e-12:
        return np.nan, np.nan  # reflection near horizon or invalid

    # Intersection with plane z=dist_mm
    t = dist_mm / kz
    X = t * k_scat[0]
    Y = t * k_scat[1]

    # Convert to pixels
    fs_pred = cx + (X / px_mm)
    ss_pred = cy + (Y / px_mm)
    return fs_pred, ss_pred

def residual_beam_center(params, reflections, R, k_in, dist_mm, px_mm):
    """
    Residual function for least_squares.
    params = [cx, cy]
    reflections = list of (h,k,l, fs_meas, ss_meas).
    """
    (cx, cy) = params
    diffs = []
    for (h, k, l, fs_m, ss_m) in reflections:
        fs_p, ss_p = predict_fs_ss(h, k, l, R, k_in, dist_mm, px_mm, cx, cy)
        if not np.isnan(fs_p) and not np.isnan(ss_p):
            diffs.append(fs_p - fs_m)
            diffs.append(ss_p - ss_m)
        else:
            diffs.append(0.0)
            diffs.append(0.0)
    return np.array(diffs)

def refine_beam_center(
    astar, bstar, cstar, 
    reflections, 
    wavelength_A, 
    clen_m, 
    px_size_mm,
    guess_cx=512.0, 
    guess_cy=512.0
):
    """
    Refine beam center for a single chunk.
    """
    # Build orientation matrix
    R = build_orientation_matrix(astar, bstar, cstar)

    # In CrystFEL, the wavevector magnitude is typically k=1/lambda in A^-1
    k_val = 1.0 / wavelength_A
    k_in = np.array([0.0, 0.0, k_val], dtype=float)

    dist_mm = clen_m * 1000.0  # convert m -> mm

    # Initial guess
    params0 = np.array([guess_cx, guess_cy], dtype=float)

    res = least_squares(
        residual_beam_center,
        x0=params0,
        args=(reflections, R, k_in, dist_mm, px_size_mm),
        method='lm',
        max_nfev=1000
    )
    return tuple(res.x)

#########################################
# 4) WRAPPER FOR PARALLEL PROCESSING
#########################################
def process_one_chunk(chunk, geom):
    """
    Parse the chunk, then refine the beam center using the geometry from 'geom'.
    Returns (event_index, cx_refined, cy_refined) or None on failure.
    """
    parsed = parse_stream_chunk(chunk)
    if not parsed:
        return None
    evt_idx, astar, bstar, cstar, refls = parsed
    if not refls:
        return None

    wavelength_A = geom.get('wavelength_A', 1.0)
    clen_m = geom.get('clen_m', 0.2)
    px_size_mm = geom.get('pixel_size_mm', 0.1)
    # Use a naive guess for center
    guess_cx = 512.0
    guess_cy = 512.0

    cx_ref, cy_ref = refine_beam_center(
        astar, bstar, cstar,
        refls,
        wavelength_A,
        clen_m,
        px_size_mm,
        guess_cx, guess_cy
    )
    return (evt_idx, cx_ref, cy_ref)

#########################################
# 5) MAIN FUNCTION
#########################################
def parse_stream_and_refine_multiproc(stream_file):
    """
    Parse geometry from the stream header, then parse & refine each chunk in parallel,
    showing a tqdm progress bar, finally plot refined centers vs. event index.
    """
    with open(stream_file, 'r') as f:
        stream_text = f.read()

    # A) Geometry
    geom = parse_header_geometry(stream_text)
    print("Parsed geometry:", geom)
    # e.g. => {'wavelength_A': 0.019687, 'clen_m': 1.885, 'res': 17857.14285714286, 'pixel_size_mm': 0.056, ...}

    # B) Extract chunks
    chunk_pat = re.compile(
        r'----- Begin chunk -----\s*(.*?)\s*----- End chunk -----',
        re.DOTALL
    )
    chunks = chunk_pat.findall(stream_text)
    print(f"Found {len(chunks)} chunks in the stream file.")

    # C) Parallel processing
    results = []
    from functools import partial
    work_func = partial(process_one_chunk, geom=geom)

    # Use ProcessPoolExecutor to handle in parallel
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor() as executor:
        # Wrap executor.map(...) in a tqdm progress bar
        for result in tqdm(executor.map(work_func, chunks), total=len(chunks), desc="Processing chunks"):
            if result is not None:
                results.append(result)

    # Sort results by event index
    results.sort(key=lambda x: x[0])

    # D) Plot
    evt_indices = [r[0] for r in results]
    cxs = [r[1] for r in results]
    cys = [r[2] for r in results]

    plt.figure()
    plt.plot(evt_indices, cxs, marker='o')
    plt.xlabel('Event index')
    plt.ylabel('Refined center X (px)')
    plt.title('Refined Beam Center X vs. Event Index')
    plt.show()

    plt.figure()
    plt.plot(evt_indices, cys, marker='o')
    plt.xlabel('Event index')
    plt.ylabel('Refined center Y (px)')
    plt.title('Refined Beam Center Y vs. Event Index')
    plt.show()

    csv_filename = os.path.join(os.path.dirname(stream_file),"refined_centers.csv")
    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # Write header row
        writer.writerow(["EventIndex", "RefinedCenterX", "RefinedCenterY"])
        # Write each result row
        for event_index, cx, cy in results:
            writer.writerow([event_index, cx, cy])

    print(f"Results written to {csv_filename}")
    
    return results

# EXAMPLE USAGE:
if __name__ == "__main__":
    # stream_file = "/Users/xiaodong/Desktop/UOX-data/UOX1/centers_xatol_0.01_frameinterval_10_lowess_0.37_shifted_0.5_-0.3/xgandalf_iterations_max_radius_0.0_step_0.5/Xtal_0.0_0.0.stream"
    stream_file = "/home/bubl3932/files/UOX1/UOX1_original/centers_xatol_0.01_frameinterval_10_lowess_0.10_shifted_0.5_-0.3/xgandalf_iterations_max_radius_1.8_step_0.5/UOX_0.0_0.0.stream"
    results = parse_stream_and_refine_multiproc(stream_file)
    # results is a list of (event_index, cx_refined, cy_refined).
