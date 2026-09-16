#!/usr/bin/env python3
"""
Produces the two additional mass-sculpting plots requested for the note:
  1. Dijet mass (Res_dijet_mass) shape overlay across score cuts, in the
     same style as the existing diphoton mass_sculpting_shapes.pdf.
  2. A 2D pull-map visualization for a representative tight cut,
     showing WHERE in the (diphoton_mass, dijet_mass) plane the shape
     discrepancy concentrates -- a bare chi2/ndof number doesn't convey
     this, and the per-bin pulls found here (up to ~17) are large enough
     that seeing their spatial pattern matters for deciding what (if
     anything) is driving the effect.

Reuses the same corrected pipeline as extended_mass_sculpting.py (loads
the trained model + scaler, rebuilds the exact TEST split, applies the
StandardScaler fix). Run in the same directory, after that script has
been confirmed working (N NaN scores: 0).

Outputs:
    dijet_mass_sculpting_shapes.png/.pdf
    joint_2d_pullmap_cut0.9.png/.pdf
"""

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
)

SCORE_CUTS = CFG.SCORE_CUTS
DIPHOTON_COL = "diphoton_mass"
DIJET_COL = "Res_dijet_mass"
PULLMAP_CUT = 0.9  # which cut to visualize spatially

PETROFF_COLORS = ["#3f90da", "#ffa90e", "#bd1f01", "#832db6", "#94a4a2"]


def rebuild_test_split():
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


def plot_dijet_shapes(df_te, test_probs, bkg_mask, w_te):
    m_bkg = df_te[DIJET_COL].to_numpy()[bkg_mask]
    lo, hi = np.nanpercentile(m_bkg, [1, 99])
    bins = np.linspace(lo, hi, 40)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for i, cut in enumerate(SCORE_CUTS):
        sel = bkg_mask & (test_probs >= cut)
        if sel.sum() < 5:
            continue
        m_cut = df_te[DIJET_COL].to_numpy()[sel]
        w_cut = w_te[sel]
        ax.hist(m_cut, bins=bins, weights=w_cut, density=True, histtype="step",
                lw=1.8, color=PETROFF_COLORS[i % len(PETROFF_COLORS)],
                label=f"score \u2265 {cut:.1f} (N={int(sel.sum())})")
    ax.set_xlabel(r"$m_{jj}$ (Res_dijet_mass) [GeV]", fontsize=12)
    ax.set_ylabel("Density (shape-normalized)", fontsize=12)
    ax.legend(fontsize=10, frameon=True, edgecolor="black", fancybox=False)
    ax.tick_params(direction="in", top=True, right=True, which="both", labelsize=10)

    ax.text(0.02, 1.02, "CMS", transform=ax.transAxes,
            fontsize=15, fontweight="bold", va="bottom", ha="left")
    ax.text(0.13, 1.02, "Work in progress", transform=ax.transAxes,
            fontsize=12, fontstyle="italic", va="bottom", ha="left")

    fig.tight_layout()
    fig.savefig("dijet_mass_sculpting_shapes.png", dpi=300, facecolor="white", bbox_inches="tight")
    fig.savefig("dijet_mass_sculpting_shapes.pdf", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("Wrote dijet_mass_sculpting_shapes.{png,pdf}")


def plot_2d_pullmap(df_te, test_probs, bkg_mask, w_te, cut, bins=10):
    x_all = df_te[DIPHOTON_COL].to_numpy()[bkg_mask]
    y_all = df_te[DIJET_COL].to_numpy()[bkg_mask]
    w_all = w_te[bkg_mask]

    sel = bkg_mask & (test_probs >= cut)
    x_cut = df_te[DIPHOTON_COL].to_numpy()[sel]
    y_cut = df_te[DIJET_COL].to_numpy()[sel]
    w_cut = w_te[sel]

    x_range = (min(x_all.min(), x_cut.min()), max(x_all.max(), x_cut.max()))
    y_range = (min(y_all.min(), y_cut.min()), max(y_all.max(), y_cut.max()))

    h_all, xedges, yedges = np.histogram2d(x_all, y_all, bins=bins, range=[x_range, y_range], weights=w_all)
    h_cut, _, _ = np.histogram2d(x_cut, y_cut, bins=[xedges, yedges], weights=w_cut)
    h_all_w2, _, _ = np.histogram2d(x_all, y_all, bins=[xedges, yedges], weights=w_all ** 2)
    h_cut_w2, _, _ = np.histogram2d(x_cut, y_cut, bins=[xedges, yedges], weights=w_cut ** 2)

    norm_all, norm_cut = h_all.sum(), h_cut.sum()
    p_all, p_cut = h_all / norm_all, h_cut / norm_cut
    sigma_all = np.sqrt(h_all_w2) / norm_all
    sigma_cut = np.sqrt(h_cut_w2) / norm_cut
    sigma2 = sigma_all ** 2 + sigma_cut ** 2

    pulls = np.zeros_like(p_all)
    mask = sigma2 > 0
    pulls[mask] = (p_cut[mask] - p_all[mask]) / np.sqrt(sigma2[mask])

    fig, ax = plt.subplots(figsize=(7.5, 6.0))
    vmax = np.max(np.abs(pulls))
    im = ax.imshow(pulls.T, origin="lower", aspect="auto", cmap="RdBu_r",
                   vmin=-vmax, vmax=vmax,
                   extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]])
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Pull: (cut $-$ no-cut) / $\\sigma$", fontsize=11)
    ax.set_xlabel(r"$m_{\gamma\gamma}$ (diphoton_mass) [GeV]", fontsize=12)
    ax.set_ylabel(r"$m_{jj}$ (Res_dijet_mass) [GeV]", fontsize=12)
    ax.tick_params(direction="out", labelsize=10)

    ax.text(0.02, 1.02, "CMS", transform=ax.transAxes,
            fontsize=15, fontweight="bold", va="bottom", ha="left")
    ax.text(0.13, 1.02, "Work in progress", transform=ax.transAxes,
            fontsize=12, fontstyle="italic", va="bottom", ha="left")
    ax.text(0.98, 1.02, f"score \u2265 {cut:.1f} vs. no-cut", transform=ax.transAxes,
            fontsize=11, va="bottom", ha="right")

    fig.tight_layout()
    fname = f"joint_2d_pullmap_cut{cut:.1f}"
    fig.savefig(f"{fname}.png", dpi=300, facecolor="white", bbox_inches="tight")
    fig.savefig(f"{fname}.pdf", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {fname}.{{png,pdf}}")


def main():
    print("Rebuilding the exact TEST split (same SEED, no retraining)...")
    df_te, feature_list = rebuild_test_split()
    x_te_raw, y_te, w_te = df_to_arrays(df_te, feature_list)

    with open(CFG.SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    x_te = scaler.transform(x_te_raw).astype("float32")

    model = load_trained_model(x_te.shape[1])
    x_te_t = torch.tensor(x_te, dtype=torch.float32).to(DEVICE)
    test_probs = safe_eval_probs(model, x_te_t, DEVICE)
    print("N NaN scores:", np.isnan(test_probs).sum())

    bkg_mask = (y_te == 0)

    plot_dijet_shapes(df_te, test_probs, bkg_mask, w_te)
    plot_2d_pullmap(df_te, test_probs, bkg_mask, w_te, cut=PULLMAP_CUT)


if __name__ == "__main__":
    main()