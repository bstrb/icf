# ssed_visualization.py is a standalone script that generates visualizations for the indexing data.
#!/usr/bin/env python3
import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Import visualization functions.
from visualization.indexing_3d_histogram import plot3d_indexing_rate
from visualization.indexing_center import indexing_heatmap

def get_ui(parent):
    """
    Creates and returns a Frame containing the Visualization GUI.
    
    This GUI allows the user to select an output folder and then click
    "Generate Visualizations" to run the visualization functions.
    Feedback is printed to the terminal.
    """
    frame = tk.Frame(parent)
    
    # Header label.
    header = tk.Label(frame, text="Indexing Data Visualization", font=("Arial", 14, "bold"))
    header.pack(pady=10)
    
    # Folder selection section.
    folder_frame = tk.Frame(frame)
    folder_frame.pack(padx=10, pady=5, fill="x")
    
    tk.Label(folder_frame, text="Output Folder:").pack(side=tk.LEFT)
    folder_var = tk.StringVar()
    folder_entry = tk.Entry(folder_frame, textvariable=folder_var, width=50)
    folder_entry.pack(side=tk.LEFT, padx=5)
    
    def browse_folder():
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=os.getcwd()
        )
        if folder:
            folder_var.set(folder)
    tk.Button(folder_frame, text="Browse", command=browse_folder).pack(side=tk.LEFT, padx=5)
    
    # Button to trigger visualization.
    def on_vis_clicked():
        output_folder = folder_var.get()
        if not output_folder:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        print("Generating visualizations for output folder:", output_folder)
        try:
            # Call the visualization functions.
            plot3d_indexing_rate(output_folder)
            indexing_heatmap(output_folder)
            print("Visualization completed successfully.")
        except Exception as e:
            print("Error during visualization:", e)
    
    tk.Button(frame, text="Generate Visualizations", command=on_vis_clicked, bg="lightblue").pack(pady=10)
    
    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Visualization GUI")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
