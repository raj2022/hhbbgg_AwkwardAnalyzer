#!/bin/bash

# Arrays for X and Y
X=(400 500 550 600 650 700)
Y=(60 70 80 90 95 100)

# Loop through all combinations of X and Y
for x in "${X[@]}"; do
  for y in "${Y[@]}"; do
    input="../../../output_parquet/merged/NMSSM_X${x}_Y${y}/nominal/NOTAG_merged.parquet"
    output="../../../output_root/NMSSM/NMSSM_X${x}_Y${y}.root"
    python scripts/postprocessing/convert_parquet_to_root.py "$input" "$output" mc
  done
done

