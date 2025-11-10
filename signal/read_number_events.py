#!/usr/bin/env python3
import os
import pandas as pd
import csv

# Directories to scan
dirs = [
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/",
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/",
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/",
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/",
]

# Variable to inspect
var = "Res_dijet_pt"

print(f"\n🔍 Checking number of events for variable '{var}' in Parquet samples...\n")

summary = []

for d in dirs:
    print("=" * 90)
    print(f"📂 Now reading directory: {d}")
    print("=" * 90)

    if not os.path.exists(d):
        print(f"⚠️  Directory not found: {d}\n")
        continue

    files = [f for f in os.listdir(d) if f.endswith(".parquet")]
    if not files:
        print("  (No parquet files found)\n")
        continue

    print(f"Found {len(files)} Parquet files. Starting to process...\n")

    for f in sorted(files):
        path = os.path.join(d, f)
        try:
            # Read only the column of interest
            df = pd.read_parquet(path, columns=[var])
            n_total = len(df)
            n_valid = df[var].notna().sum()
            print(f"{f:<45} → total: {n_total:>8}, valid: {n_valid:>8}")
            summary.append((os.path.basename(d), f, n_total, n_valid))
        except Exception as e:
            print(f"{f:<45} → ❌ ERROR: {e}")

    print()  # Blank line after each folder for clarity

# Write results to CSV
csv_path = "Res_dijet_pt_event_counts.csv"
with open(csv_path, "w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["directory", "sample", "total_events", "valid_events"])
    writer.writerows(summary)

print(f"\n✅ Summary saved to {csv_path}\n")
