import sys
import os

def parse_stream(stream_lines):
    """
    Parse the given stream file lines into three parts:
    1. header_lines: all lines up until the first chunk begins.
    2. chunks: a list of (event_number, chunk_lines) for each chunk.
    3. trailer_lines: any lines after the last chunk ends (if any).
    """
    header_lines = []
    trailer_lines = []
    chunks = []

    in_chunk = False
    chunk_lines = []
    event_number = None

    # We need to detect the start and end of chunks.
    # The chunk format is:
    # ----- Begin chunk -----
    # ...
    # Event: //N
    # ...
    # ----- End chunk -----

    for line in stream_lines:
        # Detect chunk boundaries
        if line.strip() == "----- Begin chunk -----":
            in_chunk = True
            chunk_lines = [line]
            event_number = None
        elif line.strip() == "----- End chunk -----":
            in_chunk = False
            chunk_lines.append(line)
            # Store the chunk with its event number
            if event_number is None:
                event_number = 999999999  
            chunks.append((event_number, chunk_lines))
            chunk_lines = []  # Reset chunk_lines after appending
        else:
            if in_chunk:
                chunk_lines.append(line)
                # Try to find the event number
                if "Event:" in line:
                    parts = line.strip().split()
                    for part in parts:
                        if part.startswith("//"):
                            event_number = int(part.strip("/"))
            else:
                if not chunks:  # Changed from len(chunks) == 0 for clarity
                    header_lines.append(line)
                else:
                    trailer_lines.append(line)

    return header_lines, chunks, trailer_lines

def sort_chunks_by_event(chunks):
    """
    Sort the chunks by their event number.
    chunks is a list of (event_number, chunk_lines).
    Return a new list of chunk_lines in sorted order.
    """
    chunks_sorted = sorted(chunks, key=lambda c: c[0])
    return chunks_sorted

def write_stream(outfile, header_lines, chunks, trailer_lines):
    """
    Write out the sorted stream file.
    """
    # Write header
    for line in header_lines:
        outfile.write(line)
    # Write chunks
    for _, c_lines in chunks:
        for line in c_lines:
            outfile.write(line)
    # Write trailer
    for line in trailer_lines:
        outfile.write(line)

def main():
    default_input = "/Users/xiaodong/Desktop/simulations/LTA/simulation-29/LTAsim_from_file_-512.5_-512.5.stream"

    # default_output = "/home/bubl3932/files/UOX1/UOX_subset_center_sensitivity_0.2_pixels/best_results_sorted.stream"
    
    # Separate directory and filename
    directory, filename = os.path.split(default_input)

    # Separate filename and extension
    base, ext = os.path.splitext(filename)

    # Add a string (e.g., a suffix) to the base name
    new_filename = base + "_sorted" + ext

    # Reconstruct the full path
    default_output = os.path.join(directory, new_filename)

    if len(sys.argv) == 1:
        input_file = default_input
        output_file = default_output
    elif len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        print("Usage: python sort_stream.py input.stream output.stream")
        sys.exit(1)

    with open(input_file, 'r') as f:
        stream_lines = f.readlines()

    header_lines, chunks, trailer_lines = parse_stream(stream_lines)
    sorted_chunks = sort_chunks_by_event(chunks)

    with open(output_file, 'w') as f:
        write_stream(f, header_lines, sorted_chunks, trailer_lines)

    print(f"Sorted stream file written to {output_file}")

if __name__ == "__main__":
    main()
