#!/usr/bin/env python3
import sys

def extract_geom_values(file_path):
    res_val = None
    max_ss_val = None
    with open(file_path, 'r') as file:
        for line in file:
            # Remove leading/trailing whitespace
            line = line.strip()
            # Skip empty lines or comments
            if not line or line.startswith("#"):
                continue
            # Check for the 'res' line
            if line.startswith("res"):
                # Splitting on '=' to extract the value
                parts = line.split("=")
                if len(parts) > 1:
                    # Remove any additional units or spaces if needed
                    res_val = parts[1].strip().split()[0]
            # Check for the 'p0/max_ss' line
            elif line.startswith("p0/max_ss"):
                parts = line.split("=")
                if len(parts) > 1:
                    max_ss_val = parts[1].strip().split()[0]
    return res_val, max_ss_val

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_geom.py <file.geom>")
        sys.exit(1)
    file_path = sys.argv[1]
    res, max_ss = extract_geom_values(file_path)
    print("res =", res)
    print("max_ss =", max_ss)
