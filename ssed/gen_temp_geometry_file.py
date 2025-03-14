# modify_geometry_file.py

import tempfile

def gen_temp_geometry_file(template_file_path, x, y):
    """Create a temporary geometry file with modified x, y values."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".geom")  # Creates a temporary file
    
    with open(template_file_path, 'r') as file:
        lines = file.readlines()
    
    for line in lines:
        if line.startswith("p0/corner_x"):
            temp_file.write(f"p0/corner_x = {x}\n")
        elif line.startswith("p0/corner_y"):
            temp_file.write(f"p0/corner_y = {y}\n")
        else:
            temp_file.write(line)
    
    temp_file.close()
    return temp_file.name  # Return the path to the temp file