import subprocess

def run_indexamajig(geomfile_path: str,
                     listfile_path: str, 
                     cellfile_path: str, 
                     output_path: str, 
                     num_threads: int, 
                     extra_flags: list = None):
    """
    Run the indexamajig command with the specified parameters.
    :param geomfile_path: Path to the geometry file.
    :param listfile_path: Path to the list file.
    :param cellfile_path: Path to the cell file.
    :param output_path: Path to the output file.
    :param num_threads: Number of threads to use.
    :param extra_flags: Additional flags to pass to indexamajig.
    :return: None
    """
    if extra_flags is None:
        extra_flags = []

    # Create a list of command parts
    command_parts = [
        "indexamajig",
        "-g", geomfile_path,
        "-i", listfile_path,
        "-o", output_path,
        "-p", cellfile_path,
        "-j", str(num_threads)
    ]

    # Append any extra flags provided by the user.
    command_parts.extend(extra_flags)

    # Join the parts into a single command string.
    base_command = " ".join(command_parts)
    subprocess.run(base_command, shell=True, check=True)
