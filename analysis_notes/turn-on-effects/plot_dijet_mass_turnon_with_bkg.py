#!/usr/bin/env python3
# =============================================================================
# plot_dijet_mass_turnon_with_bkg.py
#
# Same as plot_dijet_mass_turnon.py, but overlays the actual BACKGROUND
# dijet mass spectrum (GGJets + DDQCDGJets_Rescaled + GGJets_Rescaled, per
# pDNN_v2.py's Config) so the real Z->bb bump (if present) can be compared
# directly against the Y50-Y170 signal peaks, rather than just marking a
# reference line at m_Z.
#
# Usage:
#   python3 plot_dijet_mass_turnon_with_bkg.py --mx 300 --my 50 60 70 80 90 95 100 125 150 170
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

# Background files (from pDNN_v2.py Config) -- same production tree used
# for the non-resonant continuum background in training.
BACKGROUND_BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE"
BACKGROUND_FILENAMES = (
    "GGJets_MGG-80/NOTAG_merged.parquet",
    "DDQCCDGJets/DDQCDGJets_Rescaled.parquet",
    "DDQCCDGJets/GGJets_MGG-80_Rescaled.parquet",
)
BACKGROUND_FILES = [os.path.join(BACKGROUND_BASE_DIR, f) for f in BACKGROUND_FILENAMES]

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
    ap.add_argument("--xmax", type=float, default=None)
    args = ap.parse_args()

    cmap = plt.get_cmap("viridis")
    n = len(args.my)
    xmax = args.xmax if args.xmax is not None else 1.3 * max(args.my)
    bins = np.linspace(0, xmax, 61)

    plt.figure(figsize=(9.5, 6.5))

    # ---- Background: sum all three configured files ----
    bkg_m_list, bkg_w_list = [], []
    for f in BACKGROUND_FILES:
        m, w, col = read_dijet_mass(f, label=os.path.basename(os.path.dirname(f)) + "/" + os.path.basename(f))
        if m is not None:
            bkg_m_list.append(m)
            bkg_w_list.append(w)
    if bkg_m_list:
        bkg_m = np.concatenate(bkg_m_list)
        bkg_w = np.concatenate(bkg_w_list)
        plt.hist(bkg_m, bins=bins, weights=bkg_w, density=True, histtype="stepfilled",
                 alpha=0.25, color="black", label="Background (GGJets+DDQCDGJet)")
        plt.hist(bkg_m, bins=bins, weights=bkg_w, density=True, histtype="step",
                 lw=2.2, color="black")
    else:
        print("[WARN] No background files could be read -- proceeding with signal only.")

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

    plt.xlabel(r"Dijet mass $m_{b\bar{b}}$ [GeV]")
    plt.ylabel("Unit normalized")
    plt.title(f"Dijet mass: signal (X{args.mx}) vs. background")
    plt.legend(fontsize=7, ncol=2)
    plt.tight_layout()

    outpath = os.path.join(OUT_DIR, f"dijet_mass_turnon_with_bkg_X{args.mx}.png")
    plt.savefig(outpath, dpi=200)
    plt.savefig(outpath.replace(".png", ".pdf"))
    print(f"[SAVED] {outpath} (+ .pdf)")


if __name__ == "__main__":
    main()