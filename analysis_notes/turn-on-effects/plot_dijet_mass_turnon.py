#!/usr/bin/env python3
# =============================================================================
# plot_dijet_mass_turnon.py
#
# Plots the reconstructed dijet (b-jet pair) mass across a range of mY
# points at fixed mX. Since Y -> bb directly, the dijet mass peak should
# track the generated mY value; this checks whether that peak is correctly
# reconstructed at low mY, whether the peak resolution degrades, and
# whether there's any distortion/pileup near the Z->bb mass region
# (~91 GeV) that Section 7.2 of the AN attributes the mY>=90 GeV grid
# boundary to.
#
# Usage:
#   python3 plot_dijet_mass_turnon.py --mx 300 --my 50 60 70 80 90 95 100 125 150 170
# =============================================================================

import os
import argparse
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
    "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)

OUT_DIR = "dijet_mass_turnon_plots"
os.makedirs(OUT_DIR, exist_ok=True)

SENTINEL_THRESHOLD = -900.0

# Priority-ordered candidate column names for the reconstructed dijet mass.
# Res_dijet_mass_DNNreg (mass-regressed) is preferred if present, since
# that's the corrected observable actually used downstream in the analysis;
# falls back to the raw Res_dijet_mass, then the nonRes_ equivalents.
DIJET_MASS_CANDIDATES = [
    "Res_dijet_mass_DNNreg", "Res_dijet_mass",
    "nonRes_dijet_mass_DNNreg", "nonRes_dijet_mass",
    "nonResReg_dijet_mass_DNNreg", "nonResReg_dijet_mass",
]


def pick_column(schema_names, candidates):
    for c in candidates:
        if c in schema_names:
            return c
    return None


def read_dijet_mass(path):
    if not os.path.exists(path):
        print(f"[WARN] missing: {path}")
        return None, None, None
    try:
        schema_names = pq.read_schema(path).names
    except Exception as e:
        print(f"[WARN] schema read fail {path}: {e}")
        return None, None, None

    mass_col = pick_column(schema_names, DIJET_MASS_CANDIDATES)
    if mass_col is None:
        print(f"[WARN] {path}: no matching dijet mass column found")
        return None, None, None

    cols = [mass_col]
    if "weight" in schema_names:
        cols.append("weight")
    df = pd.read_parquet(path, columns=cols)

    m = df[mass_col].to_numpy(dtype=float)
    w = df["weight"].to_numpy(dtype=float) if "weight" in df.columns else np.ones(len(df))

    good = (m > SENTINEL_THRESHOLD) & np.isfinite(m) & np.isfinite(w)
    n_total, n_good = len(df), int(good.sum())
    print(f"[INFO] {os.path.basename(os.path.dirname(os.path.dirname(path)))}: "
          f"mass_col={mass_col}, n_total={n_total}, n_valid={n_good} "
          f"({100*n_good/max(n_total,1):.1f}%), "
          f"mean={np.mean(m[good]):.1f} GeV, median={np.median(m[good]):.1f} GeV")

    return m[good], w[good], mass_col


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mx", type=int, required=True)
    ap.add_argument("--my", type=int, nargs="+", required=True)
    ap.add_argument("--xmax", type=float, default=None,
                     help="Optional fixed x-axis max (GeV). Defaults to 1.3x the largest requested mY.")
    args = ap.parse_args()

    cmap = plt.get_cmap("viridis")
    n = len(args.my)
    xmax = args.xmax if args.xmax is not None else 1.3 * max(args.my)
    bins = np.linspace(0, xmax, 61)

    plt.figure(figsize=(9, 6.5))

    for i, my in enumerate(sorted(args.my)):
        path = SIG_TPL.format(m=args.mx, y=my)
        m, w, col = read_dijet_mass(path)
        if m is None:
            continue
        color = cmap(i / max(n - 1, 1))
        plt.hist(m, bins=bins, weights=w, density=True,
                 histtype="step", lw=1.7, color=color, label=f"Y{my}")

    # mark the Z->bb mass region for reference
    plt.axvline(91.2, color="gray", linestyle="--", lw=1, alpha=0.7)
    plt.text(91.2 + 2, plt.ylim()[1] * 0.95, r"$m_Z$", color="gray", fontsize=9)

    plt.xlabel(r"Dijet mass $m_{b\bar{b}}$ [GeV]")
    plt.ylabel("Unit normalized")
    plt.title(f"Reconstructed dijet mass vs. $m_Y$, X{args.mx}")
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()

    outpath = os.path.join(OUT_DIR, f"dijet_mass_turnon_X{args.mx}.png")
    plt.savefig(outpath, dpi=200)
    plt.savefig(outpath.replace(".png", ".pdf"))
    print(f"[SAVED] {outpath} (+ .pdf)")


if __name__ == "__main__":
    main()