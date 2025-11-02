#!/bin/bash


# All mass combintation
declare -A masses=(
  [300]="60 70 80 90 95 100 125 150"   
  [400]="60 70 80 90 95 100 125 150 200"
  [500]="60 70 80 90 95 100 125 150 200 300"
  [550]="60 70 80 90 95 100 125 150 200 300 400"
  [600]="60 70 80 90 95 100 125 150 200 300 400"
  [650]="60 70 80 90 95 100 125 150 200 300 400 500"
  [700]="60 70 80 90 95 100 125 150 200 300 400 500"
  [800]="60 70 80 90 95 100 125 150 200 300 400 500 600"
  [900]="60 70 80 90 95 100 125 150 200 300 400 500 600"
  [1000]="60 70 80 90 95 100 125 150 200 300 400 500 600 800"
)


echo "=== Starting NMSSM parquet copy process ==="
echo

for X in "${!masses[@]}"; do
    for Y in ${masses[$X]}; do
        src="/afs/cern.ch/user/s/sraj/Analysis/output_parquet/v3_production/production_v3/2023_postBPix/merged/NMSSM_X${X}_Y${Y}/NOTAG_merged.parquet"
        dest="/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/NMSSM_X${X}_Y${Y}.parquet"

        if [ -f "$dest" ]; then
            echo "⏭️  Skipping: $dest already exists."
            continue
        fi

        if [ -f "$src" ]; then
            cp "$src" "$dest"
            echo "✅ Copied: NMSSM_X${X}_Y${Y}.parquet"
        else
            echo "⚠️  Missing source file: $src"
        fi
    done
done

echo
echo "=== Copy process complete ==="
