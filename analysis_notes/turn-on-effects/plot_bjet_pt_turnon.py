#!/usr/bin/env python3
# =============================================================================
# plot_bjet_pt_turnon.py
#
# b-jet pT turn-on check: overlays lead_bjet_pt / sublead_bjet_pt
# distributions across a range of mY points at fixed mX, since Y->bb means
# the *b-jets*, not the photons, are the ones expected to feel a kinematic
# squeeze as mY shrinks (unlike the photon pT, which showed no mY-dependent
# turn-on in the earlier check).
#
# Branch-naming fallback: some files were found to carry only nonRes_*
# columns (no Res_* at all) at low mY, while others may carry Res_*. This
# script tries a priority-ordered list of candidate column names per file
# and PRINTS which one was actually used -- if the resonant ("Res_")
# branch disappears specifically at low mY, this will show up directly as
# a changing "column used" value across the mY scan, which is itself
# diagnostic of the turn-on (a reconstruction-level effect), separate from
# whatever the pT shape itself shows.
#
# Usage:
#   python3 plot_bjet_pt_turnon.py --mx 300 --my 50 60 70 80 90 95 100 150
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

OUT_DIR = "bjet_pt_turnon_plots"
os.makedirs(OUT_DIR, exist_ok=True)

SENTINEL_THRESHOLD = -900.0

# Priority-ordered candidate column names for lead/sublead b-jet pT.
LEAD_BJET_PT_CANDIDATES = [
    "Res_lead_bjet_pt", "nonRes_lead_bjet_pt", "nonResReg_lead_bjet_pt",
    "nonResReg_DNNpair_lead_bjet_pt", "nonResReg_vbfpair_lead_bjet_pt",
]
SUBLEAD_BJET_PT_CANDIDATES = [
    "Res_sublead_bjet_pt", "nonRes_sublead_bjet_pt", "nonResReg_sublead_bjet_pt",
    "nonResReg_DNNpair_sublead_bjet_pt", "nonResReg_vbfpair_sublead_bjet_pt",
]


def pick_column(schema_names, candidates):
    for c in candidates:
        if c in schema_names:
            return c
    return None


def read_bjet_pts(path):
    if not os.path.exists(path):
        print(f"[WARN] missing: {path}")
        return None, None, None
    try:
        schema_names = pq.read_schema(path).names
    except Exception as e:
        print(f"[WARN] schema read fail {path}: {e}")
        return None, None, None

    lead_col = pick_column(schema_names, LEAD_BJET_PT_CANDIDATES)
    sub_col = pick_column(schema_names, SUBLEAD_BJET_PT_CANDIDATES)
    if lead_col is None or sub_col is None:
        print(f"[WARN] {path}: no matching lead/sublead b-jet pT column found "
              f"(lead={lead_col}, sublead={sub_col})")
        return None, None, None

    cols = [lead_col, sub_col]
    if "weight" in schema_names:
        cols.append("weight")
    df = pd.read_parquet(path, columns=cols)

    lead = df[lead_col].to_numpy(dtype=float)
    sub = df[sub_col].to_numpy(dtype=float)
    w = df["weight"].to_numpy(dtype=float) if "weight" in df.columns else np.ones(len(df))

    # sentinel cleanup: drop events where either b-jet failed reconstruction
    good = (lead > SENTINEL_THRESHOLD) & (sub > SENTINEL_THRESHOLD) & np.isfinite(w)
    n_total, n_good = len(df), int(good.sum())
    print(f"[INFO] {os.path.basename(os.path.dirname(os.path.dirname(path)))}: "
          f"lead_col={lead_col}, sub_col={sub_col}, "
          f"n_total={n_total}, n_valid={n_good} ({100*n_good/max(n_total,1):.1f}%)")

    return lead[good], sub[good], w[good]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mx", type=int, required=True)
    ap.add_argument("--my", type=int, nargs="+", required=True)
    args = ap.parse_args()

    cmap = plt.get_cmap("viridis")
    n = len(args.my)
    bins = np.linspace(0, 250, 51)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    for i, my in enumerate(sorted(args.my)):
        path = SIG_TPL.format(m=args.mx, y=my)
        lead, sub, w = read_bjet_pts(path)
        if lead is None:
            continue
        color = cmap(i / max(n - 1, 1))
        axes[0].hist(lead, bins=bins, weights=w, density=True,
                     histtype="step", lw=1.6, color=color, label=f"Y{my}")
        axes[1].hist(sub, bins=bins, weights=w, density=True,
                     histtype="step", lw=1.6, color=color, label=f"Y{my}")

    axes[0].set_xlabel("Leading b-jet $p_T$ [GeV]")
    axes[0].set_ylabel("Unit normalized")
    axes[0].set_title(f"Lead b-jet $p_T$, X{args.mx}")
    axes[0].legend(fontsize=7, ncol=2)

    axes[1].set_xlabel("Subleading b-jet $p_T$ [GeV]")
    axes[1].set_title(f"Sublead b-jet $p_T$, X{args.mx}")
    axes[1].legend(fontsize=7, ncol=2)

    plt.tight_layout()
    outpath = os.path.join(OUT_DIR, f"bjet_pt_turnon_X{args.mx}.png")
    plt.savefig(outpath, dpi=200)
    plt.savefig(outpath.replace(".png", ".pdf"))
    print(f"[SAVED] {outpath} (+ .pdf)")


if __name__ == "__main__":
    main()