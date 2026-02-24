import pyarrow.parquet as pq
import os

# Full path to parquet file
parquet_file = "/eos/user/b/bartek/hhbbgg/systematics_v3/2022_postEE/merged/NMSSM_X900_Y95/nominal/NOTAG_merged.parquet"

# Output file in the SAME directory as parquet
output_txt = os.path.join(os.path.dirname(parquet_file), "parquet_variables.txt")

# Read only schema (no full loading)
schema = pq.read_schema(parquet_file)

# Write column names
with open(output_txt, "w") as f:
    for name in schema.names:
        f.write(name + "\n")

print(f"Saved {len(schema.names)} variables to {output_txt}")
# ----------------------------