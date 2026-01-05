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
# Gaussian models
# -----------------------
def gauss(x, mu, sigma, norm):
    return norm * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def double_gauss(x, mu, sigma1, sigma2, f, norm):
    return norm * (
        f * np.exp(-0.5 * ((x - mu) / sigma1) ** 2)
        + (1.0 - f) * np.exp(-0.5 * ((x - mu) / sigma2) ** 2)
    )


# -----------------------
# Main
# -----------------------
def main():
    ap = argparse.ArgumentParser(description="Plot and fit signal mgg with Gaussians")
    ap.add_argument("--root", required=True)
    ap.add_argument("--signal-dir", required=True)
    ap.add_argument("--score-lo", type=float, default=None)
    ap.add_argument("--score-hi", type=float, default=None)
    ap.add_argument("--mgg-min", type=float, default=115.0)
    ap.add_argument("--mgg-max", type=float, default=135.0)
    ap.add_argument("--bins", type=int, default=40)
    ap.add_argument("--out", default="signal_mgg_fit.png")
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
    # Mass window for fit
    # -----------------------
    fit_mask = (mgg >= args.mgg_min) & (mgg <= args.mgg_max)
    mgg_fit = mgg[fit_mask]

    print(f"[info] Events used in fit: {len(mgg_fit)}")

    # -----------------------
    # Histogram
    # -----------------------
    counts, edges = np.histogram(
        mgg_fit, bins=args.bins, range=(args.mgg_min, args.mgg_max)
    )
    centers = 0.5 * (edges[:-1] + edges[1:])
    errors = np.sqrt(np.maximum(counts, 1.0))
    binw = edges[1] - edges[0]

    # -----------------------
    # Single Gaussian fit
    # -----------------------
    p0_1g = [125.0, 1.5, counts.sum() * binw]
    popt_1g, _ = curve_fit(
        gauss, centers, counts, p0=p0_1g, sigma=errors, absolute_sigma=True
    )

    mu_1g, sigma_1g, _ = popt_1g

    # -----------------------
    # Double Gaussian fit
    # -----------------------
    p0_2g = [mu_1g, 1.0, 2.5, 0.7, counts.sum() * binw]
    bounds = (
        [120, 0.1, 0.1, 0.0, 0.0],
        [130, 5.0, 10.0, 1.0, np.inf],
    )

    popt_2g, _ = curve_fit(
        double_gauss,
        centers,
        counts,
        p0=p0_2g,
        bounds=bounds,
        sigma=errors,
        absolute_sigma=True,
    )

    mu, s1, s2, f, _ = popt_2g
    sigma_eff = np.sqrt(f * s1**2 + (1.0 - f) * s2**2)

    # -----------------------
    # Plot
    # -----------------------
    xplot = np.linspace(args.mgg_min, args.mgg_max, 1000)

    plt.figure(figsize=(7, 5))
    plt.errorbar(centers, counts, yerr=errors, fmt="o", ms=4, label="Simulation")

    plt.plot(
        xplot,
        gauss(xplot, *popt_1g),
        lw=2,
        label=rf"1G: $\mu={mu_1g:.2f}$, $\sigma={sigma_1g:.2f}$ GeV",
    )

    plt.plot(
        xplot,
        double_gauss(xplot, *popt_2g),
        lw=2,
        label=rf"2G: $\mu={mu:.2f}$, $\sigma_\mathrm{{eff}}={sigma_eff:.2f}$ GeV",
    )

    plt.xlabel(r"$m_{\gamma\gamma}$ [GeV]")
    plt.ylabel("Events / bin")
    plt.title("Signal $m_{\gamma\gamma}$")
    plt.legend(frameon=False)
    plt.grid(alpha=0.2)

    plt.tight_layout()
    plt.savefig(args.out, dpi=150)
    plt.close()

    print("\n[results]")
    print(f"  1G: mu = {mu_1g:.3f}, sigma = {sigma_1g:.3f}")
    print(f"  2G: mu = {mu:.3f}, sigma_eff = {sigma_eff:.3f}")
    print(f"[saved] {args.out}")


if __name__ == "__main__":
    main()



# python plot_and_fit_signal.py \
#   --root ../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root \
#   --signal-dir NMSSM_X700_Y70 \
#   --score-lo 0.65 \
#   --score-hi 0.75 \
#   --out mgg_fit_NMSSM_X700_Y70_cat1.png
