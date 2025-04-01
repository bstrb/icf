# ssed_index_from_file.py - Integration with indexing from file GUI
#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Import the indexamajig function.
from run_indexamajig import run_indexamajig
from read_stream_write_sol import read_stream_write_sol
from adjust_sol_shifts import adjust_sol_shifts
from get_pearson_symbol import get_pearson_symbol
# =================================================================
# =========================== PRINT FILTER ========================
# =================================================================
import builtins

_original_print = print

def filtered_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    if message.startswith("WARNING: No solution for"):
        return
    _original_print(*args, **kwargs)

print = filtered_print

# =================================================================
# =========================== CLEAN UP ============================
# =================================================================
# Import the necessary modules for cleanup.
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

# Register cleanup function to run at program exit.
atexit.register(cleanup_temp_dirs)

# Optionally, catch termination signals to ensure cleanup on interruptions.
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
    "Configure Peakfinder options and optionally extra flags.\n"
    )
    description_label = tk.Label(frame, text=description, justify=tk.LEFT, wraplength=600)
    description_label.pack(padx=10, pady=10)

    # ----- File Selection Section -----
    file_frame = tk.LabelFrame(frame, text="File Selection", padx=10, pady=10)
    file_frame.pack(fill="x", padx=10, pady=5)
    
    # Geometry file chooser.
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
    
    # Cell file chooser.
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

    # List file chooser.
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
    
    # Input Stream File chooser.
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
    # OptionMenu: Display labels and values are as follows.
    peakfinder_options = {"CXI": "cxi", "Peakfinder9": "peakfinder9", "Peakfinder8": "peakfinder8"}
    option_menu = tk.OptionMenu(peakfinder_frame, peakfinder_option_var, *peakfinder_options.values())
    option_menu.grid(row=0, column=1, padx=5, sticky="w")
    
    tk.Label(peakfinder_frame, text="Peakfinder Params:").grid(row=1, column=0, sticky="nw")
    # Use a Text widget for multi-line parameters.
    peakfinder_params_text = tk.Text(peakfinder_frame, width=60, height=4)
    peakfinder_params_text.grid(row=1, column=1, padx=5, pady=5)
    # Initialize with default options.
    peakfinder_params_text.insert("1.0", default_peakfinder_options[peakfinder_option_var.get()])
    
    # When the dropdown changes, update the text widget with the default options.
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
--no-half-pixel-shift
--no-refine
--no-non-hits-in-stream""")
    
    # ----- Run Button -----
    run_button = tk.Button(frame, text="Run Integration", bg="lightblue")
    run_button.pack(padx=10, pady=10)
    
    # ----- Callback for Run Button -----
    def on_run_clicked():
        # Retrieve file selections.
        geom_file = geom_path_var.get()
        cell_file = cell_path_var.get()
        listfile_path = list_path_var.get()
        input_stream = input_stream_var.get()
        
        sol_file = read_stream_write_sol(input_stream, get_pearson_symbol(cell_file))
        adjusted_sol_file = adjust_sol_shifts(sol_file, os.path.join(os.path.dirname(input_stream), "adjusted_" + os.path.basename(sol_file)))

        extra_flags=[
        # INDEXING
        "--indexing=file",
        f"--fromfile-input-file={adjusted_sol_file}",
        # "--no-check-cell",
        # "--no-check-peaks",
        # "--no-retry",
        # "--no-refine",
        # INTEGRATION
        "--integration=rings",
        "--int-radius=2,5,10",
        # OUTPUT
        # "--no-non-hits-in-stream",
        ]

        if not geom_file or not cell_file or not input_stream:
            messagebox.showerror("Error", "Please ensure Geometry, Cell, and Input Stream File are selected.")
            return
        
        # Retrieve basic parameters.
        output_base = output_base_var.get()
        try:
            threads = int(threads_var.get())
        except:
            threads = 24

        # Peakfinder parameters.
        peakfinder_method = peakfinder_option_var.get()
        peakfinder_params = peakfinder_params_text.get("1.0", tk.END).strip().splitlines()
        
        
        # Other flags.
        other_flags = [line.strip() for line in other_flags_text.get("1.0", tk.END).splitlines() if line.strip()]
        
        # Combine all flags in the proper order.
        flags_list = other_flags + peakfinder_params + extra_flags
        
        print("Running gandalf_iterator with the following parameters:")
        print("Geometry File:", geom_file)
        print("Cell File:", cell_file)
        print("Input Stream File:", input_stream)
        print("Output Base:", output_base)
        print("Threads:", threads)
        print("\nPeakfinder Option:", peakfinder_method)
        print("\nOther Flags:")
        for f in other_flags:
            print(" ", f)
        print("\nCombined Flags:", flags_list)
        
        output_path = os.path.join(os.path.dirname(input_stream), output_base+".stream")

        try:
            run_indexamajig(
                geom_file,
                listfile_path,
                cell_file,
                output_path,
                threads,
                extra_flags=flags_list
            )
            print("Indexing completed successfully.")
        except Exception as e:
            print("Error during indexing:", e)
    
    run_button.config(command=on_run_clicked)
    
    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Integration with index from file GUI")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
