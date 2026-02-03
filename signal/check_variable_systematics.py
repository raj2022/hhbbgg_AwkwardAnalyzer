#!/usr/bin/env python3
import pandas as pd
import os

# ==============================
# File paths
# ==============================
NOMINAL_FILE = "/afs/cern.ch/user/s/sraj/Analysis/output_parquet/systematics_v3/2022_postEE/merged/NMSSM_X300_Y100/nominal/NOTAG_merged.parquet"

UP_FILE = "/afs/cern.ch/user/s/sraj/Analysis/output_parquet/systematics_v3/2022_postEE/merged/NMSSM_X300_Y100/jer_syst_down/NOTAG_merged.parquet"

DOWN_FILE = "/afs/cern.ch/user/s/sraj/Analysis/output_parquet/systematics_v3/2022_postEE/merged/NMSSM_X300_Y100/jer_syst_up/NOTAG_merged.parquet"

OUTPUT_CSV = "parquet_comparison.csv"

print("CSV will be written to:", os.path.abspath(OUTPUT_CSV))

# ==============================
# Load parquet files
# ==============================
print("Loading parquet files...")
df_nominal = pd.read_parquet(NOMINAL_FILE)
df_up = pd.read_parquet(UP_FILE)
df_down = pd.read_parquet(DOWN_FILE)

# ==============================
# Event counts (rows)
# ==============================
n_nominal = len(df_nominal)
n_up = len(df_up)
n_down = len(df_down)

print("\nEvent counts:")
print("Nominal :", n_nominal)
print("UP      :", n_up)
print("DOWN    :", n_down)

same_nom_up = (n_nominal == n_up)
same_nom_down = (n_nominal == n_down)
same_up_down = (n_up == n_down)

if same_nom_up and same_nom_down:
    print("✅ All files have identical number of events.")
else:
    print("⚠️ Event count mismatch detected!")
    if not same_nom_up:
        print("   Nominal vs UP differ")
    if not same_nom_down:
        print("   Nominal vs DOWN differ")
    if not same_up_down:
        print("   UP vs DOWN differ")

# ==============================
# Column counts
# ==============================
counts = {
    "Nominal": len(df_nominal.columns),
    "UP": len(df_up.columns),
    "DOWN": len(df_down.columns),
}

print("\nColumn counts:")
for k, v in counts.items():
    print(f"{k:8s} -> {v}")

# ==============================
# Column sets
# ==============================
cols_nominal = set(df_nominal.columns)
cols_up = set(df_up.columns)
cols_down = set(df_down.columns)

# ==============================
# Column comparisons
# ==============================
only_up = sorted(cols_up - cols_down)
only_down = sorted(cols_down - cols_up)
common_up_down = sorted(cols_up & cols_down)

up_not_nominal = sorted(cols_up - cols_nominal)
nominal_not_up = sorted(cols_nominal - cols_up)

down_not_nominal = sorted(cols_down - cols_nominal)
nominal_not_down = sorted(cols_nominal - cols_down)

# ==============================
# Value comparisons (UP vs DOWN)
# ==============================
different_values = []
for c in common_up_down:
    try:
        if not df_up[c].equals(df_down[c]):
            different_values.append(c)
    except Exception:
        different_values.append(c)

# ==============================
# Prepare CSV rows
# ==============================
rows = []

def add_rows(col_list, category):
    if not col_list:
        rows.append({"category": category, "value": "None"})
    else:
        for c in col_list:
            rows.append({"category": category, "value": c})

# Event counts
rows.append({"category": "Event count (Nominal)", "value": n_nominal})
rows.append({"category": "Event count (UP)", "value": n_up})
rows.append({"category": "Event count (DOWN)", "value": n_down})

rows.append({"category": "Event counts identical?",
             "value": f"Nominal=UP={same_nom_up}, Nominal=DOWN={same_nom_down}"})

# Column counts
for name, cnt in counts.items():
    rows.append({"category": f"Column count ({name})", "value": cnt})

# Column comparisons
add_rows(only_up, "Only in UP (not in DOWN)")
add_rows(only_down, "Only in DOWN (not in UP)")
add_rows(common_up_down, "Common columns (UP & DOWN)")
add_rows(different_values, "Different values (UP vs DOWN)")

add_rows(up_not_nominal, "Only in UP (not in NOMINAL)")
add_rows(nominal_not_up, "Only in NOMINAL (not in UP)")
add_rows(down_not_nominal, "Only in DOWN (not in NOMINAL)")
add_rows(nominal_not_down, "Only in NOMINAL (not in DOWN)")

# ==============================
# Write CSV
# ==============================
df_out = pd.DataFrame(rows)
df_out.to_csv(OUTPUT_CSV, index=False)

print("\n✅ CSV file written:", OUTPUT_CSV)
print("Total CSV rows:", len(df_out))

print("\nDone.")
