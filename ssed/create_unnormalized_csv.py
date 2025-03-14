import os
import re
import csv
from tqdm import tqdm
from extract_chunk_data import extract_chunk_data

from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Lock

def process_stream_file(stream_file_path, wrmsd_tolerance=2, index_tolerance=1):
    """
    Process a stream file to extract raw chunk metrics.

    Returns:
        tuple: (results, none_results, header)
            results is a list of tuples with the form:
                (stream_file_name, event_number, weighted_rmsd, fraction_outliers,
                 length_deviation, angle_deviation, peak_ratio, percentage_unindexed,
                 chunk_content)
            none_results is a list of tuples for missing metrics:
                (stream_file_name, event_number, "None")
            header is the header string from the stream file.
    """
    results = []
    none_results = []
    header = ""

    with open(stream_file_path, 'r') as file:
        content = file.read()
        # Split the file using the chunk delimiter.
        split_content = re.split(r'----- Begin chunk -----', content)
        header, chunks = split_content[0], split_content[1:]

        # Attempt to extract cell parameters from the header (optional use).
        original_cell_params = None
        match_cp = re.search(
            r'a = ([\d.]+) A\nb = ([\d.]+) A\nc = ([\d.]+) A\nal = ([\d.]+) deg\nbe = ([\d.]+) deg\nga = ([\d.]+) deg',
            header
        )
        if match_cp:
            original_cell_params = tuple(map(float, match_cp.groups()))
        
        for chunk in tqdm(chunks, desc=f"Processing {os.path.basename(stream_file_path)}", unit="chunk"):
            if "indexed_by = none" in chunk.lower():
                continue
            
            data = extract_chunk_data(
                chunk,
                original_cell_params,
                wrmsd_tolerance=wrmsd_tolerance,
                index_tolerance=index_tolerance
            )
            if data is None:
                continue
            
            (
                event_number,
                weighted_rmsd,
                fraction_outliers,
                length_deviation,
                angle_deviation,
                peak_ratio,
                percentage_unindexed,
                chunk_content
            ) = data

            if event_number is not None:
                # Check if all required metrics exist
                if None not in (
                    weighted_rmsd, fraction_outliers, length_deviation,
                    angle_deviation, peak_ratio, percentage_unindexed
                ):
                    results.append((
                        os.path.basename(stream_file_path),
                        event_number,
                        weighted_rmsd,
                        fraction_outliers,
                        length_deviation,
                        angle_deviation,
                        peak_ratio,
                        percentage_unindexed,
                        chunk_content  # last column
                    ))
                else:
                    none_results.append((os.path.basename(stream_file_path), event_number, "None"))

    return results, none_results, header

def process_stream_file_and_append_csv(stream_file_path, csv_path, lock, wrmsd_tolerance=2, index_tolerance=1):
    """
    Process a single .stream file and append unnormalized metrics (excluding chunk content)
    to a shared CSV, protected by a lock.
    """
    results, none_results, file_header = process_stream_file(
        stream_file_path,
        wrmsd_tolerance=wrmsd_tolerance,
        index_tolerance=index_tolerance
    )

    # Append to CSV in a thread/process-safe manner
    with lock:
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            for r in results:
                # r = (stream_file, event_number, wrmsd, fraction_outliers,
                #      length_dev, angle_dev, peak_ratio, pct_unindexed, chunk_content)
                # We only want columns 0..7, skipping chunk_content at index 8:
                writer.writerow(r[:8])

        # If you want to log or keep track of the none_results, you could do so similarly
        # but typically these have no metrics, so they might not be appended.

def create_unnormalized_csv(folder_path, output_csv_name='unnormalized_metrics.csv',
                            wrmsd_tolerance=2, index_tolerance=1):
    """
    Processes all .stream files under folder_path in parallel and continuously
    appends unnormalized chunk metrics (skipping chunk content) to a CSV.
    """
    manager = Manager()
    lock = manager.Lock()

    # Path of the unnormalized metrics CSV
    output_csv_path = os.path.join(folder_path, output_csv_name)

    # Remove if existing so we start fresh
    if os.path.exists(output_csv_path):
        os.remove(output_csv_path)

    # Write header just once
    with open(output_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'stream_file',
            'event_number',
            'weighted_rmsd',
            'fraction_outliers',
            'length_deviation',
            'angle_deviation',
            'peak_ratio',
            'percentage_unindexed'
        ])

    # Gather all .stream files
    stream_files = [
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if f.endswith('.stream')
    ]

    with ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(
                process_stream_file_and_append_csv,
                sf, output_csv_path, lock, wrmsd_tolerance, index_tolerance
            )
            for sf in stream_files
        ]
        for _ in as_completed(futures):
            pass

    print(f"Unnormalized metrics CSV written to {output_csv_path}")

if __name__ == "__main__":
    # Example usage: create unnormalized CSV from all .stream files in a folder
    folder_path = "/home/buster/UOX1/different_index_params/3x3"
    create_unnormalized_csv(folder_path, output_csv_name='unnormalized_metrics.csv')
