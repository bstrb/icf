# ssed_multiple_merge_and_convert.py
#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Import your custom modules
from merge_and_convert.merge import merge
from merge_and_convert.convert_hkl_crystfel_to_shelx import convert_hkl_crystfel_to_shelx
from merge_and_convert.convert_hkl_to_mtz import convert_hkl_to_mtz

def get_ui(parent):
    """
    Demonstrates merging each .stream file separately
    and storing multiple output directories, then optionally
    converting all merges to SHELX / MTZ.
    """
    frame = tk.Frame(parent)
    explanation = (
        "Merging each selected .stream separately:\n"
        " - Select multiple .stream files.\n"
        " - Each file will be merged individually, producing multiple output dirs.\n"
        " - Conversions can be applied to ALL merges or a selected merge.\n"
    )
    explanation_label = tk.Label(frame, text=explanation, justify=tk.LEFT, wraplength=600)
    explanation_label.pack(padx=10, pady=10)

    # We'll keep a list of output directories, one per merged .stream file
    output_dirs = []

    # --- 1) Merging Section ---
    merge_frame = tk.LabelFrame(frame, text="1) Merging Parameters", padx=10, pady=10)
    merge_frame.pack(fill="x", padx=10, pady=5)

    tk.Label(merge_frame, text=".stream Files:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
    stream_var = tk.StringVar()
    tk.Entry(merge_frame, textvariable=stream_var, width=60).grid(row=0, column=1, padx=5, pady=2)

    def on_browse_stream_files():
        selected_files = filedialog.askopenfilenames(
            title="Select .stream Files",
            filetypes=[("Stream Files", "*.stream")],
            initialdir=os.getcwd()
        )
        if selected_files:
            # Join them into a single string for user display
            stream_var.set(";".join(selected_files))

    tk.Button(merge_frame, text="Browse", command=on_browse_stream_files).grid(row=0, column=2, padx=5, pady=2)

    tk.Label(merge_frame, text="Pointgroup:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
    pointgroup_var = tk.StringVar(value="")
    tk.Entry(merge_frame, textvariable=pointgroup_var, width=20).grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(merge_frame, text="Num Threads:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
    threads_var = tk.IntVar(value=24)
    tk.Entry(merge_frame, textvariable=threads_var, width=10).grid(row=2, column=1, padx=5, pady=2, sticky="w")

    tk.Label(merge_frame, text="Iterations:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
    iterations_var = tk.IntVar(value=5)
    tk.Entry(merge_frame, textvariable=iterations_var, width=10).grid(row=3, column=1, padx=5, pady=2, sticky="w")

    merge_button = tk.Button(merge_frame, text="Merge Each", bg="orange", width=12)
    merge_button.grid(row=4, column=0, columnspan=3, pady=10)

    def on_merge_clicked():
        # Clear old data
        del output_dirs[:]

        stream_files_str = stream_var.get().strip()
        if not stream_files_str:
            messagebox.showerror("Error", "Please select at least one .stream file.")
            return

        # Convert the single string to a list of paths
        stream_files_list = [s for s in stream_files_str.split(";") if s]
        
        pg = pointgroup_var.get()
        nthreads = threads_var.get()
        iters = iterations_var.get()

        print("\n" + "="*50)
        print("MERGING SECTION: One merge per file")
        print("="*50)

        # Merge each file independently
        for i, sf in enumerate(stream_files_list, start=1):
            print(f"\nMerging file {i}/{len(stream_files_list)}: {os.path.basename(sf)}")
            try:
                out_dir = merge(
                    sf,
                    pointgroup=pg,
                    num_threads=nthreads,
                    iterations=iters,
                )
                if out_dir:
                    output_dirs.append(out_dir)
                    print(f"   -> Merged OK, results in: {out_dir}")
                else:
                    print(f"   -> Merging failed for {sf}!")
            except Exception as e:
                print(f"   -> Error merging {sf}:", e)

        print(f"\nDone merging {len(stream_files_list)} file(s).")

    merge_button.config(command=on_merge_clicked)

    # --- 2) SHELX Conversion Section ---
    shelx_frame = tk.LabelFrame(frame, text="2) SHELX Conversion", padx=10, pady=10)
    shelx_frame.pack(fill="x", padx=10, pady=5)

    # Option A: Convert all merges
    shelx_button_all = tk.Button(shelx_frame, text="Convert ALL to SHELX", bg="lightblue", width=20)
    shelx_button_all.grid(row=0, column=0, padx=5, pady=5)

    def on_shelx_clicked_all():
        if not output_dirs:
            print("No merged output available. Please run the merge step first.")
            return
        print("\nSHELX CONVERSION FOR ALL MERGES")
        for odir in output_dirs:
            print(f"Converting {odir}...")
            try:
                convert_hkl_crystfel_to_shelx(odir)
            except Exception as e:
                print(f"   -> Error converting {odir}:", e)
        print("Finished SHELX conversions.")

    shelx_button_all.config(command=on_shelx_clicked_all)

    # Option B: Convert only a chosen merge
    tk.Label(shelx_frame, text="or choose one folder:").grid(row=1, column=0, sticky="e")
    single_shelx_var = tk.StringVar(value="")
    tk.Entry(shelx_frame, textvariable=single_shelx_var, width=40).grid(row=1, column=1, padx=5)

    def on_browse_single_merge_for_shelx():
        # Let the user pick from the known merges or any directory
        chosen_dir = filedialog.askdirectory(title="Select Merged Results Folder", initialdir=os.getcwd())
        if chosen_dir:
            single_shelx_var.set(chosen_dir)

    tk.Button(shelx_frame, text="Browse", command=on_browse_single_merge_for_shelx).grid(row=1, column=2, padx=5)

    shelx_button_one = tk.Button(shelx_frame, text="Convert ONE to SHELX", bg="lightblue", width=20)
    shelx_button_one.grid(row=2, column=0, columnspan=3, padx=5, pady=5)

    def on_shelx_clicked_one():
        odir = single_shelx_var.get().strip()
        if not odir:
            messagebox.showerror("Error", "Please select or enter one merged-results folder.")
            return
        print(f"\nSHELX Conversion for: {odir}")
        try:
            convert_hkl_crystfel_to_shelx(odir)
            print("Conversion to SHELX completed.")
        except Exception as e:
            print("Error during SHELX conversion:", e)

    shelx_button_one.config(command=on_shelx_clicked_one)

    # --- 3) MTZ Conversion Section ---
    mtz_frame = tk.LabelFrame(frame, text="3) MTZ Conversion", padx=10, pady=10)
    mtz_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(mtz_frame, text="Cell File:").grid(row=0, column=0, sticky="w")
    cell_var = tk.StringVar()
    tk.Entry(mtz_frame, textvariable=cell_var, width=50).grid(row=0, column=1, padx=5, pady=2)

    def on_browse_cell_file():
        cell_path = filedialog.askopenfilename(
            title="Select Cell File",
            filetypes=[("Cell Files", "*.cell"), ("All Files", "*.*")],
            initialdir=os.getcwd()
        )
        if cell_path:
            cell_var.set(cell_path)

    tk.Button(mtz_frame, text="Browse", command=on_browse_cell_file).grid(row=0, column=2, padx=5, pady=2)

    # Option A: Convert all merges
    mtz_button_all = tk.Button(mtz_frame, text="Convert ALL to MTZ", bg="green", width=20)
    mtz_button_all.grid(row=1, column=0, padx=5, pady=5)

    def on_mtz_clicked_all():
        if not output_dirs:
            print("No merged output available. Please run the merge step first.")
            return
        cell_file = cell_var.get()
        if not cell_file:
            messagebox.showerror("Error", "Please select a cell file first.")
            return
        
        print("\nMTZ CONVERSION FOR ALL MERGES")
        for odir in output_dirs:
            print(f"Converting {odir}...")
            try:
                convert_hkl_to_mtz(odir, cellfile_path=cell_file)
            except Exception as e:
                print(f"   -> Error converting {odir}:", e)
        print("Finished MTZ conversions.")

    mtz_button_all.config(command=on_mtz_clicked_all)

    # Option B: Convert only a chosen merge
    tk.Label(mtz_frame, text="or choose one folder:").grid(row=2, column=0, sticky="e")
    single_mtz_var = tk.StringVar(value="")
    tk.Entry(mtz_frame, textvariable=single_mtz_var, width=40).grid(row=2, column=1, padx=5)

    def on_browse_single_merge_for_mtz():
        chosen_dir = filedialog.askdirectory(title="Select Merged Results Folder", initialdir=os.getcwd())
        if chosen_dir:
            single_mtz_var.set(chosen_dir)

    tk.Button(mtz_frame, text="Browse", command=on_browse_single_merge_for_mtz).grid(row=2, column=2, padx=5)

    mtz_button_one = tk.Button(mtz_frame, text="Convert ONE to MTZ", bg="green", width=20)
    mtz_button_one.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

    def on_mtz_clicked_one():
        odir = single_mtz_var.get().strip()
        if not odir:
            messagebox.showerror("Error", "Please select or enter a merged-results folder.")
            return
        cell_file = cell_var.get()
        if not cell_file:
            messagebox.showerror("Error", "Please select a cell file first.")
            return
        
        print(f"\nMTZ Conversion for: {odir}")
        try:
            convert_hkl_to_mtz(odir, cellfile_path=cell_file)
            print("Conversion to MTZ completed.")
        except Exception as e:
            print("Error during MTZ conversion:", e)

    mtz_button_one.config(command=on_mtz_clicked_one)

    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Separate Merging & Multiple Conversions")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
