#!/usr/bin/env python3
import os
import pandas as pd

# Directories to scan
dirs = [
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/",
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/",
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/",
    "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/",
]

# Variable to inspect
var = "Res_dijet_pt"

print(f"\nChecking number of events for variable '{var}' in Parquet samples...\n")

summary = []

for d in dirs:
    print(f"--- Directory: {d} ---")
    files = [f for f in os.listdir(d) if f.endswith(".parquet")]
    if not files:
        print("  (No parquet files found)")
        continue

    for f in sorted(files):
        path = os.path.join(d, f)
        try:
            # Read only the column of interest
            df = pd.read_parquet(path, columns=[var])
            n_total = len(df)
            n_valid = df[var].notna().sum()
            print(f"{f:<45} → total: {n_total:>8}, valid: {n_valid:>8}")
            summary.append((f, n_total, n_valid))
        except Exception as e:
            print(f"{f:<45} → ERROR: {e}")
    print()

# Optionally write results to CSV
import csv
csv_path = "Res_dijet_pt_event_counts.csv"
with open(csv_path, "w", newline="") as out:
    writer = csv.writer(out)
    writer.writerow(["sample", "total_events", "valid_events"])
    writer.writerows(summary)

print(f"\n✅ Summary saved to {csv_path}\n")
