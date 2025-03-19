import ipywidgets as widgets
from IPython.display import display, clear_output
from ipyfilechooser import FileChooser
from .process_indexing_metrics import process_indexing_metrics

def create_metrics_section():
    # Folder chooser for the stream files folder.
    stream_folder_chooser = FileChooser("")
    stream_folder_chooser.title = "Select Stream File Folder"
    stream_folder_chooser.show_only_dirs = True  # Only directories

    # Widgets for tolerance parameters.
    wrmsd_tolerance_widget = widgets.FloatText(
        value=2.0, 
        description="WRMSD Tolerance:"
    )
    indexing_tolerance_widget = widgets.FloatText(
        value=4.0,
        description="Indexing Tolerance:"
    )

    # Explanation text using HTML.
    explanation_html = widgets.HTML(
        """
        <h4>Indexing Metrics Processing</h4>
        <p>
        <b>WRMSD Tolerance:</b> The number of standard deviations away from the mean weighted RMSD for a chunk to be considered an outlier. Default factor is 2.0.<br>
        <b>Indexing Tolerance:</b> The maximum deviation in pixels between observed and predicted peak positions for a peak to be considered indexed. Default is 4.0 pixel.
        </p>
        <p>The following metrics will be evaluated for analysis: 'weighted_rmsd', 'fraction_outliers', 'length_deviation', 'angle_deviation', 'peak_ratio', 'percentage_indexed'.</p>
        """
    )

    # Button to trigger the processing.
    process_button = widgets.Button(
        description="Process Metrics",
        button_style="primary"
    )

    # Output area for feedback.
    output_area = widgets.Output()

    def on_process_clicked(b):
        with output_area:
            clear_output()
            folder = stream_folder_chooser.selected
            if not folder:
                print("Please select a stream file folder.")
                return
            wrmsd = wrmsd_tolerance_widget.value
            indexing_tol = indexing_tolerance_widget.value
            print("Processing metrics for folder:", folder)
            print("WRMSD Tolerance:", wrmsd)
            print("Indexing Tolerance:", indexing_tol)
            try:
                process_indexing_metrics(folder, wrmsd_tolerance=wrmsd, indexing_tolerance=indexing_tol)
                print("Metrics processed successfully.")
            except Exception as e:
                print("Error processing metrics:", e)

    process_button.on_click(on_process_clicked)

    # Assemble the full UI.
    ui = widgets.VBox([
        explanation_html,
        stream_folder_chooser,
        wrmsd_tolerance_widget,
        indexing_tolerance_widget,
        process_button,
        output_area
    ])

    return ui

def get_ui():
    """
    Returns the full metrics processing UI as a widget.
    """
    return create_metrics_section()

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
