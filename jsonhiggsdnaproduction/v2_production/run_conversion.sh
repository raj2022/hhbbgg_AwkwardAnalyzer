#!/bin/bash

# Arrays for X and Y
X=(400 500 550 600 650 700 800 1000 1400 1800 2500 3000 3500 4000)
Y=(60 70 80 90 95 100 125 150 200 300 400 500 600 800 1000)

# Base path for input and output files
base_input_path="../../../output_parquet/v2_production/merged/"
base_output_path="i../../../output_root/v2_production/signal_NMSSM/
"

# Loop through all combinations of X and Y
for x in "${X[@]}"; do
  for y in "${Y[@]}"; do
    # Construct input and output paths
    input="${base_input_path}NMSSM_X${x}_Y${y}/nominal/NOTAG_merged.parquet"
    output="${base_output_path}NMSSM_X${x}_Y${y}.root"

    # Check if the input file exists
    if [ -f "$input" ]; then
        # Convert the Parquet file to ROOT format
        echo "Processing $input to $output"
        python scripts/postprocessing/convert_parquet_to_root.py "$input" "$output" mc
    else
        # If the input file does not exist, print a message
        echo "File not found: $input"
    fi
  done
done

