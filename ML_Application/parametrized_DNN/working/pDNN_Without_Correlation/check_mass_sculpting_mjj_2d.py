#!/usr/bin/env python
# =============================================================================
# check_mass_sculpting_mjj_2d.py
#
# Reviewer comment: "Check the pDNN mass sculpting in Mjj and 2D (mgg, mjj)".
#
# pDNN_v_WC.py's existing run_mass_sculpting() (see its Sec. 14) already checks
# sculpting in a diphoton-mass proxy (MASS_SCULPT_CANDIDATES), but never
# checks m_bb, and never checks the 2D (m_gg, m_bb) plane at all -- exactly
# the two things this comment is asking about.
#
# NO RETRAINING NEEDED. This script deliberately does NOT call
# train_model() or scale_features() (the latter REFITS and OVERWRITES the
# saved scaler on disk -- must not be called again here). It reuses the
# existing, already-tested data loading/splitting functions from pDNN_v_WC.py
# to deterministically reproduce the same TEST split (same seed, same
# GroupShuffleSplit calls), loads the ALREADY-SAVED model weights and
# scaler from disk, and only ever calls .transform()/model.eval() -- never
# .fit() on anything.
#
# ASSUMPTION, stated explicitly: this reproduces the same test split as the
# original training run only if the underlying signal/background parquet
# files on disk are unchanged since that run. If they've since been
# reprocessed (e.g. a fixed production, a corrected selection), this will
# still produce a valid, group-disjoint split, just not necessarily
# identical to the original training run's -- worth being aware of, not
# necessarily a problem.
#
# Res_dijet_mass (the m_bb proxy) is already a member of FEATURES_CORE in
# pDNN_v_WC.py, so it is already present in df_te without any change to that
# script -- confirmed directly by reading pDNN_v_WC.py before writing this.
#
# Run with:
#     python check_mass_sculpting_mjj_2d.py
# =============================================================================

from __future__ import annotations

import json
import os
import pickle
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Reuses pDNN_v_WC.py's own, already-tested logic directly -- no duplicated
# reimplementation of data loading, splitting, or the model architecture.
from pDNN_v_WC import (
    CFG,
    Config,
    ParameterizedDNN,
    apply_cms_plot_style,
    load_signal,
    load_background,
    assign_background_parameters,
    prepare_dataframe,
    resolve_feature_list,
    prune_correlated_features,
    split_dataset,
    df_to_arrays,
    predict,
    weighted_ks_2samp,
    group_key,
    CMS_BLUE,
    CMS_RED,
    CMS_GREEN,
    CMS_DIVERGING_CMAP,
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# m_bb proxy candidates, same fallback-list convention as pDNN_v_WC.py's own
# MASS_SCULPT_CANDIDATES for m_gg -- Res_dijet_mass is the primary,
# already-trained-on feature; the others are defensive fallbacks only.
MJJ_SCULPT_CANDIDATES: Tuple[str, ...] = (
    "Res_dijet_mass", "dibjet_mass", "mass_bb", "mjj",
)


def _find_mjj_column(df: pd.DataFrame) -> Optional[str]:
    for c in MJJ_SCULPT_CANDIDATES:
        if c in df.columns:
            return c
    return None


def reload_trained_model_and_data(cfg: Config = CFG):
    """Reproduce df_te/test_probs from the ALREADY-TRAINED model, with no
    retraining and no scaler refit. Mirrors pDNN_v_WC.py's main() exactly up
    through prediction, but loads (never fits) the scaler and model.
    """
    if not (os.path.exists(cfg.MODEL_PATH) and os.path.exists(cfg.SCALER_PATH)
             and os.path.exists(cfg.FEATURES_PATH)):
        raise FileNotFoundError(
            f"Expected a completed training run's saved artifacts at "
            f"{cfg.MODEL_PATH}, {cfg.SCALER_PATH}, {cfg.FEATURES_PATH} -- "
            f"none found. Run pDNN_v_WC.py's training first; this script only "
            f"evaluates an already-trained model, it does not train one."
        )

    # ---- Reproduce the same data split pDNN_v_WC.py's training run used ----
    signal_df = load_signal(cfg)
    background_df = load_background(cfg)
    background_df = assign_background_parameters(signal_df, background_df, seed=cfg.SEED)
    df_all = prepare_dataframe(signal_df, background_df)
    feature_list = resolve_feature_list(df_all, cfg)
    if cfg.ENABLE_CORR_PRUNING:
        feature_list, _ = prune_correlated_features(df_all, feature_list, df_all["label"].values, cfg)
    _df_tr, _df_va, df_te = split_dataset(df_all, cfg)

    # ---- Load the SAVED feature list, and confirm it matches what was
    # just recomputed -- if it doesn't, the reproduced split/features are
    # NOT trustworthy as "the same as training", and this should fail
    # loudly rather than silently evaluate the model on a mismatched
    # feature ordering. ----
    with open(cfg.FEATURES_PATH) as f:
        saved_feature_list = json.load(f)["features"]
    if list(feature_list) != list(saved_feature_list):
        raise RuntimeError(
            "Recomputed feature_list does not match the SAVED feature list "
            f"from training ({cfg.FEATURES_PATH}). This means the underlying "
            "data or config has changed since that training run -- the "
            "reproduced split/features here cannot be trusted to match the "
            "original TEST set. Recomputed: " + str(feature_list) +
            "  Saved: " + str(saved_feature_list)
        )

    # ---- Load (never fit) the saved scaler ----
    with open(cfg.SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)

    x_te_raw, y_te, w_te = df_to_arrays(df_te, feature_list)
    x_te = scaler.transform(x_te_raw)  # transform only -- scaler already fit during training

    # ---- Load the saved model weights into a fresh model of the same
    # architecture (architecture itself comes from CFG, unchanged since
    # training) ----
    model = ParameterizedDNN(x_te.shape[1], cfg.HIDDEN_LAYERS, cfg.DROPOUT, cfg.USE_BATCHNORM)
    state = torch.load(cfg.MODEL_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(state)
    model = model.to(DEVICE)

    test_probs = predict(model, x_te, DEVICE)

    return df_te, test_probs, y_te, w_te, feature_list


def _savefig(fig_dir: str, filename: str) -> None:
    os.makedirs(fig_dir, exist_ok=True)
    plt.savefig(os.path.join(fig_dir, f"{filename}.png"), dpi=600)
    plt.savefig(os.path.join(fig_dir, f"{filename}.pdf"))
    print(f"[Saved] {os.path.join(fig_dir, filename)}.{{png,pdf}}")
    plt.close()


def plot_mjj_after_score(
    mjj_values: np.ndarray, scores: np.ndarray, weights: np.ndarray, labels: np.ndarray,
    mjj_col_name: str, cfg: Config = CFG,
) -> None:
    """Background m_bb shape overlay across score cuts -- exact same method
    as pDNN_v_WC.py's plot_mass_after_score(), just applied to m_bb instead
    of m_gg."""
    out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
    bkg = labels == 0
    m_bkg, s_bkg, w_bkg = mjj_values[bkg], scores[bkg], (weights[bkg] if weights is not None else None)
    lo, hi = np.nanpercentile(m_bkg, [1, 99])
    bins = np.linspace(lo, hi, 40)

    plt.figure()
    for cut in cfg.SCORE_CUTS:
        sel = s_bkg >= cut
        if sel.sum() < 5:
            continue
        w_sel = w_bkg[sel] if w_bkg is not None else None
        plt.hist(m_bkg[sel], bins=bins, weights=w_sel, density=True, histtype="step", lw=1.8,
                  label=f"score >= {cut:.1f} (N={int(sel.sum())})")
    plt.xlabel(mjj_col_name); plt.ylabel("Density (shape-normalized)")
    plt.title("Background $m_{bb}$ sculpting vs. pDNN score cut")
    plt.legend(fontsize=8); plt.tight_layout()
    _savefig(out_dir, "mass_sculpting_mjj_shapes")


def plot_2d_sculpting(
    mgg_values: np.ndarray, mjj_values: np.ndarray, scores: np.ndarray,
    weights: np.ndarray, labels: np.ndarray, cfg: Config = CFG,
    mgg_x_min: Optional[float] = None,
) -> Dict[str, float]:
    """Genuine 2D (m_gg, m_bb) sculpting check on background only.

    Two complementary views:
      (a) 2D histograms of the background (m_gg, m_bb) plane, side by side
          across a few score cuts -- direct visual check for any localized
          bump/edge developing jointly in both variables (something either
          1D marginal check could individually miss).
      (b) The Pearson correlation between m_gg and m_bb WITHIN background
          events, computed separately at each score cut. A well-behaved
          discriminant should not induce a strong correlation between the
          two mass variables that wasn't present before the cut -- this
          catches a joint-sculpting effect quantitatively, not just
          visually.

    mgg_x_min: optional fixed lower bound for the m_gg axis specifically,
    overriding the default data-driven 1st-percentile lower bound -- same
    reasoning and same fix as pDNN_v_WC.py's plot_mass_after_score(): the
    background sample isn't pre-filtered to the analysis's actual SR mass
    window, so the automatic bound pulls the range down to ~50 GeV. Only
    ever applied to the m_gg axis, not m_bb, which has a genuinely
    different, wider real range of its own.
    """
    out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
    bkg = labels == 0
    mgg_bkg, mjj_bkg, s_bkg = mgg_values[bkg], mjj_values[bkg], scores[bkg]
    w_bkg = weights[bkg] if weights is not None else None

    mgg_lo, mgg_hi = np.nanpercentile(mgg_bkg, [1, 99])
    if mgg_x_min is not None:
        mgg_lo = mgg_x_min
    mjj_lo, mjj_hi = np.nanpercentile(mjj_bkg, [1, 99])

    display_cuts = [c for c in cfg.SCORE_CUTS if (s_bkg >= c).sum() >= 20]
    n_panels = len(display_cuts)
    if n_panels == 0:
        print("[WARN] plot_2d_sculpting: no score cut retains >=20 background "
              "events; skipping 2D histogram panels.")
    else:
        fig, axes = plt.subplots(1, n_panels, figsize=(4.6 * n_panels, 4.2), squeeze=False)
        axes = axes[0]
        for ax, cut in zip(axes, display_cuts):
            sel = s_bkg >= cut
            w_sel = w_bkg[sel] if w_bkg is not None else None
            h = ax.hist2d(
                mgg_bkg[sel], mjj_bkg[sel], bins=30,
                range=[[mgg_lo, mgg_hi], [mjj_lo, mjj_hi]],
                weights=w_sel, cmap=CMS_DIVERGING_CMAP, density=True,
            )
            ax.set_xlabel(r"$m_{\gamma\gamma}$")
            ax.set_ylabel(r"$m_{bb}$")
            ax.set_title(f"score >= {cut:.1f} (N={int(sel.sum())})")
            plt.colorbar(h[3], ax=ax)
        plt.tight_layout()
        _savefig(out_dir, "mass_sculpting_2d_shapes")

    # Quantitative: background-only mgg-vs-mjj correlation at each score cut
    corr_by_cut: Dict[str, float] = {}
    print("[2D sculpting] Background m_gg vs m_bb Pearson correlation by score cut:")
    for cut in cfg.SCORE_CUTS:
        sel = s_bkg >= cut
        if sel.sum() < 20:
            print(f"  score >= {cut:.1f}: skipped (N={int(sel.sum())} < 20)")
            continue
        # weighted Pearson correlation
        w_sel = w_bkg[sel] if w_bkg is not None else np.ones(int(sel.sum()))
        a, b = mgg_bkg[sel], mjj_bkg[sel]
        wa = np.average(a, weights=w_sel)
        wb = np.average(b, weights=w_sel)
        cov = np.average((a - wa) * (b - wb), weights=w_sel)
        var_a = np.average((a - wa) ** 2, weights=w_sel)
        var_b = np.average((b - wb) ** 2, weights=w_sel)
        r = float(cov / np.sqrt(var_a * var_b)) if var_a > 0 and var_b > 0 else float("nan")
        corr_by_cut[f"cut_{cut:.1f}"] = r
        print(f"  score >= {cut:.1f}: r = {r:+.4f}  (N={int(sel.sum())})")

    plt.figure()
    cuts_plotted = [float(k.replace("cut_", "")) for k in corr_by_cut]
    vals_plotted = list(corr_by_cut.values())
    plt.plot(cuts_plotted, vals_plotted, marker="o", color=CMS_GREEN)
    plt.axhline(0.0, color="gray", linestyle="--", lw=1)
    plt.xlabel("Score cut"); plt.ylabel(r"Background $m_{\gamma\gamma}$-$m_{bb}$ correlation")
    plt.title("Induced 2D correlation vs. score cut (background only)")
    plt.tight_layout()
    _savefig(out_dir, "mass_sculpting_2d_correlation_vs_cut")

    return corr_by_cut


def run_mjj_and_2d_sculpting(
    df_te: pd.DataFrame, test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG,
) -> Dict[str, object]:
    """Full m_bb + 2D (m_gg, m_bb) sculpting validation on the TEST split."""
    from pDNN_v_WC import _find_mass_sculpt_column  # m_gg column finder, reused directly

    mgg_col = _find_mass_sculpt_column(df_te, cfg)
    mjj_col = _find_mjj_column(df_te)

    if mjj_col is None:
        print(f"[WARN] No m_bb-proxy column found among {MJJ_SCULPT_CANDIDATES}; "
              f"skipping m_bb and 2D sculpting checks entirely.")
        return {"status": "skipped", "reason": "no mjj column available"}
    if mgg_col is None:
        print(f"[WARN] No m_gg-proxy column found among pDNN_v_WC.CFG.MASS_SCULPT_CANDIDATES; "
              f"skipping 2D sculpting check (m_bb-only 1D check will still run).")

    mjj_values = df_te[mjj_col].to_numpy(dtype=float)

    # ---- 1D m_bb sculpting, same method as pDNN_v_WC.py's existing m_gg check ----
    plot_mjj_after_score(mjj_values, test_probs, w_te, y_te, mjj_col, cfg)

    bkg_mask = y_te == 0
    m_bkg_all = mjj_values[bkg_mask]
    w_bkg_all = w_te[bkg_mask]
    ks_results_mjj = {}
    for cut in cfg.SCORE_CUTS:
        sel_bkg = bkg_mask & (test_probs >= cut)
        m_cut, w_cut = mjj_values[sel_bkg], w_te[sel_bkg]
        if len(m_cut) > 5 and len(m_bkg_all) > 5:
            stat, pval, n_eff_all, n_eff_cut = weighted_ks_2samp(m_bkg_all, w_bkg_all, m_cut, w_cut)
            ks_results_mjj[f"cut_{cut:.1f}"] = {
                "ks_stat": stat, "p_value": pval,
                "n_eff_no_cut": n_eff_all, "n_eff_this_cut": n_eff_cut,
            }
    print("[Physics validation] Weighted KS tests (background m_bb shape, no-cut vs cut):")
    for k, v in ks_results_mjj.items():
        print(f"  {k}: KS={v['ks_stat']:.4f}  p={v['p_value']:.4g}  "
              f"(n_eff no-cut={v['n_eff_no_cut']:.0f}, n_eff this-cut={v['n_eff_this_cut']:.0f})")

    # ---- 2D (m_gg, m_bb) sculpting ----
    corr_2d = {}
    if mgg_col is not None:
        mgg_values = df_te[mgg_col].to_numpy(dtype=float)
        corr_2d = plot_2d_sculpting(mgg_values, mjj_values, test_probs, w_te, y_te, cfg, mgg_x_min=95.0)

    return {
        "status": "ok",
        "mgg_column_used": mgg_col,
        "mjj_column_used": mjj_col,
        "ks_tests_mjj": ks_results_mjj,
        "background_2d_correlation_by_cut": corr_2d,
    }


def main() -> None:
    cfg = CFG
    apply_cms_plot_style()

    print(f"[INFO] Using device: {DEVICE}")
    print("[INFO] Loading already-trained model and reproducing the TEST split "
          "(no training, no scaler refit) ...")
    df_te, test_probs, y_te, w_te, feature_list = reload_trained_model_and_data(cfg)
    print(f"[INFO] TEST split reproduced: N={len(df_te)}, matches saved feature "
          f"list exactly ({len(feature_list)} features).")

    results = run_mjj_and_2d_sculpting(df_te, test_probs, y_te, w_te, cfg)

    out_path = os.path.join(cfg.LOG_DIR, "mass_sculpting_mjj_2d.json")
    os.makedirs(cfg.LOG_DIR, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[INFO] Saved results to {out_path}")

    print("\n[DONE] m_bb + 2D sculpting validation complete.")
    print(f"       Plots: {os.path.join(cfg.PLOT_DIR, 'MassSculpting')}")


if __name__ == "__main__":
    main()