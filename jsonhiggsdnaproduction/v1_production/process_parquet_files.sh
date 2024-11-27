#!/bin/bash

# Define the base directories
parquet_base_dir="../../../output_parquet/merged"
root_base_dir="../../../output_root"
script_path="scripts/postprocessing/convert_parquet_to_root.py"

# Iterate over each subdirectory in the base directory
for subdir in "$parquet_base_dir"/*/nominal; do
    # Process each .parquet file in the subdirectory
    for parquet_file in "$subdir"/*.parquet; do
        # Extract the filename and directory
        file_name=$(basename "$parquet_file")
        dir_name=$(dirname "$parquet_file")
        base_name="${file_name%.parquet}"

        # Handle files with 'NOTAG_NOTAG_' prefix
        if [[ "$file_name" == NOTAG_NOTAG_* ]]; then
            new_file_name="${file_name#NOTAG_NOTAG_}"
            mv "$parquet_file" "$dir_name/$new_file_name"
            parquet_file="$dir_name/$new_file_name"
        fi

        # Handle files with 'NOTAG_' prefix
        if [[ "$file_name" == NOTAG_* ]]; then
            echo "File $file_name already has the 'NOTAG_' prefix. Skipping."
            continue
        fi

        # Rename files that do not have 'NOTAG_' prefix
        new_file_name="NOTAG_${file_name}"
        mv "$parquet_file" "$dir_name/$new_file_name"
        parquet_file="$dir_name/$new_file_name"

        # Construct the output ROOT file path
        root_file_path="$root_base_dir/$(basename "$(dirname "$dir_name")")/$(basename "$dir_name")/$(basename "${base_name}").root"

        # Create the output directory if it doesn't exist
        mkdir -p "$(dirname "$root_file_path")"

        # Convert the .parquet file to ROOT format
        python "$script_path" "$parquet_file" "$root_file_path" mc
    done
done

