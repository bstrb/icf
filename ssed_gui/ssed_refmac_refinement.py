# ssed_refmac_refinement.py
#!/usr/bin/env python3
import os
import re
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import numpy as np

# Import your custom refinement function & parser
from refmac_refine.ctruncate_freerflag_refmac5 import ctruncate_freerflag_refmac5

def parse_refmac_log_for_table(log_path):
    """
    Opens refmac5.log at log_path, finds the last table that contains the header
    "M(4SSQ/LL)" and "Rf_used", and returns two lists:
      - resolution_list (in Å) computed as sqrt(1/(first column))
      - rf_used_list (from the 6th column)
    """
    resolution_list = []
    rf_used_list = []
    if not os.path.isfile(log_path):
        return resolution_list, rf_used_list
    
    with open(log_path, 'r') as f:
        lines = f.readlines()

    # Find the last occurrence of the relevant header line.
    header_indices = []
    for i, line in enumerate(lines):
        if "M(4SSQ/LL)" in line and "Rf_used" in line:
            header_indices.append(i)
    if not header_indices:
        return resolution_list, rf_used_list
    start_index = header_indices[-1]
    
    # Find the next line that is exactly "$$" which marks the end of the header block.
    for j in range(start_index, len(lines)):
        if lines[j].strip() == "$$":
            start_index = j + 1
            break

    end_index = None
    for j in range(start_index, len(lines)):
        if lines[j].strip() == "$$":
            end_index = j
            break
    if end_index is None:
        return resolution_list, rf_used_list

    raw_table_lines = lines[start_index:end_index]
    for line in raw_table_lines:
        parts = re.split(r"\s+", line.strip())
        if len(parts) < 6:
            continue
        try:
            col1_val = float(parts[0])
            col6_val = float(parts[5])
            if col1_val != 0:
                res = np.sqrt(1.0 / col1_val)
                resolution_list.append(res)
                rf_used_list.append(col6_val)
        except ValueError:
            continue

    return resolution_list, rf_used_list

def get_ui(parent):
    """
    Creates and returns a Tkinter Frame containing the Refmac5 refinement UI.

    This UI allows:
      - Selection of an MTZ file and PDB file,
      - Entry of optional parameters (max_res, min_res, ncycles, bins),
      - A "Refine with Refmac5" button that runs `ctruncate_freerflag_refmac5`,
      - Automatic parsing of refmac5.log for "Rf_used" vs Resolution, plotted in matplotlib.

    All feedback is printed to the terminal.
    """
    frame = tk.Frame(parent)
    
    # --- File Selection Frame ---
    file_frame = tk.LabelFrame(frame, text="Refmac5 Input Files", padx=10, pady=10)
    file_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(file_frame, text="MTZ File:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    mtz_var = tk.StringVar()
    mtz_entry = tk.Entry(file_frame, textvariable=mtz_var, width=50)
    mtz_entry.grid(row=0, column=1, padx=5, pady=2)

    def browse_mtz():
        path = filedialog.askopenfilename(
            title="Select .mtz File",
            filetypes=[("MTZ Files", "*.mtz")],
            initialdir=os.getcwd()
        )
        if path:
            mtz_var.set(path)
    tk.Button(file_frame, text="Browse", command=browse_mtz).grid(row=0, column=2, padx=5, pady=2)

    tk.Label(file_frame, text="PDB File:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    pdb_var = tk.StringVar()
    pdb_entry = tk.Entry(file_frame, textvariable=pdb_var, width=50)
    pdb_entry.grid(row=1, column=1, padx=5, pady=2)

    def browse_pdb():
        path = filedialog.askopenfilename(
            title="Select .pdb File",
            filetypes=[("PDB Files", "*.pdb"), ("All Files", "*.*")],
            initialdir=os.getcwd()
        )
        if path:
            pdb_var.set(path)
    tk.Button(file_frame, text="Browse", command=browse_pdb).grid(row=1, column=2, padx=5, pady=2)

    # --- Parameter Frame ---
    param_frame = tk.LabelFrame(frame, text="Optional Parameters", padx=10, pady=10)
    param_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(param_frame, text="max_res:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    max_res_var = tk.DoubleVar(value=20.0)
    tk.Entry(param_frame, textvariable=max_res_var, width=10).grid(row=0, column=1, padx=5, pady=2)

    tk.Label(param_frame, text="min_res:").grid(row=0, column=2, sticky="e", padx=5, pady=2)
    min_res_var = tk.DoubleVar(value=1.5)
    tk.Entry(param_frame, textvariable=min_res_var, width=10).grid(row=0, column=3, padx=5, pady=2)

    tk.Label(param_frame, text="ncycles:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    ncycles_var = tk.IntVar(value=30)
    tk.Entry(param_frame, textvariable=ncycles_var, width=10).grid(row=1, column=1, padx=5, pady=2)

    tk.Label(param_frame, text="bins:").grid(row=1, column=2, sticky="e", padx=5, pady=2)
    bins_var = tk.IntVar(value=10)
    tk.Entry(param_frame, textvariable=bins_var, width=10).grid(row=1, column=3, padx=5, pady=2)

    # --- Refine Button ---
    def on_refine_clicked():
        print("\n" + "="*50)
        print("REFMAC5 REFINEMENT + TABLE PARSING & PLOTTING")
        print("="*50)

        mtz_file = mtz_var.get()
        pdb_file = pdb_var.get()
        if not mtz_file:
            print("Please select an MTZ file first.")
            return
        if not pdb_file:
            print("Please select a PDB file first.")
            return

        max_res = max_res_var.get()
        min_res = min_res_var.get()
        ncycles = ncycles_var.get()
        bins_ = bins_var.get()

        print("Running refinement with parameters:")
        print("  MTZ:", mtz_file)
        print("  PDB:", pdb_file)
        print("  max_res:", max_res)
        print("  min_res:", min_res)
        print("  ncycles:", ncycles)
        print("  bins:", bins_)

        output_dir = ctruncate_freerflag_refmac5(
            mtz_file,
            pdb_file,
            max_res=max_res,
            min_res=min_res,
            ncycles=ncycles,
            bins=bins_
        )
        print("Refinement completed.")

        if output_dir is None:
            print("No output directory returned. Cannot locate refmac5.log for plotting.")
            return

        log_path = os.path.join(output_dir, "refmac5.log")
        if not os.path.isfile(log_path):
            print(f"refmac5.log not found at {log_path}. Skipping plot.")
            return
        
        resolution_list, rf_used_list = parse_refmac_log_for_table(log_path)
        if not resolution_list:
            print("No valid table found in refmac5.log, or columns didn't parse. Skipping plot.")
            return

        # Sort data by resolution ascending.
        sorted_pairs = sorted(zip(resolution_list, rf_used_list), key=lambda x: x[0])
        sorted_res, sorted_rf = zip(*sorted_pairs)

        plt.figure(figsize=(6, 4))
        plt.plot(sorted_res, sorted_rf, marker='o', linestyle='-')
        plt.xlabel("Resolution (Å)")
        plt.ylabel("Rf_used")
        plt.title("Rf_used vs. Resolution")
        plt.grid(True)
        plt.gca().invert_xaxis()  # Flip x-axis so higher resolution is to the left
        plt.tight_layout()
        plt.show()

    refine_button = tk.Button(frame, text="Refine with Refmac5 (and Plot)", bg="lightblue", command=on_refine_clicked)
    refine_button.pack(padx=10, pady=10)

    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Refmac5 Refinement UI")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
