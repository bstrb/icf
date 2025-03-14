import ipywidgets as widgets
from IPython.display import display, clear_output
from ipyfilechooser import FileChooser

# Import visualization functions
from indexing_3d_histogram import plot3d_indexing_rate
from indexing_center import indexing_heatmap
 
def create_visualization_section():
    # Create a folder chooser for the output folder.
    output_folder_chooser = FileChooser("")
    output_folder_chooser.title = "Select Output Folder"
    output_folder_chooser.show_only_dirs = True  # Only directories
    
    # Create a button to trigger the visualization.
    vis_button = widgets.Button(
        description="Generate Visualizations",
        button_style="primary"
    )
    
    # Output area for feedback.
    vis_output = widgets.Output()
    
    def on_vis_clicked(b):
        with vis_output:
            clear_output()
            output_folder = output_folder_chooser.selected
            if not output_folder:
                print("Please select an output folder.")
                return
            print("Generating visualizations for output folder:", output_folder)
            try:
                # Call the visualization functions.
                plot3d_indexing_rate(output_folder)
                indexing_heatmap(output_folder)
                print("Visualization completed successfully.")
            except Exception as e:
                print("Error during visualization:", e)
    
    vis_button.on_click(on_vis_clicked)
    
    # Assemble the full UI.
    ui = widgets.VBox([
        widgets.HTML("<h3>Indexing Data Visualization</h3>"),
        output_folder_chooser,
        vis_button,
        vis_output
    ])
    
    return ui

def get_ui():
    """
    Returns the full visualization UI as a widget.
    """
    return create_visualization_section()

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
