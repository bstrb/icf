import subprocess
import os
from tqdm import tqdm

def run_ctruncate(hklin, hklout):
    """Run ctruncate to process the input MTZ."""
    ctruncate_command = (
        f"ctruncate -hklin {hklin} -hklout {hklout} -colin '/*/*/[I,SIGI]'"
    )
    with open(os.devnull, 'w') as fnull:
        subprocess.run(ctruncate_command, shell=True, stdout=fnull, stderr=fnull)

def run_freerflag(hklin, hklout):
    """Run freerflag to set the FreeR_flag column."""
    freerflag_command = f"""freerflag hklin {hklin} hklout {hklout} << EOF
freerfrac 0.05
EOF
"""
    with open(os.devnull, 'w') as fnull:
        subprocess.run(freerflag_command, shell=True, stdout=fnull, stderr=fnull)

def run_refmac5(pdb_file, mtz_file, output_dir, max_res=20, min_res=1.5, ncycles=30, bins=10):
    """
    Run refmac5 for structure refinement.
    Output files (refined PDB, MTZ, log) are written in output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_pdb = os.path.join(output_dir, "output.pdb")
    output_mtz = os.path.join(output_dir, "ref_output.mtz")
    output_log = os.path.join(output_dir, "refmac5.log")

    refmac_command = f"""refmac5 \
xyzin {pdb_file} xyzout {output_pdb} \
hklin {mtz_file} hklout {output_mtz} << EOF
    ncyc {ncycles}
    bins {bins}
    refi TYPE RESTRAINED RESOLUTION {max_res} {min_res}
    make HYDROGENS ALL
    make HOUT No
    scat ELEC
    scal TYPE BULK
    labin FP=F SIGFP=SIGF FREE=FreeR_flag
    END
EOF
"""

    with open(output_log, "w") as flog, open(os.devnull, 'w') as fnull:
        process = subprocess.Popen(
            refmac_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=flog,
            stdin=subprocess.DEVNULL,
            universal_newlines=True
        )
        pbar = tqdm(total=ncycles, desc="Refmac5 CGMAT cycles", unit="cycle")
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if "CGMAT cycle number" in line:
                pbar.update(1)
            flog.write(line)
        pbar.close()

def ctruncate_freerflag_refmac5(mtz_file, pdb_file, max_res=20, min_res=1.5, ncycles=30, bins=10):

    # Output directory is the same as the directory containing the input MTZ file
    output_dir = os.path.dirname(os.path.abspath(mtz_file))

    # Define intermediate file paths in the same directory
    ctruncate_mtz = os.path.join(output_dir, "output_ctruncate.mtz")
    freerflag_mtz = os.path.join(output_dir, "output_freerflag.mtz")

    print("Running ctruncate...")
    run_ctruncate(mtz_file, ctruncate_mtz)

    print("Running freerflag...")
    run_freerflag(ctruncate_mtz, freerflag_mtz)

    print("Running refmac5...")
    run_refmac5(pdb_file, freerflag_mtz, output_dir, max_res, min_res, ncycles, bins)

    print(f"Done! Check the output files in {output_dir}")

    return output_dir

if __name__ == "__main__":
    mtz_file = "/home/bubl3932/files/UOX1/UOX1_original_IQM/xgandalf_iterations_max_radius_1_step_0.5/filtered_metrics_merge_5_iter/output.mtz"
    pdb_file = "/home/bubl3932/files/UOX1/UOX1_original_IQM/UOX.pdb"
    output_dir = ctruncate_freerflag_refmac5(mtz_file, pdb_file)
    print(f"Output directory: {output_dir}")
