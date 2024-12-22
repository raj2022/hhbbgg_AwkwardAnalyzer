#!/bin/bash

# Activate Higgs-DNA environment
mamba activate higgs-dna

# Initialize VOMS proxy
voms-proxy-init --rfc --voms cms -valid 192:00

# Define the list of numbers
numbers=(600 650 700 800 900 1000 1200 1400 1600 1800 2000 2500 3000 3500 4000)

# Base path for the script and output directories
script_path="/afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/parquet_production/HiggsDNA/scripts/run_analysis.py"
output_path="/afs/cern.ch/user/s/sraj/private/output/"

# Loop through each number and execute the command
for num in "${numbers[@]}"; do
    # Print a message about the current submission
    echo "Submitting job for number $num..."

    # Construct the JSON filename with the current number
    json_file="My_Json_${num}.json"

    # Run the command with the current JSON file
    python "$script_path" \
        --json-analysis "$json_file" \
        --dump "$output_path" \
        --doFlow_corrections \
        --fiducialCuts store_flag \
        --skipCQR \
        --Smear_sigma_m \
        --doDeco \
        --executor vanilla_lxplus \
        --queue espresso

    # Indicate the submission is complete for this number
    echo "Job for number $num submitted."
done

