#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDNN inference at specific mass points (X, Y)

Example:
  python inference_PDnn.py \
    --points 400:125 500:95 \
    --model best_pdnn.pt \
    --signal-root ../../../output_parquet/final_production_Syst/merged \
    --bkg "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GGJets/preselection" \
         "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GJetPt20To40/preselection" \
         "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GJetPt40/preselection" \
    --background-frac 0.3 \
    --fit-scaler-on-inference \
    --outdir inference_outputs
"""

import os
import argparse
from typing import List, Tuple

import numpy as np
import pandas as pd
import uproot

import torch
import torch.nn as nn

from sklearn.metrics import roc_auc_score, roc_curve, auc
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt

# -----------------------------
# Default config (override via CLI)
# -----------------------------
FEATURES_CORE: List[str] = [
    "bbgg_eta", "bbgg_phi",
    "lead_pho_phi", "sublead_pho_eta", "sublead_pho_phi",
    "diphoton_eta", "diphoton_phi",
    "dibjet_eta", "dibjet_phi",
    "lead_bjet_pt", "sublead_bjet_pt",
    "lead_bjet_eta", "lead_bjet_phi",
    "sublead_bjet_eta", "sublead_bjet_phi",
    "sublead_bjet_PNetB", "lead_bjet_PNetB",
    "CosThetaStar_gg", "CosThetaStar_jj", "CosThetaStar_CS",
    "DeltaR_jg_min",
    "pholead_PtOverM", "phosublead_PtOverM",
    "lead_pho_mvaID", "sublead_pho_mvaID",
]
WEIGHT_COL = "weight_preselection"
FEATURES_FINAL: List[str] = FEATURES_CORE + ["mass", "y_value"]

BACKGROUND_DEFAULT: List[Tuple[str, str]] = [
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GGJets/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt20To40/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt40/preselection"),
]

# -----------------------------
# Utilities
# -----------------------------
def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast float64 -> float32 to reduce memory."""
    float64_cols = df.select_dtypes(include=["float64"]).columns
    if len(float64_cols):
        df[float64_cols] = df[float64_cols].astype("float32")
    return df

def ensure_weight(df: pd.DataFrame, weight_col: str = WEIGHT_COL) -> pd.DataFrame:
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df

def parse_mass_points(specs: List[str]) -> List[Tuple[int, int]]:
    """Parse CLI points like '400:125' or '400,125'."""
    out: List[Tuple[int, int]] = []
    for s in specs:
        if ":" in s:
            x, y = s.split(":")
        elif "," in s:
            x, y = s.split(",")
        else:
            raise argparse.ArgumentTypeError(f"Bad mass point '{s}', use X:Y (e.g. 400:125)")
        out.append((int(x), int(y)))
    return out

# -----------------------------
# I/O: Signal & Background
# -----------------------------
def load_signal(signal_root: str, points: List[Tuple[int, int]]) -> pd.DataFrame:
    """Load signal for specific mass points from parquet files."""
    sig_frames: List[pd.DataFrame] = []

    for mass, y in points:
        fp = os.path.join(signal_root, f"NMSSM_X{mass}_Y{y}", "nominal", "NOTAG_merged.parquet")
        if not os.path.exists(fp):
            print(f"[WARN] Missing signal parquet for (X={mass}, Y={y}): {fp}")
            continue
        try:
            df = pd.read_parquet(fp, columns=list(set(FEATURES_CORE + [WEIGHT_COL])))
        except Exception:
            df = pd.read_parquet(fp)

        keep_cols = [c for c in FEATURES_CORE if c in df.columns]
        extras = [WEIGHT_COL] if WEIGHT_COL in df.columns else []
        df = df[keep_cols + extras].copy()

        df["mass"] = mass
        df["y_value"] = y
        df["label"] = 1

        df = ensure_weight(df)
        df = downcast_float_cols(df)
        sig_frames.append(df)

    if not sig_frames:
        raise RuntimeError("No signal events loaded for the requested points.")
    return pd.concat(sig_frames, ignore_index=True)

def load_background(bkg_specs: List[Tuple[str, str]]) -> pd.DataFrame:
    """Load background from ROOT using Uproot."""
    frames: List[pd.DataFrame] = []
    for path, tree in bkg_specs:
        if not os.path.exists(path):
            print(f"[WARN] Background file not found: {path}")
            continue
        try:
            with uproot.open(path) as f:
                if tree not in f:
                    print(f"[WARN] Tree {tree} not in {path}")
                    continue
                t = f[tree]
                requested = list(set(FEATURES_CORE + [WEIGHT_COL]))
                df = t.arrays(filter_name=requested, library="pd")

            df = ensure_weight(df)
            df["label"] = 0
            keep_cols = [c for c in FEATURES_CORE if c in df.columns]
            df = df[keep_cols + [WEIGHT_COL, "label"]].copy()
            df = downcast_float_cols(df)
            frames.append(df)

        except Exception as e:
            print(f"[WARN] Could not read {path} ({tree}): {e}")

    if not frames:
        raise RuntimeError("No background loaded.")
    return pd.concat(frames, ignore_index=True)

def tag_background_mass_y(df_background: pd.DataFrame, signal_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Assign (mass, y_value) to background rows to match signal (mass,y) mixture."""
    sig_mass_y = signal_df[["mass", "y_value"]].copy()
    value_counts = sig_mass_y.value_counts(normalize=True).reset_index()
    value_counts.columns = ["mass", "y_value", "weight"]  # sampling probability

    sampled = value_counts.sample(
        n=len(df_background),
        replace=True,
        weights="weight",
        random_state=seed,
    ).reset_index(drop=True)

    df_bkg = df_background.copy()
    df_bkg["mass"] = sampled["mass"].values
    df_bkg["y_value"] = sampled["y_value"].values
    return df_bkg

# -----------------------------
# Model (must match training)
# -----------------------------
class ParameterizedDNN(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.BatchNorm1d(16),
            nn.Dropout(0.3),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.BatchNorm1d(8),
            nn.Dropout(0.3),
            nn.Linear(8, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

# -----------------------------
# Inference helpers
# -----------------------------
def build_feature_matrix(df: pd.DataFrame, features_order: List[str]) -> pd.DataFrame:
    """Ensure required features, column order, and simple mean imputation for NaNs."""
    for c in features_order:
        if c not in df.columns:
            raise RuntimeError(f"Missing required feature '{c}' at inference time.")
    out = df[features_order].copy()
    out = out.fillna(out.mean(numeric_only=True))
    return downcast_float_cols(out)

def evaluate_point(
    all_probs: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
    masses: np.ndarray,
    yvals: np.ndarray,
    mass: int,
    yval: int,
    outdir: str,
) -> None:
    """Make per-point summaries and plots."""
    mask = (masses == mass) & (yvals == yval)
    n_pt = int(mask.sum())
    print(f"\n[Point] (X={mass}, Y={yval}) : {n_pt} events")
    if n_pt == 0:
        return

    probs = all_probs[mask]
    labs = labels[mask]
    wts = weights[mask]

    s_mask = labs == 1
    b_mask = labs == 0
    n_s, n_b = int(s_mask.sum()), int(b_mask.sum())
    W_s = float(wts[s_mask].sum()) if n_s else 0.0
    W_b = float(wts[b_mask].sum()) if n_b else 0.0
    print(f"  Unweighted counts: S={n_s}, B={n_b}")
    print(f"  Weighted sums:     S={W_s:.3e}, B={W_b:.3e}")

    # AUC if both classes present
    auc_pt = None
    if n_s > 0 and n_b > 0:
        auc_pt = roc_auc_score(labs, probs)
        print(f"  AUC: {auc_pt:.6f}")
    else:
        print("  AUC undefined (needs both S and B).")

    # Plots
    bins = np.linspace(0.0, 1.0, 51)

    plt.figure()
    plt.hist(probs[s_mask], bins=bins, histtype="step", linewidth=1.6, label="Signal")
    plt.hist(probs[b_mask], bins=bins, histtype="step", linewidth=1.6, label="Background")
    plt.xlabel("DNN output")
    plt.ylabel("Events")
    plt.title(f"Unweighted — X={mass}, Y={yval}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"sep_unweighted_X{mass}_Y{yval}.png"), dpi=150)
    plt.close()

    plt.figure()
    plt.hist(probs[s_mask], bins=bins, weights=wts[s_mask], histtype="step", linewidth=1.6, label="Signal")
    plt.hist(probs[b_mask], bins=bins, weights=wts[b_mask], histtype="step", linewidth=1.6, label="Background")
    plt.yscale("log")
    plt.xlabel("DNN output")
    plt.ylabel("Weighted events")
    plt.title(f"Weighted (log y) — X={mass}, Y={yval}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"sep_weighted_logy_X{mass}_Y{yval}.png"), dpi=150)
    plt.close()

    plt.figure()
    plt.hist(probs[s_mask], bins=bins, weights=wts[s_mask], density=True, histtype="step", linewidth=1.6, label="Signal")
    plt.hist(probs[b_mask], bins=bins, weights=wts[b_mask], density=True, histtype="step", linewidth=1.6, label="Background")
    plt.xlabel("DNN output")
    plt.ylabel("Density")
    plt.title(f"Weighted, normalized — X={mass}, Y={yval}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"sep_weighted_density_X{mass}_Y{yval}.png"), dpi=150)
    plt.close()

    if auc_pt is not None:
        fpr, tpr, _ = roc_curve(labs, probs)
        roc_auc = auc(fpr, tpr)
        plt.figure()
        plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}")
        plt.plot([0, 1], [0, 1], "k--", lw=1)
        plt.xlabel("False positive rate")
        plt.ylabel("True positive rate")
        plt.title(f"ROC — X={mass}, Y={yval}")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"roc_X{mass}_Y{yval}.png"), dpi=150)
        plt.close()

# -----------------------------
# Robust checkpoint loading
# -----------------------------
def load_state_dict_flexible(path: str, device: torch.device) -> dict:
    """Load a checkpoint and sanitize keys to match a plain nn.Module:
       - handles torch.compile wrapper (prefix '_orig_mod.')
       - handles DataParallel (prefix 'module.')
       - handles checkpoints saved as {'state_dict': ...} or raw state_dict
    """
    # Try to suppress pickle warning with weights_only if available
    try:
        state = torch.load(path, map_location=device, weights_only=True)  # PyTorch >= 2.4
    except TypeError:
        state = torch.load(path, map_location=device)

    # If wrapped inside a dict with a key like 'state_dict' or 'model'
    if isinstance(state, dict):
        # Heuristic: pick 'state_dict' if present; otherwise if looks like a raw sd, keep it
        if "state_dict" in state and isinstance(state["state_dict"], dict):
            state = state["state_dict"]

    if not isinstance(state, dict):
        raise RuntimeError("Loaded object is not a state_dict or a dict containing 'state_dict'.")

    cleaned = {}
    for k, v in state.items():
        new_k = k
        # strip common wrappers
        if new_k.startswith("_orig_mod."):
            new_k = new_k[len("_orig_mod."):]
        if new_k.startswith("module."):
            new_k = new_k[len("module."):]
        cleaned[new_k] = v
    return cleaned

# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="PDNN inference at specific mass points")
    ap.add_argument(
        "--signal-root",
        default="../../../output_parquet/final_production_Syst/merged",
        help="Base dir containing NMSSM_X{X}_Y{Y}/nominal/NOTAG_merged.parquet",
    )
    ap.add_argument(
        "--bkg",
        nargs="*",
        default=[],
        help='Background specs as path::tree (repeatable). If empty, built-in defaults are used. '
             'Example: ".../file.root::/GGJets/preselection"',
    )
    ap.add_argument(
        "--points",
        nargs="+",
        required=True,
        help="Mass points as 'X:Y' or 'X,Y' (e.g. 400:125 500:95 ...)",
    )
    ap.add_argument("--model", default="best_pdnn.pt", help="Path to saved model weights (.pt)")
    ap.add_argument("--scaler", default="scaler.pkl", help="Path to saved StandardScaler (joblib/pickle)")
    ap.add_argument(
        "--no-scaler",
        action="store_true",
        help="Skip scaling; pass raw features to the model (NOT recommended if the model was trained with scaling).",
    )
    ap.add_argument(
        "--fit-scaler-on-inference",
        action="store_true",
        help="If no scaler file is available, fit a StandardScaler on the current inference sample as a fallback.",
    )
    ap.add_argument("--background-frac", type=float, default=1.0, help="Optional pre-reduction of background (0-1].")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", default="inference_outputs")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Reproducibility
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    # Parse background specs
    if args.bkg:
        bkg_specs: List[Tuple[str, str]] = []
        for spec in args.bkg:
            if "::" not in spec:
                raise ValueError(f"--bkg entry must be path::tree, got '{spec}'")
            path, tree = spec.split("::", 1)
            bkg_specs.append((path, tree))
    else:
        bkg_specs = BACKGROUND_DEFAULT

    # Parse points
    points = parse_mass_points(args.points)
    print(f"[INFO] Evaluating points: {points}")

    # -----------------------------
    # Load data
    # -----------------------------
    signal_df = load_signal(args.signal_root, points)
    df_bkg = load_background(bkg_specs)

    if args.background_frac < 1.0 and len(df_bkg) > 0:
        df_bkg = df_bkg.sample(frac=args.background_frac, random_state=args.seed).reset_index(drop=True)

    # Tag background with (mass, y) to follow the loaded signal mixture
    df_bkg = tag_background_mass_y(df_bkg, signal_df, seed=args.seed)

    # Combine
    df_all = pd.concat([signal_df, df_bkg], ignore_index=True)

    # -----------------------------
    # Features & labels
    # -----------------------------
    features_df = build_feature_matrix(df_all, FEATURES_FINAL)
    labels = df_all["label"].astype(np.int8).values
    weights = df_all[WEIGHT_COL].astype("float32").values
    masses = df_all["mass"].astype(np.int32).values
    yvals = df_all["y_value"].astype(np.int32).values

    print(f"[INFO] N(all) = {len(df_all)}  |  N(features) = {len(features_df)}")
    print("[INFO] Feature order used for inference:")
    print("       ", FEATURES_FINAL)

    # -----------------------------
    # Scaler logic
    # -----------------------------
    scaler = None
    if not args.no_scaler:
        if os.path.exists(args.scaler):
            scaler = joblib.load(args.scaler)
            print(f"[INFO] Loaded scaler from '{args.scaler}'")
        else:
            if args.fit_scaler_on_inference:
                print("[WARN] Scaler file not found; fitting StandardScaler on the inference sample (may bias metrics).")
                scaler = StandardScaler().fit(features_df.values)
            else:
                print("[WARN] Scaler file not found and --fit-scaler-on-inference not set; proceeding WITHOUT scaling.")
    else:
        print("[INFO] --no-scaler: passing raw features to the model (not recommended).")

    X = features_df.values if scaler is None else scaler.transform(features_df.values)

    # -----------------------------
    # Model & inference
    # -----------------------------
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    model = ParameterizedDNN(X.shape[1]).to(device)

    if not os.path.exists(args.model):
        raise FileNotFoundError(f"Model weights '{args.model}' not found.")
    cleaned_state = load_state_dict_flexible(args.model, device)
    model.load_state_dict(cleaned_state, strict=True)

    model.eval()
    with torch.no_grad():
        xb = torch.tensor(X, dtype=torch.float32, device=device)
        logits = model(xb).view(-1)
        probs = torch.sigmoid(logits).cpu().numpy()

    # -----------------------------
    # Outputs
    # -----------------------------
    out_csv = os.path.join(args.outdir, "inference_scores.csv")
    out_df = pd.DataFrame(
        {
            "prob": probs,
            "label": labels,
            "weight": weights,
            "mass": masses,
            "y_value": yvals,
        }
    )
    out_df.to_csv(out_csv, index=False)
    print(f"[INFO] Wrote scores to {out_csv} (N={len(out_df)})")

    # Global sanity
    print("\n=== Global diagnostics ===")
    print("Any NaNs in probs?", np.isnan(probs).any())
    print("Range: {:.6f} → {:.6f}".format(float(np.min(probs)), float(np.max(probs))))

    # Per-point evaluation & plots
    for (xm, yv) in points:
        evaluate_point(probs, labels, weights, masses, yvals, xm, yv, args.outdir)

    print("\n[DONE] Inference complete.")

# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    main()
