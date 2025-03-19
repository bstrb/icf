import ipywidgets as widgets
from IPython.display import display, clear_output
from ipyfilechooser import FileChooser
import matplotlib.pyplot as plt
import os
import time

# Import your custom modules (assumed to be available in your PYTHONPATH)
from .csv_to_stream import write_stream_from_filtered_csv
from .interactive_iqm import (
    read_metric_csv,
    select_best_results_by_event,
    get_metric_ranges,
    create_combined_metric,
    filter_rows,
    write_filtered_csv
)

def get_ui():
    
    # CSV File Selection Section
    csv_file_chooser = FileChooser("")
    csv_file_chooser.title = "Select CSV file with normalized metrics"
    csv_file_chooser.filter_pattern = "*.csv"
    
    load_csv_button = widgets.Button(
        description="Load CSV",
        button_style="primary"
    )
    
    load_csv_output = widgets.Output()
    ui_container = widgets.VBox()
    
    def load_csv_callback(b):
        with load_csv_output:
            clear_output()
            if not csv_file_chooser.selected:
                print("Please select a CSV file.")
                return
            CSV_PATH = csv_file_chooser.selected
            print("Loading CSV file:", CSV_PATH)
            try:
                grouped_data = read_metric_csv(CSV_PATH, group_by_event=True)
                all_rows = [row for rows in grouped_data.values() for row in rows]
                print(f"Loaded {len(all_rows)} rows from CSV.")
                
                # Set path for filtered CSV (in same folder as CSV)
                FILTERED_CSV_PATH = os.path.join(os.path.dirname(CSV_PATH), 'filtered_metrics.csv')
                
                # Define metrics to be analyzed.
                metrics_in_order = [
                    'weighted_rmsd',
                    'fraction_outliers',
                    'length_deviation',
                    'angle_deviation',
                    'peak_ratio',
                    'percentage_unindexed'
                ]
                
                ########################################################
                # SECTION 1: Separate Metrics Filtering
                ########################################################
                ranges_dict = get_metric_ranges(all_rows, metrics=metrics_in_order)
                metric_sliders = {}
                
                def create_slider(metric_name, min_val, max_val):
                    default_val = max_val  # default includes all values
                    step = (max_val - min_val) / 100.0 if max_val != min_val else 0.01
                    slider = widgets.FloatSlider(
                        value=default_val,
                        min=min_val,
                        max=max_val,
                        step=step,
                        description=f"{metric_name} ≤",
                        layout=widgets.Layout(width='95%')
                    )
                    return slider
                
                for metric in metrics_in_order:
                    mn, mx = ranges_dict[metric]
                    metric_sliders[metric] = create_slider(metric, mn, mx)
                
                slider_box = widgets.GridBox(
                    children=[metric_sliders[m] for m in metrics_in_order],
                    layout=widgets.Layout(
                        grid_template_columns="repeat(2, 300px)",
                        grid_gap="10px 20px"
                    )
                )
                
                filter_separate_button = widgets.Button(
                    description="Apply Separate Metrics Thresholds",
                    button_style='info'
                )
                
                separate_output = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})
                
                def on_filter_separate_clicked(_):
                    with separate_output:
                        clear_output()
                        print("\n" + "="*50)
                        print("SEPARATE METRICS FILTERING")
                        print("="*50)
                        
                        thresholds = {m: metric_sliders[m].value for m in metrics_in_order}
                        filtered_separate = filter_rows(all_rows, thresholds)
                        
                        print(f"Filtering: {len(all_rows)} total rows -> {len(filtered_separate)} pass thresholds.")
                        if not filtered_separate:
                            print("No rows passed the thresholds.")
                            return
                        
                        # Plot histograms for each metric.
                        fig, axes = plt.subplots(3, 2, figsize=(12, 12))
                        axes = axes.flatten()
                        for i, metric in enumerate(metrics_in_order):
                            values = [r[metric] for r in filtered_separate if metric in r]
                            axes[i].hist(values, bins=20)
                            axes[i].set_title(f"Histogram of {metric}")
                            axes[i].set_xlabel(metric)
                            axes[i].set_ylabel("Count")
                        plt.tight_layout()
                        plt.show()
                
                filter_separate_button.on_click(on_filter_separate_clicked)
                
                separate_control_panel = widgets.VBox([
                    widgets.HTML("<h3>Separate Metrics Filtering</h3>"),
                    slider_box,
                    filter_separate_button,
                    separate_output
                ])
                
                ########################################################
                # SECTION 2: Combined Metric Creation & Filtering (Best Rows)
                ########################################################
                weight_text_fields = {}
                for metric in metrics_in_order:
                    weight_text_fields[metric] = widgets.FloatText(
                        value=0.0,
                        description=f"{metric}",
                        style={"description_width": "60px"},
                        layout=widgets.Layout(width='150px')
                    )
                weights_box = widgets.GridBox(
                    children=[weight_text_fields[m] for m in metrics_in_order],
                    layout=widgets.Layout(
                        grid_template_columns="repeat(2, 200px)",
                        grid_gap="10px 20px"
                    )
                )
                
                combined_metric_slider = widgets.FloatSlider(
                    value=0.0,
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    description="threshold ≤",
                    layout=widgets.Layout(width='300px')
                )
                
                create_combined_button = widgets.Button(
                    description="Create Combined Metric",
                    button_style='primary'
                )
                
                combined_output = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})
                
                def create_or_update_combined_metric(_):
                    with combined_output:
                        clear_output()
                        print("\n" + "="*50)
                        print("COMBINED METRIC CREATION")
                        print("="*50)
                        
                        selected_metrics = []
                        weights_list = []
                        for m in metrics_in_order:
                            w = weight_text_fields[m].value
                            selected_metrics.append(m)
                            weights_list.append(w)
                        
                        create_combined_metric(
                            rows=all_rows,
                            metrics_to_combine=selected_metrics,
                            weights=weights_list,
                            new_metric_name="combined_metric"
                        )
                        
                        combined_vals = [r["combined_metric"] for r in all_rows if "combined_metric" in r]
                        if combined_vals:
                            cmin, cmax = min(combined_vals), max(combined_vals)
                            current_val = combined_metric_slider.value
                            if current_val < cmin or current_val > cmax:
                                current_val = cmax
                            
                            with combined_metric_slider.hold_trait_notifications():
                                combined_metric_slider.min = cmin
                                combined_metric_slider.max = cmax
                                combined_metric_slider.value = current_val
                            
                            print("Combined metric created successfully!")
                            print(f"  * Min value: {cmin:.3f}")
                            print(f"  * Max value: {cmax:.3f}")
                            print("Adjust the slider below and click 'Apply Combined Metric Threshold (Best Rows)' to filter.")
                        else:
                            print("Failed to create combined metric. Check your weights.")
                
                create_combined_button.on_click(create_or_update_combined_metric)
                
                filter_combined_button = widgets.Button(
                    description="Apply Combined Metric Threshold (Best Rows)",
                    button_style='info'
                )
                
                def on_filter_combined_clicked(_):
                    with combined_output:
                        clear_output()
                        print("\n" + "="*50)
                        print("COMBINED METRIC FILTERING")
                        print("="*50)
                        
                        threshold = combined_metric_slider.value
                        filtered_combined = [r for r in all_rows if "combined_metric" in r and r["combined_metric"] <= threshold]
                        
                        print(f"Filtering rows by combined_metric ≤ {threshold:.3f}")
                        if not filtered_combined:
                            print("No rows passed the combined metric threshold.")
                            return
                        
                        grouped_filtered = {}
                        for r in filtered_combined:
                            event = r.get("event_number")
                            if event not in grouped_filtered:
                                grouped_filtered[event] = []
                            grouped_filtered[event].append(r)
                        
                        best_filtered = select_best_results_by_event(grouped_filtered, sort_metric="combined_metric")
                        
                        print(f"{len(filtered_combined)} rows passed threshold, {len(best_filtered)} best rows selected per event.")
                        write_filtered_csv(best_filtered, FILTERED_CSV_PATH)
                        print(f"Wrote {len(best_filtered)} best-filtered rows to {FILTERED_CSV_PATH}")
                        
                        plt.figure(figsize=(8, 6))
                        values = [r["combined_metric"] for r in best_filtered]
                        plt.hist(values, bins=20)
                        plt.title("Histogram of Best Rows (combined_metric)")
                        plt.xlabel("combined_metric")
                        plt.ylabel("Count")
                        plt.tight_layout()
                        plt.show()
                
                filter_combined_button.on_click(on_filter_combined_clicked)
                
                convert_button = widgets.Button(
                    description="Convert to Stream",
                    button_style='success'
                )
                
                def on_convert_clicked(_):
                    with combined_output:
                        print("\n" + "="*50)
                        print("CONVERT TO STREAM")
                        print("="*50)
                        
                        pb = widgets.IntProgress(
                            value=0,
                            min=0,
                            max=5,
                            step=1,
                            description='Converting...',
                            bar_style=''
                        )
                        display(pb)
                        
                        # Get the directory of the CSV_PATH and construct the subfolder path.
                        output_dir = os.path.join(os.path.dirname(CSV_PATH), 'filtered_metrics')
                        os.makedirs(output_dir, exist_ok=True)

                        # Now create the stream file path inside the subfolder.
                        OUTPUT_STREAM_PATH = os.path.join(output_dir, 'filtered_metrics.stream')
                        
                        print("\nStarting conversion...\n")
                        time.sleep(0.2)
                        
                        pb.value = 1
                        print("  * Step 1/5: Reading filtered CSV file...")
                        filtered_grouped_data = read_metric_csv(FILTERED_CSV_PATH, group_by_event=True)
                        time.sleep(0.2)
                        
                        pb.value = 2
                        print("  * Step 2/5: Checking for combined metric, if present, picking best rows...")
                        first_event = next(iter(filtered_grouped_data.values()))
                        time.sleep(0.2)
                        
                        pb.value = 3
                        if "combined_metric" in first_event[0]:
                            best_filtered = select_best_results_by_event(filtered_grouped_data, sort_metric="combined_metric")
                            write_filtered_csv(best_filtered, FILTERED_CSV_PATH)
                            print("      - Best rows selected & CSV overwritten.")
                        else:
                            print("      - No combined_metric found, skipping best-row selection.")
                        time.sleep(0.2)
                        
                        pb.value = 4
                        print("  * Step 4/5: Writing the .stream file...")
                        write_stream_from_filtered_csv(
                            filtered_csv_path=FILTERED_CSV_PATH,
                            output_stream_path=OUTPUT_STREAM_PATH,
                            event_col="event_number",
                            streamfile_col="stream_file"
                        )
                        time.sleep(0.2)
                        
                        pb.value = 5
                        print("  * Step 5/5: Conversion complete!\n")
                        print(f"CSV has been successfully converted to:\n  {OUTPUT_STREAM_PATH}")
                
                convert_button.on_click(on_convert_clicked)
                
                combined_control_panel = widgets.VBox([
                    widgets.HTML("<h3>Combined Metric Creation & Filtering</h3>"),
                    widgets.HTML("Enter weights for each metric:"),
                    weights_box,
                    widgets.HTML("<hr style='margin:10px 0;'>"),
                    create_combined_button,
                    combined_metric_slider,
                    widgets.HTML("<hr style='margin:10px 0;'>"),
                    widgets.HBox([filter_combined_button, convert_button]),
                    combined_output
                ])
                
                # Assemble the final layout for the analysis tool.
                final_layout = widgets.VBox([
                    widgets.HTML("<h2>Interactive Metric Analysis Tool</h2>"),
                    separate_control_panel,
                    combined_control_panel
                ])
                ui_container.children = [final_layout]
                
            except Exception as e:
                print("Error loading CSV:", e)
    
    load_csv_button.on_click(load_csv_callback)
    
    # Create the final UI layout.
    main_ui = widgets.VBox([
        widgets.HTML("<h3>Select CSV file with normalized metrics:</h3>"),
        csv_file_chooser,
        load_csv_button,
        load_csv_output,
        ui_container
    ])
    return main_ui

# Allow running the UI directly for testing.
if __name__ == "__main__":
    ui = get_ui()
    display(ui)
