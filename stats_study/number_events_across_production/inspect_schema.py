#!/usr/bin/env python3
"""Quick schema dump for one parquet file, to see what's actually there."""
import sys
import pyarrow.parquet as pq

path = sys.argv[1] if len(sys.argv) > 1 else \
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/NMSSM_X600_Y300/nominal/NOTAG_merged.parquet"

pf = pq.ParquetFile(path)
names = pf.schema.names
print(f"File: {path}")
print(f"Total columns: {len(names)}")
print(f"Total rows: {pf.metadata.num_rows}")
print()
mass_related = [n for n in names if "mass" in n.lower() or "bjet" in n.lower() or "pho" in n.lower() or "hhbbgg" in n.lower()]
print("Columns containing 'mass'/'bjet'/'pho'/'hhbbgg' (case-insensitive):")
for n in sorted(mass_related):
    print(f"  {n}")