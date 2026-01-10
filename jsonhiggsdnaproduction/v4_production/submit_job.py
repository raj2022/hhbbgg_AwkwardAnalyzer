#!/usr/bin/env python3

import os
import sys

RUN_ANALYSIS = (
    "/afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/"
    "parquet_production_v3/HiggsDNA/higgs_dna/scripts/run_analysis.py"
)

def run_analysis(json_file, output_dir):
    return (
        f"python {RUN_ANALYSIS} "
        f"--json-analysis {json_file} "
        f"--dump {output_dir} "
        f"--doFlow-corrections "
        f"--fiducialCuts store_flag "
        f"--Smear-sigma-m "
        f"--doDeco "
        f"--executor vanilla_lxplus "
        f"--queue workday "
        f"--memory 10000 "
        f"--timeout 300 "
        f"--nano-version 12"
    )

def main():
    if len(sys.argv) != 3:
        print("Usage:")
        print("  python submit_job.py <json_file> <output_dir>")
        sys.exit(1)

    json_file = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isfile(json_file):
        print(f"ERROR: JSON file not found: {json_file}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    cmd = run_analysis(json_file, output_dir)

    print("\nSubmitting HiggsDNA job:")
    print(cmd)
    print()

    os.system(cmd)

if __name__ == "__main__":
    main()

