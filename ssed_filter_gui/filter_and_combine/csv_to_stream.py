import csv
import os
from collections import defaultdict

BEGIN = "----- Begin chunk -----"
END   = "----- End chunk -----"
EVENT_PREFIX = "Event:"

def collect_requests(csv_path, event_col="event_number", streamfile_col="stream_file"):
    """Read the CSV once and build {stream_file: set(event_numbers)}."""
    wants = defaultdict(set)          # {path -> {evt1, evt2, …}}
    rows  = []                        # keep original row order for output ordering
    wdir  = os.path.dirname(csv_path)

    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            evt = row[event_col].strip()
            sfile = os.path.join(wdir, row[streamfile_col].strip())
            wants[sfile].add(evt)
            rows.append((sfile, evt))

    return wants, rows

def stream_chunks(stream_path, wanted_events):
    """
    Generator that yields (event_str, full_chunk_text) *only* for wanted_events.
    Reads the file line-by-line; never keeps more than one chunk in memory.
    """
    with open(stream_path) as fh:
        header_parts = []
        in_chunk = False
        cur_chunk = []
        cur_event = None

        for line in fh:
            if not in_chunk:
                if line.startswith(BEGIN):
                    in_chunk = True
                    cur_chunk = [line]     # include BEGIN line
                    cur_event = None
                else:
                    # Still in the header region
                    header_parts.append(line)
            else:
                cur_chunk.append(line)

                # sniff the event number as soon as we see it
                if cur_event is None and line.lstrip().startswith(EVENT_PREFIX):
                    cur_event = line.split(EVENT_PREFIX, 1)[1].strip()
                    if cur_event.startswith("//"):
                        cur_event = cur_event[2:].strip()

                if line.startswith(END):
                    # Chunk finished – decide whether to yield
                    chunk_text = ''.join(cur_chunk)
                    if cur_event in wanted_events:
                        yield cur_event, chunk_text
                    in_chunk = False        # reset state

        # on exit yield header once (outside the generator for clarity)
        header = ''.join(header_parts)
    return header

def write_stream_from_filtered_csv(csv_path, out_path,
                          event_col="event_number", streamfile_col="stream_file"):
    wants, row_order = collect_requests(csv_path, event_col, streamfile_col)
    header_written = False

    with open(out_path, "w") as out:
        for sfile, evt in row_order:            # preserve CSV ordering
            if evt not in wants[sfile]:
                continue                        # already handled (duplicate rows)

            # Stream chunk generator
            gen = stream_chunks(sfile, {evt})

            # Grab header from this file exactly once if not already written
            if not header_written:
                header = next(gen)  # header is returned before the first chunk
                out.write(header)
                header_written = True

            # Write (evt, chunk) pairs – there will be exactly one
            for _evt, chunk in gen:
                out.write(chunk)
                if not chunk.rstrip().endswith(END):
                    out.write(END + "\n")

            wants[sfile].discard(evt)           # mark as done

    print("Finished. Combined stream saved to", out_path)
