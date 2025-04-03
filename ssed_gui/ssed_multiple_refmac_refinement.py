# ssed_multiple_refmac_refinement.py
#!/usr/bin/env python3
import os
import re
import time
import tkinter as tk
from tkinter import filedialog, messagebox, END
import matplotlib.pyplot as plt
import numpy as np

# Import your custom refinement function & parser
from refmac_refine.ctruncate_freerflag_refmac5 import ctruncate_freerflag_refmac5

def parse_refmac_log_for_table(log_path):
    """
    Opens refmac5.log at log_path, finds the last table that contains
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

    # Find the last occurrence of the relevant header line
    header_indices = []
    for i, line in enumerate(lines):
        if "M(4SSQ/LL)" in line and "Rf_used" in line:
            header_indices.append(i)
    if not header_indices:
        return resolution_list, rf_used_list
    start_index = header_indices[-1]
    
    # Find the next line that is exactly "$$" which marks end of the header block.
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
            col1_val = float(parts[0])     # M(4SSQ/LL)
            col6_val = float(parts[5])     # Rf_used
            if col1_val != 0:
                res = np.sqrt(1.0 / col1_val)
                resolution_list.append(res)
                rf_used_list.append(col6_val)
        except ValueError:
            continue

    return resolution_list, rf_used_list

def get_ui(parent):
    """
    Creates and returns a Tkinter Frame containing the Refmac5 refinement UI
    that allows selecting MTZ files from different folders (via a listbox)
    and a single PDB file. It then refines each MTZ and plots all results on one chart.
    """
    frame = tk.Frame(parent)
    explanation = (
        "Refmac5 Refinement and Analysis:\n\n"
        "1) Add MTZ files (you can add files from different folders).\n"
        "2) Select a single PDB file.\n"
        "3) Enter the optional refinement parameters.\n"
        "4) Click 'Refine with Refmac5 (and Plot All)' to run Refmac5 on each MTZ.\n"
        "   A single chart will show Rf_used vs Resolution for all refinements.\n"
    )
    explanation_label = tk.Label(frame, text=explanation, justify=tk.LEFT, wraplength=600)
    explanation_label.pack(padx=10, pady=10)

    # --- File Selection Frame ---
    file_frame = tk.LabelFrame(frame, text="Refmac5 Input Files", padx=10, pady=10)
    file_frame.pack(fill="x", padx=10, pady=5)

    # Listbox to hold multiple MTZ file paths
    tk.Label(file_frame, text="MTZ Files:").grid(row=0, column=0, sticky="nw", padx=5, pady=2)
    mtz_listbox = tk.Listbox(file_frame, width=60, height=5)
    mtz_listbox.grid(row=0, column=1, padx=5, pady=2)

    def add_mtz_file():
        path = filedialog.askopenfilename(
            title="Select an MTZ File",
            filetypes=[("MTZ Files", "*.mtz")],
            initialdir=os.getcwd()
        )
        if path and path not in mtz_listbox.get(0, END):
            mtz_listbox.insert(END, path)
    tk.Button(file_frame, text="Add MTZ File", command=add_mtz_file).grid(row=0, column=2, padx=5, pady=2)

    def remove_selected_mtz():
        selected = mtz_listbox.curselection()
        for index in reversed(selected):
            mtz_listbox.delete(index)
    tk.Button(file_frame, text="Remove Selected", command=remove_selected_mtz).grid(row=1, column=2, padx=5, pady=2)

    # PDB file selection remains the same
    tk.Label(file_frame, text="PDB File:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    pdb_var = tk.StringVar()
    pdb_entry = tk.Entry(file_frame, textvariable=pdb_var, width=50)
    pdb_entry.grid(row=2, column=1, padx=5, pady=2)

    def browse_pdb():
        path = filedialog.askopenfilename(
            title="Select a PDB File",
            filetypes=[("PDB Files", "*.pdb"), ("All Files", "*.*")],
            initialdir=os.getcwd()
        )
        if path:
            pdb_var.set(path)
    tk.Button(file_frame, text="Browse", command=browse_pdb).grid(row=2, column=2, padx=5, pady=2)

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

    # --- Refinement + Plotting ---
    def on_refine_all_clicked():
        """
        For each selected MTZ, run Refmac5 with the single PDB file and
        parse the resulting refmac5.log to plot Rf_used vs. Resolution.
        All results are combined on a single chart.
        """
        print("\n" + "="*50)
        print("REFMAC5 REFINEMENT (MULTIPLE MTZ) + TABLE PARSING & PLOTTING")
        print("="*50)

        mtz_file_list = list(mtz_listbox.get(0, END))
        pdb_file = pdb_var.get().strip()

        if not mtz_file_list:
            print("Please add at least one MTZ file.")
            return
        if not pdb_file:
            print("Please select a PDB file.")
            return

        max_res = max_res_var.get()
        min_res = min_res_var.get()
        ncycles = ncycles_var.get()
        bins_ = bins_var.get()

        print("Running refinement with parameters:")
        print("  MTZ files:", mtz_file_list)
        print("  PDB file: ", pdb_file)
        print("  max_res:  ", max_res)
        print("  min_res:  ", min_res)
        print("  ncycles:  ", ncycles)
        print("  bins:     ", bins_)

        # Dictionary to store (resolution, Rf_used) for each MTZ file
        results_dict = {}

        # Process each MTZ file individually
        for i, mtz_path in enumerate(mtz_file_list, start=1):
            print(f"\n-- Refinement {i}/{len(mtz_file_list)}: {mtz_path}")
            output_dir = ctruncate_freerflag_refmac5(
                mtz_path,
                pdb_file,
                max_res=max_res,
                min_res=min_res,
                ncycles=ncycles,
                bins=bins_
            )
            if not output_dir:
                print("  -> No output directory returned. Skipping.")
                continue

            log_path = os.path.join(output_dir, "refmac5.log")
            if not os.path.isfile(log_path):
                print(f"  -> refmac5.log not found in {output_dir}. Skipping parse.")
                continue

            resolution_list, rf_used_list = parse_refmac_log_for_table(log_path)
            if resolution_list:
                # Sort data by resolution ascending for a nicer plot
                sorted_pairs = sorted(zip(resolution_list, rf_used_list), key=lambda x: x[0])
                sorted_res, sorted_rf = zip(*sorted_pairs)
                results_dict[mtz_path] = (sorted_res, sorted_rf)
            else:
                print("  -> No valid table found in refmac5.log for this MTZ.")

        if not results_dict:
            print("\nNo data to plot. Exiting.")
            return

        # Plot all results on one chart
        plt.figure(figsize=(6, 4))
        for mtz_path, (res_list, rf_list) in results_dict.items():
            label_str = os.path.basename(os.path.dirname(mtz_path))
            plt.plot(res_list, rf_list, marker='o', linestyle='-', label=label_str)

        plt.xlabel("Resolution (Å)")
        plt.ylabel("Rf_used")
        plt.title("Rf_used vs. Resolution (Multiple MTZ Refinements)")
        plt.grid(True)
        plt.gca().invert_xaxis()  # Higher resolution on the left
        plt.legend()
        plt.tight_layout()
        plt.show()

    refine_button = tk.Button(
        frame,
        text="Refine with Refmac5 (and Plot All)",
        bg="lightblue",
        command=on_refine_all_clicked
    )
    refine_button.pack(padx=10, pady=10)

    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Refmac5 Refinement UI - Multiple MTZ")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
