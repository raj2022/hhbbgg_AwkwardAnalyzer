#!/bin/bash

# List of directories
directories=(
    "NMSSM_X400_Y80/" "NMSSM_X550_Y100/" "NMSSM_X600_Y80/" "NMSSM_X700_Y100/"
    "NMSSM_X400_Y90/" "NMSSM_X550_Y60/" "NMSSM_X600_Y90/" "NMSSM_X700_Y60/"
    "NMSSM_X400_Y95/" "NMSSM_X550_Y70/" "NMSSM_X600_Y95/" "NMSSM_X700_Y70/"
    "NMSSM_X500_Y100/" "NMSSM_X550_Y80/" "NMSSM_X650_Y100/" "NMSSM_X700_Y80/"
    "NMSSM_X500_Y60/" "NMSSM_X550_Y90/" "NMSSM_X650_Y60/" "NMSSM_X700_Y90/"
    "NMSSM_X500_Y70/" "NMSSM_X550_Y95/" "NMSSM_X650_Y70/" "NMSSM_X700_Y95/"
    "NMSSM_X400_Y100/" "NMSSM_X500_Y80/" "NMSSM_X600_Y100/" "NMSSM_X650_Y80/"
    "NMSSM_X400_Y60/" "NMSSM_X500_Y90/" "NMSSM_X600_Y60/" "NMSSM_X650_Y90/"
    "NMSSM_X400_Y70/" "NMSSM_X500_Y95/" "NMSSM_X600_Y70/" "NMSSM_X650_Y95/"
)

# Function to rename files
rename_files_in_nominal() {
    for dir in "${directories[@]}"; do
        nominal_path="${dir}/nominal"
        if [ -d "$nominal_path" ]; then
            for file in "$nominal_path"/*; do
                if [ -f "$file" ]; then
                    filename=$(basename -- "$file")
                    if [ "$filename" == "NOTAG_merged.parquet" ] || [ "$filename" == "NOTAG_NOTAG_merged.parquet" ]; then
                        new_file_path="${nominal_path}/NOTAG_NOTAG_merged.parquet"
                        mv "$file" "$new_file_path"
                        echo "Renamed $file to $new_file_path"
                    fi
                fi
            done
        fi
    done
}

# Execute the function
rename_files_in_nominal

