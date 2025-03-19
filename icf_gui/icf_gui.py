import tkinter as tk
from tkinter import ttk
import center_finding_gui as center_finding_gui
import filter_centers_gui as filter_centers_gui      # your filtering GUI module (refactored similarly)
import smooth_and_shift_gui as smooth_and_shift_gui  # your lowess/H5 update GUI module (refactored similarly)

def main():
    root = tk.Tk()
    root.title("Combined Image Processing GUI")
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    
    # Create a frame for each section.
    frame1 = tk.Frame(notebook)
    frame2 = tk.Frame(notebook)
    frame3 = tk.Frame(notebook)
    
    # Populate each frame using the get_ui function from the modules.
    center_finding_gui.get_ui(frame1).pack(fill="both", expand=True)
    filter_centers_gui.get_ui(frame2).pack(fill="both", expand=True)
    smooth_and_shift_gui.get_ui(frame3).pack(fill="both", expand=True)
    
    notebook.add(frame1, text="Center Finding")
    notebook.add(frame2, text="Filtering & Plotting")
    notebook.add(frame3, text="Lowess H5 Update")
    
    root.mainloop()

if __name__ == "__main__":
    main()
