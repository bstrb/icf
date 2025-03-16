import os
import pandas as pd
import matplotlib.pyplot as plt
from ipywidgets import (
    interact, FloatRangeSlider, Checkbox, FloatSlider, Layout,
    Button, VBox, Output, HBox, HTML
)
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output

def get_ui():
    # File chooser widget to browse for a CSV file.
    csv_file_chooser = FileChooser(os.getcwd())
    csv_file_chooser.title = "Select CSV File with Center Data"
    csv_file_chooser.filter_pattern = "*.csv"
    
    # Button to trigger CSV loading.
    load_button = Button(description="Load CSV", button_style="primary")
    load_output = Output()
    
    # Output area where the interactive filtering UI will be built.
    interactive_output = Output()
    
    # Dictionary to store the loaded DataFrame and its file path.
    state = {"df": None, "csv_path": None}
    
    def build_interactive_ui():
        """Builds and displays the interact widget using the loaded CSV."""
        df = state["df"]
        csv_path = state["csv_path"]
        if df is None:
            with interactive_output:
                clear_output()
                print("No CSV loaded.")
            return
        
        # Calculate slider default values from the CSV.
        x_min_default = df['center_x'].min()
        x_max_default = df['center_x'].max()
        y_min_default = df['center_y'].min()
        y_max_default = df['center_y'].max()
        
        def filter_and_plot(x_range, y_range, remove_outliers, outlier_std):
            if df.empty:
                print("No data loaded. Exiting.")
                return
            
            x_min, x_max = x_range
            y_min, y_max = y_range
            
            # Create a copy of the DataFrame to modify.
            df_filtered = df.copy()
            # Ensure center_x and center_y can store empty strings.
            df_filtered['center_x'] = df_filtered['center_x'].astype(object)
            df_filtered['center_y'] = df_filtered['center_y'].astype(object)
            
            # Create mask for rows with center values within the selected range.
            mask_range = (
                (df_filtered['center_x'].astype(float) >= x_min) & 
                (df_filtered['center_x'].astype(float) <= x_max) &
                (df_filtered['center_y'].astype(float) >= y_min) & 
                (df_filtered['center_y'].astype(float) <= y_max)
            )
            
            # If outlier removal is enabled, compute additional mask on the in-range rows.
            if remove_outliers:
                valid_in_range = df_filtered[mask_range].copy()
                # Convert to float for calculations.
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
            
            # For rows that do not satisfy the filter, replace center_x and center_y with empty strings.
            df_filtered.loc[~valid_mask, ['center_x', 'center_y']] = ""
            
            # Print statistics only for the valid rows.
            valid_rows = df_filtered[valid_mask]
            print("=== Valid Data Statistics ===")
            print(f"Number of valid rows: {len(valid_rows)} out of {len(df_filtered)}")
            for col in ['center_x', 'center_y']:
                # Convert to float for calculation if possible.
                try:
                    valid_floats = valid_rows[col].astype(float)
                    mean_val = valid_floats.mean()
                    median_val = valid_floats.median()
                    std_val = valid_floats.std()
                    print(f"{col} => mean: {mean_val:.3f}, median: {median_val:.3f}, std: {std_val:.3f}")
                except Exception:
                    print(f"{col} has non-numeric values.")
            
            # Save the modified CSV in the same folder as the input.
            output_folder = os.path.dirname(csv_path)
            base = os.path.basename(csv_path)
            basename, ext = os.path.splitext(base)
            output_filename = os.path.join(output_folder, f"{basename}_filtered.csv")
            df_filtered.to_csv(output_filename, index=False)
            print(f"\nFiltered CSV saved to: {output_filename}\n")
            
            # Plot scatter using only the valid rows (converted back to float for plotting).
            valid_rows_numeric = valid_rows.copy()
            valid_rows_numeric['center_x'] = valid_rows_numeric['center_x'].apply(lambda v: float(v) if v != "" else None)
            valid_rows_numeric['center_y'] = valid_rows_numeric['center_y'].apply(lambda v: float(v) if v != "" else None)
            valid_rows_numeric = valid_rows_numeric.dropna(subset=['center_x', 'center_y'])
            plt.figure(figsize=(8, 6))
            plt.scatter(valid_rows_numeric['center_x'], valid_rows_numeric['center_y'], marker='o')
            plt.xlabel('Center X')
            plt.ylabel('Center Y')
            plt.title('Scatter Plot of Valid Center Coordinates')
            plt.grid(True)
            plt.show()
            
            # Plot histogram for center_x.
            plt.figure(figsize=(8, 6))
            plt.hist(valid_rows_numeric['center_x'], bins=30, edgecolor='black')
            plt.xlabel('Center X')
            plt.ylabel('Frequency')
            plt.title('Histogram of Valid Center X')
            plt.grid(True)
            plt.show()
            
            # Plot histogram for center_y.
            plt.figure(figsize=(8, 6))
            plt.hist(valid_rows_numeric['center_y'], bins=30, edgecolor='black')
            plt.xlabel('Center Y')
            plt.ylabel('Frequency')
            plt.title('Histogram of Valid Center Y')
            plt.grid(True)
            plt.show()
        
        with interactive_output:
            clear_output()
            interact(
                filter_and_plot,
                x_range=FloatRangeSlider(
                    value=(x_min_default, x_max_default),
                    min=x_min_default, max=x_max_default, step=0.1,
                    description='X range',
                    layout=Layout(width='800px')
                ),
                y_range=FloatRangeSlider(
                    value=(y_min_default, y_max_default),
                    min=y_min_default, max=y_max_default, step=0.1,
                    description='Y range',
                    layout=Layout(width='800px')
                ),
                remove_outliers=Checkbox(
                    value=False,
                    description='Remove Outliers'
                ),
                outlier_std=FloatSlider(
                    value=3.0,
                    min=1.0, max=5.0, step=0.1,
                    description='Outlier Std'
                )
            )
    
    def on_load_clicked(b):
        with load_output:
            clear_output()
            selected = csv_file_chooser.selected
            if not selected:
                print("Please browse and select a CSV file.")
                return
            try:
                df_loaded = pd.read_csv(selected)
                state["df"] = df_loaded
                state["csv_path"] = selected
                print(f"Loaded {len(df_loaded)} rows from {selected}")
            except Exception as e:
                print(f"Error loading CSV: {e}")
        build_interactive_ui()
    
    load_button.on_click(on_load_clicked)
    
    ui = VBox([
        HTML("<h2>Filter & Plot Centers</h2>"),
        csv_file_chooser,
        load_button,
        load_output,
        interactive_output
    ])
    
    return ui

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
