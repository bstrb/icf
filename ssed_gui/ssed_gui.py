import tkinter as tk
from tkinter import ttk
import ssed_gandalf_iterator  # assuming this file is saved as ssed_gandalf_iterator.py
import ssed_visualization  # assuming this file is saved as ssed_visualization.py
import ssed_calc_metrics  # assuming this file is saved as ssed_calc_metrics.py
import ssed_filter_combine  # assuming this file is saved as ssed_filter_combine.py
import ssed_merge_convert  # assuming this file is saved as ssed_merge_convert.py
import ssed_refmac_refinement # assuming this file is saved as ssed_refmac_refinement.py

def main():
    root = tk.Tk()
    root.title("Combined Application")
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    
    indexing_frame = tk.Frame(notebook)
    vis_frame = tk.Frame(notebook)
    metrics_frame = tk.Frame(notebook)
    filter_frame = tk.Frame(notebook)
    merge_frame = tk.Frame(notebook)
    refinement_frame = tk.Frame(notebook)

    ui = ssed_gandalf_iterator.get_ui(indexing_frame)
    ui.pack(fill="both", expand=True)
    ui = ssed_visualization.get_ui(vis_frame)
    ui.pack(fill="both", expand=True)
    ui = ssed_calc_metrics.get_ui(metrics_frame)
    ui.pack(fill="both", expand=True)
    ui = ssed_filter_combine.get_ui(filter_frame)
    ui.pack(fill="both", expand=True)
    ui = ssed_merge_convert.get_ui(merge_frame)
    ui.pack(fill="both", expand=True)
    ui = ssed_refmac_refinement.get_ui(refinement_frame)
    ui.pack(fill="both", expand=True)

    
    notebook.add(indexing_frame, text="Indexing")
    notebook.add(vis_frame, text="Visualization")
    notebook.add(metrics_frame, text="Evaluate Metrics")
    notebook.add(filter_frame, text="Filter and Combine")
    notebook.add(merge_frame, text="Merge and Convert")
    notebook.add(refinement_frame, text="REFMAC Refinement")

    root.mainloop()

if __name__ == "__main__":
    main()
