import os
import glob
import numpy as np 
import pandas as pd 




def read_parquet_folder(folder, columns=None, recursive=True):
    """Read all .parquet in  a folder into one DataFrame."""
    pattern = "**/*.parquet" if recursive else "*.parquet"
    files = glob.glob(os.path.join(folder, pattern), recursive=recursive)
    if not files:
        raise FileNotFoundError(f"No parquet files found under {folder}")
    # If files are large, just read the needed columns
    parts = [pd.read_parquet(f, columns=columns) for f in files]
    return pd.concat(parts, ignore_index=True)

FOLDER = "../../output_parquet/final_production_Syst/merged"
cols   = [ "Res_HHbbggCandidate_mass"]  # pick any variables you want
df = read_parquet_folder(FOLDER, columns=cols)
print("Total events (rows):", len(df))
print("Counts per label:\n", df["label"].value_counts())