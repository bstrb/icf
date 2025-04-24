import tkinter as tk
from tkinter import ttk

from gui_util.create_scrollable_frame import create_scrollable_frame

import separate_gui.ssed_gandalf_iterator as ssed_gandalf_iterator  # assuming this file is saved as ssed_gandalf_iterator.py
import separate_gui.ssed_visualization  as ssed_visualization # assuming this file is saved as ssed_visualization.py
import separate_gui.ssed_calc_metrics  as ssed_calc_metrics # assuming this file is saved as ssed_calc_metrics.py
import separate_gui.ssed_filter_combine  as ssed_filter_combine # assuming this file is saved as ssed_filter_combine.py
import separate_gui.ssed_merge_convert  as ssed_merge_convert # assuming this file is saved as ssed_merge_convert.py

def main():
    root = tk.Tk()
    root.title("SSED Workflow Including Gandalf Iterator and Index Metrics Based Filtering")
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    
    indexing_frame = tk.Frame(notebook)
    indexing_scrollable = create_scrollable_frame(indexing_frame)
    ui = ssed_gandalf_iterator.get_ui(indexing_scrollable)
    ui.pack(fill="both", expand=True)

    vis_frame = tk.Frame(notebook)
    ui = ssed_visualization.get_ui(vis_frame)
    ui.pack(fill="both", expand=True)

    metrics_frame = tk.Frame(notebook)
    ui = ssed_calc_metrics.get_ui(metrics_frame)
    ui.pack(fill="both", expand=True)

    filter_frame = tk.Frame(notebook)
    filter_scrollable = create_scrollable_frame(filter_frame)
    ui = ssed_filter_combine.get_ui(filter_scrollable)
    ui.pack(fill="both", expand=True)

    merge_frame = tk.Frame(notebook)
    ui = ssed_merge_convert.get_ui(merge_frame)
    ui.pack(fill="both", expand=True)

    
    notebook.add(indexing_frame, text="Indexing")
    notebook.add(vis_frame, text="Visualization")
    notebook.add(metrics_frame, text="Evaluate Metrics")
    notebook.add(filter_frame, text="Filter and Combine")
    notebook.add(merge_frame, text="Merge and Convert")

    root.mainloop()

if __name__ == "__main__":
    main()
