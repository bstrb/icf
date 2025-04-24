#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from tqdm import tqdm

# Compile once at import time
EVENT_RE = re.compile(r'^(Event:\s*//)(\d+)(.*)$')

def process_file(path: Path, verbose: bool = False) -> bool:
    """
    Read the file once.  On the first Event line, decide:
      – if already processed (rest starts with '-'), skip the file.
      – otherwise, start appending counters.
    Returns True if we wrote out a new version, False if skipped.
    """
    counts = {}
    new_lines = []
    saw_first_event = False

    with path.open('r') as src:
        for line in src:
            if not saw_first_event:
                m = EVENT_RE.match(line)
                if m:
                    saw_first_event = True
                    _, _, rest = m.groups()
                    if rest.lstrip().startswith('-'):
                        # already processed; abort early
                        if verbose:
                            tqdm.write(f"→ Skipping {path.name} (already processed)")
                        return False

            m = EVENT_RE.match(line)
            if m:
                prefix, num, rest = m.groups()
                counts[num] = counts.get(num, 0) + 1
                # rebuild line with counter
                new_line = f"{prefix}{num}-{counts[num]}{rest}\n"
                new_lines.append(new_line)
            else:
                new_lines.append(line)

    # overwrite file
    path.write_text(''.join(new_lines))
    if verbose:
        tqdm.write(f"✓ Processed {path.name} ({len(counts)} distinct events)")
    return True

def main():
    p = argparse.ArgumentParser(
        description="Append per-event occurrence counters to .stream files."
    )
    p.add_argument(
        "folder",
        type=Path,
        help="Directory containing your .stream files",
    )
    p.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress per-file status messages",
    )
    args = p.parse_args()

    folder: Path = args.folder
    if not folder.is_dir():
        raise SystemExit(f"Error: {folder!r} is not a directory")

    files = sorted(folder.glob("*.stream"))
    if not files:
        print(f"No .stream files found in {folder}")
        return

    # file-level progress bar
    for path in tqdm(files, desc="Processing files", unit="file"):
        process_file(path, verbose=not args.quiet)

if __name__ == "__main__":
    main()
