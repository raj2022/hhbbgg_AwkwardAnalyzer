#!/usr/bin/env python3
# =============================================================================
# plot_photon_pt_turnon.py
#
# Photon pT turn-on check: overlays lead_pt / sublead_pt distributions
# across a range of mY points at fixed mX, to visualize where photon pT
# spectra start piling up against (or falling below) the analysis's
# effective pT threshold as mY decreases.
#
# Also overlays the nominal weight vs. weight_TriggerSFUp/Down variation
# for the lowest-mY point shown, as a quick visual on how much the
# trigger-SF systematic grows near the turn-on region.
#
# CMS-style plotting (mplhep), and lead/sublead saved as SEPARATE files
# (rather than one combined two-panel figure), matching the AN's
# individual \includegraphics placeholders for each.
#
# Usage:
#   python3 plot_photon_pt_turnon.py --mx 600 --my 50 60 70 80 90 95 100 150
# =============================================================================

import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
    "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)

OUT_DIR = "photon_pt_turnon_plots"
os.makedirs(OUT_DIR, exist_ok=True)

# CMS-recommended qualitative palette (Petroff scheme), cycled across mY points
CMS_COLORS = [
    "#5790FC", "#F89C20", "#E42536", "#964A8B", "#9C9CA1",
    "#7A21DD", "#008000", "#B8860B", "#00B2EE", "#DA70D6",
]


def read_pt(path, cols):
    if not os.path.exists(path):
        print(f"[WARN] missing: {path}")
        return None
    try:
        df = pd.read_parquet(path, columns=cols)
    except Exception as e:
        print(f"[WARN] read fail {path}: {e}")
        return None
    return df


def make_single_pt_plot(args, var_col, xlabel, out_name, bins):
    """Build one CMS-style unit-normalized pT overlay plot for a single
    variable (lead_pt or sublead_pt) across all requested mY points,
    saved as its own standalone file."""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    n = len(args.my)

    for i, my in enumerate(sorted(args.my)):
        path = SIG_TPL.format(m=args.mx, y=my)
        df = read_pt(path, [var_col, "weight"])
        if df is None:
            continue
        w = df["weight"].to_numpy(dtype=float) if "weight" in df.columns else None
        color = CMS_COLORS[i % len(CMS_COLORS)]
        ax.hist(df[var_col], bins=bins, weights=w, density=True,
                histtype="step", lw=2.2, color=color, label=f"$m_Y={my}$ GeV")
        print(f"[INFO] X{args.mx}_Y{my} ({var_col}): {len(df)} events")

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Events (unit normalized)")
    ax.legend(fontsize=15, ncol=2, frameon=False, loc="upper right")

    hep.cms.label("Work in progress", ax=ax, data=True, com=13.6, loc=0, fontsize=20)

    outpath = os.path.join(OUT_DIR, out_name)
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.savefig(outpath.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"[SAVED] {outpath} (+ .pdf)")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mx", type=int, required=True)
    ap.add_argument("--my", type=int, nargs="+", required=True,
                     help="List of mY points to overlay, e.g. --my 50 60 70 80 90 95 100 150")
    args = ap.parse_args()

    bins = np.linspace(0, 200, 51)

    # ---- Two SEPARATE standalone plots: lead and sublead photon pT ----
    make_single_pt_plot(
        args, "lead_pt", r"Leading photon $p_T$ [GeV]",
        f"photon_pt_turnon_lead_X{args.mx}.png", bins,
    )
    make_single_pt_plot(
        args, "sublead_pt", r"Subleading photon $p_T$ [GeV]",
        f"photon_pt_turnon_sublead_X{args.mx}.png", bins,
    )

    # ---- Trigger SF variation, lowest mY point (CMS style) ----
    my_lowest = min(args.my)
    path = SIG_TPL.format(m=args.mx, y=my_lowest)
    df = read_pt(path, ["lead_pt", "weight", "weight_TriggerSFUp", "weight_TriggerSFDown"])
    if df is not None and {"weight_TriggerSFUp", "weight_TriggerSFDown"}.issubset(df.columns):
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.hist(df["lead_pt"], bins=bins, weights=df["weight"], density=True,
                histtype="step", lw=2.4, color="black", label="Nominal")
        ax.hist(df["lead_pt"], bins=bins, weights=df["weight_TriggerSFUp"], density=True,
                histtype="step", lw=1.8, color="#E42536", linestyle="--", label="Trigger SF up")
        ax.hist(df["lead_pt"], bins=bins, weights=df["weight_TriggerSFDown"], density=True,
                histtype="step", lw=1.8, color="#5790FC", linestyle="--", label="Trigger SF down")
        ax.set_xlabel("Leading photon $p_T$ [GeV]")
        ax.set_ylabel("Events (unit normalized)")
        ax.legend(fontsize=16, frameon=False, loc="upper right")
        ax.text(0.03, 0.95, rf"$m_X={args.mx}$ GeV, $m_Y={my_lowest}$ GeV",
                transform=ax.transAxes, fontsize=15, va="top", ha="left")

        hep.cms.label("Work in progress", ax=ax, data=True, com=13.6, loc=0, fontsize=20)

        outpath2 = os.path.join(OUT_DIR, f"trigger_sf_variation_X{args.mx}_Y{my_lowest}.png")
        plt.savefig(outpath2, dpi=300, bbox_inches="tight")
        plt.savefig(outpath2.replace(".png", ".pdf"), bbox_inches="tight")
        print(f"[SAVED] {outpath2} (+ .pdf)")
        plt.close(fig)
    else:
        print(f"[WARN] Could not build trigger-SF variation plot for X{args.mx}_Y{my_lowest} "
              f"(missing columns or file).")


if __name__ == "__main__":
    main()