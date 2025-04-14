# ssed_multi_ring_integration.py- Integration for multiple rings with indexing from file GUI
#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from run_indexamajig import run_indexamajig
from read_stream_write_sol import read_stream_write_sol
from adjust_sol_shifts import adjust_sol_shifts
from get_pearson_symbol import get_pearson_symbol

# =================================================================
# =========================== CLEAN UP =============================
# =================================================================
import glob
import shutil
import atexit
import signal

def cleanup_temp_dirs():
    """Remove all directories in the current working directory that start with 'indexamajig'."""
    for d in glob.glob("indexamajig*"):
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"Removed temporary directory: {d}")

atexit.register(cleanup_temp_dirs)

def signal_handler(sig, frame):
    cleanup_temp_dirs()
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
# =================================================================

# Define default peakfinder options.
default_peakfinder_options = {
    'cxi': "--peaks=cxi",
    'peakfinder9': """--peaks=peakfinder9
--min-snr=1
--min-snr-peak-pix=6
--min-sig=9 
--min-peak-over-neighbour=5
--local-bg-radius=5""",
    'peakfinder8': """--peaks=peakfinder8
--threshold=45
--min-snr=3
--min-pix-count=3
--max-pix-count=500
--local-bg-radius=9
--min-res=30
--max-res=500"""
}

def get_ui(parent):
    """
    Creates and returns a Frame containing the complete Gandalf Indexing GUI.
    """
    frame = tk.Frame(parent)
    description = (
    "Run the indexamajig command with indexing from .sol file.\n"
    "Select the input Stream File to be processed.\n"
    "Set basic parameters such as Output Base (name of your sample), Threads (number of used CPU).\n"
    "Configure Peakfinder options, extra flags, and multiple ring-radii sets.\n"
    )
    description_label = tk.Label(frame, text=description, justify=tk.LEFT, wraplength=600)
    description_label.pack(padx=10, pady=10)

    # ----- File Selection Section -----
    file_frame = tk.LabelFrame(frame, text="File Selection", padx=10, pady=10)
    file_frame.pack(fill="x", padx=10, pady=5)
    
    # Geometry file chooser
    tk.Label(file_frame, text="Geometry File (.geom):").grid(row=0, column=0, sticky="w")
    geom_path_var = tk.StringVar()
    geom_entry = tk.Entry(file_frame, textvariable=geom_path_var, width=50)
    geom_entry.grid(row=0, column=1, padx=5)
    tk.Button(file_frame, text="Browse", command=lambda: geom_path_var.set(
        filedialog.askopenfilename(
            title="Select Geometry File (.geom)",
            filetypes=[("Geometry Files", "*.geom")],
            initialdir=os.getcwd()
        )
    )).grid(row=0, column=2, padx=5)
    
    # Cell file chooser
    tk.Label(file_frame, text="Cell File (.cell):").grid(row=1, column=0, sticky="w")
    cell_path_var = tk.StringVar()
    cell_entry = tk.Entry(file_frame, textvariable=cell_path_var, width=50)
    cell_entry.grid(row=1, column=1, padx=5)
    tk.Button(file_frame, text="Browse", command=lambda: cell_path_var.set(
        filedialog.askopenfilename(
            title="Select Cell File (.cell)",
            filetypes=[("Cell Files", "*.cell")],
            initialdir=os.getcwd()
        )
    )).grid(row=1, column=2, padx=5)

    # List file chooser
    tk.Label(file_frame, text="List File (.lst):").grid(row=2, column=0, sticky="w")
    list_path_var = tk.StringVar()
    list_entry = tk.Entry(file_frame, textvariable=list_path_var, width=50)
    list_entry.grid(row=2, column=1, padx=5)
    tk.Button(file_frame, text="Browse", command=lambda: list_path_var.set(
        filedialog.askopenfilename(
            title="Select List File (.lst)",
            filetypes=[("List Files", "*.lst")],
            initialdir=os.getcwd()
        )
    )).grid(row=2, column=2, padx=5)
    
    # Input Stream File chooser
    tk.Label(file_frame, text="Input Stream File:").grid(row=3, column=0, sticky="w")
    input_stream_var = tk.StringVar()
    input_stream_entry = tk.Entry(file_frame, textvariable=input_stream_var, width=50)
    input_stream_entry.grid(row=3, column=1, padx=5)
    tk.Button(file_frame, text="Browse", command=lambda: input_stream_var.set(
        filedialog.askopenfilename(
            title="Select Input Stream File",
            filetypes=[("Stream Files", "*.stream")],
            initialdir=os.getcwd()
        )
    )).grid(row=3, column=2, padx=5)
    
    # ----- Basic Parameters -----
    basic_frame = tk.LabelFrame(frame, text="Basic Parameters", padx=10, pady=10)
    basic_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(basic_frame, text="Output Base:").grid(row=0, column=0, sticky="w")
    output_base_var = tk.StringVar(value="Xtal")
    tk.Entry(basic_frame, textvariable=output_base_var, width=40).grid(row=0, column=1, padx=5)
    
    tk.Label(basic_frame, text="Threads:").grid(row=1, column=0, sticky="w")
    threads_var = tk.StringVar(value="24")
    tk.Entry(basic_frame, textvariable=threads_var, width=10).grid(row=1, column=1, sticky="w", padx=5)
    
    # ----- Peakfinder Section -----
    peakfinder_frame = tk.LabelFrame(frame, text="Peakfinder Options", padx=10, pady=10)
    peakfinder_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(peakfinder_frame, text="Peakfinder:").grid(row=0, column=0, sticky="w")
    peakfinder_option_var = tk.StringVar(value="cxi")
    peakfinder_options = {"CXI": "cxi", "Peakfinder9": "peakfinder9", "Peakfinder8": "peakfinder8"}
    option_menu = tk.OptionMenu(peakfinder_frame, peakfinder_option_var, *peakfinder_options.values())
    option_menu.grid(row=0, column=1, padx=5, sticky="w")
    
    tk.Label(peakfinder_frame, text="Peakfinder Params:").grid(row=1, column=0, sticky="nw")
    peakfinder_params_text = tk.Text(peakfinder_frame, width=60, height=4)
    peakfinder_params_text.grid(row=1, column=1, padx=5, pady=5)
    peakfinder_params_text.insert("1.0", default_peakfinder_options[peakfinder_option_var.get()])
    
    def update_peakfinder_params(*args):
        method = peakfinder_option_var.get()
        peakfinder_params_text.delete("1.0", tk.END)
        peakfinder_params_text.insert("1.0", default_peakfinder_options.get(method, ""))

    peakfinder_option_var.trace_add("write", update_peakfinder_params)
    
    # ----- Other Extra Flags -----
    other_flags_frame = tk.LabelFrame(frame, text="Other Extra Flags", padx=10, pady=10)
    other_flags_frame.pack(fill="x", padx=10, pady=5)
    
    other_flags_text = tk.Text(other_flags_frame, width=60, height=4)
    other_flags_text.pack(padx=5, pady=5)
    other_flags_text.insert("1.0", """--no-revalidate
--min-peaks=15
--no-half-pixel-shift
--no-refine
--no-non-hits-in-stream""")

    # ----- Multiple Ring Radius Sets -----
    multi_int_frame = tk.LabelFrame(frame, text="Multiple Ring Radii Sets", padx=10, pady=10)
    multi_int_frame.pack(fill="x", padx=10, pady=5)
    
    ring_sets_label = tk.Label(multi_int_frame, text="Enter one set per line, e.g.:\n2,5,10\n4,5,9\n3,4,7")
    ring_sets_label.pack(anchor="w")
    
    ring_sets_text = tk.Text(multi_int_frame, width=60, height=5)
    ring_sets_text.pack(padx=5, pady=5)
    ring_sets_text.insert("1.0", "2,5,10\n4,5,9")

    # ----- Run Button -----
    run_button = tk.Button(frame, text="Run Integration", bg="lightblue")
    run_button.pack(padx=10, pady=10)
    
    # ----- Callback for Run Button -----
    def on_run_clicked():
        geom_file = geom_path_var.get()
        cell_file = cell_path_var.get()
        listfile_path = list_path_var.get()
        input_stream = input_stream_var.get()
        
        if not geom_file or not cell_file or not input_stream:
            messagebox.showerror("Error", "Please ensure Geometry, Cell, and Input Stream File are selected.")
            return

        # Create .sol from the .stream, then adjust it
        sol_file = read_stream_write_sol(input_stream, get_pearson_symbol(cell_file))
        adjusted_sol_file = adjust_sol_shifts(
            sol_file, 
            os.path.join(os.path.dirname(input_stream), "adjusted_" + os.path.basename(sol_file))
        )

        # Basic parameters
        output_base = output_base_var.get()
        try:
            threads = int(threads_var.get())
        except ValueError:
            threads = 24

        # Peakfinder parameters
        peakfinder_method = peakfinder_option_var.get()
        peakfinder_params = peakfinder_params_text.get("1.0", tk.END).strip().splitlines()
        
        # Other flags
        other_flags = [line.strip() for line in other_flags_text.get("1.0", tk.END).splitlines() if line.strip()]

        # Fixed flags needed for indexing from file
        fixed_flags = [
            "--indexing=file",
            f"--fromfile-input-file={adjusted_sol_file}",
            "--no-refine",
            "--integration=rings"
        ]

        # Parse ring radius sets
        ring_sets_lines = ring_sets_text.get("1.0", tk.END).splitlines()
        ring_sets = []
        for line in ring_sets_lines:
            line = line.strip()
            if not line:
                continue
            ring_sets.append(line)  # e.g. '2,5,10'
        
        if not ring_sets:
            messagebox.showerror("Error", "Please specify at least one line of ring radii in 'Multiple Ring Radii Sets'.")
            return

        print("Running integration with the following parameters:")
        print("Geometry File:", geom_file)
        print("Cell File:", cell_file)
        print("Input Stream File:", input_stream)
        print("Output Base:", output_base)
        print("Threads:", threads)
        print("Peakfinder Option:", peakfinder_method)
        print("Other Flags:", other_flags)
        print("Ring Sets to be used:", ring_sets)
        print("-----------------------------------------------------")

        for radii_str in ring_sets:
            # Build a new set of flags for *this* ring set
            # We remove any existing `--int-radius=...` from user flags (if present)
            clean_other_flags = [f for f in other_flags if not f.startswith("--int-radius=")]

            # Now, add the ring radius we want:
            this_run_flags = clean_other_flags + peakfinder_params + [f"--int-radius={radii_str}"] + fixed_flags
            
            # Build output path that includes ring radii string
            # e.g. output_base="Xtal" + "_int-2_5_10.stream"
            safe_radii_str = radii_str.replace(",", "_")
            output_path = os.path.join(
                os.path.dirname(input_stream),
                f"{output_base}_int-{safe_radii_str}.stream"
            )
            
            print(f"\n===== Running with int-radius={radii_str} =====")
            print("Combined Flags:", this_run_flags)
            print("Output Stream:", output_path)
            try:
                run_indexamajig(
                    geom_file,
                    listfile_path,
                    cell_file,
                    output_path,
                    threads,
                    extra_flags=this_run_flags
                )
                print("Indexing completed for ring set:", radii_str)
            except Exception as e:
                print(f"Error during indexing for ring set {radii_str}:", e)
    
    run_button.config(command=on_run_clicked)
    
    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Integration with index from file GUI")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
