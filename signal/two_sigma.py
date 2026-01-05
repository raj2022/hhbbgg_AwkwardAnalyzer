# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """Two Sigma implementation of the Signal samples after fitting and applying cuts on each samples."""
# """Need to be done individually for each sample from each eras since the cuts are different."""

# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import argparse
# import uproot
# import awkward as ak
# import numpy as np

# TREE_NAME = "selection"
# BR_MGG    = "diphoton_mass"
# BR_SCORE  = "pDNN_score"
# BR_ISDATA = "isdata"


# def main():
#     ap = argparse.ArgumentParser(description="Minimal ROOT reader for one signal sample")
#     ap.add_argument(
#         "--root",
#         required=True,
#         help="Merged ROOT file path"
#     )
#     ap.add_argument(
#         "--signal-dir",
#         required=True,
#         help="Exact directory name of the signal sample (e.g. nmssm_X1000_Y125)"
#     )
#     args = ap.parse_args()

#     # -------------------------------
#     # Open ROOT file
#     # -------------------------------
#     print(f"[info] Opening ROOT file:\n  {args.root}")
#     fin = uproot.open(args.root)

#     # -------------------------------
#     # Check signal directory
#     # -------------------------------
#     if args.signal_dir not in fin:
#         print("\n[error] Directory not found!")
#         print("Available directories:")
#         for k in fin.keys():
#             print("  ", k)
#         raise RuntimeError(f"Signal directory '{args.signal_dir}' not found")

#     tdir = fin[args.signal_dir]
#     print(f"\n[info] Using signal directory: {args.signal_dir}")

#     # -------------------------------
#     # Check tree
#     # -------------------------------
#     if TREE_NAME not in tdir:
#         print("\n[error] Tree not found in directory")
#         print("Available keys:")
#         for k in tdir.keys():
#             print("  ", k)
#         raise RuntimeError(f"Tree '{TREE_NAME}' not found")

#     tree = tdir[TREE_NAME]
#     print(f"[info] Found tree '{TREE_NAME}'")

#     # -------------------------------
#     # Check branches
#     # -------------------------------
#     branches = tree.keys()
#     print("\n[info] Available branches:")
#     for b in branches:
#         print("  ", b)

#     for br in [BR_MGG, BR_SCORE, BR_ISDATA]:
#         if br not in branches:
#             raise RuntimeError(f"Required branch '{br}' not found")

#     # -------------------------------
#     # Read arrays
#     # -------------------------------
#     arr = tree.arrays(
#         [BR_MGG, BR_SCORE, BR_ISDATA],
#         library="ak"
#     )

#     mgg   = arr[BR_MGG]
#     score = arr[BR_SCORE]
#     isdata = arr[BR_ISDATA]

#     #-------------------------------
#     # MC only selection
#     mc_mask = (isdata == 0)

#     mgg_mc   = mgg[mc_mask]
#     score_mc = score[mc_mask]

#     print(f"\n[info] MC-only events: {len(mgg_mc)}")

    
    
#     # -------------------------------
#     # Basic sanity checks
#     # -------------------------------
#     n_tot = len(mgg)
#     n_mc  = ak.sum(isdata == 0)
#     n_dt  = ak.sum(isdata == 1)

#     print("\n[info] Event counts:")
#     print(f"  Total events : {n_tot}")
#     print(f"  MC events    : {n_mc}")
#     print(f"  Data events  : {n_dt}")

#     print("\n[info] diphoton_mass:")
#     print(f"  min / max : {ak.min(mgg):.2f} / {ak.max(mgg):.2f}")
#     print(f"  mean      : {ak.mean(mgg):.2f}")

#     print("\n[info] pDNN_score:")
#     print(f"  min / max : {ak.min(score):.3f} / {ak.max(score):.3f}")

#     print("\n[success] ROOT file read successfully.")


# if __name__ == "__main__":
#     main()




# # To run:
# # python two_sigma.py --root ../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root   --signal-dir NMSSM_X700_Y70



#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

TREE_NAME = "selection"
BR_MGG    = "diphoton_mass"
BR_SCORE  = "pDNN_score"
BR_ISDATA = "isdata"


# -----------------------
# Single Gaussian model
# -----------------------
def gauss(x, mu, sigma, norm):
    return norm * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def main():
    ap = argparse.ArgumentParser(description="Single-Gaussian fit and ±1σ/±2σ lines")
    ap.add_argument("--root", required=True)
    ap.add_argument("--signal-dir", required=True)
    ap.add_argument("--score-lo", type=float, default=None)
    ap.add_argument("--score-hi", type=float, default=None)
    ap.add_argument("--mgg-min", type=float, default=115.0)
    ap.add_argument("--mgg-max", type=float, default=135.0)
    ap.add_argument("--bins", type=int, default=40)
    ap.add_argument("--out", default="mgg_single_gauss.png")
    args = ap.parse_args()

    # -----------------------
    # Read ROOT
    # -----------------------
    fin = uproot.open(args.root)
    tree = fin[args.signal_dir][TREE_NAME]

    arr = tree.arrays([BR_MGG, BR_SCORE, BR_ISDATA], library="ak")

    mgg   = arr[BR_MGG]
    score = arr[BR_SCORE]
    isdata = arr[BR_ISDATA]

    # MC only
    mc_mask = (isdata == 0)
    mgg = mgg[mc_mask]
    score = score[mc_mask]

    # Optional pDNN category
    if args.score_lo is not None and args.score_hi is not None:
        cat_mask = (score >= args.score_lo) & (score < args.score_hi)
        mgg = mgg[cat_mask]
        print(f"[info] pDNN category [{args.score_lo}, {args.score_hi})")

    mgg = ak.to_numpy(mgg)

    # -----------------------
    # Fit window
    # -----------------------
    fit_mask = (mgg >= args.mgg_min) & (mgg <= args.mgg_max)
    mgg_fit = mgg[fit_mask]

    print(f"[info] Events used in fit: {len(mgg_fit)}")

    # -----------------------
    # Histogram
    # -----------------------
    counts, edges = np.histogram(
        mgg_fit,
        bins=args.bins,
        range=(args.mgg_min, args.mgg_max),
    )
    centers = 0.5 * (edges[:-1] + edges[1:])
    errors = np.sqrt(np.maximum(counts, 1.0))
    binw = edges[1] - edges[0]

    # -----------------------
    # Single Gaussian fit
    # -----------------------
    p0 = [125.0, 1.5, counts.sum() * binw]

    popt, pcov = curve_fit(
        gauss,
        centers,
        counts,
        p0=p0,
        sigma=errors,
        absolute_sigma=True,
    )

    mu, sigma, norm = popt
    mu_err, sigma_err, _ = np.sqrt(np.diag(pcov))

    m1_lo = mu - sigma
    m1_hi = mu + sigma
    m2_lo = mu - 2.0 * sigma
    m2_hi = mu + 2.0 * sigma


    print("\n[fit results]")
    print(f"  mu    = {mu:.3f} ± {mu_err:.3f} GeV")
    print(f"  sigma = {sigma:.3f} ± {sigma_err:.3f} GeV")

    # -----------------------
    # Plot
    # -----------------------
    xplot = np.linspace(args.mgg_min, args.mgg_max, 1000)

    plt.figure(figsize=(7, 5))
    plt.errorbar(
        centers, counts, yerr=errors,
        fmt="o", ms=4, label="Simulation"
    )

    plt.plot(
        xplot,
        gauss(xplot, *popt),
        lw=2,
        label=rf"Gaussian fit ($\mu={mu:.2f}$, $\sigma={sigma:.2f}$ GeV)",
    )

    # ±1σ lines
    plt.axvline(mu - sigma, color="green", ls="--", lw=1.5, label=r"$\mu \pm 1\sigma$")
    plt.axvline(mu + sigma, color="green", ls="--", lw=1.5)

    # ±2σ lines
    plt.axvline(mu - 2*sigma, color="red", ls=":", lw=1.8, label=r"$\mu \pm 2\sigma$")
    plt.axvline(mu + 2*sigma, color="red", ls=":", lw=1.8)

    plt.xlabel(r"$m_{\gamma\gamma}$ [GeV]")
    plt.ylabel("Events / bin")
    plt.title("Signal $m_{\gamma\gamma}$ (Single Gaussian)")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    plt.close()

    print(f"[saved] {args.out}")


if __name__ == "__main__":
    main()



# python plot_and_fit_signal.py \
#   --root ../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
#   --signal-dir NMSSM_X700_Y70 \
#   --score-lo 0.65 \
#   --score-hi 0.75 \
#   --out mgg_fit_NMSSM_X700_Y70_cat1.png
