#!/usr/bin/env python3
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, END
import matplotlib.pyplot as plt
import numpy as np

# Try to import tkinterdnd2 for drag-and-drop support; if unavailable, we'll work without it.
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

def parse_refmac_log_for_table(log_path):
    """
    Parses refmac5.log to extract a table with resolution and Rf_used.
    Returns two lists:
      - resolution_list: computed as sqrt(1/(first column))
      - rf_used_list: from the 6th column.
    """
    resolution_list = []
    rf_used_list = []
    if not os.path.isfile(log_path):
        return resolution_list, rf_used_list

    with open(log_path, 'r') as f:
        lines = f.readlines()

    # Locate the last occurrence of the header with "M(4SSQ/LL)" and "Rf_used"
    header_indices = [i for i, line in enumerate(lines) if "M(4SSQ/LL)" in line and "Rf_used" in line]
    if not header_indices:
        return resolution_list, rf_used_list
    start_index = header_indices[-1]

    # Skip to after the header block (marked by "$$")
    for j in range(start_index, len(lines)):
        if lines[j].strip() == "$$":
            start_index = j + 1
            break

    end_index = None
    for j in range(start_index, len(lines)):
        if lines[j].strip() == "$$":
            end_index = j
            break
    if end_index is None:
        return resolution_list, rf_used_list

    raw_table_lines = lines[start_index:end_index]
    for line in raw_table_lines:
        parts = re.split(r"\s+", line.strip())
        if len(parts) < 6:
            continue
        try:
            col1_val = float(parts[0])
            col6_val = float(parts[5])
            if col1_val != 0:
                res = np.sqrt(1.0 / col1_val)
                resolution_list.append(res)
                rf_used_list.append(col6_val)
        except ValueError:
            continue

    return resolution_list, rf_used_list

def add_folder(listbox):
    """Opens a directory dialog to select a folder and adds it to the listbox."""
    folder = filedialog.askdirectory(title="Select a Folder")
    if folder and folder not in listbox.get(0, END):
        listbox.insert(END, folder)

def remove_selected_folder(listbox):
    """Removes the selected folder(s) from the listbox."""
    selected = listbox.curselection()
    for index in reversed(selected):
        listbox.delete(index)

# If drag-and-drop is available, this callback will process dropped folder paths.
def drop_event(event, listbox):
    # event.data is a string with one or more file/folder paths.
    paths = event.data
    # The tk.splitlist method handles curly braces and spaces.
    for folder in event.widget.tk.splitlist(paths):
        # Only add if it's a directory and not already in the listbox.
        if os.path.isdir(folder) and folder not in listbox.get(0, END):
            listbox.insert(END, folder)

def plot_results(folders):
    """
    For each folder, attempts to parse refmac5.log to extract (resolution, Rf_used) data,
    and plots each dataset on one chart. The legend label is the folder's basename.
    The legend is interactive: click a legend item to toggle the corresponding line.
    """
    results_dict = {}
    for folder in folders:
        log_path = os.path.join(folder, "refmac5.log")
        if not os.path.isfile(log_path):
            print(f"refmac5.log not found in {folder}. Skipping.")
            continue

        resolution_list, rf_used_list = parse_refmac_log_for_table(log_path)
        if resolution_list:
            sorted_pairs = sorted(zip(resolution_list, rf_used_list), key=lambda x: x[0])
            sorted_res, sorted_rf = zip(*sorted_pairs)
            results_dict[folder] = (sorted_res, sorted_rf)
        else:
            print(f"No valid data found in {folder}.")

    if not results_dict:
        messagebox.showinfo("No Data", "No valid data to plot.")
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    lines = []
    labels = []
    for folder, (res_list, rf_list) in results_dict.items():
        label_str = os.path.basename(folder)
        line, = ax.plot(res_list, rf_list, marker='o', linestyle='-', label=label_str)
        lines.append(line)
        labels.append(label_str)

    ax.set_xlabel("Resolution (Å)")
    ax.set_ylabel("Rf_used")
    ax.set_title("Rf_used vs. Resolution")
    ax.grid(True)
    ax.invert_xaxis()  # Higher resolution to the left

    # Create a legend with interactive picking.
    leg = ax.legend(fancybox=True, shadow=True)
    leg_lines = leg.get_lines()
    # Map legend line to original line.
    lined = {}
    for legline, origline in zip(leg_lines, lines):
        legline.set_picker(5)  # 5 pts tolerance
        lined[legline] = origline

    def on_pick(event):
        legline = event.artist
        origline = lined[legline]
        # Toggle visibility
        vis = not origline.get_visible()
        origline.set_visible(vis)
        # Fade legend entry if line is hidden.
        legline.set_alpha(1.0 if vis else 0.2)
        fig.canvas.draw()

    fig.canvas.mpl_connect('pick_event', on_pick)
    plt.tight_layout()
    plt.show()

def main():
    # Use TkinterDnD.Tk if available for drag-and-drop, otherwise normal Tk.
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title("Interactive Plot of Refmac5 Results")

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)

    instruction = tk.Label(frame, text="Add folders containing refmac5.log files (drag-and-drop supported if available):")
    instruction.pack(pady=(0, 5))

    # Listbox for folder paths.
    listbox = tk.Listbox(frame, width=70, height=8, selectmode=tk.EXTENDED)
    listbox.pack()

    btn_frame = tk.Frame(frame)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Add Folder", command=lambda: add_folder(listbox)).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Remove Selected", command=lambda: remove_selected_folder(listbox)).grid(row=0, column=1, padx=5)

    tk.Button(frame, text="Plot Results", command=lambda: plot_results(listbox.get(0, END))).pack(pady=5)

    # If drag-and-drop is available, register the listbox as a drop target.
    if DND_AVAILABLE:
        listbox.drop_target_register(DND_FILES)
        listbox.dnd_bind('<<Drop>>', lambda event: drop_event(event, listbox))

    root.mainloop()

if __name__ == '__main__':
    main()
