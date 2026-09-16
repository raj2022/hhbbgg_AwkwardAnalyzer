#!/usr/bin/env python3
# =============================================================================
# bumphunt_dijet_mass_Z.py
#
# Proper test of whether the 2022 data dijet mass spectrum shows a
# statistically significant excess near m_Z (91.2 GeV), rather than just
# comparing global peak positions (which can't detect a smaller localized
# bump sitting on a larger, differently-peaked background).
#
# Method: fit a smooth background function to the SIDEBANDS (excluding a
# window around m_Z), then evaluate that fit INSIDE the excluded window
# and compute the (data - fit) pull in each bin there. A real resonance
# shows up as a run of positive pulls concentrated in the excluded window;
# pure background fluctuation should look statistically unremarkable.
#
# Usage:
#   python3 bumphunt_dijet_mass_Z.py --eras E F G --blind-lo 80 --blind-hi 100
# =============================================================================

import os
import argparse
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep

hep.style.use("CMS")

DATA_BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored"
DATA_FILE_TPL = "Data{era}_2022_NOTAG_merged.parquet"

OUT_DIR = "bumphunt_plots"
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
        return None, None
    schema_names = pq.read_schema(path).names
    mass_col = pick_column(schema_names, DIJET_MASS_CANDIDATES)
    if mass_col is None:
        print(f"[WARN] {path}: no matching dijet mass column found")
        return None, None
    cols = [mass_col] + (["weight"] if "weight" in schema_names else [])
    df = pd.read_parquet(path, columns=cols)
    m = df[mass_col].to_numpy(dtype=float)
    w = df["weight"].to_numpy(dtype=float) if "weight" in df.columns else np.ones(len(df))
    good = (m > SENTINEL_THRESHOLD) & np.isfinite(m) & np.isfinite(w)
    print(f"[INFO] {label}: mass_col={mass_col}, n_valid={int(good.sum())}")
    return m[good], w[good]


def double_crystal_ball(x, amp, mean, sigma, aL, nL, aR, nR):
    """Double-sided Crystal Ball: Gaussian core with independent power-law
    tails on the left and right. Standard CMS mass-peak parameterization,
    used here to fit the data's broad rise-then-fall shape directly --
    giving independent tail behavior on each side (unlike the single
    x^b*exp(-c*x-d*x^2) form, which still showed a residual wave pattern
    across the full range) rather than the resonance-peak use this
    function is more commonly known for."""
    x = np.asarray(x, dtype=float)
    aL = max(abs(aL), 1e-3)
    aR = max(abs(aR), 1e-3)
    nL = max(nL, 1e-3)
    nR = max(nR, 1e-3)
    t = (x - mean) / sigma

    A_L = (nL / aL) ** nL * np.exp(-0.5 * aL ** 2)
    B_L = nL / aL - aL
    A_R = (nR / aR) ** nR * np.exp(-0.5 * aR ** 2)
    B_R = nR / aR - aR

    core = np.exp(-0.5 * t ** 2)
    left_tail = A_L * np.power(np.clip(B_L - t, 1e-6, None), -nL)
    right_tail = A_R * np.power(np.clip(B_R + t, 1e-6, None), -nR)

    result = np.where(t < -aL, left_tail, np.where(t > aR, right_tail, core))
    return amp * result


bkg_model = double_crystal_ball


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eras", type=str, nargs="+", default=["E", "F", "G"])
    ap.add_argument("--xmin", type=float, default=20.0)
    ap.add_argument("--xmax", type=float, default=220.0)
    ap.add_argument("--fit-xmin", type=float, default=None,
                     help="Lower edge of the region actually used in the background fit "
                          "(default: same as --xmin). Set higher than --xmin to exclude "
                          "a low-mass turn-on region from the fit while still plotting it.")
    ap.add_argument("--nbins", type=int, default=50)
    ap.add_argument("--blind-lo", type=float, default=80.0,
                     help="Lower edge of the window excluded from the background fit (GeV)")
    ap.add_argument("--blind-hi", type=float, default=100.0,
                     help="Upper edge of the window excluded from the background fit (GeV)")
    args = ap.parse_args()

    # ---- Load and combine data eras ----
    m_list, w_list = [], []
    for era in args.eras:
        path = os.path.join(DATA_BASE_DIR, DATA_FILE_TPL.format(era=era))
        m, w = read_dijet_mass(path, label=f"Data{era}")
        if m is not None:
            m_list.append(m)
            w_list.append(w)
    if not m_list:
        raise RuntimeError("No data could be read.")
    m_all = np.concatenate(m_list)
    w_all = np.concatenate(w_list)

    # ---- Histogram (raw counts + weighted counts + Poisson-like errors) ----
    bins = np.linspace(args.xmin, args.xmax, args.nbins + 1)
    centers = 0.5 * (bins[:-1] + bins[1:])
    counts, _ = np.histogram(m_all, bins=bins, weights=w_all)
    counts_raw, _ = np.histogram(m_all, bins=bins)  # for a simple sqrt(N) error proxy
    errors = np.sqrt(np.maximum(counts_raw, 1)) * (counts / np.maximum(counts_raw, 1))
    errors = np.where(errors == 0, 1.0, errors)

    # ---- Sideband mask (fit region = everywhere EXCEPT the blinded window,
    # AND excluding any low-mass turn-on region below --fit-xmin) ----
    fit_xmin = args.fit_xmin if args.fit_xmin is not None else args.xmin
    sideband_mask = (centers >= fit_xmin) & ((centers < args.blind_lo) | (centers > args.blind_hi))
    blind_mask = (centers >= args.blind_lo) & (centers <= args.blind_hi)

    # ---- Fit smooth background to sidebands only ----
    # Initial guess: mean/sigma seeded from the data's rough peak (~65 GeV)
    # and width; aL/aR/nL/nR start at generic "moderate power-law tail"
    # values and let the fit find the actual left/right asymmetry.
    peak_bin = centers[np.argmax(counts)]
    p0 = [counts.max(), peak_bin, 25.0, 1.5, 2.0, 1.5, 2.0]
    #      amp,          mean,     sigma, aL,  nL,  aR,  nR
    bounds = (
        [0,        args.xmin, 3.0,  0.1, 0.1, 0.1, 0.1],
        [np.inf,   args.xmax, 100.0, 10.0, 50.0, 10.0, 500.0],
    )
    popt, pcov = curve_fit(
        bkg_model, centers[sideband_mask], counts[sideband_mask],
        sigma=errors[sideband_mask], p0=p0, bounds=bounds, maxfev=80000,
    )
    fit_curve = bkg_model(centers, *popt)

    chi2_sideband = np.sum(((counts[sideband_mask] - fit_curve[sideband_mask]) / errors[sideband_mask]) ** 2)
    ndof_sideband = int(sideband_mask.sum()) - len(popt)
    print(f"[FIT] Sideband chi2/ndof = {chi2_sideband:.1f} / {ndof_sideband} = "
          f"{chi2_sideband/max(ndof_sideband,1):.2f}")

    # ---- Residuals / pulls everywhere, and specifically in the blinded window ----
    pulls = (counts - fit_curve) / errors
    blind_pulls = pulls[blind_mask]
    excess_sum = np.sum((counts - fit_curve)[blind_mask])
    excess_significance_naive = np.sum((counts - fit_curve)[blind_mask]) / np.sqrt(np.sum(errors[blind_mask] ** 2))

    print(f"\n[FIT] Background model: double-sided Crystal Ball")
    print(f"[FIT] amp={popt[0]:.1f}, mean={popt[1]:.2f} GeV, sigma={popt[2]:.2f} GeV, "
          f"aL={popt[3]:.2f}, nL={popt[4]:.2f}, aR={popt[5]:.2f}, nR={popt[6]:.2f}")
    fine_grid = np.linspace(args.xmin, args.xmax, 2000)
    fit_peak_x = fine_grid[np.argmax(bkg_model(fine_grid, *popt))]
    print(f"[FIT] Implied peak location (numeric) = {fit_peak_x:.1f} GeV")
    print(f"[FIT] Sideband fit range: [{fit_xmin},{args.blind_lo}) U ({args.blind_hi},{args.xmax}] GeV")
    print(f"[BLIND WINDOW] [{args.blind_lo},{args.blind_hi}] GeV")
    print(f"[BLIND WINDOW] bin-by-bin pulls: {np.round(blind_pulls, 2).tolist()}")
    print(f"[BLIND WINDOW] total (data - fit) excess = {excess_sum:.2f} events (weighted)")
    print(f"[BLIND WINDOW] naive combined significance (sum-excess / sqrt(sum-var)) = "
          f"{excess_significance_naive:.2f} sigma")
    print("[NOTE] This naive significance is a quick diagnostic, not a rigorous "
          "look-elsewhere-corrected significance -- treat as indicative, not a final result.")

    # ---- Plot: CMS-style data + fit + residuals ----
    fig, (ax0, ax1) = plt.subplots(
        2, 1, figsize=(10, 10), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05},
    )

    ax0.errorbar(centers, counts, yerr=errors, fmt="o", ms=4, color="black",
                 elinewidth=1.2, capsize=0,
                 label=f"Data (2022 postEE, Run {'+'.join(args.eras)})")
    ax0.plot(centers, fit_curve, color="#E42536", lw=2.2,
             label="Background fit (sidebands)")
    ax0.axvspan(args.blind_lo, args.blind_hi, color="0.85", alpha=0.6, zorder=0,
                label=r"Excluded window ($Z\to b\bar{b}$ test)")
    if fit_xmin > args.xmin:
        ax0.axvspan(args.xmin, fit_xmin, color="#F4A825", alpha=0.20, zorder=0,
                    label="Excluded from fit (turn-on)")
    ax0.axvline(91.2, color="#5790FC", linestyle="--", lw=1.6, alpha=0.9, label=r"$m_Z$ = 91.2 GeV")

    ax0.set_ylabel("Events")
    ax0.set_ylim(bottom=0)
    ax0.legend(loc="center right", fontsize=15, frameon=False,
               bbox_to_anchor=(0.98, 0.62))

    # fit-quality / result annotation box, CMS-plot convention (upper-left, in-axes text)
    info_text = (
        rf"$\chi^2$/ndof = {chi2_sideband:.1f}/{ndof_sideband} = {chi2_sideband/max(ndof_sideband,1):.2f}"
        "\n"
        rf"Excess in window $\approx$ {excess_sum:.0f} events"
        "\n"
        rf"Naive significance $\approx$ {excess_significance_naive:.1f}$\sigma$"
    )
    ax0.text(0.03, 0.55, info_text, transform=ax0.transAxes, fontsize=13,
             va="top", ha="left",
             bbox=dict(boxstyle="round", facecolor="white", edgecolor="0.6", alpha=0.92))

    hep.cms.label("Preliminary", ax=ax0, data=True, lumi=None, com=13.6, loc=0)

    ax1.axhline(0, color="gray", lw=1)
    ax1.bar(centers, pulls, width=(bins[1] - bins[0]) * 0.9,
            color=["#9C9C9C" if s else "#E42536" for s in sideband_mask],
            edgecolor="none")
    ax1.axvspan(args.blind_lo, args.blind_hi, color="0.85", alpha=0.6, zorder=0)
    if fit_xmin > args.xmin:
        ax1.axvspan(args.xmin, fit_xmin, color="#F4A825", alpha=0.20, zorder=0)
    ax1.axvline(91.2, color="#5790FC", linestyle="--", lw=1.6, alpha=0.9)
    ax1.set_ylabel(r"$\frac{\mathrm{Data-Fit}}{\sigma}$", fontsize=20)
    ax1.set_xlabel(r"Dijet mass $m_{b\bar{b}}$ [GeV]")
    ax1.set_xlim(args.xmin, args.xmax)

    outpath = os.path.join(OUT_DIR, "bumphunt_dijet_mass_Z.png")
    plt.savefig(outpath, dpi=300, bbox_inches="tight")
    plt.savefig(outpath.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"\n[SAVED] {outpath} (+ .pdf)")


if __name__ == "__main__":
    main()