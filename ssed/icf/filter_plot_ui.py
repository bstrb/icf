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
    
    # State dictionary to store the loaded DataFrame and its file path.
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
            
            # Filter data based on the slider values.
            filtered = df[
                (df['center_x'] >= x_min) & (df['center_x'] <= x_max) &
                (df['center_y'] >= y_min) & (df['center_y'] <= y_max)
            ]
            
            # Optionally remove outliers.
            if remove_outliers:
                x_mean = filtered['center_x'].mean()
                x_std = filtered['center_x'].std()
                y_mean = filtered['center_y'].mean()
                y_std = filtered['center_y'].std()
                filtered = filtered[
                    (abs(filtered['center_x'] - x_mean) <= outlier_std * x_std) &
                    (abs(filtered['center_y'] - y_mean) <= outlier_std * y_std)
                ]
                print(f"Outliers removed using threshold: {outlier_std} standard deviations.")
            
            # Print descriptive statistics.
            print("=== Filtered Data Statistics ===")
            print(f"Number of rows: {len(filtered)}")
            for col in ['center_x', 'center_y']:
                mean_val = filtered[col].mean()
                median_val = filtered[col].median()
                std_val = filtered[col].std()
                print(f"{col} => mean: {mean_val:.3f}, median: {median_val:.3f}, std: {std_val:.3f}")
            
            # Save filtered CSV in the same folder as the loaded file.
            output_folder = os.path.dirname(csv_path)
            output_filename = os.path.join(output_folder, "filtered_centers.csv")
            filtered.to_csv(output_filename, index=False)
            print(f"\nFiltered CSV saved to: {output_filename}\n")
            
            # Scatter plot.
            plt.figure(figsize=(8, 6))
            plt.scatter(filtered['center_x'], filtered['center_y'], marker='o')
            plt.xlabel('Center X')
            plt.ylabel('Center Y')
            plt.title('Scatter Plot of Center Coordinates')
            plt.grid(True)
            plt.show()
            
            # Histogram for center_x.
            plt.figure(figsize=(8, 6))
            plt.hist(filtered['center_x'], bins=30, edgecolor='black')
            plt.xlabel('Center X')
            plt.ylabel('Frequency')
            plt.title('Histogram of Center X')
            plt.grid(True)
            plt.show()
            
            # Histogram for center_y.
            plt.figure(figsize=(8, 6))
            plt.hist(filtered['center_y'], bins=30, edgecolor='black')
            plt.xlabel('Center Y')
            plt.ylabel('Frequency')
            plt.title('Histogram of Center Y')
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
