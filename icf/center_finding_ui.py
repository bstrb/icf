import os
import h5py
import numpy as np
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output

# Import your updated processing function.
from image_processing import process_images_apply_async

def create_center_finding_section():
    """
    Creates a UI for selecting:
      - An H5 image file,
      - A mask file,
      - Center-finding parameters,
    and then processes the images with a progress bar that updates per computed center.
    """
    # Explanation text.
    explanation_html = widgets.HTML(
        """
        <h4>Center Finding for Diffraction Images</h4>
        <p>
        Select your H5 image file and a mask file, then set parameters to find the diffraction center.<br>
        A CSV with the found centers will be created in the same folder as the selected image file.<br>
        The progress bar will update for each computed center.
        </p>
        """
    )

    # File choosers.
    image_file_chooser = FileChooser(os.getcwd())
    image_file_chooser.title = "Select H5 Image File"
    image_file_chooser.filter_pattern = "*.h5"

    mask_file_chooser = FileChooser(os.getcwd())
    mask_file_chooser.title = "Select Mask H5 File"
    mask_file_chooser.filter_pattern = "*.h5"

    # Checkbox for using the mask.
    use_mask_checkbox = widgets.Checkbox(value=True, description="Use Mask")

    # Parameter widgets.
    xatol_widget = widgets.FloatText(value=0.01, description="xatol:")
    frame_interval_widget = widgets.IntText(value=10, description="Frame Interval:")
    verbose_checkbox = widgets.Checkbox(value=False, description="Verbose")

    xmin_widget = widgets.IntText(value=400, description="xmin:")
    xmax_widget = widgets.IntText(value=600, description="xmax:")
    ymin_widget = widgets.IntText(value=400, description="ymin:")
    ymax_widget = widgets.IntText(value=600, description="ymax:")

    # Processing button.
    process_button = widgets.Button(
        description="Process Images",
        button_style="primary"
    )

    # Output area.
    output_area = widgets.Output()

    def on_process_clicked(_):
        with output_area:
            clear_output()
            # Get file selections.
            image_file = image_file_chooser.selected
            if not image_file:
                print("Please select an H5 image file.")
                return

            mask_file = mask_file_chooser.selected
            if not mask_file:
                print("Please select a mask H5 file.")
                return

            # Load or create mask.
            try:
                with h5py.File(mask_file, 'r') as f_mask:
                    if use_mask_checkbox.value:
                        mask = f_mask['/mask'][:].astype(bool)
                    else:
                        sample = f_mask['/mask'][0]
                        mask = np.ones_like(sample, dtype=bool)
            except Exception as e:
                print("Error loading mask file:", e)
                return

            # Get numeric parameters.
            xatol_val = xatol_widget.value
            frame_interval_val = frame_interval_widget.value
            verbose_val = verbose_checkbox.value
            xmin_val = xmin_widget.value
            xmax_val = xmax_widget.value
            ymin_val = ymin_widget.value
            ymax_val = ymax_widget.value

            print(f"Processing images from file:\n  {image_file}\n")
            print(f"Parameters:\n  xatol={xatol_val}, frame_interval={frame_interval_val}, verbose={verbose_val}")
            print(f"ROI: xmin={xmin_val}, xmax={xmax_val}, ymin={ymin_val}, ymax={ymax_val}\n")

            # Run the processing using apply_async.
            process_images_apply_async(
                image_file=image_file,
                mask=mask,
                frame_interval=frame_interval_val,
                xatol=xatol_val,
                fatol=10,
                n_wedges=4,
                n_rad_bins=100,
                xmin=xmin_val,
                xmax=xmax_val,
                ymin=ymin_val,
                ymax=ymax_val,
                verbose=verbose_val
            )
            print("Processing completed.")

    process_button.on_click(on_process_clicked)

    # Assemble the UI.
    ui = widgets.VBox([
        explanation_html,
        image_file_chooser,
        mask_file_chooser,
        use_mask_checkbox,
        widgets.HBox([xatol_widget, frame_interval_widget, verbose_checkbox]),
        widgets.HBox([xmin_widget, xmax_widget, ymin_widget, ymax_widget]),
        process_button,
        output_area
    ])
    return ui

def get_ui():
    """
    Returns the full center-finding UI as a widget.
    """
    return create_center_finding_section()

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
