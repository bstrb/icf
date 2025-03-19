# filter_centers_import.py
#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox

def load_csv(filename=None):
    """
    Loads a CSV file. If a filename is provided, it uses that; otherwise, it opens a file dialog.
    Returns the dataframe and the filename.
    """
    if not filename:
        filename = filedialog.askopenfilename(
            title="Select CSV File with Center Data",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=os.getcwd()
        )
    if not filename:
        return None, None
    try:
        df = pd.read_csv(filename)
        print(f"Loaded {len(df)} rows from {filename}")
        return df, filename
    except Exception as e:
        messagebox.showerror("Error", f"Error loading CSV: {e}")
        return None, None

def apply_filtering(df, csv_path, x_min, x_max, y_min, y_max, remove_outliers, outlier_std):
    """Applies the filtering logic to the dataframe and plots the results in subplots."""
    # Close any previously opened figures.
    plt.close('all')
    
    # Create a copy and ensure center columns can store empty strings.
    df_filtered = df.copy()
    df_filtered['center_x'] = df_filtered['center_x'].astype(object)
    df_filtered['center_y'] = df_filtered['center_y'].astype(object)
    
    # Create mask for rows with center values within the selected range.
    mask_range = (
        (df_filtered['center_x'].astype(float) >= x_min) &
        (df_filtered['center_x'].astype(float) <= x_max) &
        (df_filtered['center_y'].astype(float) >= y_min) &
        (df_filtered['center_y'].astype(float) <= y_max)
    )
    
    # Remove outliers if enabled.
    if remove_outliers:
        valid_in_range = df_filtered[mask_range].copy()
        valid_in_range['center_x'] = valid_in_range['center_x'].astype(float)
        valid_in_range['center_y'] = valid_in_range['center_y'].astype(float)
        if not valid_in_range.empty:
            x_mean = valid_in_range['center_x'].mean()
            x_std = valid_in_range['center_x'].std()
            y_mean = valid_in_range['center_y'].mean()
            y_std = valid_in_range['center_y'].std()
            mask_outlier = (
                (abs(df_filtered['center_x'].astype(float) - x_mean) <= outlier_std * x_std) &
                (abs(df_filtered['center_y'].astype(float) - y_mean) <= outlier_std * y_std)
            )
        else:
            mask_outlier = mask_range
        valid_mask = mask_range & mask_outlier
    else:
        valid_mask = mask_range
    
    # For rows that do not satisfy the filter, replace center values with empty strings.
    df_filtered.loc[~valid_mask, ['center_x', 'center_y']] = ""
    
    # Compute and print statistics for the valid rows.
    valid_rows = df_filtered[valid_mask]
    print("=== Valid Data Statistics ===")
    print(f"Number of valid rows: {len(valid_rows)} out of {len(df_filtered)}")
    for col in ['center_x', 'center_y']:
        try:
            valid_floats = valid_rows[col].astype(float)
            mean_val = valid_floats.mean()
            median_val = valid_floats.median()
            std_val = valid_floats.std()
            print(f"{col} => mean: {mean_val:.3f}, median: {median_val:.3f}, std: {std_val:.3f}")
        except Exception:
            print(f"{col} has non-numeric values.")
    
    # Save the modified CSV.
    output_folder = os.path.dirname(csv_path)
    base = os.path.basename(csv_path)
    basename, ext = os.path.splitext(base)
    output_filename = os.path.join(output_folder, f"{basename}_filtered.csv")
    df_filtered.to_csv(output_filename, index=False)
    print(f"\nFiltered CSV saved to: {output_filename}\n")
    
    # Prepare valid rows for plotting.
    valid_rows_numeric = valid_rows.copy()
    valid_rows_numeric['center_x'] = valid_rows_numeric['center_x'].apply(lambda v: float(v) if v != "" else None)
    valid_rows_numeric['center_y'] = valid_rows_numeric['center_y'].apply(lambda v: float(v) if v != "" else None)
    valid_rows_numeric = valid_rows_numeric.dropna(subset=['center_x', 'center_y'])
    
    # Use the 'data_index' column as the x-axis for the plots.
    if 'data_index' not in valid_rows_numeric.columns:
        print("Warning: 'data_index' column not found in CSV. Using default DataFrame index.")
        x_axis = valid_rows_numeric.index
    else:
        x_axis = valid_rows_numeric['data_index']
    
    # Create subplots in a single figure.
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Plot center_x vs data_index.
    ax1.plot(x_axis, valid_rows_numeric['center_x'], marker='o', linestyle='-')
    ax1.set_ylabel('Center X')
    ax1.set_title('Center X vs Data Index')
    ax1.grid(True)
    
    # Plot center_y vs data_index.
    ax2.plot(x_axis, valid_rows_numeric['center_y'], marker='o', linestyle='-')
    ax2.set_xlabel('Data Index')
    ax2.set_ylabel('Center Y')
    ax2.set_title('Center Y vs Data Index')
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show()

def get_ui(parent):
    """
    Creates and returns a Frame containing the filtering & plotting GUI.
    This frame can be embedded into a larger application.
    """
    frame = tk.Frame(parent)
    
    # A state container to hold loaded CSV data.
    state = {"df": None, "csv_path": None}
    
    # --- CSV File Selection ---
    file_frame = tk.Frame(frame)
    file_frame.pack(padx=10, pady=10, fill=tk.X)
    tk.Label(file_frame, text="CSV File with Center Data:").pack(side=tk.LEFT)
    file_path_var = tk.StringVar(frame)
    file_entry = tk.Entry(file_frame, textvariable=file_path_var, width=50)
    file_entry.pack(side=tk.LEFT, padx=5)
    
    def browse_file():
        filename = filedialog.askopenfilename(
            title="Select CSV File with Center Data",
            filetypes=[("CSV Files", "*.csv")],
            initialdir=os.getcwd()
        )
        if filename:
            file_path_var.set(filename)
    
    tk.Button(file_frame, text="Browse", command=browse_file).pack(side=tk.LEFT)
    
    # --- Load CSV Button ---
    def on_load_csv():
        filename = file_path_var.get()
        if not filename:
            messagebox.showerror("Error", "Please select a CSV file.")
            return
        df, path = load_csv(filename)
        if df is not None:
            state["df"] = df
            state["csv_path"] = path
            try:
                x_min_default = df['center_x'].min()
                x_max_default = df['center_x'].max()
                y_min_default = df['center_y'].min()
                y_max_default = df['center_y'].max()
                x_min_var.set(x_min_default)
                x_max_var.set(x_max_default)
                y_min_var.set(y_min_default)
                y_max_var.set(y_max_default)
            except Exception as e:
                print(f"Error setting default values: {e}")
    
    tk.Button(frame, text="Load CSV", command=on_load_csv).pack(padx=10, pady=5)
    
    # --- Filtering Parameters ---
    param_frame = tk.Frame(frame)
    param_frame.pack(padx=10, pady=10)
    
    tk.Label(param_frame, text="X min:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    x_min_var = tk.DoubleVar(frame, value=0)
    tk.Entry(param_frame, textvariable=x_min_var, width=10).grid(row=0, column=1, padx=5, pady=5)
    
    tk.Label(param_frame, text="X max:").grid(row=0, column=2, sticky="e", padx=5, pady=5)
    x_max_var = tk.DoubleVar(frame, value=0)
    tk.Entry(param_frame, textvariable=x_max_var, width=10).grid(row=0, column=3, padx=5, pady=5)
    
    tk.Label(param_frame, text="Y min:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    y_min_var = tk.DoubleVar(frame, value=0)
    tk.Entry(param_frame, textvariable=y_min_var, width=10).grid(row=1, column=1, padx=5, pady=5)
    
    tk.Label(param_frame, text="Y max:").grid(row=1, column=2, sticky="e", padx=5, pady=5)
    y_max_var = tk.DoubleVar(frame, value=0)
    tk.Entry(param_frame, textvariable=y_max_var, width=10).grid(row=1, column=3, padx=5, pady=5)
    
    remove_outliers_var = tk.BooleanVar(frame, value=False)
    tk.Checkbutton(param_frame, text="Remove Outliers", variable=remove_outliers_var).grid(row=2, column=0, columnspan=2, pady=5)
    
    tk.Label(param_frame, text="Outlier Std:").grid(row=2, column=2, sticky="e", padx=5, pady=5)
    outlier_std_var = tk.DoubleVar(frame, value=3.0)
    tk.Entry(param_frame, textvariable=outlier_std_var, width=10).grid(row=2, column=3, padx=5, pady=5)
    
    # --- Apply Filtering Button ---
    def on_apply_filter():
        if state["df"] is None:
            messagebox.showerror("Error", "Please load a CSV file first.")
            return
        try:
            x_min = float(x_min_var.get())
            x_max = float(x_max_var.get())
            y_min = float(y_min_var.get())
            y_max = float(y_max_var.get())
            remove_outliers = remove_outliers_var.get()
            outlier_std = float(outlier_std_var.get())
            apply_filtering(state["df"], state["csv_path"], x_min, x_max, y_min, y_max, remove_outliers, outlier_std)
        except Exception as e:
            messagebox.showerror("Error", f"Error during filtering: {e}")
    
    tk.Button(frame, text="Apply Filtering", command=on_apply_filter).pack(padx=10, pady=10)
    
    return frame

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Filter & Plot Centers")
    ui = get_ui(root)
    ui.pack(fill="both", expand=True)
    root.mainloop()
