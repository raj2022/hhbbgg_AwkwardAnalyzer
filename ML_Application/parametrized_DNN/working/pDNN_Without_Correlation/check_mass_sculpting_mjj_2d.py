#!/usr/bin/env python3
"""
Consolidated mass sculpting validation, built on top of pDNN_v_WC.py.
Merges what were previously two separate scripts (extended_mass_sculpting.py
and plot_mass_sculpting_extended.py) into one, so every helper (test-split
rebuild, model/scaler loading, weighted-percentile binning) exists in
exactly one place -- avoiding the kind of two-copies-drift-apart bug this
same codebase already hit once (RAW_COLUMNS_OF_INTEREST vs FEATURES_CORE).

Produces:
  1. 1D weighted KS test: diphoton_mass (background, no-cut vs each score cut).
  2. 1D weighted KS test: Res_dijet_mass (same).
  3. 2D binned, weighted chi2 comparison: (diphoton_mass, Res_dijet_mass).
  4. Dijet mass shape overlay plot (same style as the existing diphoton one).
  5. 2D pull-map plot for a representative score cut.

History of fixes folded in here (kept for provenance, not repeated per-run):
  - Correct (sample-from-observed-distribution) imputation, via pDNN_v_WC.py's
    own df_to_arrays -- not the older script's mean-imputation.
  - StandardScaler now loaded and applied before scoring -- omitting this
    previously produced float16-overflow NaN scores for ~3.76% of test
    events, silently breaking the trivial cut>=0.0 closure test.
  - 2D binning range now uses the weighted 1st-99th percentile of the
    pooled sample, not raw min/max -- raw min/max let a single rare,
    low-weight, high-mass background event stretch the axis (and the
    chi2 binning itself) out into mostly-empty space.

Run in the same environment/directory as pDNN_v_WC.py, after it has been
run at least once (so outputs/models/best_pdnn.pt, scaler.pkl exist):
    python3 check_mass_sculpting_mjj_2d.py
"""

import json
import os
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from pDNN_v_WC import (
    CFG, DEVICE, ParameterizedDNN, load_signal, load_background,
    assign_background_parameters, prepare_dataframe, resolve_feature_list,
    prune_correlated_features, split_dataset, df_to_arrays, safe_eval_probs,
    weighted_ks_2samp,
)

SCORE_CUTS = CFG.SCORE_CUTS  # (0.0, 0.3, 0.5, 0.7, 0.9)
DIPHOTON_COL_CANDIDATES = ["diphoton_mass", "mass_gg", "CMS_hgg_mass", "mgg", "Res_HHbbggCandidate_mass"]
DIJET_COL_CANDIDATES = ["Res_dijet_mass", "dijet_mass", "Res_dijet_mass_DNNreg"]
PULLMAP_CUT = 0.9  # which cut to visualize spatially
PETROFF_COLORS = ["#3f90da", "#ffa90e", "#bd1f01", "#832db6", "#94a4a2"]
MIN_DIJET_MASS = 95.0
# Physics floor, not a plotting choice: below ~90 GeV the background m_jj
# spectrum is not smoothly-falling (Z -> bb contamination near the Z
# mass), which is the same reasoning behind the analysis's m_Y >= 90 GeV
# grid boundary established earlier in this session. The dijet mass axis
# should respect this floor rather than following wherever a percentile
# happens to land.

# Output paths -- reuse pDNN_v_WC.py's own CFG.PLOT_DIR/CFG.LOG_DIR
# convention (outputs/plots, outputs/logs) rather than writing into the
# current working directory, and match the existing "MassSculpting"
# subfolder convention already used by that script's own mass-sculpting
# plots (see plot_mass_after_score's out_dir).
PLOT_OUT_DIR = os.path.join(CFG.PLOT_DIR, "MassSculpting")
LOG_OUT_DIR = CFG.LOG_DIR
os.makedirs(PLOT_OUT_DIR, exist_ok=True)
os.makedirs(LOG_OUT_DIR, exist_ok=True)


# =============================================================================
# Shared helpers
# =============================================================================
def find_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def weighted_percentile(values, weights, percentiles):
    """Weighted percentile -- avoids a single rare, low-weight outlier
    event stretching an axis/binning range out into mostly-empty space."""
    sorter = np.argsort(values)
    v_sorted = values[sorter]
    w_sorted = weights[sorter]
    cum_w = np.cumsum(w_sorted) - 0.5 * w_sorted
    cum_w /= np.sum(w_sorted)
    return np.interp(np.asarray(percentiles) / 100.0, cum_w, v_sorted)


def rebuild_test_split():
    """Reproduce pDNN_v_WC.py's exact data pipeline up through the TEST
    split, using the same CFG (same SEED -> same GroupShuffleSplit
    results), without retraining."""
    signal_df = load_signal(CFG)
    background_df = load_background(CFG)
    background_df = assign_background_parameters(signal_df, background_df, seed=CFG.SEED)
    df_all = prepare_dataframe(signal_df, background_df)
    feature_list = resolve_feature_list(df_all, CFG)
    if CFG.ENABLE_CORR_PRUNING:
        feature_list, _ = prune_correlated_features(df_all, feature_list, df_all["label"].values, CFG)
    df_tr, df_va, df_te = split_dataset(df_all, CFG)
    return df_te, feature_list


def load_trained_model(n_features):
    model = ParameterizedDNN(n_features, CFG.HIDDEN_LAYERS, CFG.DROPOUT, CFG.USE_BATCHNORM)
    state = torch.load(CFG.MODEL_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(state)
    model = model.to(DEVICE)
    model.eval()
    return model


def weighted_2d_chi2(x_a, y_a, w_a, x_b, y_b, w_b, y_min=None, max_bins_per_axis=10):
    """Binned, weighted chi-square-style comparison of two 2D shapes
    (each independently shape-normalized to unit total weight first).

    Bin count is adaptive, not fixed: a fixed grid (e.g. always 10x10)
    cannot be right simultaneously for the no-cut sample (n_eff ~ 10^4)
    and the tightest score cut (n_eff ~ 200) -- confirmed directly from a
    real pull-map render at a fixed 10x10 grid, which showed an
    unphysical scattered/salt-and-pepper pattern at the tightest cut
    (statistical noise from ~2 effective entries per bin on average),
    rather than the smooth, physically coherent pattern seen at looser
    cuts. Bins per axis are instead set from the effective sample size of
    the SMALLER (more constraining) of the two samples, aiming for
    roughly 10 effective entries per bin.

    y_min, if given, is a hard physics floor on the y-axis range (not
    derived from the data) -- see MIN_DIJET_MASS above.

    Returns (chi2_stat, ndof, per_bin_max_abs_pull, bin_edges, pulls, bins_used).
    """
    n_eff_a = float(w_a.sum() ** 2 / np.sum(w_a ** 2)) if np.sum(w_a ** 2) > 0 else 0.0
    n_eff_b = float(w_b.sum() ** 2 / np.sum(w_b ** 2)) if np.sum(w_b ** 2) > 0 else 0.0
    n_eff_limiting = min(n_eff_a, n_eff_b)
    bins = max(2, min(max_bins_per_axis, int(np.sqrt(n_eff_limiting / 10.0))))

    x_pool = np.concatenate([x_a, x_b])
    y_pool = np.concatenate([y_a, y_b])
    w_pool = np.concatenate([w_a, w_b])
    x_range = tuple(weighted_percentile(x_pool, w_pool, [1, 99]))
    y_range = tuple(weighted_percentile(y_pool, w_pool, [1, 99]))
    if y_min is not None:
        y_range = (max(y_range[0], y_min), y_range[1])

    h_a, xedges, yedges = np.histogram2d(x_a, y_a, bins=bins, range=[x_range, y_range], weights=w_a)
    h_b, _, _ = np.histogram2d(x_b, y_b, bins=[xedges, yedges], weights=w_b)
    h_a_w2, _, _ = np.histogram2d(x_a, y_a, bins=[xedges, yedges], weights=w_a ** 2)
    h_b_w2, _, _ = np.histogram2d(x_b, y_b, bins=[xedges, yedges], weights=w_b ** 2)

    norm_a, norm_b = h_a.sum(), h_b.sum()
    if norm_a <= 0 or norm_b <= 0:
        return float("nan"), 0, float("nan"), (xedges, yedges), None, bins

    p_a, p_b = h_a / norm_a, h_b / norm_b
    sigma_a = np.sqrt(h_a_w2) / norm_a
    sigma_b = np.sqrt(h_b_w2) / norm_b
    sigma2 = sigma_a ** 2 + sigma_b ** 2

    mask = sigma2 > 0
    chi2 = np.sum(((p_a[mask] - p_b[mask]) ** 2) / sigma2[mask])
    ndof = int(mask.sum())
    pulls = np.zeros_like(p_a)
    pulls[mask] = (p_b[mask] - p_a[mask]) / np.sqrt(sigma2[mask])
    max_pull = float(np.max(np.abs(pulls[mask]))) if ndof > 0 else float("nan")
    return float(chi2), ndof, max_pull, (xedges, yedges), pulls, bins


# =============================================================================
# Plotting
# =============================================================================
def plot_dijet_shapes(df_te, test_probs, bkg_mask, w_te, dijet_col):
    m_bkg = df_te[dijet_col].to_numpy()[bkg_mask]
    w_bkg_all = w_te[bkg_mask]
    lo, hi = weighted_percentile(m_bkg, w_bkg_all, [1, 99])
    lo = max(lo, MIN_DIJET_MASS)
    bins = np.linspace(lo, hi, 40)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for i, cut in enumerate(SCORE_CUTS):
        sel = bkg_mask & (test_probs >= cut)
        if sel.sum() < 5:
            continue
        m_cut = df_te[dijet_col].to_numpy()[sel]
        w_cut = w_te[sel]
        ax.hist(m_cut, bins=bins, weights=w_cut, density=True, histtype="step",
                lw=1.8, color=PETROFF_COLORS[i % len(PETROFF_COLORS)],
                label=f"score \u2265 {cut:.1f} (N={int(sel.sum())})")
    ax.set_xlabel(rf"$m_{{jj}}$ ({dijet_col}) [GeV]", fontsize=12)
    ax.set_ylabel("Density (shape-normalized)", fontsize=12)
    ax.legend(fontsize=10, frameon=True, edgecolor="black", fancybox=False)
    ax.tick_params(direction="in", top=True, right=True, which="both", labelsize=10)
    ax.text(0.02, 1.02, "CMS", transform=ax.transAxes,
            fontsize=15, fontweight="bold", va="bottom", ha="left")
    ax.text(0.13, 1.02, "Work in progress", transform=ax.transAxes,
            fontsize=12, fontstyle="italic", va="bottom", ha="left")
    fig.tight_layout()
    out_path = os.path.join(PLOT_OUT_DIR, "dijet_mass_sculpting_shapes")
    fig.savefig(f"{out_path}.png", dpi=300, facecolor="white", bbox_inches="tight")
    fig.savefig(f"{out_path}.pdf", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}.{{png,pdf}}")


def plot_2d_pullmap(diphoton_col, dijet_col, cut, edges, pulls):
    xedges, yedges = edges
    fig, ax = plt.subplots(figsize=(7.5, 6.0))
    vmax = np.max(np.abs(pulls))
    im = ax.imshow(pulls.T, origin="lower", aspect="auto", cmap="RdBu_r",
                   vmin=-vmax, vmax=vmax,
                   extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]])
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Pull: (cut $-$ no-cut) / $\\sigma$", fontsize=11)
    ax.set_xlabel(rf"$m_{{\gamma\gamma}}$ ({diphoton_col}) [GeV]", fontsize=12)
    ax.set_ylabel(rf"$m_{{jj}}$ ({dijet_col}) [GeV]", fontsize=12)
    ax.tick_params(direction="out", labelsize=10)
    ax.text(0.02, 1.02, "CMS", transform=ax.transAxes,
            fontsize=15, fontweight="bold", va="bottom", ha="left")
    ax.text(0.13, 1.02, "Work in progress", transform=ax.transAxes,
            fontsize=12, fontstyle="italic", va="bottom", ha="left")
    ax.text(0.98, 1.02, f"score \u2265 {cut:.1f} vs. no-cut", transform=ax.transAxes,
            fontsize=11, va="bottom", ha="right")
    fig.tight_layout()
    fname = os.path.join(PLOT_OUT_DIR, f"joint_2d_pullmap_cut{cut:.1f}")
    fig.savefig(f"{fname}.png", dpi=300, facecolor="white", bbox_inches="tight")
    fig.savefig(f"{fname}.pdf", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {fname}.{{png,pdf}}")


# =============================================================================
# Main
# =============================================================================
def main():
    print("Rebuilding the exact TEST split used by pDNN_v_WC.py (same SEED, no retraining)...")
    df_te, feature_list = rebuild_test_split()
    x_te_raw, y_te, w_te = df_to_arrays(df_te, feature_list)

    print("Loading the saved StandardScaler...")
    with open(CFG.SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    x_te = scaler.transform(x_te_raw).astype("float32")

    print("Loading the already-trained model checkpoint...")
    model = load_trained_model(x_te.shape[1])
    x_te_t = torch.tensor(x_te, dtype=torch.float32).to(DEVICE)
    test_probs = safe_eval_probs(model, x_te_t, DEVICE)
    print("N NaN scores:", np.isnan(test_probs).sum())
    print("N Inf scores:", np.isinf(test_probs).sum())
    print("N out-of-range scores (not in [0,1]):", ((test_probs < 0) | (test_probs > 1)).sum())

    diphoton_col = find_column(df_te, DIPHOTON_COL_CANDIDATES)
    dijet_col = find_column(df_te, DIJET_COL_CANDIDATES)
    print(f"Diphoton mass column: {diphoton_col}")
    print(f"Dijet mass column: {dijet_col}")

    bkg_mask = (y_te == 0)
    results = {"diphoton_1d": {}, "dijet_1d": {}, "joint_2d": {}}

    # ---- 1D diphoton ----
    if diphoton_col:
        m_bkg_all = df_te[diphoton_col].to_numpy()[bkg_mask]
        w_bkg_all = w_te[bkg_mask]
        print(f"\n=== 1D KS: {diphoton_col} (background, no-cut vs each score cut) ===")
        for cut in SCORE_CUTS:
            sel = bkg_mask & (test_probs >= cut)
            m_cut = df_te[diphoton_col].to_numpy()[sel]
            w_cut = w_te[sel]
            if len(m_cut) > 5:
                stat, pval, n_eff_all, n_eff_cut = weighted_ks_2samp(m_bkg_all, w_bkg_all, m_cut, w_cut)
                results["diphoton_1d"][f"cut_{cut:.1f}"] = {
                    "ks_stat": stat, "p_value": pval,
                    "n_eff_no_cut": n_eff_all, "n_eff_this_cut": n_eff_cut,
                }
                print(f"  cut>={cut:.1f}: KS={stat:.4f}  p={pval:.4g}  "
                      f"(n_eff no-cut={n_eff_all:.0f}, this-cut={n_eff_cut:.0f})")
    else:
        print("[WARN] No diphoton mass column found; skipping 1D diphoton check.")

    # ---- 1D dijet ----
    if dijet_col:
        m_bkg_all = df_te[dijet_col].to_numpy()[bkg_mask]
        w_bkg_all = w_te[bkg_mask]
        print(f"\n=== 1D KS: {dijet_col} (background, no-cut vs each score cut) ===")
        for cut in SCORE_CUTS:
            sel = bkg_mask & (test_probs >= cut)
            m_cut = df_te[dijet_col].to_numpy()[sel]
            w_cut = w_te[sel]
            if len(m_cut) > 5:
                stat, pval, n_eff_all, n_eff_cut = weighted_ks_2samp(m_bkg_all, w_bkg_all, m_cut, w_cut)
                results["dijet_1d"][f"cut_{cut:.1f}"] = {
                    "ks_stat": stat, "p_value": pval,
                    "n_eff_no_cut": n_eff_all, "n_eff_this_cut": n_eff_cut,
                }
                print(f"  cut>={cut:.1f}: KS={stat:.4f}  p={pval:.4g}  "
                      f"(n_eff no-cut={n_eff_all:.0f}, this-cut={n_eff_cut:.0f})")
        plot_dijet_shapes(df_te, test_probs, bkg_mask, w_te, dijet_col)
    else:
        print("[WARN] No dijet mass column found; skipping 1D dijet check and its plot.")

    # ---- 2D joint ----
    if diphoton_col and dijet_col:
        x_all = df_te[diphoton_col].to_numpy()[bkg_mask]
        y_all = df_te[dijet_col].to_numpy()[bkg_mask]
        w_all = w_te[bkg_mask]
        print(f"\n=== 2D binned chi2: ({diphoton_col}, {dijet_col}) (background, no-cut vs each score cut) ===")
        for cut in SCORE_CUTS:
            sel = bkg_mask & (test_probs >= cut)
            x_cut = df_te[diphoton_col].to_numpy()[sel]
            y_cut = df_te[dijet_col].to_numpy()[sel]
            w_cut = w_te[sel]
            if len(x_cut) > 20:
                chi2, ndof, max_pull, edges, pulls, bins_used = weighted_2d_chi2(
                    x_all, y_all, w_all, x_cut, y_cut, w_cut, y_min=MIN_DIJET_MASS
                )
                results["joint_2d"][f"cut_{cut:.1f}"] = {
                    "chi2": chi2, "ndof": ndof,
                    "chi2_per_ndof": chi2 / ndof if ndof else float("nan"),
                    "max_abs_pull": max_pull, "bins_per_axis": bins_used,
                }
                print(f"  cut>={cut:.1f}: chi2={chi2:.2f}  ndof={ndof}  "
                      f"chi2/ndof={chi2/ndof if ndof else float('nan'):.3f}  "
                      f"max|pull|={max_pull:.2f}  bins/axis={bins_used}")
                if abs(cut - PULLMAP_CUT) < 1e-9 and pulls is not None:
                    plot_2d_pullmap(diphoton_col, dijet_col, cut, edges, pulls)
    else:
        print("[WARN] Missing diphoton or dijet column; skipping 2D check and its plot.")

    json_path = os.path.join(LOG_OUT_DIR, "mass_sculpting_validation_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {json_path}")


if __name__ == "__main__":
    main()