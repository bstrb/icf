# ssed_gandalf_iterator.py - Gandalf Indexing GUI
#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import signal
import tempfile
import glob
import shutil
import atexit

# For a fallback "hard stop" of the entire script:
import sys

# Import your indexing function.
from gandalf_interations.gandalf_radial_iterator import gandalf_iterator

# =========================================================================
# Cleanup logic for "indexamajig*" directories
def cleanup_temp_dirs():
    """Remove all directories in the current working directory that start with 'indexamajig'."""
    for d in glob.glob("indexamajig*"):
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"Removed temporary directory: {d}")

atexit.register(cleanup_temp_dirs)

def signal_handler(sig, frame):
    cleanup_temp_dirs()
    sys.exit(0)  # or exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
# =========================================================================

# A global flag and threading object so we can attempt a graceful stop.
stop_requested = False
indexing_thread = None

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

# Fixed indexing flags
INDEXING_FLAGS = [
    "--indexing=xgandalf",
    "--integration=rings",
]

def create_temp_geometry(original_geom_file,
                         wavelength, adu_per_photon,
                         clen, res,
                         corner_x, corner_y):
    """
    Create a temporary geometry file from `original_geom_file` with the specified parameters
    replaced or appended if not found. Returns the path to the newly created temp .geom file.
    """
    with open(original_geom_file, 'r') as f:
        lines = f.readlines()

    # Prepare lines for each parameter we want to override.
    # The dictionary key is the line prefix to match (lowercase),
    # and the value is the *exact* line we want to enforce.
    new_params = {
        'wavelength': f"wavelength  = {wavelength} A\n",
        'adu_per_photon': f"adu_per_photon = {adu_per_photon}\n",
        'clen': f"clen = {clen} m\n",
        'res': f"res = {res}\n",
        # Because corner_x and corner_y usually appear like `p0/corner_x = -512`
        # we match on "p0/corner_x" etc.
        'p0/corner_x': f"p0/corner_x = {corner_x}\n",
        'p0/corner_y': f"p0/corner_y = {corner_y}\n",
    }

    replaced = {k: False for k in new_params}

    for idx, line in enumerate(lines):
        # For matching, strip and lower.
        line_stripped = line.strip().lower()
        for key in new_params:
            # If the line starts with the parameter (e.g. "p0/corner_x")
            if line_stripped.startswith(key):
                lines[idx] = new_params[key]
                replaced[key] = True

    # If any parameter is not found in the file, append it.
    for key, done in replaced.items():
        if not done:
            lines.append(new_params[key])

    # Create a temp directory to hold the updated geometry file.
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="geom_tmp_")
    temp_geom_path = os.path.join(temp_dir, "modified_geometry.geom")

    with open(temp_geom_path, 'w') as out:
        out.writelines(lines)

    return temp_geom_path

def run_indexing(geom_file, cell_file, input_folder, output_base, threads,
                 max_radius, step, flags_list):
    """
    Function to be called inside a separate thread.  
    If gandalf_iterator can check the stop_requested flag, do so.
    Otherwise, we rely on a fallback forced stop (signal).
    """
    global stop_requested

    # Attempt to do something like a pre-check:
    # If stop_requested is True, we skip entirely.
    if stop_requested:
        return

    try:
        # If your gandalf_iterator can check for an external stop signal,
        # you would pass something like `stop_requested=stop_requested`
        # but if not, we just call it.
        gandalf_iterator(
            geom_file,
            cell_file,
            input_folder,
            output_base,
            threads,
            max_radius=max_radius,
            step=step,
            extra_flags=flags_list
        )
        print("Indexing completed successfully.")
    except Exception as e:
        print("Error during indexing:", e)

def get_ui(parent):
    frame = tk.Frame(parent)
    description = (
        "Run the indexamajig command with optional outward center shifts in a grid.\n"
        "Select .geom and .cell files and choose the input folder with .h5 files.\n"
        "Set basic parameters such as Output Base, Threads, Max Radius, and Step.\n"
        "Configure Peakfinder options and advanced indexing parameters.\n"
        "Override geometry parameters below if desired.\n"
        "Click 'Run Indexing' to execute, or 'Stop Indexing' to interrupt.\n"
    )
    description_label = tk.Label(frame, text=description, justify=tk.LEFT, wraplength=600)
    description_label.pack(padx=10, pady=10)

    # ----- File Selection -----
    file_frame = tk.LabelFrame(frame, text="File Selection", padx=10, pady=10)
    file_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(file_frame, text="Geometry File (.geom):").grid(row=0, column=0, sticky="w")
    geom_path_var = tk.StringVar()
    tk.Entry(file_frame, textvariable=geom_path_var, width=50).grid(row=0, column=1, padx=5)
    tk.Button(file_frame, text="Browse",
              command=lambda: geom_path_var.set(filedialog.askopenfilename(
                  title="Select Geometry File (.geom)",
                  filetypes=[("Geometry Files", "*.geom")],
                  initialdir=os.getcwd()))
              ).grid(row=0, column=2, padx=5)
    
    tk.Label(file_frame, text="Cell File (.cell):").grid(row=1, column=0, sticky="w")
    cell_path_var = tk.StringVar()
    tk.Entry(file_frame, textvariable=cell_path_var, width=50).grid(row=1, column=1, padx=5)
    tk.Button(file_frame, text="Browse",
              command=lambda: cell_path_var.set(filedialog.askopenfilename(
                  title="Select Cell File (.cell)",
                  filetypes=[("Cell Files", "*.cell")],
                  initialdir=os.getcwd()))
              ).grid(row=1, column=2, padx=5)
    
    tk.Label(file_frame, text="Input Folder:").grid(row=2, column=0, sticky="w")
    input_folder_var = tk.StringVar()
    tk.Entry(file_frame, textvariable=input_folder_var, width=50).grid(row=2, column=1, padx=5)
    tk.Button(file_frame, text="Browse",
              command=lambda: input_folder_var.set(filedialog.askdirectory(
                  title="Select Input Folder",
                  initialdir=os.getcwd()))
              ).grid(row=2, column=2, padx=5)
    
    # ----- Basic Parameters -----
    basic_frame = tk.LabelFrame(frame, text="Basic Parameters", padx=10, pady=10)
    basic_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(basic_frame, text="Output Base:").grid(row=0, column=0, sticky="w")
    output_base_var = tk.StringVar(value="Xtal")
    tk.Entry(basic_frame, textvariable=output_base_var, width=40).grid(row=0, column=1, padx=5)
    
    tk.Label(basic_frame, text="Threads:").grid(row=1, column=0, sticky="w")
    threads_var = tk.StringVar(value="24")
    tk.Entry(basic_frame, textvariable=threads_var, width=10).grid(row=1, column=1, sticky="w", padx=5)
    
    tk.Label(basic_frame, text="Max Radius:").grid(row=2, column=0, sticky="w")
    max_radius_var = tk.StringVar(value="0.1")
    tk.Entry(basic_frame, textvariable=max_radius_var, width=10).grid(row=2, column=1, sticky="w", padx=5)
    
    tk.Label(basic_frame, text="Step:").grid(row=3, column=0, sticky="w")
    step_var = tk.StringVar(value="0.1")
    tk.Entry(basic_frame, textvariable=step_var, width=10).grid(row=3, column=1, sticky="w", padx=5)
    
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
    
    # ----- Advanced Indexing Parameters -----
    adv_frame = tk.LabelFrame(frame, text="Advanced Indexing Parameters", padx=10, pady=10)
    adv_frame.pack(fill="x", padx=10, pady=5)
    
    tk.Label(adv_frame, text="Min Peaks:").grid(row=0, column=0, sticky="w")
    min_peaks_var = tk.StringVar(value="15")
    tk.Entry(adv_frame, textvariable=min_peaks_var, width=10).grid(row=0, column=1, padx=5)
    
    tk.Label(adv_frame, text="Cell Tolerance:").grid(row=0, column=2, sticky="w")
    tolerance_var = tk.StringVar(value="10,10,10,5")
    tk.Entry(adv_frame, textvariable=tolerance_var, width=20).grid(row=0, column=3, padx=5)
    
    tk.Label(adv_frame, text="Sampling Pitch:").grid(row=1, column=0, sticky="w")
    sampling_pitch_var = tk.StringVar(value="5")
    tk.Entry(adv_frame, textvariable=sampling_pitch_var, width=10).grid(row=1, column=1, padx=5)
    
    tk.Label(adv_frame, text="Grad Desc Iterations:").grid(row=1, column=2, sticky="w")
    grad_desc_iter_var = tk.StringVar(value="1")
    tk.Entry(adv_frame, textvariable=grad_desc_iter_var, width=10).grid(row=1, column=3, padx=5)
    
    tk.Label(adv_frame, text="XGandalf Tolerance:").grid(row=2, column=0, sticky="w")
    xgandalf_tol_var = tk.StringVar(value="0.02")
    tk.Entry(adv_frame, textvariable=xgandalf_tol_var, width=10).grid(row=2, column=1, padx=5)
    
    tk.Label(adv_frame, text="Integration Radius:").grid(row=2, column=2, sticky="w")
    int_radius_var = tk.StringVar(value="2,4,10")
    tk.Entry(adv_frame, textvariable=int_radius_var, width=20).grid(row=2, column=3, padx=5)
    
    # ----- Other Extra Flags -----
    other_flags_frame = tk.LabelFrame(frame, text="Other Extra Flags", padx=10, pady=10)
    other_flags_frame.pack(fill="x", padx=10, pady=5)
    
    other_flags_text = tk.Text(other_flags_frame, width=60, height=4)
    other_flags_text.pack(padx=5, pady=5)
    other_flags_text.insert("1.0", """--no-revalidate
--no-half-pixel-shift
--no-refine
--no-non-hits-in-stream""")
    # --no-image-data
    
    # ----- Override Geometry Parameters -----
    geom_override_frame = tk.LabelFrame(frame, text="Override Geometry Parameters", padx=10, pady=10)
    geom_override_frame.pack(fill="x", padx=10, pady=5)
    
    # Wavelength
    tk.Label(geom_override_frame, text="Wavelength (A):").grid(row=0, column=0, sticky="w")
    wavelength_var = tk.StringVar(value="0.019687")
    tk.Entry(geom_override_frame, textvariable=wavelength_var, width=12).grid(row=0, column=1, padx=5)
    
    # ADU
    tk.Label(geom_override_frame, text="ADU/Photon:").grid(row=0, column=2, sticky="w")
    adu_var = tk.StringVar(value="5")
    tk.Entry(geom_override_frame, textvariable=adu_var, width=12).grid(row=0, column=3, padx=5)
    
    # clen
    tk.Label(geom_override_frame, text="Detector Distance (m):").grid(row=1, column=0, sticky="w")
    clen_var = tk.StringVar(value="0.295")
    tk.Entry(geom_override_frame, textvariable=clen_var, width=12).grid(row=1, column=1, padx=5)
    
    # res
    tk.Label(geom_override_frame, text="Resolution (res):").grid(row=1, column=2, sticky="w")
    res_var = tk.StringVar(value="17857.14285714286")
    tk.Entry(geom_override_frame, textvariable=res_var, width=12).grid(row=1, column=3, padx=5)

    # corner_x
    tk.Label(geom_override_frame, text="p0/corner_x:").grid(row=2, column=0, sticky="w")
    corner_x_var = tk.StringVar(value="-512")
    tk.Entry(geom_override_frame, textvariable=corner_x_var, width=12).grid(row=2, column=1, padx=5)

    # corner_y
    tk.Label(geom_override_frame, text="p0/corner_y:").grid(row=2, column=2, sticky="w")
    corner_y_var = tk.StringVar(value="-512")
    tk.Entry(geom_override_frame, textvariable=corner_y_var, width=12).grid(row=2, column=3, padx=5)
    
    # ----- Buttons -----
    button_frame = tk.Frame(frame)
    button_frame.pack(fill="x", padx=10, pady=10)
    
    run_button = tk.Button(button_frame, text="Run Indexing", bg="lightblue")
    run_button.pack(side="left", padx=5)
    
    stop_button = tk.Button(button_frame, text="Stop Indexing", bg="salmon")
    stop_button.pack(side="left", padx=5)
    
    # ----- Callbacks -----
    def on_run_clicked():
        global stop_requested, indexing_thread
        stop_requested = False  # reset each time we start a new indexing job

        # Validate user input
        geom_file = geom_path_var.get()
        cell_file = cell_path_var.get()
        input_folder = input_folder_var.get()
        if not geom_file or not cell_file or not input_folder:
            messagebox.showerror("Error", "Please ensure Geometry, Cell, and Input Folder are selected.")
            return
        
        # Retrieve basic parameters
        output_base = output_base_var.get()
        try:
            threads = int(threads_var.get())
        except ValueError:
            threads = 24
        try:
            max_radius = float(max_radius_var.get())
        except ValueError:
            max_radius = 1.8
        try:
            step = float(step_var.get())
        except ValueError:
            step = 0.5
        
        # Peakfinder parameters
        peakfinder_method = peakfinder_option_var.get()
        peakfinder_params = peakfinder_params_text.get("1.0", tk.END).strip().splitlines()
        
        # Advanced parameters
        min_peaks_flag = f"--min-peaks={min_peaks_var.get()}"
        tolerance_flag = f"--tolerance={tolerance_var.get()}"
        sampling_pitch_flag = f"--xgandalf-sampling-pitch={sampling_pitch_var.get()}"
        grad_desc_flag = f"--xgandalf-grad-desc-iterations={grad_desc_iter_var.get()}"
        xgandalf_tol_flag = f"--xgandalf-tolerance={xgandalf_tol_var.get()}"
        int_radius_flag = f"--int-radius={int_radius_var.get()}"
        advanced_flags = [
            min_peaks_flag, tolerance_flag, sampling_pitch_flag,
            grad_desc_flag, xgandalf_tol_flag, int_radius_flag
        ]
        
        # Other flags
        other_flags = [
            line.strip() for line in other_flags_text.get("1.0", tk.END).splitlines() if line.strip()
        ]
        
        # Combine all flags
        flags_list = advanced_flags + other_flags + peakfinder_params + INDEXING_FLAGS
        
        # Create temporary geometry file with overrides
        try:
            updated_geom_file = create_temp_geometry(
                geom_file,
                wavelength_var.get(),
                adu_var.get(),
                clen_var.get(),
                res_var.get(),
                corner_x_var.get(),
                corner_y_var.get()
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to create temporary geometry file:\n{exc}")
            return
        
        # Debug print
        print("Running gandalf_iterator with the following parameters:")
        print("  Original Geometry File:", geom_file)
        print("  Temp Geometry File Used:", updated_geom_file)
        print("  Cell File:", cell_file)
        print("  Input Folder:", input_folder)
        print("  Output Base:", output_base)
        print("  Threads:", threads)
        print("  Max Radius:", max_radius)
        print("  Step:", step)
        print("\nPeakfinder Option:", peakfinder_method)
        print("\nCombined Flags:", flags_list)
        
        # Spawn background thread
        def background_task():
            run_indexing(
                updated_geom_file,
                cell_file,
                input_folder,
                output_base,
                threads,
                max_radius,
                step,
                flags_list
            )
        
        indexing_thread = threading.Thread(target=background_task, daemon=True)
        indexing_thread.start()
    
    def on_stop_clicked():
        global stop_requested, indexing_thread
        confirm = messagebox.askyesno("Stop Indexing", "Are you sure you want to stop the indexing process?")
        if confirm:
            # 1) Try setting stop_requested if your gandalf_iterator can handle it:
            stop_requested = True

            # 2) If your indexing function doesn't support a "stop" flag, fallback:
            #    This kills the entire process (including GUI).
            # os.kill(os.getpid(), signal.SIGINT)
            # or:
            # signal.raise_signal(signal.SIGINT)
            
            # If you want to forcibly join the thread or do something else:
            # if indexing_thread and indexing_thread.is_alive():
            #     # Possibly wait or do something else
            #     pass
            print("Stop requested. If gandalf_iterator doesn't check this flag, consider the fallback kill above.")

    run_button.config(command=on_run_clicked)
    stop_button.config(command=on_stop_clicked)
    
    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Gandalf Indexing GUI")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
