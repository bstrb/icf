#!/usr/bin/env python3
"""
compare_rsplit_cc_combined.py

Parse two crystallographic intensity‐statistics files (CSV + “Overall …” footer)
and generate a single figure with two stacked panels:
  Top:    Rsplit vs. resolution
  Bottom: CC1/2 vs. resolution

Usage
-----
python compare_rsplit_cc_combined.py <file1.csv> <file2.csv> [output_prefix]

If you supply `output_prefix` (e.g., "comparison"), one file will be written:
  comparison_combined.png

If you omit `output_prefix`, defaults to "comparison_combined.png".
"""

import sys
import csv
from pathlib import Path
from typing import Tuple, Dict

import pandas as pd
import matplotlib.pyplot as plt


def parse_stats_file(path: Path) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Parse a CSV‐style stats file with per‐shell data and an “Overall …” footer.

    Returns
    -------
    df : pandas.DataFrame with the per‐shell statistics
    overall : dict with keys "I/sigI", "Completeness", "Rsplit", "CC"
    """
    data_rows = []
    overall = {}

    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = [h.strip().strip('"') for h in next(reader)]

        for row in reader:
            # Stop on blank line (end of per‐shell table)
            if not row or not row[0].strip():
                break
            data_rows.append([float(item) for item in row])

        # Read remaining lines for "Overall ..." entries
        for line in f:
            line = line.strip()
            if not line or not line.lower().startswith("overall"):
                continue
            key, value = [x.strip() for x in line.split("=", maxsplit=1)]
            key = key.replace("Overall", "").strip()  # e.g. "Rsplit"
            overall[key] = float(value)

    df = pd.DataFrame(data_rows, columns=header)
    return df, overall


def plot_combined(df1: pd.DataFrame,
                  df2: pd.DataFrame,
                  label1: str,
                  label2: str,
                  outfile: Path) -> None:
    """
    Generate a single figure with two stacked panels (Rsplit and CC1/2)
    sharing the same Resolution (Å) axis.
    """
    # Determine combined resolution range so both panels share identical x-limits.
    # (Assuming "d center/A" column is numeric and higher values = lower resolution)
    all_res = pd.concat([df1["d center/A"], df2["d center/A"]])
    xmin, xmax = all_res.min(), all_res.max()

    # Create a 2×1 subplot grid with shared x-axis
    fig, (ax_rsplit, ax_cc) = plt.subplots(
        nrows=2,
        ncols=1,
        sharex=True,
        figsize=(4.0, 5.0),  # you can adjust the height/width as needed
        dpi=300,
        constrained_layout=True
    )

    # --- Top panel: Rsplit vs resolution ---
    ax_rsplit.plot(
        df1["d center/A"],
        df1["Rsplit"],
        marker="o",
        linestyle="-",
        label=f"{label1}",# Rsplit",
        markersize=4
    )
    ax_rsplit.plot(
        df2["d center/A"],
        df2["Rsplit"],
        marker="s",
        linestyle="--",
        label=f"{label2}",# Rsplit",
        markersize=4
    )
    ax_rsplit.set_ylabel("Rsplit")
    ax_rsplit.invert_xaxis()  # crystallographic convention
    ax_rsplit.set_xlim(xmax, xmin)  # enforce same x-limits (inverted)
    ax_rsplit.legend(loc="best", fontsize=7)
    ax_rsplit.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)

    # --- Bottom panel: CC1/2 vs resolution ---
    ax_cc.plot(
        df1["d center/A"],
        df1["CC"],
        marker="^",
        linestyle="-.",
        label=f"{label1}",# CC1/2",
        markersize=4
    )
    ax_cc.plot(
        df2["d center/A"],
        df2["CC"],
        marker="v",
        linestyle=":",
        label=f"{label2}",# CC1/2",
        markersize=4
    )
    ax_cc.set_xlabel("Resolution (Å)")
    ax_cc.set_ylabel("CC1/2")
    ax_cc.invert_xaxis()
    ax_cc.set_xlim(xmax, xmin)
    ax_cc.legend(loc="best", fontsize=7)
    ax_cc.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)

    # Save and show
    fig.savefig(outfile, transparent=True)
    plt.show()


def main() -> None:
    # Parse arguments
    # if len(sys.argv) < 3:
    #     print("Usage: python compare_rsplit_cc_combined.py <file1.csv> <file2.csv> [output_prefix]")
    #     sys.exit(1)

    file1 = Path("/home/bubl3932/files/MFM300_VIII/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524_2038/xgandalf_iterations_max_radius_1.0_step_0.1/merge-0_0/merge00-2/Single-Index.csv")
    file2 = Path("/home/bubl3932/files/MFM300_VIII/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524_2038/xgandalf_iterations_max_radius_1.0_step_0.1/filtered_metrics/merge/Multiple-Index+IQ.csv")
    
    if len(sys.argv) >= 4:
        prefix = sys.argv[3]
    else:
        prefix = "comparison"

    outfile = Path(f"{prefix}_combined.png")

    # Read data
    df1, overall1 = parse_stats_file(file1)
    df2, overall2 = parse_stats_file(file2)

    # Legend labels from filename stems
    label1, label2 = file1.stem, file2.stem

    # Generate combined plot
    plot_combined(df1, df2, label1, label2, outfile)

    # Print overall stats in a neat table (optional)
    print(f"\nOverall statistics\n{'Metric':<15}{label1:>12}{label2:>12}")
    for metric in ["I/sigI", "Completeness", "Rsplit", "CC"]:
        v1 = overall1.get(metric, float("nan"))
        v2 = overall2.get(metric, float("nan"))
        print(f"{metric:<15}{v1:12.6f}{v2:12.6f}")

    print(f"\nCombined plot saved to: {outfile.resolve()}")


if __name__ == "__main__":
    main()

