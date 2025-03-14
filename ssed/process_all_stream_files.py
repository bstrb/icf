import os
import re
import csv
import statistics
from itertools import groupby
from tqdm import tqdm
from extract_chunk_data import extract_chunk_data
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Lock


def process_stream_file(stream_file_path, wrmsd_tolerance=2, index_tolerance=1):
    """
    Process a stream file to extract raw chunk metrics.

    This function reads a stream file from the provided path, splits it into chunks
    (using "----- Begin chunk -----" as delimiter), and extracts metrics for each chunk.
    Chunks that are unindexed (i.e. contain "indexed_by = none") are skipped.
    
    The raw metrics extracted are:
      - weighted_rmsd, length_deviation, angle_deviation, peak_ratio, percentage_unindexed
    
    Parameters:
        stream_file_path (str):
            Full path to the stream file.
        metric_weights (dict, list, or tuple, optional):
            Weights for each metric. If a list/tuple is given, it must have the same
            length as the metric names below. If omitted, a default set of weights is used.
    
    Returns:
        tuple:
            (results, none_results, header) where:
              - results is a list of tuples containing raw metric values and the chunk content.
                Each valid result has the form:
                    (stream_file_name, event_number, weighted_rmsd, length_deviation,
                     angle_deviation, peak_ratio, percentage_unindexed, chunk_content)
              - none_results is a list of tuples for chunks with missing metric values.
                Each tuple is of the form: (stream_file_name, event_number, "None")
              - header is the header string extracted from the stream file.
    """
    
    results = []      # will store valid results with raw metric values
    none_results = [] # will store entries for chunks with missing metrics
    
    with open(stream_file_path, 'r') as file:
        content = file.read()
        # Split the file using the chunk delimiter.
        header, *chunks = re.split(r'----- Begin chunk -----', content)
        
        # Extract original cell parameters from header if available.
        cell_params_match = re.search(
            r'a = ([\d.]+) A\nb = ([\d.]+) A\nc = ([\d.]+) A\nal = ([\d.]+) deg\nbe = ([\d.]+) deg\nga = ([\d.]+) deg',
            header
        )
        if cell_params_match:
            original_cell_params = tuple(map(float, cell_params_match.groups()))
        else:
            original_cell_params = None
            print("No original cell parameters found in header.")
        
        for chunk in tqdm(chunks, desc=f"Processing chunks in {os.path.basename(stream_file_path)}", unit="chunk"):
            if "indexed_by = none" in chunk.lower():
                continue  # Skip unindexed chunks
            
            # extract_chunk_data is assumed to return a tuple:
            # (event_number, weighted_rmsd, fraction_outliers, length_deviation, angle_deviation,
            # peak_ratio, percentage_unindexed, chunk_content)
            data = extract_chunk_data(chunk, original_cell_params, wrmsd_tolerance=wrmsd_tolerance, index_tolerance=index_tolerance)
            if data is None:
                continue
            (event_number, weighted_rmsd, fraction_outliers, length_deviation, angle_deviation, peak_ratio, percentage_unindexed, chunk_content) = data
            
            if event_number is not None:
                # Only add valid chunks (all required metrics not None)
                if None not in (weighted_rmsd, fraction_outliers, length_deviation, angle_deviation, peak_ratio, percentage_unindexed):
                    results.append((
                        os.path.basename(stream_file_path),
                        event_number,
                        weighted_rmsd,
                        fraction_outliers,
                        length_deviation,
                        angle_deviation,
                        peak_ratio,
                        percentage_unindexed,
                        chunk_content
                    ))
                else:
                    none_results.append((os.path.basename(stream_file_path), event_number, "None"))
    
    return results, none_results, header

def process_and_store(stream_file_path, all_results, header, lock, wrmsd_tolerance=2, index_tolerance=1):
    """
    Helper function to process a single stream file and add its results to a shared list.
    """
    results, none_results, file_header = process_stream_file(stream_file_path, wrmsd_tolerance=wrmsd_tolerance, index_tolerance=index_tolerance)
    with lock:
        # Save header from the first processed file
        if file_header and not header:
            header.append(file_header)
        all_results.extend(results)
        all_results.extend(none_results)

def process_all_stream_files(folder_path, wrmsd_tolerance=2, index_tolerance=1, normalization_method='zscore'):
    """
    Process all stream files in a folder, perform global normalization, and output CSV.

    Steps:
      1. Load each stream file in parallel and extract raw chunk metrics.
      2. Build global metric arrays across all chunks.
      3. Normalize each metric globally using either 'minmax' or 'zscore' normalization.
      5. Write a CSV with each chunk's file name, event number,
         and individual normalized metrics (grouped by event number).

    Parameters:
        folder_path (str):
            The folder that contains the stream files.
        normalization_method (str, optional):
            Either 'minmax' (default) or 'zscore' to select the normalization method.

    Returns:
        None
    """
    manager = Manager()
    all_results = manager.list()  # will hold raw results from all files
    header = manager.list()       # store header from the first file
    lock = manager.Lock()

    # Remove existing best_results stream files in the folder.
    for f in os.listdir(folder_path):
        if f.startswith('best_results') and f.endswith('.stream'):
            os.remove(os.path.join(folder_path, f))

    # Get list of stream files.
    stream_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.stream')]

    # Process each stream file in parallel.
    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(process_and_store, stream_file, all_results, header, lock, wrmsd_tolerance, index_tolerance): stream_file
            for stream_file in stream_files
        }
        for future in as_completed(futures):
            futures.pop(future)

    # Convert the shared list to a normal list.
    all_results = list(all_results)

    # Separate valid results (tuples of length 12) from those with missing metrics.
    valid_results = [r for r in all_results if len(r) == 9]
    invalid_results = [r for r in all_results if len(r) == 3]

    if not valid_results:
        print("No valid chunks found in any stream file.")
        return

    # Build global metric arrays from valid_results.
    # The order (indices) in each valid result is:
    # 0: stream_file, 1: event_number, 2: weighted_rmsd, 3: fraction_outliers, 4:length_deviation, 5: angle_deviation,
    # 6: peak_ratio, 7: percentage_unindexed, 8: chunk_content

    global_metrics = {
        'weighted_rmsd': [r[2] for r in valid_results],
        'fraction_outliers': [r[3] for r in valid_results],
        'length_deviation': [r[4] for r in valid_results],
        'angle_deviation': [r[5] for r in valid_results],
        'peak_ratio': [r[6] for r in valid_results],
        'percentage_unindexed': [r[7] for r in valid_results]
    }

    # Normalize the metrics globally.
    norm_metrics = {}
    if normalization_method == 'minmax':
        for key, values in global_metrics.items():
            min_val = min(values)
            max_val = max(values)
            if max_val != min_val:
                norm_metrics[key] = [(v - min_val) / (max_val - min_val) for v in values]
            else:
                norm_metrics[key] = [0.5 for _ in values]
    elif normalization_method == 'zscore':
        for key, values in global_metrics.items():
            # if key == 'percentage_unindexed' or key == 'fraction_outliers':
            #     norm_metrics[key] = values
            #     continue

            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values) if len(values) > 1 else 1
            norm_metrics[key] = [(v - mean_val) / stdev_val for v in values]
    else:
        print("Unknown normalization method. Use 'minmax' or 'zscore'.")
        return

    updated_results = []
    for i, r in enumerate(valid_results):
        norm_weighted_rmsd = norm_metrics['weighted_rmsd'][i]
        norm_fraction_outliers = norm_metrics['fraction_outliers'][i]
        norm_length_deviation = norm_metrics['length_deviation'][i]
        norm_angle_deviation = norm_metrics['angle_deviation'][i]
        norm_peak_ratio = norm_metrics['peak_ratio'][i]
        norm_percentage_unindexed = norm_metrics['percentage_unindexed'][i]
        
        updated_results.append((
            r[0],  # stream file name
            r[1],  # event number
            norm_weighted_rmsd,
            norm_fraction_outliers,
            norm_length_deviation,
            norm_angle_deviation,
            norm_peak_ratio,
            norm_percentage_unindexed,
            r[8]  # chunk content
        ))
    
    # Group the results by event number.
    # First, sort by event number and then by percentage unindexed.
    updated_results.sort(key=lambda x: (x[1], x[7]))
    
    output_csv_path = os.path.join(folder_path, f'metric_values.csv')

    # Write all updated results (with normalized metrics) to CSV grouped by event number.
    csv_header = [
        'stream_file', 'event_number', 'weighted_rmsd', 'fraction_outliers', 'length_deviation', 'angle_deviation', 'peak_ratio', 'percentage_unindexed'
    ]
    with open(output_csv_path, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(csv_header)
        # Group rows by event number.
        for event, group in groupby(updated_results, key=lambda x: x[1]):
            # Write a header row for this event group.
            csv_writer.writerow([f"Event number: {event}"] + [""] * (len(csv_header)-1))
            for row in group:
                csv_writer.writerow(row[:9])
    
    print(f'Metrics CSV written to {output_csv_path}')
    

if __name__ == "__main__":
    folder_path = "/home/buster/UOX1/different_index_params/3x3"
    # Choose normalization_method='minmax' or 'zscore' as needed.
    process_all_stream_files(folder_path, normalization_method='zscore')
