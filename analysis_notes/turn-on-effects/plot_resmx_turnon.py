#!/usr/bin/env python3
# =============================================================================
# plot_resmx_turnon.py
#
# Reproduces the Fig. 14-style plot from AN_25_133_v6: unit-normalized
# Res_M_X (reduced four-body mass) distributions for background and a
# handful of signal (mX, mY) hypotheses, illustrating the turn-on
# behavior in the background at low mX.
#
# Config (paths, weight column, mass grid) extracted directly from
# pDNN_v2.py so this matches the same samples used in training/validation.
#
# CMS-style plotting (mplhep), matching the style used throughout the
# rest of this section's figures (photon/bjet pT turn-on, bump-hunt).
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

# --- Paths (from pDNN_v2.py Config) ---
SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
    "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)
BACKGROUND_BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE"
BACKGROUND_FILENAMES = (
    "GGJets_MGG-80/NOTAG_merged.parquet",
    "DDQCCDGJets/DDQCDGJets_Rescaled.parquet",
    "DDQCCDGJets/GGJets_MGG-80_Rescaled.parquet",
)
BACKGROUND_FILES = [os.path.join(BACKGROUND_BASE_DIR, f) for f in BACKGROUND_FILENAMES]

WEIGHT_COL = "weight"
RES_MX_COL = "Res_M_X"
SENTINEL_THRESHOLD = -900.0  # values <= this are failed-reco placeholders, treat as missing

# --- Signal points to overlay (matches AN Fig. 14: Y150 fixed, mX scan) ---
Y_FIXED = 150
X_POINTS = [300, 400, 500, 600, 700, 800, 900, 1000]

OUT_DIR = "resmx_turnon_plots"
os.makedirs(OUT_DIR, exist_ok=True)

# CMS-recommended qualitative palette (Petroff scheme), cycled across mX points
CMS_COLORS = [
    "#5790FC", "#F89C20", "#E42536", "#964A8B", "#9C9CA1",
    "#7A21DD", "#008000", "#B8860B", "#00B2EE", "#DA70D6",
]


def read_resmx(path, weight_col=WEIGHT_COL, mass_col=RES_MX_COL):
    """Read just the columns needed, and clean the sentinel/failed-reco values."""
    if not os.path.exists(path):
        print(f"[WARN] missing: {path}")
        return None, None
    cols = [c for c in (mass_col, weight_col) if c is not None]
    df = pd.read_parquet(path, columns=cols)
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    m = df[mass_col].to_numpy(dtype=float)
    w = df[weight_col].to_numpy(dtype=float)
    # sentinel cleanup: HiggsDNA-stage failed-reco default is ~ -999
    good = (m > SENTINEL_THRESHOLD) & np.isfinite(m) & np.isfinite(w)
    return m[good], w[good]


def main():
    # ---- Background: sum all three configured files ----
    bkg_m_list, bkg_w_list = [], []
    for f in BACKGROUND_FILES:
        m, w = read_resmx(f)
        if m is not None:
            bkg_m_list.append(m)
            bkg_w_list.append(w)
            print(f"[INFO] {f}: {len(m)} events after sentinel cleanup")
    if not bkg_m_list:
        raise RuntimeError("No background files could be read -- check paths/mount.")
    bkg_m = np.concatenate(bkg_m_list)
    bkg_w = np.concatenate(bkg_w_list)

    # ---- Signal: one file per mX at fixed mY ----
    sig_data = {}
    for mx in X_POINTS:
        path = SIG_TPL.format(m=mx, y=Y_FIXED)
        m, w = read_resmx(path)
        if m is not None:
            sig_data[mx] = (m, w)
            print(f"[INFO] X{mx}_Y{Y_FIXED}: {len(m)} events after sentinel cleanup")
        else:
            print(f"[WARN] X{mx}_Y{Y_FIXED}: not found on disk, skipping")

    # ---- Plot: unit-normalized overlay, CMS style ----
    bins = np.linspace(200, 1200, 51)  # match AN Fig. 14 x-range

    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.hist(bkg_m, bins=bins, weights=bkg_w, density=True, histtype="step",
            lw=2.6, color="black", label="Background")

    for i, mx in enumerate(sorted(sig_data.keys())):
        m, w = sig_data[mx]
        color = CMS_COLORS[i % len(CMS_COLORS)]
        ax.hist(m, bins=bins, weights=w, density=True, histtype="step",
                lw=2.0, color=color, label=rf"$m_X={mx}$ GeV")

    ax.set_xlabel(r"Reduced four-body mass $M_X$ [GeV]")
    ax.set_ylabel("Events (unit normalized)")
    ax.text(0.03, 0.95, rf"$X \to YH$, $m_Y = {Y_FIXED}$ GeV",
            transform=ax.transAxes, fontsize=16, va="top", ha="left")
    ax.legend(fontsize=14, ncol=2, frameon=False, loc="upper right")

    hep.cms.label("Work in progress", ax=ax, data=True, com=13.6, loc=0, fontsize=20)

    outpath = os.path.join(OUT_DIR, f"resmx_turnon_Y{Y_FIXED}.png")
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.savefig(outpath.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"[SAVED] {outpath} (+ .pdf)")


if __name__ == "__main__":
    main()