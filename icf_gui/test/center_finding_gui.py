# center_finding_import.py
import os
import h5py
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox

# Import your updated processing function.
from image_processing_fast import process_images_apply_async

def select_file(title, filetypes):
    """Helper to open a file dialog and return the selected file path."""
    return filedialog.askopenfilename(
        title=title,
        filetypes=filetypes,
        initialdir=os.getcwd()
    )

def get_ui(parent):
    """
    Creates and returns a Frame containing the Center Finding GUI.
    This frame can be embedded in another container.
    """
    frame = tk.Frame(parent)
    
    # Instruction label.
    instructions = (
        "Select your H5 image file and a mask file, then set parameters to find the diffraction center.\n"
        "A CSV with the found centers will be created in the same folder as the selected image file.\n"
        "Processing feedback will be printed to the terminal."
    )
    instruction_label = tk.Label(frame, text=instructions, justify=tk.LEFT)
    instruction_label.grid(row=0, column=0, columnspan=5, padx=10, pady=10, sticky='w')
    
    # H5 Image File selection.
    tk.Label(frame, text="H5 Image File:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    image_file_var = tk.StringVar()
    image_file_entry = tk.Entry(frame, textvariable=image_file_var, width=50)
    image_file_entry.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky='w')
    
    def browse_image():
        file = select_file("Select H5 Image File", [("H5 files", "*.h5")])
        if file:
            image_file_var.set(file)
    tk.Button(frame, text="Browse", command=browse_image).grid(row=1, column=4, padx=10, pady=5)
    
    # Mask File selection.
    tk.Label(frame, text="Mask H5 File:").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    mask_file_var = tk.StringVar()
    mask_file_entry = tk.Entry(frame, textvariable=mask_file_var, width=50)
    mask_file_entry.grid(row=2, column=1, columnspan=3, padx=10, pady=5, sticky='w')
    
    def browse_mask():
        file = select_file("Select Mask H5 File", [("H5 files", "*.h5")])
        if file:
            mask_file_var.set(file)
    tk.Button(frame, text="Browse", command=browse_mask).grid(row=2, column=4, padx=10, pady=5)
    
    # Checkbox for using the mask.
    use_mask_var = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="Use Mask", variable=use_mask_var).grid(row=3, column=0, columnspan=5, padx=10, pady=5, sticky='w')
    
    # Parameter entries: xatol, frame interval, and verbose.
    tk.Label(frame, text="xatol:").grid(row=4, column=0, padx=10, pady=5, sticky='e')
    xatol_var = tk.DoubleVar(value=0.01)
    tk.Entry(frame, textvariable=xatol_var, width=10).grid(row=4, column=1, padx=10, pady=5, sticky='w')
    
    tk.Label(frame, text="Frame Interval:").grid(row=4, column=2, padx=10, pady=5, sticky='e')
    frame_interval_var = tk.IntVar(value=10)
    tk.Entry(frame, textvariable=frame_interval_var, width=10).grid(row=4, column=3, padx=10, pady=5, sticky='w')
    
    verbose_var = tk.BooleanVar(value=False)
    tk.Checkbutton(frame, text="Verbose", variable=verbose_var).grid(row=4, column=4, padx=10, pady=5, sticky='w')
    
    # ROI parameter entries for xmin and xmax.
    tk.Label(frame, text="xmin:").grid(row=5, column=0, padx=10, pady=5, sticky='e')
    xmin_var = tk.IntVar(value=0)
    tk.Entry(frame, textvariable=xmin_var, width=10).grid(row=5, column=1, padx=10, pady=5, sticky='w')
    
    tk.Label(frame, text="xmax:").grid(row=5, column=2, padx=10, pady=5, sticky='e')
    xmax_var = tk.IntVar(value=0)
    tk.Entry(frame, textvariable=xmax_var, width=10).grid(row=5, column=3, padx=10, pady=5, sticky='w')
    
    # ROI parameter entries for ymin and ymax.
    tk.Label(frame, text="ymin:").grid(row=6, column=0, padx=10, pady=5, sticky='e')
    ymin_var = tk.IntVar(value=0)
    tk.Entry(frame, textvariable=ymin_var, width=10).grid(row=6, column=1, padx=10, pady=5, sticky='w')
    
    tk.Label(frame, text="ymax:").grid(row=6, column=2, padx=10, pady=5, sticky='e')
    ymax_var = tk.IntVar(value=0)
    tk.Entry(frame, textvariable=ymax_var, width=10).grid(row=6, column=3, padx=10, pady=5, sticky='w')
    
    def process_images():
        # Retrieve file paths and parameters.
        image_file = image_file_var.get()
        mask_file = mask_file_var.get()
        if not image_file:
            print("Please select an H5 image file.")
            messagebox.showerror("Error", "Please select an H5 image file.")
            return
        if not mask_file:
            print("Please select a mask H5 file.")
            messagebox.showerror("Error", "Please select a mask H5 file.")
            return

        print("Processing images from file:")
        print(" ", image_file)
        print("Parameters:")
        print("  xatol =", xatol_var.get())
        print("  Frame Interval =", frame_interval_var.get())
        print("  Verbose =", verbose_var.get())
        print("ROI:")
        print("  xmin =", xmin_var.get(), "xmax =", xmax_var.get(),
              "ymin =", ymin_var.get(), "ymax =", ymax_var.get())
        print("Using Mask:", use_mask_var.get())
        print("")
        
        try:
            with h5py.File(mask_file, 'r') as f_mask:
                if use_mask_var.get():
                    mask = f_mask['/mask'][:].astype(bool)
                else:
                    sample = f_mask['/mask'][0]
                    mask = np.ones_like(sample, dtype=bool)
        except Exception as e:
            print("Error loading mask file:", e)
            messagebox.showerror("Error", "Error loading mask file:\n" + str(e))
            return
        
        # Run the processing function.
        process_images_apply_async(
            image_file=image_file,
            mask=mask,
            frame_interval=frame_interval_var.get(),
            xatol=xatol_var.get(),
            fatol=10,
            n_wedges=4,
            n_rad_bins=100,
            xmin=xmin_var.get(),
            xmax=xmax_var.get(),
            ymin=ymin_var.get(),
            ymax=ymax_var.get(),
            verbose=verbose_var.get()
        )
        print("Processing completed.")
    
    tk.Button(frame, text="Process Images", command=process_images)\
        .grid(row=7, column=0, columnspan=5, padx=10, pady=10)
    
    return frame

if __name__ == '__main__':
    # For standalone testing.
    root = tk.Tk()
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
