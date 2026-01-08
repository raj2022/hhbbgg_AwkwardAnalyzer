#!/usr/bin/env python3
# ============================================================
# Overlay weight distributions (same CLI as ratio script)
# ============================================================

import argparse
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

DEFAULT_WEIGHT_COLUMNS = [
    "genWeight",
    "weight",
    "weight_central",
    "weight_interference",
    "weight_nominal",
]

def main():
    parser = argparse.ArgumentParser(
        description="Overlay weight distributions from two Parquet files"
    )
    parser.add_argument(
        "--ref",
        required=True,
        help="Reference (nominal) Parquet file"
    )
    parser.add_argument(
        "--var",
        required=True,
        help="Variation Parquet file (e.g. jer_syst_down)"
    )
    parser.add_argument(
        "-o", "--outdir",
        default="weight_overlay_plots",
        help="Output directory"
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=100,
        help="Histogram bins"
    )

    args = parser.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    for f in [args.ref, args.var]:
        if not os.path.isfile(f):
            print(f"❌ File not found: {f}")
            sys.exit(1)

    # --------------------------------------------------------
    # Metadata only
    # --------------------------------------------------------
    pf_ref = pq.ParquetFile(args.ref)
    pf_var = pq.ParquetFile(args.var)

    cols_ref = set(pf_ref.schema_arrow.names)
    cols_var = set(pf_var.schema_arrow.names)

    common_weights = [
        w for w in DEFAULT_WEIGHT_COLUMNS
        if w in cols_ref and w in cols_var
    ]

    if len(common_weights) == 0:
        print("❌ No common weight columns found")
        sys.exit(1)

    print("\n✔ Overlaying weights:")
    for w in common_weights:
        print(f"  - {w}")

    # --------------------------------------------------------
    # Read only weights
    # --------------------------------------------------------
    data_ref = pq.read_table(args.ref, columns=common_weights).to_pandas()
    data_var = pq.read_table(args.var, columns=common_weights).to_pandas()

    data_ref = data_ref.replace([np.inf, -np.inf], np.nan)
    data_var = data_var.replace([np.inf, -np.inf], np.nan)

    # --------------------------------------------------------
    # Plot overlays
    # --------------------------------------------------------
    for w in common_weights:
        mask = data_ref[w].notna() & data_var[w].notna()

        plt.figure()
        plt.hist(
            data_ref.loc[mask, w],
            bins=args.bins,
            histtype="step",
            label="Nominal"
        )
        plt.hist(
            data_var.loc[mask, w],
            bins=args.bins,
            histtype="step",
            label="JER down"
        )

        plt.xlabel(w)
        plt.ylabel("Events")
        plt.title(f"{w}: nominal vs variation")
        plt.legend()
        plt.grid(True)

        outpng = os.path.join(args.outdir, f"{w}_overlay.png")
        plt.savefig(outpng, dpi=150)
        plt.close()

        print(f"✔ Saved {outpng}")

    print(f"\n✔ All overlay plots saved in: {args.outdir}")

if __name__ == "__main__":
    main()
