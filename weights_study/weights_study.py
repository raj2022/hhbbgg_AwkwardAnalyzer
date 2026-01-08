#!/usr/bin/env python3
# ============================================================
# List variables in Parquet file + plot weight distributions
# ============================================================

import argparse
import pyarrow.parquet as pq
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

WEIGHT_COLUMNS = [
    "genWeight",
    "weight",
    "weight_central",
    "weight_interference",
    "weight_nominal",
]

def main():
    parser = argparse.ArgumentParser(
        description="List Parquet variables and plot weight distributions"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input Parquet file"
    )
    parser.add_argument(
        "-o", "--outdir",
        default="weight_plots",
        help="Output directory (default: weight_plots)"
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=100,
        help="Number of histogram bins (default: 100)"
    )

    args = parser.parse_args()

    parquet_file = args.input
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)

    if not os.path.isfile(parquet_file):
        print(f"❌ File not found: {parquet_file}")
        sys.exit(1)

    # --------------------------------------------------------
    # Read Parquet metadata (NO data load)
    # --------------------------------------------------------
    pf = pq.ParquetFile(parquet_file)
    all_columns = pf.schema_arrow.names

    print(f"\n📄 File: {parquet_file}")
    print(f"🔢 Total variables: {len(all_columns)}\n")

    for col in all_columns:
        print(col)

    # Save variable list ONLY
    variables_csv = os.path.join(outdir, "parquet_variables.csv")
    pd.DataFrame({"variable": all_columns}).to_csv(variables_csv, index=False)
    print(f"\n💾 Saved variable list to: {variables_csv}")

    # --------------------------------------------------------
    # Read ONLY weight columns for plotting
    # --------------------------------------------------------
    existing_weights = [c for c in WEIGHT_COLUMNS if c in all_columns]

    if len(existing_weights) == 0:
        print("\n⚠️ No weight columns found — skipping plots.")
        sys.exit(0)

    table = pq.read_table(parquet_file, columns=existing_weights)
    df = table.to_pandas()
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    # --------------------------------------------------------
    # Individual weight plots
    # --------------------------------------------------------
    for col in existing_weights:
        plt.figure()
        plt.hist(df[col], bins=args.bins, histtype="step")
        plt.xlabel(col)
        plt.ylabel("Events")
        plt.title(col)
        plt.grid(True)

        png_out = os.path.join(outdir, f"{col}.png")
        plt.savefig(png_out, dpi=150)
        plt.close()

        print(f"✔ Saved {png_out}")

    # --------------------------------------------------------
    # Stacked weight plot
    # --------------------------------------------------------
    if len(existing_weights) > 1:
        plt.figure()
        plt.hist(
            [df[c] for c in existing_weights],
            bins=args.bins,
            stacked=True,
            label=existing_weights,
            histtype="stepfilled",
            alpha=0.8
        )
        plt.xlabel("Weight value")
        plt.ylabel("Events")
        plt.title("Stacked weight distributions")
        plt.legend()
        plt.grid(True)

        stacked_png = os.path.join(outdir, "weights_stacked.png")
        plt.savefig(stacked_png, dpi=150)
        plt.close()

        print(f"✔ Saved {stacked_png}")
        print("\n✅ Done.")
        print(f"All plots saved in directory: {outdir}")

if __name__ == "__main__":
    main()
