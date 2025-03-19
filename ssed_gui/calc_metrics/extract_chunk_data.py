import re
from .calc_wrmsd import calc_wrmsd
from .calculate_cell_deviation import calculate_cell_deviation
from .match_peaks_to_reflections import match_peaks_to_reflections

def extract_chunk_data(chunk,
                       original_cell_params,
                       wrmsd_tolerance:float=2.0,
                       index_tolerance:float=1.0
                       ):
    # Extract event string (including appended dash and count, if present)
    event_match = re.search(r'Event:\s*//(\d+(?:-\d+)?)', chunk)
    event_string = event_match.group(1) if event_match else None
    if event_string is None:
        print("No event number found in chunk.")

    # Extract peak list with intensities
    peak_list_match = re.search(r'Peaks from peak search(.*?)End of peak list', chunk, re.S)
    if peak_list_match:
        # Regex captures: fs/px, ss/px, (1/d)/nm^-1, Intensity for panel p0
        peaks = re.findall(
            r'\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+p0', 
            peak_list_match.group(1)
        )
        fs_ss = []
        intensities = []
        
        for fs, ss, one_over_d, I in peaks:
            fs_ss.append((float(fs), float(ss)))
            intensities.append(float(I))
        
        if not peaks:
            print("No peaks found in chunk.")
    else:
        fs_ss = []
        intensities = []
        print("No peak list found in chunk.")
        
    # Extract reflections
    reflections_match = re.search(r'Reflections measured after indexing(.*?)End of reflections', chunk, re.S)
    if reflections_match:
        reflections = re.findall(
            r'\s+-?\d+\s+-?\d+\s+-?\d+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+(\d+\.\d+)\s+(\d+\.\d+)\s+p0',
            reflections_match.group(1)
        )
        ref_fs_ss = [(float(fs), float(ss)) for fs, ss in reflections]
        if not reflections:
            print("No reflections found in chunk.")
    else:
        ref_fs_ss = []
        print("No reflections section found in chunk.")

    # Calculate weighted RMSD if possible
    if fs_ss and ref_fs_ss:
        weighted_rmsd, fraction_outliers = calc_wrmsd(fs_ss, intensities, ref_fs_ss, tolerance_factor=wrmsd_tolerance)
    else:
        weighted_rmsd = None
        print("Unable to calculate weighted RMSD for chunk.")

    # Extract cell parameters (lengths and angles)
    cell_params_match = re.search(r'Cell parameters ([\d.]+) ([\d.]+) ([\d.]+) nm, ([\d.]+) ([\d.]+) ([\d.]+) deg', chunk)
    if cell_params_match:
        a, b, c = map(lambda x: float(x) * 10, cell_params_match.groups()[:3])  # Convert from nm to Å
        al, be, ga = map(float, cell_params_match.groups()[3:])
        cell_params = (a, b, c, al, be, ga)
    else:
        cell_params = None
        print("No cell parameters found in chunk.")

    # Calculate cell deviation if possible
    if cell_params is not None and original_cell_params is not None:
        length_deviation, angle_deviation = calculate_cell_deviation(cell_params, original_cell_params)
    else:
        length_deviation, angle_deviation = None, None
        print("Unable to calculate cell deviation for chunk.")

    # Extract number of peaks and reflections
    num_peaks_match = re.search(r'num_peaks = (\d+)', chunk)
    num_peaks = int(num_peaks_match.group(1)) if num_peaks_match else len(fs_ss)
    if num_peaks == 0:
        print("No peaks count found in chunk.")

    num_reflections_match = re.search(r'num_reflections = (\d+)', chunk)
    num_reflections = int(num_reflections_match.group(1)) if num_reflections_match else len(ref_fs_ss)
    if num_reflections == 0:
        print("No reflections count found in chunk.")

    # Calculate predicted peaks to observed peaks ratio
    peak_ratio = num_reflections / num_peaks if num_peaks > 0 else num_reflections

    # Calculate percentage of peaks indexed
    if fs_ss and ref_fs_ss:
        number_matched_peaks = match_peaks_to_reflections(fs_ss, ref_fs_ss, tolerance=index_tolerance)
        fraction_indexed = (number_matched_peaks / len(fs_ss))
        fraction_unindexed = 1 - fraction_indexed
    else:
        number_matched_peaks = 0
        fraction_indexed = 0.0
        print("Unable to calculate percentage of peaks indexed for chunk.")

    return (
        event_string,
        weighted_rmsd,
        fraction_outliers,
        length_deviation,
        angle_deviation,
        peak_ratio,
        fraction_unindexed,
        chunk
    )
