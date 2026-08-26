#!/bin/bash

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <submit_script.sh> <output_parquet_dir>"
    exit 1
fi
SUBMIT_FILE="$1"
OUTPUT_DIR="$2"


# Check if files/directories exist
if [[ ! -f "$SUBMIT_FILE" ]]; then
    echo "❌ Submit file not found: $SUBMIT_FILE"
    exit 1
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "❌ Output directory not found: $OUTPUT_DIR"
    exit 1
fi

BASE_NAME="${SUBMIT_FILE%.*}"
SUB_FILE="${BASE_NAME}.sub"
if [[ ! -f "$SUB_FILE" ]]; then
    echo "❌ Corresponding .sub file not found: $SUB_FILE"
    exit 1
fi

echo "🔍 Scanning for missing .parquet files using $SUBMIT_FILE..."

declare -A job_json_map
current_job=""
while IFS= read -r line; do
    if [[ $line =~ if\ \[\ \$1\ -eq\ ([0-9]+) ]]; then
        current_job="${BASH_REMATCH[1]}"
    fi
    if [[ $line =~ --json-analysis[[:space:]]+([^\ ]+) ]]; then
        json_path="${BASH_REMATCH[1]}"
        tag=$(basename "$json_path" | cut -d'-' -f1)
        job_json_map["$json_path"]="$current_job"
    fi
done < "$SUBMIT_FILE"

missing_jobs=()
missing_count=0
for json in "${!job_json_map[@]}"; do
    tag=$(basename "$json" | cut -d'-' -f1)
    filejson=$(basename "$json" | sed -E 's/^[^-]+-[^-]+-([a-f0-9\-]{23}).*/\1/')
    jobid="${job_json_map[$json]}"    
    samplejson=$(echo $json | sed -E 's#/[^/]+/[^/]+$##')/inputs/$(echo $filejson | sed -E 's/^[^-]*-//')
    uuid=$(grep -oE '/[^/]+\.root' $samplejson | sed -E 's#.*/([^/]+)\.root#\1#')
    expected_parquet="$OUTPUT_DIR/nominal/${uuid}*Events*.parquet"
    matches=( $expected_parquet )
    if [[ ! -e "${matches[0]}" ]]; then
	# Extract the directory path of the submit file
	submit_dir=$(dirname "$SUBMIT_FILE")

	# Find all .out files in the submit directory that end with .$jobid.out
	out_files=( "$submit_dir"/*."$jobid".out )

	# Flag to decide if we should skip resubmission for this job
	skip_resubmit=false

	# Loop over all matching .out files
	for f in "${out_files[@]}"; do
            # Check if the file actually exists
            if [[ -f "$f" ]]; then
		# Search quietly for the phrase "No surviving events"
		if grep -q "No surviving events" "$f"; then
                    echo "ℹ️ Job $jobid has no surviving events (file $f) — skipping resubmission"
                    skip_resubmit=true
                    break  # No need to check other files, skip this job
		fi
            fi
	done

	# If the flag is set, skip adding this job to the resubmit list
	if $skip_resubmit; then
            continue
	fi
        echo "❌ Missing: $expected_parquet"
        echo "→ Resubmit: ./$SUBMIT_FILE $jobid"
	missing_jobs+=("$jobid")
        ((missing_count++))
    fi
done

echo ""
echo "✅ Total missing: $missing_count"

if (( missing_count > 0 )); then
    failed_jobs_str="${missing_jobs[*]}"
    echo "ℹ️ Resubmitting jobs: $failed_jobs_str"
    echo "python3 submission/tools_HHbbgg/resubmit_jobs.py $SUB_FILE \"$failed_jobs_str\" "
    #python3 submission/tools_HHbbgg/resubmit_jobs.py $SUB_FILE "$failed_jobs_str"
fi

