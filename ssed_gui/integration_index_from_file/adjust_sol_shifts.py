#!/usr/bin/env python3

import sys
import h5py

def adjust_sol_shifts(input_sol_filename, output_sol_filename):
    """
    Reads each line of a .sol file, extracts the final two det_shifts,
    subtracts from them the corresponding det_shifts in the .h5, and
    writes a new .sol file with those updated shifts.
    """
    with open(input_sol_filename, 'r') as fin, open(output_sol_filename, 'w') as fout:
        for line in fin:
            line = line.strip()
            if not line:
                # Skip empty lines
                fout.write("\n")
                continue
            
            # Example line structure:
            # /home/bubl3932/files/UOX1/UOX1_min_15_peak/UOX1_min_15_peak.h5 //14
            #   +0.0452289 -0.0035423 -0.1136987 +0.0931451 +0.0362681 +0.0342180
            #   +0.0303068 -0.0905448 +0.0174231 0.193748 -0.157075 oI
            #
            # The last token is the Pearson symbol ("oI" here).
            # The last two numeric values before that are your .sol det_shifts (x_sol, y_sol).

            tokens = line.split()
            if len(tokens) < 4:
                # Not enough tokens to parse meaningfully
                fout.write(line + "\n")
                continue

            # Extract the path to the HDF5 file (tokens[0])
            h5_file_path = tokens[0]

            # Extract the index, removing leading "//"
            sol_index_token = tokens[1]
            if not sol_index_token.startswith('//'):
                # Not a valid index line; just output unchanged and continue
                fout.write(line + "\n")
                continue

            try:
                h5_index = int(sol_index_token.replace('//', ''))
            except ValueError:
                # Could not parse index; just output unchanged and continue
                fout.write(line + "\n")
                continue

            # The last token should be something like 'oI' (the Pearson symbol).
            # The last two floats before that are tokens[-3] and tokens[-2].
            # tokens[-1] is the final non-numeric symbol in your example.

            # We ensure we have at least 3 tokens from the end
            # (one for the Pearson symbol, two for the shifts):
            if len(tokens) < 3:
                fout.write(line + "\n")
                continue

            # Attempt to parse the .sol shifts:
            try:
                x_sol = float(tokens[-3])
                y_sol = float(tokens[-2])
            except ValueError:
                # Could not parse them as floats; output unchanged
                fout.write(line + "\n")
                continue

            # Now open the HDF5 file and read the det_shifts at the given index
            try:
                with h5py.File(h5_file_path, 'r') as h5f:
                    x_arr = h5f["/entry/data/det_shift_x_mm"]
                    y_arr = h5f["/entry/data/det_shift_y_mm"]

                    x_h5 = x_arr[h5_index]
                    y_h5 = y_arr[h5_index]
            except Exception as e:
                # Could not read from HDF5 for some reason;
                # just keep the original line
                sys.stderr.write(f"Warning: unable to read H5: {h5_file_path}. Error: {e}\n")
                fout.write(line + "\n")
                continue

            # Subtract the HDF5 shifts from the sol shifts
            # (In your question you said: "subtracts the extracted det shifts found in the .h5 from those in the .sol")
            diff_x = x_sol - x_h5
            diff_y = y_sol - y_h5

            # Replace the last two numeric tokens with the difference
            tokens[-3] = f"{diff_x:.6f}"
            tokens[-2] = f"{diff_y:.6f}"

            # Reconstruct the line
            new_line = " ".join(tokens)
            fout.write(new_line + "\n")
            
    return output_sol_filename


def main():
    """
    Usage: python adjust_sol_shifts.py input.sol output.sol
    """

    input_sol_filename =  "/home/bubl3932/files/UOX1/xgandalf_iterations_max_radius_1.8_step_0.5/filtered_metrics/filtered_metrics.sol"
    output_sol_filename = "/home/bubl3932/files/UOX1/xgandalf_iterations_max_radius_1.8_step_0.5/filtered_metrics/filtered_metrics_adjusted.sol"

    adjust_sol_shifts(input_sol_filename, output_sol_filename)

if __name__ == "__main__":
    main()
