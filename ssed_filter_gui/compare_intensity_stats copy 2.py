#!/usr/bin/env python3
"""
compare_rsplit_cc_separate.py

Parse two crystallographic intensity‐statistics files (CSV + “Overall …” footer)
and generate two separate comparison plots:
  1) Rsplit vs. resolution
  2) CC vs. resolution

Usage
-----
python compare_rsplit_cc_separate.py <file1.csv> <file2.csv> [output_prefix]

If you supply `output_prefix` (e.g., "comparison"), two files will be written:
  comparison_rsplit.png
  comparison_cc.png

If you omit `output_prefix`, defaults to "comparison", producing:
  comparison_rsplit.png
  comparison_cc.png
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


def plot_rsplit(df1: pd.DataFrame, df2: pd.DataFrame, label1: str,
                label2: str, outfile: Path) -> None:
    """
    Generate a plot of Rsplit vs. resolution for two data sets.
    """
    fig, ax = plt.subplots(figsize=(3.5, 3.5), dpi=300)

    ax.plot(
        df1["d center/A"],
        df1["Rsplit"],
        marker="o",
        linestyle="-",
        label=f"{label1} Rsplit",
    )
    ax.plot(
        df2["d center/A"],
        df2["Rsplit"],
        marker="s",
        linestyle="--",
        label=f"{label2} Rsplit",
    )

    ax.set_xlabel("Resolution (Å)")
    ax.set_ylabel("Rsplit")
    ax.invert_xaxis()  # crystallographic convention

    ax.legend(loc="best", fontsize=7)
    plt.tight_layout()
    fig.savefig(outfile, transparent=True)
    plt.show()


def plot_cc(df1: pd.DataFrame, df2: pd.DataFrame, label1: str,
            label2: str, outfile: Path) -> None:
    """
    Generate a plot of CC vs. resolution for two data sets.
    """
    fig, ax = plt.subplots(figsize=(3.5, 3.5), dpi=300)

    ax.plot(
        df1["d center/A"],
        df1["CC"],
        marker="^",
        linestyle="-.",
        label=f"{label1} CC1/2",
    )
    ax.plot(
        df2["d center/A"],
        df2["CC"],
        marker="v",
        linestyle=":",
        label=f"{label2} CC1/2",
    )

    ax.set_xlabel("Resolution (Å)")
    ax.set_ylabel("CC1/2")
    ax.invert_xaxis()  # crystallographic convention

    ax.legend(loc="best", fontsize=7)
    plt.tight_layout()
    fig.savefig(outfile, transparent=True)

    plt.show()



def main() -> None:

    file1 = Path("/home/bubl3932/files/MFM300_VIII/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524_2038/xgandalf_iterations_max_radius_1.0_step_0.1/merge-0_0/merge00.csv")
    file2 = Path("/home/bubl3932/files/MFM300_VIII/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524/MFM300_UK_2ndGrid_spot_4_220mm_0deg_150nm_50ms_20250524_2038/xgandalf_iterations_max_radius_1.0_step_0.1/filtered_metrics/merge/mergefull.csv")
    outfile = Path("comparison.png")
    outfile_rsplit = outfile.with_name(outfile.stem + "_rsplit.png")
    outfile_cc = outfile.with_name(outfile.stem + "_cc.png")

    df1, overall1 = parse_stats_file(file1)
    df2, overall2 = parse_stats_file(file2)

    # Use the stem (filename without extension) as legend labels
    label1, label2 = file1.stem, file2.stem

    plot_rsplit(df1, df2, label1, label2, outfile_rsplit)
    plot_cc(df1, df2, label1, label2, outfile_cc)

    # Print overall stats in a neat table
    print(f"\nOverall statistics\n{'Metric':<15}{label1:>12}{label2:>12}")
    for metric in ["I/sigI", "Completeness", "Rsplit", "CC"]:
    # for metric in ["Rsplit", "CC"]:
        v1 = overall1.get(metric, float("nan"))
        v2 = overall2.get(metric, float("nan"))
        print(f"{metric:<15}{v1:12.6f}{v2:12.6f}")

    print(f"\nPlot saved to: {outfile.resolve()}")


if __name__ == "__main__":
    main()
