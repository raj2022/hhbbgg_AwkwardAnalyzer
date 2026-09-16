#!/usr/bin/env python3
"""
Empirical quantification of the float16 sigmoid-quantization issue.

Computes the pDNN score TWO ways on the identical test-set events, using
the identical trained model:
  1. "buggy": sigmoid applied INSIDE the CUDA autocast context, so the
     probability itself is computed at float16 precision (the original
     bug pattern -- logits are float16 under autocast, and applying
     sigmoid without first upcasting keeps the result at that precision).
  2. "fixed": logits explicitly upcast to float32 BEFORE sigmoid is
     applied (the fix already present in pDNN_v_WC.py's real
     predict_batched/safe_eval_probs, reused directly here for the
     "fixed" side so this comparison can't accidentally diverge from
     what the real pipeline actually does).

Reports, with real numbers rather than a qualitative precision argument:
  - How many events differ at all, and by how much (summary statistics).
  - How many events CROSS a score-cut boundary (0.3/0.5/0.7/0.9) between
    the two methods -- i.e. would land in a different category purely
    from this precision artifact, not from any real physics difference.
  - Exact-1.0 saturation counts under each method.
  - Number of distinct representable score values in the extreme tail
    (score > 0.99) under each method -- directly demonstrates the
    "comb"/quantization pattern (float16 has far fewer representable
    values near 1.0 than float32 does).
  - A histogram figure of the tail region for a direct visual comparison.

Requires a CUDA device -- autocast only produces a float16 difference on
GPU; run in the same environment/session used for real training.

Run in the same environment/directory as pDNN_v_WC.py, after it has been
run at least once (so outputs/models/best_pdnn.pt, scaler.pkl exist):
    python3 quantization_study.py
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
)

SCORE_CUTS = CFG.SCORE_CUTS
PLOT_OUT_DIR = os.path.join(CFG.PLOT_DIR, "Quantization")
LOG_OUT_DIR = CFG.LOG_DIR
os.makedirs(PLOT_OUT_DIR, exist_ok=True)
os.makedirs(LOG_OUT_DIR, exist_ok=True)


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


@torch.no_grad()
def predict_batched_buggy(model, x_tensor, device, batch=CFG.EVAL_BATCH):
    """Reproduces the ORIGINAL bug: sigmoid computed INSIDE the autocast
    context, at float16 precision, rather than upcasting first."""
    model.eval()
    n = x_tensor.shape[0]
    out = np.empty(n, dtype=np.float32)
    amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda"))
    for i in range(0, n, batch):
        xb = x_tensor[i:i + batch].to(device, non_blocking=True)
        with amp_ctx:
            logits = model(xb).view(-1)
            probs = torch.sigmoid(logits)  # <-- BUG: sigmoid still inside autocast, still float16
        out[i:i + batch] = probs.detach().float().cpu().numpy()
    return out


def main():
    if DEVICE.type != "cuda":
        print("[WARN] No CUDA device available -- autocast will not actually run in "
              "float16 on CPU, so 'buggy' and 'fixed' will likely be identical here. "
              "This study needs to run on the same GPU environment used for training "
              "to be meaningful.")

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

    print("Scoring with the BUGGY method (sigmoid inside float16 autocast)...")
    probs_buggy = predict_batched_buggy(model, x_te_t, DEVICE)
    print("Scoring with the FIXED method (upcast to float32 before sigmoid)...")
    probs_fixed = safe_eval_probs(model, x_te_t, DEVICE)  # the real, already-fixed pipeline function

    diff = probs_buggy - probs_fixed
    abs_diff = np.abs(diff)
    n_total = len(probs_fixed)

    results = {"n_total_events": int(n_total)}

    # ---- summary statistics ----
    print("\n=== Score difference: buggy - fixed ===")
    print(f"  max |diff|:  {abs_diff.max():.6e}")
    print(f"  mean |diff|: {abs_diff.mean():.6e}")
    for thresh in [1e-6, 1e-4, 1e-3, 1e-2]:
        n_above = int((abs_diff > thresh).sum())
        print(f"  events with |diff| > {thresh:.0e}: {n_above} ({100 * n_above / n_total:.4f}%)")
    results["diff_summary"] = {
        "max_abs_diff": float(abs_diff.max()),
        "mean_abs_diff": float(abs_diff.mean()),
        "n_above_1e-6": int((abs_diff > 1e-6).sum()),
        "n_above_1e-4": int((abs_diff > 1e-4).sum()),
        "n_above_1e-3": int((abs_diff > 1e-3).sum()),
        "n_above_1e-2": int((abs_diff > 1e-2).sum()),
    }

    # ---- category/score-cut crossing ----
    print("\n=== Events crossing a score-cut boundary (buggy vs fixed) ===")
    results["category_crossings"] = {}
    for cut in SCORE_CUTS:
        side_buggy = probs_buggy >= cut
        side_fixed = probs_fixed >= cut
        n_crossed = int((side_buggy != side_fixed).sum())
        print(f"  cut>={cut:.1f}: {n_crossed} event(s) change side ({100 * n_crossed / n_total:.4f}%)")
        results["category_crossings"][f"cut_{cut:.1f}"] = n_crossed

    # ---- exact saturation to 1.0 ----
    n_sat_buggy = int((probs_buggy >= 1.0).sum())
    n_sat_fixed = int((probs_fixed >= 1.0).sum())
    print(f"\n=== Exact saturation to 1.0 ===")
    print(f"  buggy: {n_sat_buggy} ({100 * n_sat_buggy / n_total:.4f}%)")
    print(f"  fixed: {n_sat_fixed} ({100 * n_sat_fixed / n_total:.4f}%)")
    results["saturation_to_1"] = {"buggy": n_sat_buggy, "fixed": n_sat_fixed}

    # ---- distinct representable values in the extreme tail ----
    tail_mask = probs_fixed > 0.99
    n_unique_buggy_tail = int(len(np.unique(probs_buggy[tail_mask])))
    n_unique_fixed_tail = int(len(np.unique(probs_fixed[tail_mask])))
    n_tail_events = int(tail_mask.sum())
    print(f"\n=== Distinct score values for events with score > 0.99 (N={n_tail_events}) ===")
    print(f"  buggy: {n_unique_buggy_tail} distinct value(s)")
    print(f"  fixed: {n_unique_fixed_tail} distinct value(s)")
    results["tail_quantization"] = {
        "n_events_above_0.99": n_tail_events,
        "n_unique_buggy": n_unique_buggy_tail,
        "n_unique_fixed": n_unique_fixed_tail,
    }

    # ---- figure: tail region histogram, buggy vs fixed ----
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    bins = np.linspace(0.99, 1.0, 101)
    ax.hist(probs_buggy[probs_buggy > 0.99], bins=bins, histtype="step", lw=1.8,
            color="#bd1f01", label=f"Buggy (float16 sigmoid), {n_unique_buggy_tail} distinct values")
    ax.hist(probs_fixed[probs_fixed > 0.99], bins=bins, histtype="step", lw=1.8,
            color="#3f90da", label=f"Fixed (float32 sigmoid), {n_unique_fixed_tail} distinct values")
    ax.set_xlabel("pDNN score (tail region, score > 0.99)", fontsize=12)
    ax.set_ylabel("Events", fontsize=12)
    ax.legend(fontsize=10, frameon=True, edgecolor="black", fancybox=False)
    ax.tick_params(direction="in", top=True, right=True, which="both", labelsize=10)
    ax.text(0.02, 1.02, "CMS", transform=ax.transAxes,
            fontsize=15, fontweight="bold", va="bottom", ha="left")
    ax.text(0.13, 1.02, "Work in progress", transform=ax.transAxes,
            fontsize=12, fontstyle="italic", va="bottom", ha="left")
    fig.tight_layout()
    out_path = os.path.join(PLOT_OUT_DIR, "quantization_tail_comparison")
    fig.savefig(f"{out_path}.png", dpi=300, facecolor="white", bbox_inches="tight")
    fig.savefig(f"{out_path}.pdf", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"\nWrote {out_path}.{{png,pdf}}")

    json_path = os.path.join(LOG_OUT_DIR, "quantization_study_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()