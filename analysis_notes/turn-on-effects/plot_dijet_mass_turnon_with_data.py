#!/usr/bin/env python3
# =============================================================================
# plot_dijet_mass_turnon_with_data.py
#
# Same as the signal-vs-simulated-background version, but overlays REAL
# 2022 postEE DATA (eras E, F, G) instead of simulation, since a genuine
# Z->bb resonance -- if it's the actual driver of the mY>=90 GeV grid
# boundary discussed in AN Section 7.2 -- can only show up in a sample
# that contains real SM Z production, which the GGJets/DDQCDGJets
# simulation used earlier does not.
#
# Data file layout is FLAT (no nominal/ subdirectory, unlike the signal
# template), confirmed directly:
#   DataC_2022_NOTAG_merged.parquet   (preEE)
#   DataD_2022_NOTAG_merged.parquet   (preEE)
#   DataE_2022_NOTAG_merged.parquet   (postEE)
#   DataF_2022_NOTAG_merged.parquet   (postEE)
#   DataG_2022_NOTAG_merged.parquet   (postEE)
# Only E/F/G (postEE) are used by default, to match the postEE signal/
# background samples used throughout this study; pass --eras to override.
#
# Usage:
#   python3 plot_dijet_mass_turnon_with_data.py --mx 300 --my 50 60 70 80 90 95 100 125 150 170
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

DATA_BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored"
DATA_FILE_TPL = "Data{era}_2022_NOTAG_merged.parquet"

OUT_DIR = "dijet_mass_turnon_plots"
os.makedirs(OUT_DIR, exist_ok=True)

SENTINEL_THRESHOLD = -900.0

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


def read_dijet_mass(path, label=""):
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
    # Data has no MC event weight; default to 1.0 if the column is absent.
    w = df["weight"].to_numpy(dtype=float) if "weight" in df.columns else np.ones(len(df))

    good = (m > SENTINEL_THRESHOLD) & np.isfinite(m) & np.isfinite(w)
    n_total, n_good = len(df), int(good.sum())
    print(f"[INFO] {label or os.path.basename(path)}: mass_col={mass_col}, "
          f"n_total={n_total}, n_valid={n_good} ({100*n_good/max(n_total,1):.1f}%)")

    return m[good], w[good], mass_col


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mx", type=int, required=True)
    ap.add_argument("--my", type=int, nargs="+", required=True)
    ap.add_argument("--eras", type=str, nargs="+", default=["E", "F", "G"],
                     help="Data eras to combine (default: E F G, i.e. postEE). "
                          "Pass e.g. --eras C D for preEE, or all 5 for full 2022.")
    ap.add_argument("--xmax", type=float, default=None)
    args = ap.parse_args()

    cmap = plt.get_cmap("viridis")
    n = len(args.my)
    xmax = args.xmax if args.xmax is not None else 1.3 * max(args.my)
    bins = np.linspace(0, xmax, 61)

    plt.figure(figsize=(9.5, 6.5))

    # ---- Data: sum requested eras ----
    data_m_list, data_w_list = [], []
    for era in args.eras:
        path = os.path.join(DATA_BASE_DIR, DATA_FILE_TPL.format(era=era))
        m, w, col = read_dijet_mass(path, label=f"Data{era}")
        if m is not None:
            data_m_list.append(m)
            data_w_list.append(w)
    peak_center = None
    if data_m_list:
        data_m = np.concatenate(data_m_list)
        data_w = np.concatenate(data_w_list)
        counts, edges = np.histogram(data_m, bins=bins, weights=data_w, density=True)
        plt.hist(data_m, bins=bins, weights=data_w, density=True, histtype="stepfilled",
                 alpha=0.25, color="black", label=f"Data ({''.join(args.eras)})")
        plt.hist(data_m, bins=bins, weights=data_w, density=True, histtype="step",
                 lw=2.2, color="black")

        # mark the data peak (bin center of the tallest bin)
        peak_idx = int(np.argmax(counts))
        peak_center = 0.5 * (edges[peak_idx] + edges[peak_idx + 1])
        print(f"[INFO] Data peak: bin center = {peak_center:.1f} GeV "
              f"(bin edges [{edges[peak_idx]:.1f}, {edges[peak_idx+1]:.1f}])")
    else:
        print("[WARN] No data files could be read -- proceeding with signal only.")

    # ---- Signal: one file per mY ----
    for i, my in enumerate(sorted(args.my)):
        path = SIG_TPL.format(m=args.mx, y=my)
        m, w, col = read_dijet_mass(path, label=f"X{args.mx}_Y{my}")
        if m is None:
            continue
        color = cmap(i / max(n - 1, 1))
        plt.hist(m, bins=bins, weights=w, density=True,
                 histtype="step", lw=1.5, color=color, label=f"Y{my}")

    plt.axvline(91.2, color="red", linestyle="--", lw=1, alpha=0.7)
    plt.text(91.2 + 2, plt.ylim()[1] * 0.95, r"$m_Z$", color="red", fontsize=9)

    if peak_center is not None:
        plt.axvline(peak_center, color="black", linestyle=":", lw=1.5, alpha=0.85)
        plt.text(peak_center + 2, plt.ylim()[1] * 0.88,
                 f"Data peak\n{peak_center:.0f} GeV", color="black", fontsize=8)

    plt.xlabel(r"Dijet mass $m_{b\bar{b}}$ [GeV]")
    plt.ylabel("Unit normalized")
    plt.title(f"Dijet mass: signal (X{args.mx}) vs. 2022 data ({''.join(args.eras)})")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()

    outpath = os.path.join(OUT_DIR, f"dijet_mass_turnon_with_data_X{args.mx}.png")
    plt.savefig(outpath, dpi=200)
    plt.savefig(outpath.replace(".png", ".pdf"))
    print(f"[SAVED] {outpath} (+ .pdf)")


if __name__ == "__main__":
    main()