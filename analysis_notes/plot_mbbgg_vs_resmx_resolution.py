#!/usr/bin/env python3
"""
Compare the raw four-body mass (Res_HHbbggCandidate_mass) vs the
corrected Res_M_X distributions and resolutions, for a few
representative mX values with multiple mY curves overlaid, quantifying
resolution via a Double-Sided Crystal Ball (DSCB) fit sigma.

Reads directly from HiggsDNA's parquet output (pre-analyzer stage),
2022 postEE only, as a representative single era.

Run inside an environment with pandas/pyarrow available (try
`micromamba activate hhbbgg-awk` first; if pyarrow is missing there,
`micromamba activate higgs-dna` or `pip install pyarrow --break-system-packages`):
    python3 plot_resmx_resolution_parquet.py

Outputs:
    resmx_resolution_mX{value}.png   (one figure per representative mX)
    resolution_comparison_parquet.csv
"""

import glob
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

try:
    import mplhep as hep
    hep.style.use("CMS")
    HAVE_MPLHEP = True
except ImportError:
    HAVE_MPLHEP = False

BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged"
PATH_TEMPLATE = os.path.join(BASE_DIR, "NMSSM_X{mx}_Y{my}", "nominal", "NOTAG_merged.parquet")

COL_RAW_MASS = "Res_HHbbggCandidate_mass"
COL_RESMX = "Res_M_X"
COL_WEIGHT = "weight"

# Sentinel/placeholder cut: HiggsDNA writes an unphysical negative default
# (visibly piled up near -1000 in the raw output) when reconstruction of
# a quantity fails. Any genuine mass is positive, so this is a safe,
# general validity cut rather than a tuned physics selection.
MIN_VALID_MASS = 0.0

# Representative mY subset per mX, to keep the legend readable -- the
# full grid (up to 21 points) is too cluttered for a publication figure.
N_REPRESENTATIVE_MY = 6

REPRESENTATIVE_MX = {
    400: None,
    600: None,
    900: None,
}

# ROOT/CMS-classic bold color cycle (black, red, green, blue, orange,
# magenta, cyan, dark green, ...), matching the style of published
# CMS/ROOT-generated overlay plots -- distinct, high-contrast, no pastels.
ROOT_STYLE_COLORS = ["#000000", "#e41a1c", "#4daf4a", "#377eb8", "#ff7f00",
                      "#984ea3", "#00bcd4", "#1b5e20", "#a65628", "#f781bf"]


def discover_available_mY(mx):
    """Find which mY values actually have a parquet file for this mX,
    by globbing the directory rather than assuming the full nominal grid."""
    pattern = os.path.join(BASE_DIR, f"NMSSM_X{mx}_Y*", "nominal", "NOTAG_merged.parquet")
    files = glob.glob(pattern)
    my_values = []
    for fpath in files:
        m = re.search(rf"NMSSM_X{mx}_Y(\d+)", fpath)
        if m:
            my_values.append(int(m.group(1)))
    return sorted(my_values)


def load_mass_arrays(mx, my):
    path = PATH_TEMPLATE.format(mx=mx, my=my)
    if not os.path.exists(path):
        return None, None, None
    try:
        df = pd.read_parquet(path, columns=[COL_RAW_MASS, COL_RESMX, COL_WEIGHT])
    except Exception as e:
        print(f"    Failed to read {path}: {e}")
        return None, None, None

    raw_mass = df[COL_RAW_MASS].to_numpy()
    resmx = df[COL_RESMX].to_numpy()
    w = df[COL_WEIGHT].to_numpy()

    # drop sentinel/placeholder entries (failed reconstruction defaults)
    valid = (raw_mass > MIN_VALID_MASS) & (resmx > MIN_VALID_MASS) & np.isfinite(w)
    n_dropped = (~valid).sum()
    if n_dropped:
        print(f"    Dropped {n_dropped}/{len(raw_mass)} sentinel/invalid entries "
              f"(mass <= {MIN_VALID_MASS} GeV)")
    return raw_mass[valid], resmx[valid], w[valid]


def pick_representative_mY(my_values, n):
    """Evenly-spaced subset of the available mY grid, always including
    the smallest and largest, to keep the legend readable."""
    if len(my_values) <= n:
        return my_values
    idx = np.linspace(0, len(my_values) - 1, n).round().astype(int)
    idx = sorted(set(idx))
    return [my_values[i] for i in idx]


def weighted_percentile(values, weights, percentiles):
    """Weighted percentile -- tracks where the statistical weight actually
    sits, rather than raw entry counts. Using plain np.percentile on raw
    values lets a handful of low-weight, poorly-reconstructed outlier
    events stretch the axis range out into mostly-empty space."""
    sorter = np.argsort(values)
    values_sorted = values[sorter]
    weights_sorted = weights[sorter]
    cum_weights = np.cumsum(weights_sorted) - 0.5 * weights_sorted
    cum_weights /= np.sum(weights_sorted)
    return np.interp(np.asarray(percentiles) / 100.0, cum_weights, values_sorted)


def dscb(x, mu, sigma, alphaL, nL, alphaR, nR, norm):
    t = (x - mu) / sigma
    result = np.zeros_like(x, dtype=float)

    left_tail = t < -alphaL
    right_tail = t > alphaR
    gauss_region = (~left_tail) & (~right_tail)

    result[gauss_region] = np.exp(-0.5 * t[gauss_region] ** 2)

    AL = (nL / abs(alphaL)) ** nL * np.exp(-0.5 * alphaL ** 2)
    BL = nL / abs(alphaL) - abs(alphaL)
    result[left_tail] = AL * (BL - t[left_tail]) ** (-nL)

    AR = (nR / abs(alphaR)) ** nR * np.exp(-0.5 * alphaR ** 2)
    BR_ = nR / abs(alphaR) - abs(alphaR)
    result[right_tail] = AR * (BR_ + t[right_tail]) ** (-nR)

    return norm * result


def fit_dscb(values, weights, mass_hint):
    finite = np.isfinite(values) & np.isfinite(weights)
    values, weights = values[finite], weights[finite]
    if len(values) < 50:
        return None

    lo, hi = np.percentile(values, [1, 99])
    bins = np.linspace(lo, hi, 80)
    counts, edges = np.histogram(values, bins=bins, weights=weights)
    centers = 0.5 * (edges[:-1] + edges[1:])

    if counts.sum() <= 0:
        return None

    p0 = [mass_hint, max(5.0, 0.05 * mass_hint), 1.5, 5.0, 1.5, 5.0, counts.max()]
    bounds_lo = [mass_hint - 0.3 * mass_hint, 1.0, 0.3, 0.5, 0.3, 0.5, 0.0]
    bounds_hi = [mass_hint + 0.3 * mass_hint, 0.5 * mass_hint, 10.0, 50.0, 10.0, 50.0, np.inf]

    try:
        popt, _ = curve_fit(dscb, centers, counts, p0=p0,
                             bounds=(bounds_lo, bounds_hi), maxfev=20000)
        return popt[1]
    except Exception as e:
        print(f"    DSCB fit failed: {e}")
        return None


def main():
    resolution_rows = []

    for mx, my_subset in REPRESENTATIVE_MX.items():
        all_my = my_subset if my_subset else discover_available_mY(mx)
        if not all_my:
            print(f"mX={mx}: no available parquet files found, skipping.")
            continue
        print(f"mX={mx}: found mY values {all_my}")
        plot_my_values = pick_representative_mY(all_my, N_REPRESENTATIVE_MY)
        print(f"mX={mx}: plotting representative subset {plot_my_values} "
              f"(fits still run on the full set)")

        if HAVE_MPLHEP:
            fig, (ax_raw, ax_resmx) = plt.subplots(1, 2, figsize=(14, 6))
        else:
            fig, (ax_raw, ax_resmx) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

        pooled_raw_vals, pooled_raw_w = [], []
        pooled_resmx_vals, pooled_resmx_w = [], []

        for i, my in enumerate(all_my):
            raw_mass, resmx, w = load_mass_arrays(mx, my)
            if raw_mass is None or len(raw_mass) == 0:
                print(f"mX={mx} mY={my}: no valid data, skipping.")
                continue

            color = ROOT_STYLE_COLORS[i % len(ROOT_STYLE_COLORS)]

            if my in plot_my_values:
                pooled_raw_vals.append(raw_mass); pooled_raw_w.append(w)
                pooled_resmx_vals.append(resmx); pooled_resmx_w.append(w)

                # per-curve range still used only for the histogram binning
                # of that individual curve, not for the shared axis limits
                lo, hi = weighted_percentile(raw_mass, w, [1, 99])
                bins = np.linspace(lo, hi, 60)
                counts, edges = np.histogram(raw_mass, bins=bins, weights=w, density=True)
                ax_raw.step(edges[:-1], counts, where="post", color=color,
                            linewidth=1.6, label=f"$m_Y$={my} GeV")

                lo2, hi2 = weighted_percentile(resmx, w, [1, 99])
                bins2 = np.linspace(lo2, hi2, 60)
                counts2, edges2 = np.histogram(resmx, bins=bins2, weights=w, density=True)
                ax_resmx.step(edges2[:-1], counts2, where="post", color=color,
                              linewidth=1.6, label=f"$m_Y$={my} GeV")

            print(f"Fitting mX={mx} mY={my} (N={len(raw_mass)}) ...")
            sigma_raw = fit_dscb(raw_mass, w, mass_hint=mx)
            sigma_resmx = fit_dscb(resmx, w, mass_hint=mx)
            improvement = None
            if sigma_raw and sigma_resmx:
                improvement = 100.0 * (sigma_raw - sigma_resmx) / sigma_raw
            resolution_rows.append((mx, my, sigma_raw, sigma_resmx, improvement))
            print(f"    sigma(raw)={sigma_raw}, sigma(Res_M_X)={sigma_resmx}, "
                  f"improvement={improvement}")

        # Axis range from the POOLED distribution across all plotted
        # curves (weighted percentile of everything combined), not the
        # union of each curve's individual range -- the latter lets a
        # single wide-tailed curve (e.g. low mY) dominate and drag the
        # shared axis out into mostly-empty space for every other curve.
        if pooled_raw_vals:
            all_raw = np.concatenate(pooled_raw_vals)
            all_raw_w = np.concatenate(pooled_raw_w)
            lo, hi = weighted_percentile(all_raw, all_raw_w, [1, 99])
            ax_raw.set_xlim(lo * 0.97, hi * 1.03)
        if pooled_resmx_vals:
            all_resmx = np.concatenate(pooled_resmx_vals)
            all_resmx_w = np.concatenate(pooled_resmx_w)
            lo2, hi2 = weighted_percentile(all_resmx, all_resmx_w, [1, 99])
            ax_resmx.set_xlim(lo2 * 0.97, hi2 * 1.03)

        ax_raw.set_xlabel(r"$m_{b\bar{b}\gamma\gamma}$ [GeV]", fontsize=12)
        ax_raw.set_ylabel("Unit normalized", fontsize=12)
        ax_resmx.set_xlabel(r"$\mathrm{Res}\_M_X$ [GeV]", fontsize=12)
        ax_resmx.set_ylabel("Unit normalized", fontsize=12)

        for ax in (ax_raw, ax_resmx):
            ax.legend(fontsize=9, frameon=True, edgecolor="black",
                      fancybox=False, ncol=2, loc="upper right",
                      handlelength=1.2, columnspacing=0.8, labelspacing=0.3)
            ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5))
            ax.tick_params(direction="in", top=True, right=True, which="both",
                            labelsize=10)

        # mX label placed inside the plot, top-left -- no longer needs to
        # clear a CMS/era line above it since that's been removed.
        ax_raw.text(0.03, 0.96, rf"$m_X$ = {mx} GeV", transform=ax_raw.transAxes,
                    fontsize=12, va="top", ha="left")
        ax_resmx.text(0.03, 0.96, rf"$m_X$ = {mx} GeV", transform=ax_resmx.transAxes,
                      fontsize=12, va="top", ha="left")

        fig.tight_layout()
        out_path = f"resmx_resolution_mX{mx}.png"
        fig.savefig(out_path, dpi=300, facecolor="white", bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out_path}\n")

    with open("resolution_comparison_parquet.csv", "w") as f:
        f.write("mX,mY,sigma_raw,sigma_ResMX,improvement_pct\n")
        for mx, my, s1, s2, imp in resolution_rows:
            s1_s = f"{s1:.4g}" if s1 is not None else ""
            s2_s = f"{s2:.4g}" if s2 is not None else ""
            imp_s = f"{imp:.2f}" if imp is not None else ""
            f.write(f"{mx},{my},{s1_s},{s2_s},{imp_s}\n")
    print("Wrote resolution_comparison_parquet.csv")

    valid_improvements = [imp for _, _, s1, s2, imp in resolution_rows if imp is not None]
    if valid_improvements:
        print(f"\nOverall resolution improvement: mean={np.mean(valid_improvements):.1f}%, "
              f"min={np.min(valid_improvements):.1f}%, max={np.max(valid_improvements):.1f}%")


if __name__ == "__main__":
    main()