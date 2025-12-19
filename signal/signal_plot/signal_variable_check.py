#!/usr/bin/env python3

import os
import pyarrow.parquet as pq
import awkward as ak
import numpy as np
import matplotlib.pyplot as plt

# Input parquet file
parquet_file = (
    "/eos/user/b/bsahu/HiggsDNA_v4PrelimProd/2024/merged/"
    "NMSSM-XtoYH-MX-300-MY-100/NOTAG_merged.parquet"
)

# Output directory and file
out_dir = "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/2022"
out_plot = os.path.join(out_dir, "mass.png")

os.makedirs(out_dir, exist_ok=True)

# Open parquet file
pf = pq.ParquetFile(parquet_file)

mass_chunks = []

# Read in batches (same safe pattern you use elsewhere)
for batch in pf.iter_batches(
        batch_size=10000,
        columns=["mass"]
    ):
    arr = ak.from_arrow(batch)
    mass_chunks.append(arr["mass"])

# Concatenate and convert to numpy
mass = ak.to_numpy(ak.concatenate(mass_chunks))

# Plot
plt.figure(figsize=(8, 6))
plt.hist(mass, bins=100)
plt.xlabel("mass")
plt.ylabel("Events")
plt.title("Mass distribution")

# Save plot
plt.tight_layout()
plt.savefig(out_plot)
plt.close()

print(f"[OK] Plot saved to: {out_plot}")
