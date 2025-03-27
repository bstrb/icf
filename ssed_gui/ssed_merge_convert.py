# ssed_merge_convert.py
#!/usr/bin/env python3
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox

# Import your custom modules (assumed to be available in your PYTHONPATH)
from merge_and_convert.merge import merge
from merge_and_convert.convert_hkl_crystfel_to_shelx import convert_hkl_crystfel_to_shelx 
from merge_and_convert.convert_hkl_to_mtz import convert_hkl_to_mtz

def get_ui(parent):
    """
    Creates and returns a Tkinter Frame containing the interactive merging and conversion UI.
    
    This version prints all feedback to the terminal (no progress bar or log text widget).
    It provides three sections:
      1. Merging Section: Select a .stream file and parameters, then run merge.
      2. SHELX Conversion Section: Convert merged output to SHELX.
      3. MTZ Conversion Section: Select a cell file and convert merged output to MTZ.
    """
    frame = tk.Frame(parent)
    explanation = (
    "Merging:\n"
    " - Select a .stream file and set merging parameters (pointgroup, threads, iterations) to merge data from multiple indexing iterations.\n\n"
    "SHELX Conversion:\n"
    " - Convert the merged output to the SHELX format.\n\n"
    "MTZ Conversion:\n"
    " - Select a cell file and convert the merged output to MTZ format for further analysis."
    )
    explanation_label = tk.Label(frame, text=explanation, justify=tk.LEFT, wraplength=600)
    explanation_label.pack(padx=10, pady=10)
    # Container to store the merged output directory.
    global_output_dir = [None]

    # --- 1) Merging Section ---
    merge_frame = tk.LabelFrame(frame, text="1) Merging Parameters", padx=10, pady=10)
    merge_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(merge_frame, text=".stream File:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    stream_var = tk.StringVar()
    tk.Entry(merge_frame, textvariable=stream_var, width=50).grid(row=0, column=1, padx=5, pady=2)
    tk.Button(merge_frame, text="Browse", command=lambda: stream_var.set(
        filedialog.askopenfilename(
            title="Select .stream File",
            filetypes=[("Stream Files", "*.stream")],
            initialdir=os.getcwd()
        )
    )).grid(row=0, column=2, padx=5, pady=2)
    
    tk.Label(merge_frame, text="Pointgroup:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    pointgroup_var = tk.StringVar(value="")
    tk.Entry(merge_frame, textvariable=pointgroup_var, width=20).grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(merge_frame, text="Num Threads:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    threads_var = tk.IntVar(value=24)
    tk.Entry(merge_frame, textvariable=threads_var, width=10).grid(row=2, column=1, padx=5, pady=2, sticky="w")

    tk.Label(merge_frame, text="Iterations:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
    iterations_var = tk.IntVar(value=5)
    tk.Entry(merge_frame, textvariable=iterations_var, width=10).grid(row=3, column=1, padx=5, pady=2, sticky="w")

    merge_button = tk.Button(merge_frame, text="Merge", bg="orange", width=10)
    merge_button.grid(row=4, column=0, columnspan=3, pady=10)

    def on_merge_clicked():
        stream_file = stream_var.get()
        if not stream_file:
            messagebox.showerror("Error", "Please select a .stream file first.")
            return
        pg = pointgroup_var.get()
        nthreads = threads_var.get()
        iters = iterations_var.get()
        print("\n" + "="*50)
        print("MERGING SECTION")
        print("="*50)
        print("Merging in progress...")
        time.sleep(0.2)
        output_dir = merge(
            stream_file,
            pointgroup=pg,
            num_threads=nthreads,
            iterations=iters,
        )
        time.sleep(0.2)
        if output_dir is not None:
            global_output_dir[0] = output_dir
            print("Merging done. Results are in:", output_dir)
        else:
            print("Merging failed. Please check the parameters and try again.")
        print("Done merging.")

    merge_button.config(command=on_merge_clicked)

    # --- 2) SHELX Conversion Section ---
    shelx_frame = tk.LabelFrame(frame, text="2) SHELX Conversion", padx=10, pady=10)
    shelx_frame.pack(fill="x", padx=10, pady=5)
    
    shelx_button = tk.Button(shelx_frame, text="Convert to SHELX", bg="lightblue", width=20)
    shelx_button.pack(pady=5)

    def on_shelx_clicked():
        print("\n" + "="*50)
        print("SHELX CONVERSION")
        print("="*50)
        if global_output_dir[0] is None:
            print("No merged output available. Please run the merge step first.")
            return
        try:
            print("Converting to SHELX...")
            convert_hkl_crystfel_to_shelx(global_output_dir[0])
            print("Conversion to SHELX completed.")
        except Exception as e:
            print("Error during SHELX conversion:", e)

    shelx_button.config(command=on_shelx_clicked)

    # --- 3) MTZ Conversion Section ---
    mtz_frame = tk.LabelFrame(frame, text="3) MTZ Conversion", padx=10, pady=10)
    mtz_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(mtz_frame, text="Cell File:").grid(row=0, column=0, sticky="w")
    cell_var = tk.StringVar()
    tk.Entry(mtz_frame, textvariable=cell_var, width=50).grid(row=0, column=1, padx=5, pady=2)
    tk.Button(mtz_frame, text="Browse", command=lambda: cell_var.set(
        filedialog.askopenfilename(
            title="Select Cell File",
            filetypes=[("Cell Files", "*.cell"), ("All Files", "*.*")],
            initialdir=os.getcwd()
        )
    )).grid(row=0, column=2, padx=5, pady=2)
    
    mtz_button = tk.Button(mtz_frame, text="Convert to MTZ", bg="green", width=20)
    mtz_button.grid(row=1, column=0, columnspan=3, pady=5)

    def on_mtz_clicked():
        print("\n" + "="*50)
        print("MTZ CONVERSION")
        print("="*50)
        if global_output_dir[0] is None:
            print("No merged output available. Please run the merge step first.")
            return
        cell_file = cell_var.get()
        if not cell_file:
            messagebox.showerror("Error", "Please select a cell file first.")
            return
        try:
            print("Converting to MTZ...")
            convert_hkl_to_mtz(global_output_dir[0], cellfile_path=cell_file)
            print("Conversion to MTZ completed.")
        except Exception as e:
            print("Error during MTZ conversion:", e)

    mtz_button.config(command=on_mtz_clicked)

    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Interactive Merging & Conversion Tool")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
