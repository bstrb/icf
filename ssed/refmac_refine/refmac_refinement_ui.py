import ipywidgets as widgets
from IPython.display import display
import matplotlib.pyplot as plt
import numpy as np
import os
import re

# Try to import file chooser widget.
try:
    from ipyfilechooser import FileChooser 
except ImportError:
    print("ipyfilechooser is required. Install with: pip install ipyfilechooser")

# Try to import your refinement function.
import_failed = False
import_error_msg = ""
refmac_import_out = widgets.Output(layout={'border': '1px solid black', 'padding': '5px'})
with refmac_import_out:
    try:
        from .ctruncate_freerflag_refmac5 import ctruncate_freerflag_refmac5  # Update module name/path if needed.
        print("Successfully imported ctruncate_freerflag_refmac5.")
    except Exception as e:
        import_failed = True
        import_error_msg = str(e)
        print("Error importing ctruncate_freerflag_refmac5:", e)

def parse_refmac_log_for_table(log_path):
    """
    Opens refmac5.log at log_path, finds the last table that contains the header
    "M(4SSQ/LL)" and "Rf_used", and returns two lists:
      - resolution_list (in Å) computed as sqrt(1/(first column))
      - rf_used_list (from the 6th column)
    """
    resolution_list = []
    rf_used_list = []
    if not os.path.isfile(log_path):
        return resolution_list, rf_used_list

    with open(log_path, 'r') as f:
        lines = f.readlines()

    # Find the last occurrence of the header line.
    header_indices = []
    for i, line in enumerate(lines):
        if "M(4SSQ/LL)" in line and "Rf_used" in line:
            header_indices.append(i)
    if not header_indices:
        return resolution_list, rf_used_list
    start_index = header_indices[-1]
    
    # Find the next line that is exactly "$$" which marks the end of header block.
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
            # Avoid division by zero.
            if col1_val != 0:
                res = np.sqrt(1.0 / col1_val)
            else:
                res = None
            if res is not None:
                resolution_list.append(res)
                rf_used_list.append(col6_val)
        except ValueError:
            continue

    return resolution_list, rf_used_list

# Create an output widget for feedback and logs.
refmac_feedback_out = widgets.Output(layout={
    'border': '1px solid black',
    'height': '350px',
    'overflow_y': 'auto',
    'padding': '5px'
})

def get_ui():
    """
    Returns the full Refmac5 refinement and plot UI as a widget.
    """
    if not import_failed:
        # File choosers for input files.
        mtz_file_chooser = FileChooser(os.getcwd())
        mtz_file_chooser.title = 'Select .mtz File'
        mtz_file_chooser.filter_pattern = '*.mtz'
        
        pdb_file_chooser = FileChooser(os.getcwd())
        pdb_file_chooser.title = 'Select .pdb File'
        pdb_file_chooser.filter_pattern = '*.pdb'
        
        # Extra parameter widgets.
        max_res_widget = widgets.FloatText(
            value=20.0,
            description="max_res:",
            style={"description_width": "80px"},
            layout=widgets.Layout(width='200px')
        )
        min_res_widget = widgets.FloatText(
            value=1.5,
            description="min_res:",
            style={"description_width": "80px"},
            layout=widgets.Layout(width='200px')
        )
        ncycles_widget = widgets.IntText(
            value=30,
            description="ncycles:",
            style={"description_width": "80px"},
            layout=widgets.Layout(width='200px')
        )
        bins_widget = widgets.IntText(
            value=10,
            description="bins:",
            style={"description_width": "80px"},
            layout=widgets.Layout(width='200px')
        )
        
        extra_params_box = widgets.HBox([max_res_widget, min_res_widget, ncycles_widget, bins_widget])
        
        # Refine button.
        refine_button = widgets.Button(
            description="Refine with Refmac5 (and Plot)",
            button_style='info'
        )
        
        @refmac_feedback_out.capture(clear_output=False)
        def on_refine_clicked(b):
            print("\n" + "="*50)
            print("REFMAC5 REFINEMENT + TABLE PARSING & PLOTTING")
            print("="*50)
            
            mtz_file = mtz_file_chooser.selected
            pdb_file = pdb_file_chooser.selected
            
            if not mtz_file:
                print("Please select an MTZ file first.")
                return
            if not pdb_file:
                print("Please select a PDB file first.")
                return
            
            max_res = max_res_widget.value
            min_res = min_res_widget.value
            ncycles = ncycles_widget.value
            bins_ = bins_widget.value
            
            print(f"Running refinement with parameters:\n  MTZ: {mtz_file}\n  PDB: {pdb_file}\n  max_res: {max_res}\n  min_res: {min_res}\n  ncycles: {ncycles}\n  bins: {bins_}")
            
            # Run the refinement function; it should return a string output directory.
            output_dir = ctruncate_freerflag_refmac5(mtz_file, pdb_file, max_res=max_res, min_res=min_res, ncycles=ncycles, bins=bins_)
            
            print("Refinement completed.")
            if output_dir is None:
                print("No output directory returned. Cannot locate refmac5.log for plotting.")
                return
            
            log_file_path = os.path.join(output_dir, "refmac5.log")
            if not os.path.isfile(log_file_path):
                print(f"refmac5.log not found at {log_file_path}. Skipping plot.")
                return
            
            resolution_list, rf_used_list = parse_refmac_log_for_table(log_file_path)
            if not resolution_list:
                print("No valid table found in refmac5.log, or columns didn't parse. Skipping plot.")
                return
            
            # Sort the data by resolution (ascending).
            sorted_pairs = sorted(zip(resolution_list, rf_used_list), key=lambda x: x[0])
            sorted_res, sorted_rf = zip(*sorted_pairs)
            
            plt.figure(figsize=(6, 4))
            plt.plot(sorted_res, sorted_rf, marker='o', linestyle='-')
            plt.xlabel("Resolution (Å)")
            plt.ylabel("Rf_used")
            plt.title("Rf_used vs. Resolution")
            plt.grid(True)
            plt.gca().invert_xaxis()  # Flip the x-axis so high resolutions appear on the left.
            plt.tight_layout()
            plt.show()
        
        refine_button.on_click(on_refine_clicked)
        
        refine_controls = widgets.VBox([
            widgets.HTML("<h3>Refmac5 Refinement (with Table Parsing & Plot)</h3>"),
            mtz_file_chooser,
            pdb_file_chooser,
            widgets.HTML("<h4>Optional Parameters</h4>"),
            extra_params_box,
            refine_button
        ])
        
        final_layout = widgets.VBox([
            refmac_import_out,
            widgets.HTML("<h2>Refmac5 Refinement & Plot Tool</h2>"),
            refine_controls,
            widgets.HTML("<h3>Logs & Feedback</h3>"),
            refmac_feedback_out
        ])
        
        return final_layout
    else:
        error_ui = widgets.VBox([
            refmac_import_out,
            widgets.HTML("<b>Could not load ctruncate_freerflag_refmac5:</b>"),
            widgets.HTML(import_error_msg)
        ])
        return error_ui

if __name__ == '__main__':
    ui = get_ui()
    display(ui)
