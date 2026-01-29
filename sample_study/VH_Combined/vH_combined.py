# VH_combined.py
# -----------------------
# Script to combine VHtoGG samples into a single Parquet file with proper weighting.
# shivam raj
# -----------------------
# https://xsecdb-xsdb-official.app.cern.ch/xsdb/?columns=67108863&currentPage=0&pageSize=10&searchQuery=DAS%3DW%2AH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8
# -----------------------
#!/usr/bin/env python3

import os
import pyarrow.parquet as pq
import pyarrow as pa
import pandas as pd
import numpy as np

# -----------------------
# Configuration
# -----------------------

LUMI_PB = 108960.0  # 108.96 fb^-1

XSECS = {
    "WmHtoGG": 0.647,
    "WpHtoGG": 1.021,
    "ZHtoGG":  0.9079,
}

PATHS = {
    "WmHtoGG": "/eos/cms/store/group/phys_b2g/HHbbgg/HiggsDNA_parquet/v4/Run3_2024/sim/WmHtoGG/NOTAG_merged.parquet",
    "WpHtoGG": "/eos/cms/store/group/phys_b2g/HHbbgg/HiggsDNA_parquet/v4/Run3_2024/sim/WpHtoGG/NOTAG_merged.parquet",
    "ZHtoGG":  "/eos/cms/store/group/phys_b2g/HHbbgg/HiggsDNA_parquet/v4/Run3_2024/sim/ZHtoGG/NOTAG_merged.parquet",
}

OUTPUT_DIR = "/afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2024/"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "VHtoGG.parquet")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Remove old output if exists
if os.path.exists(OUTPUT_FILE):
    os.remove(OUTPUT_FILE)

# -----------------------
# Step 1: Build UNION schema (all columns)
# -----------------------

print("\n>>> Building union schema")

all_columns = set()

for sample, path in PATHS.items():
    pf = pq.ParquetFile(path)
    cols = pf.schema_arrow.names
    print(f"    {sample}: {len(cols)} columns")
    all_columns.update(cols)

# Final ordered schema (sorted for stability)
ALL_COLUMNS = sorted(all_columns)

print(f"\n>>> Total union columns = {len(ALL_COLUMNS)}")

# -----------------------
# Streaming write
# -----------------------

writer = None
total_yield = 0.0
total_events = 0

for sample, path in PATHS.items():
    print(f"\n>>> Processing {sample}")

    parquet_file = pq.ParquetFile(path)

    # ---- Pass 1: compute sum of genWeight
    sumw = 0.0
    for batch in parquet_file.iter_batches(columns=["genWeight"], batch_size=20000):
        sumw += batch.column(0).to_numpy().sum()

    xsec = XSECS[sample]
    scale = (xsec * LUMI_PB) / sumw

    print(f"    sum(genWeight) = {sumw:.3e}")
    print(f"    scale factor   = {scale:.6e}")

    # ---- Pass 2: stream, pad missing columns, write
    for batch in parquet_file.iter_batches(batch_size=50000):
        table = pa.Table.from_batches([batch])
        df = table.to_pandas(split_blocks=True, self_destruct=True)

        # Overwrite nominal weight
        df["weight_nominal"] = df["genWeight"] * scale

        # Bookkeeping
        total_yield += df["weight_nominal"].sum()
        total_events += len(df)

        # ---- Add missing columns
        missing = set(ALL_COLUMNS) - set(df.columns)
        for col in missing:
            df[col] = np.nan

        # ---- Reorder columns to union schema
        df = df[ALL_COLUMNS]

        out_table = pa.Table.from_pandas(df, preserve_index=False)

        # Initialize writer once with union schema
        if writer is None:
            writer = pq.ParquetWriter(OUTPUT_FILE, out_table.schema)

        writer.write_table(out_table)

    print(f"    cumulative events written = {total_events:,}")

# Close parquet writer
if writer:
    writer.close()

print("\n==============================")
print("VH build completed")
print("==============================")
print(f"Total events written = {total_events:,}")
print(f"Total VH yield       = {total_yield:.2f}")
print(f"\n✅ Output saved to → {OUTPUT_FILE}")
