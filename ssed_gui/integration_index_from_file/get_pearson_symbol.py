#!/usr/bin/env python3

def get_pearson_symbol(cell_file_path: str) -> str:
    """
    Read a CrystFEL unit cell file and return the corresponding Pearson symbol.
    
    Parameters:
        cell_file_path (str): Path to the CrystFEL unit cell file.
        
    Returns:
        str: The Pearson symbol (e.g., "oI").
        
    Raises:
        ValueError: If the file cannot be parsed or if the mapping is not found.
    """
    lattice_type = None
    centering = None

    # Open and parse the cell file.
    with open(cell_file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("lattice_type"):
                # Expected format: lattice_type = orthorhombic
                parts = line.split("=")
                if len(parts) == 2:
                    lattice_type = parts[1].strip().lower()
            elif line.startswith("centering"):
                # Expected format: centering = I
                parts = line.split("=")
                if len(parts) == 2:
                    centering = parts[1].strip().upper()

    if lattice_type is None or centering is None:
        raise ValueError("Could not parse lattice_type and/or centering from the file.")

    # Mapping table for crystal system and centering to Pearson symbol.
    mapping = {
        "triclinic":    {"P": "aP"},
        "monoclinic":   {"P": "mP", "S": "mS"},
        "orthorhombic": {"P": "oP", "S": "oS", "F": "oF", "I": "oI"},
        "tetragonal":   {"P": "tP", "I": "tI"},
        "hexagonal":    {"P": "hP", "R": "hR"},
        "cubic":        {"P": "cP", "F": "cF", "I": "cI"}
    }

    if lattice_type in mapping and centering in mapping[lattice_type]:
        return mapping[lattice_type][centering]
    else:
        raise ValueError("Unrecognized lattice type or centering.")

# If run as a script, allow the user to pass the cell file path as an argument.
if __name__ == '__main__':
    input_file = "/home/bubl3932/files/UOX1/UOX.cell"
    result = get_pearson_symbol(input_file)
    print(result)