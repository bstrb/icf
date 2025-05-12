import csv
import re
import os

def extract_chunks_from_stream(stream_file):
    """
    Reads an XDS .stream file, splits it by "----- Begin chunk -----",
    and returns (header_text, { event_number_str -> chunk_text }).

    - header_text is everything before the first "----- Begin chunk -----".
    - chunk_text is the raw text (including the "----- End chunk -----" if present).
    """
    with open(stream_file, 'r') as f:
        content = f.read()

    # Split the file on '----- Begin chunk -----'
    parts = re.split(r'----- Begin chunk -----', content)
    header = parts[0]  # everything before the first chunk
    
    chunk_dict = {}
    for chunk_body in parts[1:]:
        # Attempt to find the event number from a line "Event: X"
        # chunk_body may contain '----- End chunk -----' at the end
        lines = chunk_body.splitlines(keepends=True)
        event_str = None
        # for line in lines:
        #     line_strip = line.strip()
        #     if line_strip.startswith("Event:"):
        #         event_str = line_strip.split("Event:", 1)[1].strip()
        #         break
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("Event:"):
                event_str = line_strip.split("Event:", 1)[1].strip()
                # Remove leading '//' if present:
                if event_str.startswith("//"):
                    event_str = event_str[2:].strip()
                break

        
        if event_str is not None:
            chunk_dict[event_str] = chunk_body
        # If no event line found, we ignore this chunk

    return header, chunk_dict


def write_stream_from_filtered_csv(
    filtered_csv_path,
    output_stream_path,
    event_col="event_number",
    streamfile_col="stream_file"
):
    """
    Reads a CSV containing 'stream_file' and 'event_number' columns.
    For each row:
      - extracts the chunk with that event_number from stream_file
      - writes it to a single combined output_stream_path.

    We only write the header region from the *first row's* stream file.
    We also print that header to the console.

    The CSV is read in order, so rows are processed top-to-bottom.
    """
    wdir = os.path.dirname(filtered_csv_path)
    # 1) Read all rows from CSV
    rows = []
    with open(filtered_csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        print(f"No rows found in CSV: {filtered_csv_path}")
        return

    # 2) We'll cache each stream file (so we only parse it once)
    stream_cache = {}  # { stream_file_path : (header_text, {event_str: chunk_body}) }
    header_written = False  # We'll write exactly one header

    with open(output_stream_path, 'w') as out:
        for i, row in enumerate(rows):
            evt_str = row[event_col]
            sfile   = os.path.join(wdir,row[streamfile_col])

            # Lazy-load this stream file if not already in cache
            if sfile not in stream_cache:
                try:
                    header_text, chunks_dict = extract_chunks_from_stream(sfile)
                    stream_cache[sfile] = (header_text, chunks_dict)
                except Exception as e:
                    print(f"ERROR reading '{sfile}': {e}")
                    continue

            header_text, chunks_dict = stream_cache[sfile]

            # If this is the *first* row we're processing overall,
            # write the header from this stream file
            if not header_written:
                out.write(header_text)  # everything before "----- Begin chunk -----"
                print("Header from first stream file in the CSV:\n")
                print(header_text)
                header_written = True

            # Look for the chunk that matches evt_str
            if evt_str not in chunks_dict:
                print(f"WARNING: Event '{evt_str}' not found in '{sfile}'. Skipping.")
                continue

            chunk_body = chunks_dict[evt_str]

            # Write that chunk into our output, preceded by "----- Begin chunk -----"
            out.write("----- Begin chunk -----")
            out.write(chunk_body)
            # Ensure we have "----- End chunk -----" if not included
            if not chunk_body.strip().endswith("----- End chunk -----"):
                out.write("\n----- End chunk -----\n")

    print(f"\nDone! Combined stream written to: {output_stream_path}")
