import ipywidgets as widgets
from IPython.display import display, clear_output
from ipyfilechooser import FileChooser
from .gandalf_radial_iterator import gandalf_iterator  # Ensure this module is importable

# Define default peakfinder options.
default_peakfinder_options = {
    'cxi': "--peaks=cxi",
    'peakfinder9': """--peaks=peakfinder9
--min-snr=1
--min-snr-peak-pix=6
--min-sig=9 
--min-peak-over-neighbour=5
--local-bg-radius=5""",
    'peakfinder8': """--peaks=peakfinder8
--threshold=45
--min-snr=3
--min-pix-count=3
--max-pix-count=500
--local-bg-radius=9
--min-res=30
--max-res=500"""
}

def create_indexing_section():
    # Create file choosers for the geometry and cell files
    geom_file_chooser = FileChooser("")
    geom_file_chooser.title = 'Select Geometry File (.geom)'
    geom_file_chooser.filter_pattern = "*.geom"

    cell_file_chooser = FileChooser("")
    cell_file_chooser.title = 'Select Cell File (.cell)'
    cell_file_chooser.filter_pattern = "*.cell"

    # Create a folder chooser for the input folder
    input_folder_chooser = FileChooser("")
    input_folder_chooser.title = 'Select Input Folder'
    input_folder_chooser.show_only_dirs = True  # Allows directory browsing

    # Other basic parameters as text or numeric widgets
    output_base_text = widgets.Text(
        value="UOX", 
        description="Output Base:", 
        layout=widgets.Layout(width='400px')
    )
    num_threads_int = widgets.IntText(
        value=24, 
        description="Threads:"
    )
    max_radius_float = widgets.FloatText(
        value=1.0, 
        description="Max Radius:"
    )
    step_float = widgets.FloatText(
        value=0.5, 
        description="Step:"
    )
    
    # ----- Peakfinder Section -----
    # Dropdown to select the peakfinder method
    peakfinder_dropdown = widgets.Dropdown(
        options=[('CXI', 'cxi'), ('Peakfinder9', 'peakfinder9'), ('Peakfinder8', 'peakfinder8')],
        value='cxi',
        description='Peakfinder:'
    )
    
    # Text area for peakfinder parameters, prefilled with defaults
    peakfinder_params_text = widgets.Textarea(
        value=default_peakfinder_options[peakfinder_dropdown.value],
        description='Peakfinder Params:',
        layout=widgets.Layout(width='600px', height='100px')
    )
    
    # Update text area when dropdown selection changes.
    def on_peakfinder_change(change):
        if change['name'] == 'value':
            new_method = change['new']
            peakfinder_params_text.value = default_peakfinder_options[new_method]
    peakfinder_dropdown.observe(on_peakfinder_change, names='value')
    
    # ----- Advanced Indexing Parameters -----
    # Create dedicated entry fields for several indexing parameters.
    min_peaks_int = widgets.IntText(value=15, description="Min Peaks:")
    tolerance_text = widgets.Text(value="10,10,10,5", description="Cell Tolerance:")
    xgandalf_sampling_pitch = widgets.IntText(value=5, description="Sampling Pitch:")
    xgandalf_grad_desc_iterations = widgets.IntText(value=1, description="Grad Desc Iterations:")
    xgandalf_tolerance = widgets.FloatText(value=0.02, description="XGandalf Tolerance:")
    int_radius_text = widgets.Text(value="2,5,10", description="Integration Radius:")
    
    advanced_params = widgets.VBox([
        widgets.HTML("<b>Advanced Indexing Parameters</b>"),
        min_peaks_int,
        tolerance_text,
        xgandalf_sampling_pitch,
        xgandalf_grad_desc_iterations,
        xgandalf_tolerance,
        int_radius_text
    ])
    
    # ----- Other Flags -----
    # This text area retains any additional flags you might want.
    other_flags_text = widgets.Textarea(
        value="""--no-revalidate
--no-half-pixel-shift
--no-refine
--no-non-hits-in-stream""",
        description="Other Flags:",
        layout=widgets.Layout(width='600px', height='80px')
    )
    
    # ----- Fixed Indexing Flags -----
    # These flags remain hardcoded.
    indexing_flags = [
        "--indexing=xgandalf",
        "--integration=rings",
    ]
    
    # Create a button to trigger the indexing workflow
    run_button = widgets.Button(
        description="Run Indexing",
        button_style="primary"
    )
    
    # Output area for feedback
    output_area = widgets.Output()
    
    # Callback for the button click.
    def on_run_clicked(b):
        with output_area:
            clear_output()
            # Retrieve file paths and folder
            geom_file = geom_file_chooser.selected
            cell_file = cell_file_chooser.selected
            input_folder = input_folder_chooser.selected

            print("Running gandalf_iterator with the following parameters:")
            print("Geom File:", geom_file)
            print("Cell File:", cell_file)
            print("Input Folder:", input_folder)
            print("Output Base:", output_base_text.value)
            print("Threads:", num_threads_int.value)
            print("Max Radius:", max_radius_float.value)
            print("Step:", step_float.value)
            
            # Build flags from the various sections.
            # Global/other flags (from the text area).
            other_flags = [line.strip() for line in other_flags_text.value.splitlines() if line.strip()]
            
            # Peakfinder flags (editable in its own section).
            peakfinder_flags = [line.strip() for line in peakfinder_params_text.value.splitlines() if line.strip()]
            
            # Advanced parameters, assembled from the new fields.
            min_peaks_flag = f"--min-peaks={min_peaks_int.value}"
            tolerance_flag = f"--tolerance={tolerance_text.value}"
            sampling_pitch_flag = f"--xgandalf-sampling-pitch={xgandalf_sampling_pitch.value}"
            grad_desc_iterations_flag = f"--xgandalf-grad-desc-iterations={xgandalf_grad_desc_iterations.value}"
            xgandalf_tolerance_flag = f"--xgandalf-tolerance={xgandalf_tolerance.value}"
            int_radius_flag = f"--int-radius={int_radius_text.value}"
            advanced_flags = [
                min_peaks_flag,
                tolerance_flag,
                sampling_pitch_flag,
                grad_desc_iterations_flag,
                xgandalf_tolerance_flag,
                int_radius_flag
            ]
            
            # Combine all flags in order:
            # 1. Advanced parameter flags,
            # 2. Other (global) flags,
            # 3. Peakfinder flags,
            # 4. Fixed indexing flags.
            flags_list = advanced_flags + other_flags + peakfinder_flags + indexing_flags
            
            print("\nSelected Peakfinder Option:", peakfinder_dropdown.value)
            print("\nPeakfinder Parameters:")
            for flag in peakfinder_flags:
                print(" ", flag)
            print("\nAdvanced Indexing Parameters:")
            for flag in advanced_flags:
                print(" ", flag)
            print("\nOther Flags:")
            for flag in other_flags:
                print(" ", flag)
            print("\nFixed Indexing Flags:")
            for flag in indexing_flags:
                print(" ", flag)
            print("\nCombined Flags:", flags_list)
            
            try:
                # Call the indexing workflow with the assembled flags.
                gandalf_iterator(
                    geom_file,
                    cell_file,
                    input_folder,
                    output_base_text.value,
                    num_threads_int.value,
                    max_radius=max_radius_float.value,
                    step=step_float.value,
                    extra_flags=flags_list
                )
                print("Indexing completed successfully.")
            except Exception as e:
                print("Error during indexing:", e)
    
    run_button.on_click(on_run_clicked)
    
    # Assemble the full UI with the updated ordering.
    ui = widgets.VBox([
        widgets.HTML("<h3>Indexing on a Circular Grid</h3>"),
        geom_file_chooser,
        cell_file_chooser,
        input_folder_chooser,
        output_base_text,
        num_threads_int,
        max_radius_float,
        step_float,
        widgets.HTML("<h4>Peakfinder Options</h4>"),
        peakfinder_dropdown,
        peakfinder_params_text,
        widgets.HTML("<h4>Advanced Indexing Parameters</h4>"),
        advanced_params,
        widgets.HTML("<h4>Other Extra Flags</h4>"),
        other_flags_text,
        run_button,
        output_area
    ])
    
    return ui

def get_ui():
    """
    Returns the full indexing UI as a widget.
    """
    return create_indexing_section()

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
