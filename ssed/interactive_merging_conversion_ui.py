import ipywidgets as widgets
from IPython.display import display, clear_output
import os
import time  # Only if you want to simulate progress bar delays

# Try to import file chooser widget
try:
    from ipyfilechooser import FileChooser
except ImportError:
    print("ipyfilechooser not found. Install via: pip install ipyfilechooser")

def get_ui():
    # Local variable to store merged output directory.
    global_output_dir = None

    # Try to import your custom modules.
    import_failed = False
    import_error_msg = ""
    modules_import_out = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})
    with modules_import_out:
        try:
            from merge import merge
            from convert_hkl_crystfel_to_shelx import convert_hkl_crystfel_to_shelx 
            from convert_hkl_to_mtz import convert_hkl_to_mtz
            print("Successfully imported merge, convert_hkl_crystfel_to_shelx, and convert_hkl_to_mtz modules.")
        except Exception as e:
            import_failed = True
            import_error_msg = str(e)
            print("Error importing modules:", e)

    # A single output widget to capture feedback from all operations.
    feedback_out = widgets.Output(
        layout={
            'border': '1px solid black',
            'height': '300px',
            'overflow_y': 'auto',
            'padding': '5px'
        }
    )

    # If module imports failed, return a UI that displays the error.
    if import_failed:
        error_ui = widgets.VBox([
            modules_import_out,
            widgets.HTML("<b>Could not load your modules:</b>"),
            widgets.HTML(import_error_msg)
        ])
        return error_ui

    #################################
    # 1) Merging Section
    #################################
    # File chooser for selecting the .stream file.
    stream_file_chooser = FileChooser(os.getcwd())
    stream_file_chooser.title = 'Select .stream File'
    stream_file_chooser.filter_pattern = '*.stream'  # Only show .stream files

    pointgroup_widget = widgets.Text(
        value="",
        description="Pointgroup:",
        style={"description_width": "150px"}
    )
    num_threads_widget = widgets.IntText(
        value=24,
        description="Num Threads:",
        style={"description_width": "150px"}
    )
    iterations_widget = widgets.IntText(
        value=5,
        description="Iterations:",
        style={"description_width": "150px"}
    )

    merge_button = widgets.Button(
        description="Merge",
        button_style='warning'
    )

    def on_merge_clicked(b):
        nonlocal global_output_dir
        with feedback_out:
            print("\n" + "="*50)
            print("MERGING SECTION")
            print("="*50)

            stream_file = stream_file_chooser.selected
            pointgroup = pointgroup_widget.value
            num_threads = num_threads_widget.value
            iterations = iterations_widget.value

            if not stream_file:
                print("Please select a .stream file first.")
                return

            # Progress bar for merging.
            pb_merge = widgets.IntProgress(
                value=0,
                min=0,
                max=3,
                step=1,
                description='Merging...',
                bar_style=''
            )
            display(pb_merge)

            print("Merging in progress...")
            pb_merge.value = 1
            time.sleep(0.2)  # Delay to simulate progress

            output_dir = merge(
                stream_file,
                pointgroup=pointgroup,
                num_threads=num_threads,
                iterations=iterations,
            )
            pb_merge.value = 2
            time.sleep(0.2)

            if output_dir is not None:
                print("Merging done. Results are in:", output_dir)
                global_output_dir = output_dir
            else:
                print("Merging failed. Please check the parameters and try again.")

            pb_merge.value = 3
            print("Done merging.")

    merge_button.on_click(on_merge_clicked)

    merge_controls = widgets.VBox([
        widgets.HTML("<h3>Merging Parameters</h3>"),
        stream_file_chooser,
        pointgroup_widget,
        num_threads_widget,
        iterations_widget,
        merge_button
    ])

    #################################
    # 2) SHELX Conversion Section
    #################################
    shelx_button = widgets.Button(
        description="Convert to SHELX",
        button_style='primary'
    )

    def on_shelx_clicked(b):
        with feedback_out:
            print("\n" + "="*50)
            print("SHELX CONVERSION")
            print("="*50)

            if global_output_dir is None:
                print("No merged output available. Please run the merge step first.")
                return

            print("Converting to SHELX...")
            convert_hkl_crystfel_to_shelx(global_output_dir)
            print("Conversion to SHELX completed.")

    shelx_button.on_click(on_shelx_clicked)

    shelx_controls = widgets.VBox([
        widgets.HTML("<h3>SHELX Conversion</h3>"),
        shelx_button
    ])

    #################################
    # 3) MTZ Conversion Section
    #################################
    cell_file_chooser = FileChooser(os.getcwd())
    cell_file_chooser.title = 'Select Cell File'

    mtz_button = widgets.Button(
        description="Convert to MTZ",
        button_style='success'
    )

    def on_mtz_clicked(b):
        with feedback_out:
            print("\n" + "="*50)
            print("MTZ CONVERSION")
            print("="*50)

            if global_output_dir is None:
                print("No merged output available. Please run the merge step first.")
                return

            cellfile_path = cell_file_chooser.selected
            if not cellfile_path:
                print("Please select a cell file first.")
                return

            print("Converting to MTZ...")
            convert_hkl_to_mtz(global_output_dir, cellfile_path=cellfile_path)
            print("Conversion to MTZ completed.")

    mtz_button.on_click(on_mtz_clicked)

    mtz_controls = widgets.VBox([
        widgets.HTML("<h3>MTZ Conversion</h3>"),
        cell_file_chooser,
        mtz_button
    ])

    #################################
    # 4) Display All Controls
    #################################
    controls_layout = widgets.VBox([
        modules_import_out,
        widgets.HTML("<h2>Interactive Merging & Conversion Tool</h2>"),
        merge_controls,
        shelx_controls,
        mtz_controls,
        widgets.HTML("<h3>Feedback & Logs</h3>"),
        feedback_out
    ])

    return controls_layout

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
