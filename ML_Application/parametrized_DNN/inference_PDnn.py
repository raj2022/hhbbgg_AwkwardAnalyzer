# # eval_other_samples.py
# # Evaluate saved PDNN on *other* samples and plot Signal/Data/Background overlays.
# # Matches training features (engineered) and plotting style used in your script.

# import os, json, pickle, warnings
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# from typing import List, Dict, Optional, Tuple

# import torch
# import torch.nn as nn
# from sklearn.metrics import roc_curve, auc, roc_auc_score

# warnings.filterwarnings("ignore", category=UserWarning)

# # ------------------ Visual style (same as training) ------------------
# from matplotlib.colors import LinearSegmentedColormap
# from cycler import cycler

# plt.rcParams.update({
#     "figure.figsize": (7.5, 5.5),
#     "figure.dpi": 110,
#     "axes.grid": True,
#     "grid.alpha": 0.30,
#     "axes.titlesize": 14,
#     "axes.labelsize": 12,
#     "legend.fontsize": 10,
#     "xtick.labelsize": 10,
#     "ytick.labelsize": 10,
#     "lines.linewidth": 2.0,
# })
# CMS_BLUE   = "#2368B5"
# CMS_RED    = "#C0392B"
# CMS_ORANGE = "#E67E22"
# CMS_GREEN  = "#2E8B57"
# CMS_PURPLE = "#6C5CE7"
# CMS_GRAY   = "#4D4D4D"

# plt.rcParams["axes.prop_cycle"] = cycler(color=[
#     CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE, "#1ABC9C", "#8E44AD",
#     "#16A085", "#D35400", "#2C3E50"
# ])
# cms_div = LinearSegmentedColormap.from_list("cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256)

# # ------------------ Config ------------------
# SAVE_MODEL_PATH = "best_pdnn.pt"
# SCALER_PATH     = "scaler.pkl"
# FEATLIST_PATH   = "features_used.json"
# WEIGHT_COL      = "weight_central"
# EVAL_BATCH      = 32768
# USE_AMP_EVAL    = True
# CPU_FALLBACK_ON_OOM = True
# SEED = 42
# np.random.seed(SEED)
# torch.manual_seed(SEED)

# # ------------------ Helpers reused from training ------------------
# def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
#     for c in df.select_dtypes(include=["float64"]).columns:
#         df[c] = df[c].astype("float32")
#     return df

# def ensure_weight(df: pd.DataFrame, weight_col=WEIGHT_COL) -> pd.DataFrame:
#     if weight_col not in df.columns:
#         df[weight_col] = 1.0
#     return df

# def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
#     pairs = [("lead_mvaID_run3","lead_mvaID_nano"),
#              ("sublead_mvaID_run3","sublead_mvaID_nano")]
#     for want, alt in pairs:
#         if want not in df.columns and alt in df.columns:
#             df[want] = df[alt]
#     return df

# def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
#     mHH = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
#     mHH = mHH.replace(0, np.nan)

#     if "Res_dijet_pt" in df.columns:
#         df["ptjj_over_mHH"] = df["Res_dijet_pt"] / mHH
#     else:
#         df["ptjj_over_mHH"] = 0.0

#     if "Res_HHbbggCandidate_pt" in df.columns:
#         df["ptHH_over_mHH"] = df["Res_HHbbggCandidate_pt"] / mHH
#     else:
#         df["ptHH_over_mHH"] = 0.0

#     if all(c in df.columns for c in ["lead_phi","sublead_phi","lead_eta","sublead_eta"]):
#         dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
#         dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
#         deta = df["lead_eta"] - df["sublead_eta"]
#         df["DeltaR_gg"] = np.sqrt(deta**2 + dphi**2)
#     else:
#         df["DeltaR_gg"] = 0.0

#     for c in ["Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS"]:
#         if c in df.columns:
#             df[c] = df[c].abs()

#     for c in ["ptjj_over_mHH","ptHH_over_mHH","DeltaR_gg"]:
#         df[c] = df[c].fillna(0)
#     return df

# def df_to_X(df: pd.DataFrame, features: List[str]) -> np.ndarray:
#     Xdf = df[features].copy()
#     Xdf = Xdf.fillna(Xdf.mean(numeric_only=True))
#     Xdf = downcast_float_cols(Xdf)
#     return Xdf.values

# @torch.no_grad()
# def predict_batched(model: nn.Module, X_tensor: torch.Tensor, device: torch.device,
#                     batch: int = EVAL_BATCH, use_amp: bool = True) -> np.ndarray:
#     model.eval()
#     N = X_tensor.shape[0]
#     out = np.empty(N, dtype=np.float32)
#     amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type=="cuda"))
#     with amp_ctx:
#         for i in range(0, N, batch):
#             xb = X_tensor[i:i+batch].to(device, non_blocking=True)
#             logits = model(xb).view(-1)
#             out[i:i+batch] = torch.sigmoid(logits).detach().cpu().numpy()
#     return out

# def safe_eval_probs(model: nn.Module, X_tensor: torch.Tensor, device: torch.device) -> np.ndarray:
#     try:
#         return predict_batched(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL)
#     except RuntimeError as e:
#         if CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
#             print("[WARN] CUDA OOM during eval → falling back to CPU (batched).")
#             cpu_model = model.to(torch.device("cpu"))
#             X_cpu = X_tensor.to(torch.device("cpu"))
#             return predict_batched(cpu_model, X_cpu, torch.device("cpu"),
#                                    batch=max(8192, EVAL_BATCH), use_amp=False)
#         raise

# # ------------------ Model skeleton (must match training) ------------------
# class ParameterizedDNN(nn.Module):
#     def __init__(self, d):
#         super().__init__()
#         self.net = nn.Sequential(
#             nn.Linear(d, 128), nn.ReLU(), nn.Dropout(0.3),
#             nn.Linear(128,64), nn.ReLU(), nn.Dropout(0.3),
#             nn.Linear(64,32), nn.ReLU(), nn.Dropout(0.2),
#             nn.Linear(32, 1)
#         )
#     def forward(self, x): 
#         return self.net(x)

# # ------------------ I/O Layer ------------------
# def load_artifacts(model_path=SAVE_MODEL_PATH,
#                    scaler_path=SCALER_PATH,
#                    featlist_path=FEATLIST_PATH):
#     with open(featlist_path, "r") as f:
#         features = json.load(f)["features"]
#     with open(scaler_path, "rb") as f:
#         scaler = pickle.load(f)
#     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#     model = ParameterizedDNN(len(features)).to(device)
#     try:
#         state = torch.load(model_path, map_location=device, weights_only=True)
#     except TypeError:
#         state = torch.load(model_path, map_location=device)
#     model.load_state_dict(state)
#     print(f"[INFO] Loaded model '{model_path}', scaler, and {len(features)} features.")
#     return model, scaler, features, device

# def read_parquet_sample(path: str,
#                         label: Optional[int],
#                         mass: Optional[int] = None,
#                         y_value: Optional[int] = None,
#                         name: Optional[str] = None) -> Dict:
#     """
#     Reads a parquet file, adds engineered features, ensures weights and (mass,y) if needed.
#     label: 1 (signal), 0 (background), or None (data).
#     mass/y_value: optional constants to fill if absent in file (required if features expect them).
#     """
#     if not os.path.exists(path):
#         raise FileNotFoundError(path)
#     df = pd.read_parquet(path)
#     df = ensure_photon_mva_columns(df)
#     df = add_engineered_features(df)
#     df = ensure_weight(df)
#     if "mass" not in df.columns or "y_value" not in df.columns:
#         if (mass is None) or (y_value is None):
#             raise ValueError(f"{name or path}: 'mass'/'y_value' missing in file and no constants provided.")
#         df["mass"] = mass
#         df["y_value"] = y_value
#     if label is not None:
#         df["label"] = int(label)
#     return {
#         "name": name or os.path.basename(path),
#         "path": path,
#         "df": downcast_float_cols(df)
#     }

# # ------------------ Evaluation & Plots ------------------
# def evaluate_samples(model, scaler, features, device,
#                      signals: List[Dict],
#                      backgrounds: List[Dict],
#                      datas: List[Dict],
#                      out_prefix: str = "eval"):
#     """
#     signals/backgrounds/datas: each is a list of dicts returned by read_parquet_sample().
#     """
#     # Build one big DF for S+B (for ROC) and separate DFs for per-sample hists
#     parts_sb = []
#     for s in signals:
#         parts_sb.append(s["df"])
#     for b in backgrounds:
#         parts_sb.append(b["df"])
#     df_sb = pd.concat(parts_sb, ignore_index=True)
#     if "label" not in df_sb.columns or df_sb["label"].nunique() != 2:
#         raise RuntimeError("Signal/Background mix must have 'label' ∈ {0,1} to compute ROC.")

#     # Transform using training scaler (order must match)
#     X_sb_raw = df_sb[features].copy()
#     X_sb_raw = X_sb_raw.fillna(X_sb_raw.mean(numeric_only=True))
#     X_sb = scaler.transform(X_sb_raw.values)
#     X_sb_t = torch.tensor(X_sb, dtype=torch.float32).to(device)
#     scores_sb = safe_eval_probs(model, X_sb_t, device)
#     y_sb = df_sb["label"].astype(int).values
#     w_sb = df_sb[WEIGHT_COL].astype("float32").values if WEIGHT_COL in df_sb.columns else None

#     # Compute global ROC/AUC
#     fpr, tpr, _ = roc_curve(y_sb, scores_sb, sample_weight=w_sb)
#     auc_all = auc(fpr, tpr)
#     print(f"[INFO] Overall ROC AUC (S vs B): {auc_all:.6f}")

#     # Per-bucket score arrays for plotting
#     def slice_scores(d: Dict) -> Tuple[np.ndarray, Optional[np.ndarray]]:
#         Xr = d["df"][features].copy()
#         Xr = Xr.fillna(Xr.mean(numeric_only=True))
#         X = scaler.transform(Xr.values)
#         Xt = torch.tensor(X, dtype=torch.float32).to(device)
#         s = safe_eval_probs(model, Xt, device)
#         w = d["df"][WEIGHT_COL].astype("float32").values if WEIGHT_COL in d["df"].columns else None
#         return s, w

#     sig_scores = []
#     for s in signals:
#         sc, w = slice_scores(s)
#         sig_scores.append((s["name"], sc, w))

#     bkg_scores = []
#     for b in backgrounds:
#         sc, w = slice_scores(b)
#         bkg_scores.append((b["name"], sc, w))

#     data_scores = []
#     for d in datas:
#         sc, w = slice_scores(d)
#         data_scores.append((d["name"], sc, w))

#     # ---------- Plots ----------
#     bins = np.linspace(0.0, 1.0, 51)

#     # (1) Unweighted shapes: Signal vs each Background + Data overlaid
#     plt.figure()
#     for name, sc, _ in bkg_scores:
#         plt.hist(sc, bins=bins, density=True, histtype="step", linewidth=2.0, label=f"Bkg: {name}")
#     for name, sc, _ in sig_scores:
#         plt.hist(sc, bins=bins, density=True, histtype="step", linewidth=2.2, label=f"Sig: {name}")
#     for name, sc, _ in data_scores:
#         # plot data as points (density)
#         hist, edges = np.histogram(sc, bins=bins, density=True)
#         centers = 0.5*(edges[:-1]+edges[1:])
#         plt.plot(centers, hist, marker="o", linestyle="", label=f"Data: {name}")
#     plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
#     plt.title("Score distributions — unweighted (Signal / Backgrounds / Data)")
#     plt.legend(ncol=2, fontsize=9)
#     plt.tight_layout(); plt.savefig(f"{out_prefix}_shapes_unweighted.png"); plt.show()

#     # (2) Weighted counts (log-y): S vs each B, plus Data (unit weight)
#     plt.figure()
#     for name, sc, w in bkg_scores:
#         plt.hist(sc, bins=bins, weights=w, histtype="step", linewidth=2.0, label=f"Bkg: {name}")
#     for name, sc, w in sig_scores:
#         plt.hist(sc, bins=bins, weights=w, histtype="step", linewidth=2.0, label=f"Sig: {name}")
#     for name, sc, _ in data_scores:
#         plt.hist(sc, bins=bins, weights=np.ones_like(sc), histtype="step", linewidth=1.6, label=f"Data: {name}")
#     plt.yscale("log"); plt.xlabel("DNN output (probability)"); plt.ylabel("Events (weighted)")
#     plt.title("Score distributions — weighted (log y)")
#     plt.legend(ncol=2, fontsize=9); plt.tight_layout()
#     plt.savefig(f"{out_prefix}_counts_weighted.png"); plt.show()

#     # (3) Combined ROC (all signal vs all background, weighted)
#     plt.figure()
#     plt.plot(fpr, tpr, label=f"All (AUC = {auc_all:.3f})", color=CMS_BLUE, lw=2.4)
#     plt.plot([0,1],[0,1], linestyle="--", color=CMS_GRAY, lw=1)
#     plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
#     plt.title("ROC — other samples")
#     plt.legend(loc="lower right"); plt.tight_layout()
#     plt.savefig(f"{out_prefix}_roc.png"); plt.show()

#     # (4) Optional: per-sample ROC for each signal vs combined backgrounds
#     # Build combined background arrays once
#     bkg_all_scores = np.concatenate([sc for _, sc, _ in bkg_scores]) if bkg_scores else np.array([])
#     bkg_all_weights = np.concatenate([w for _, _, w in bkg_scores if w is not None]) if bkg_scores and (bkg_scores[0][2] is not None) else None

#     if bkg_all_scores.size:
#         plt.figure()
#         for name, sc, w in sig_scores:
#             y = np.concatenate([np.ones_like(sc), np.zeros_like(bkg_all_scores)])
#             s = np.concatenate([sc, bkg_all_scores])
#             if w is not None and bkg_all_weights is not None:
#                 ww = np.concatenate([w, bkg_all_weights])
#             else:
#                 ww = None
#             fpr_g, tpr_g, _ = roc_curve(y, s, sample_weight=ww)
#             auc_g = auc(fpr_g, tpr_g)
#             plt.plot(fpr_g, tpr_g, lw=2.0, label=f"{name} (AUC {auc_g:.3f})")
#         plt.plot([0,1],[0,1], "k--", lw=1)
#         plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
#         plt.title("Per-signal ROC vs combined backgrounds")
#         plt.legend(fontsize=9); plt.tight_layout()
#         plt.savefig(f"{out_prefix}_roc_per_signal.png"); plt.show()

#     print("[DONE] Wrote: "
#           f"{out_prefix}_shapes_unweighted.png, "
#           f"{out_prefix}_counts_weighted.png, "
#           f"{out_prefix}_roc.png"
#           + (", "+f"{out_prefix}_roc_per_signal.png" if bkg_all_scores.size else ""))

# # ------------------ Example usage ------------------
# if __name__ == "__main__":
#     """
#     Edit these lists to point to your *other* samples.
#     For files that do NOT carry 'mass' and 'y_value' columns, provide constants.
#     """
#     model, scaler, features, device = load_artifacts()

#     # --- Signals (label=1) ---
#     signals = [
#         # If file already has mass/y_value columns, you can omit mass=..., y_value=...
#         read_parquet_sample(
#             path="../../../output_parquet/final_production_Syst/merged/NMSSM_X600_Y100/nominal/NOTAG_merged.parquet",
#             label=1, mass=600, y_value=100, name="NMSSM_X600_Y100"
#         ),
#         # Add more as needed...
#     ]

#     # --- Backgrounds (label=0) ---
#     backgrounds = [
#         read_parquet_sample(
#             path="../../../output_root/v3_production/samples/postEE/GGJets.parquet",
#             label=0, mass=600, y_value=100, name="GGJets"
#         ),
#         read_parquet_sample(
#             path="../../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
#             label=0, mass=600, y_value=100, name="GJetPt40"
#         ),
#         # Add more as needed...
#     ]

#     # --- Data (label=None) ---
#     datas = [
#         read_parquet_sample(
#             path="../../../output_root/v3_production/samples/postEE/DataDoublePhoton.parquet",
#             label=None, mass=600, y_value=100, name="Data"
#         ),
#         # Add more runs/eras if you want separate overlays
#     ]

#     evaluate_samples(model, scaler, features, device,
#                      signals=signals,
#                      backgrounds=backgrounds,
#                      datas=datas,
#                      out_prefix="otherSamples")





#!/usr/bin/env python3
"""
Score all Parquet files in a folder with a Parameterized DNN.

Usage:
  python score_folder.py -i /path/to/folder
Optional:
  --artifacts /path/to/artifacts   (default: current directory)
  --output /path/to/output         (default: "<input>/scored")
  --pattern "*.parquet"            (default)
  --recursive                      (recurse into subfolders)
  --mass-const 600 --y-const 100   (used if file lacks 'mass' / 'y_value')
"""

import argparse
import glob
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import pickle


# -----------------------------
# Defaults / constants
# -----------------------------
SAVE_MODEL_NAME = "best_pdnn.pt"
SCALER_NAME     = "scaler.pkl"
FEATLIST_NAME   = "features_used.json"
WEIGHT_COL      = "weight_central"

MASS_CONST = 600
Y_CONST    = 100

BATCH_SIZE = 65536
USE_AMP    = True  # mixed precision on CUDA


# -----------------------------
# Helpers to match your notebook
# -----------------------------
def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fallback for older NanoAOD-like columns."""
    for want, alt in [("lead_mvaID_run3", "lead_mvaID_nano"),
                      ("sublead_mvaID_run3", "sublead_mvaID_nano")]:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create the engineered features used at training time."""
    mHH = df.get("Res_HHbbggCandidate_mass",
                 pd.Series(index=df.index, dtype="float32")).replace(0, np.nan)

    df["ptjj_over_mHH"] = (df["Res_dijet_pt"] / mHH) if "Res_dijet_pt" in df.columns else 0.0
    df["ptHH_over_mHH"] = (df["Res_HHbbggCandidate_pt"] / mHH) if "Res_HHbbggCandidate_pt" in df.columns else 0.0

    if all(c in df.columns for c in ["lead_phi", "sublead_phi", "lead_eta", "sublead_eta"]):
        dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
        dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
        df["DeltaR_gg"] = np.sqrt((df["lead_eta"] - df["sublead_eta"])**2 + dphi**2)
    else:
        df["DeltaR_gg"] = 0.0

    for c in ["Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    for c in ["ptjj_over_mHH", "ptHH_over_mHH", "DeltaR_gg"]:
        df[c] = df[c].fillna(0)

    return df

def ensure_weight(df: pd.DataFrame, weight_col: str = WEIGHT_COL) -> pd.DataFrame:
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df


# -----------------------------
# Model
# -----------------------------
def maybe_bn(_):  # BatchNorm was disabled in the notebook you shared
    return nn.Identity()

class ParameterizedDNN(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 128), maybe_bn(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128,  64), maybe_bn(64),  nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64,   32), maybe_bn(32),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32,    1)
        )

    def forward(self, x):
        return self.net(x)


# -----------------------------
# Scoring
# -----------------------------
@torch.no_grad()
def predict_batched(model: nn.Module, X_torch: torch.Tensor, device: torch.device) -> np.ndarray:
    """
    Returns probabilities in [0,1] for the positive class.
    Supports models with 1-logit (sigmoid) or 2-logit (softmax) heads.
    """
    model.eval()
    out = []
    N = X_torch.shape[0]
    for i in range(0, N, BATCH_SIZE):
        xb = X_torch[i:i+BATCH_SIZE].to(device, non_blocking=True)
        if device.type == "cuda" and USE_AMP:
            with torch.cuda.amp.autocast():
                logits = model(xb)
        else:
            logits = model(xb)

        if logits.ndim == 1 or logits.shape[1] == 1:
            prob = torch.sigmoid(logits).reshape(-1)
        elif logits.shape[1] == 2:
            prob = torch.softmax(logits, dim=1)[:, 1]
        else:
            raise ValueError(f"Unexpected model output shape: {tuple(logits.shape)}")

        out.append(prob.detach().cpu())
        del xb, logits, prob
        if device.type == "cuda":
            torch.cuda.empty_cache()

    return torch.cat(out).numpy().astype("float32")


def load_artifacts(artifacts_dir: Path, device: torch.device):
    feat_path = artifacts_dir / FEATLIST_NAME
    scaler_path = artifacts_dir / SCALER_NAME
    model_path = artifacts_dir / SAVE_MODEL_NAME

    if not feat_path.exists():
        raise FileNotFoundError(f"Missing features file: {feat_path}")
    if not scaler_path.exists():
        raise FileNotFoundError(f"Missing scaler file:   {scaler_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model file:    {model_path}")

    with open(feat_path, "r") as f:
        FEATURES = json.load(f)["features"]

    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    model = ParameterizedDNN(len(FEATURES)).to(device)
    try:
        state = torch.load(model_path, map_location=device, weights_only=True)
    except TypeError:
        # older PyTorch doesn't support weights_only
        state = torch.load(model_path, map_location=device)
    model.load_state_dict(state)
    model.eval()

    return FEATURES, scaler, model


def score_parquet_file(
    file_path: Path,
    FEATURES,
    scaler,
    model,
    device: torch.device,
    mass_const: int = MASS_CONST,
    y_const: int = Y_CONST,
) -> pd.DataFrame:
    """Read a Parquet, align features, scale, score, and return a DF with pDNN_score added."""
    df = pd.read_parquet(file_path)

    # Align with training-time expectations
    df = ensure_photon_mva_columns(df)
    df = add_engineered_features(df)
    df = ensure_weight(df)

    # Inject constants if missing
    if "mass" not in df.columns:
        df["mass"] = mass_const
    if "y_value" not in df.columns:
        df["y_value"] = y_const

    # Ensure every model feature exists
    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0

    # Build X in the correct column order
    X = df[FEATURES].copy()
    # Fill NaNs with column means (fallback)
    X = X.fillna(X.mean(numeric_only=True))
    # Scale as at training time
    X_scaled = scaler.transform(X.values).astype("float32")

    # Torch & predict
    X_t = torch.tensor(X_scaled, dtype=torch.float32)
    scores = predict_batched(model, X_t, device=device)

    df["pDNN_score"] = scores
    return df


# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Score all Parquet files in a folder with a trained Parameterized DNN.")
    ap.add_argument("-i", "--input", required=True, help="Input folder containing .parquet files")
    ap.add_argument("-o", "--output", default=None, help="Output folder for scored Parquets (default: <input>/scored)")
    ap.add_argument("--artifacts", default=".", help="Folder with best_pdnn.pt, scaler.pkl, features_used.json")
    ap.add_argument("--pattern", default="*.parquet", help='Glob pattern for input files (default: "*.parquet")')
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--mass-const", type=int, default=MASS_CONST, help=f"Default mass if column missing (default: {MASS_CONST})")
    ap.add_argument("--y-const", type=int, default=Y_CONST, help=f"Default y_value if column missing (default: {Y_CONST})")
    args = ap.parse_args()

    inp_dir = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve() if args.output else (inp_dir / "scored")
    art_dir = Path(args.artifacts).expanduser().resolve()

    if not inp_dir.is_dir():
        raise ValueError(f"Input is not a folder: {inp_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    # Load artifacts
    FEATURES, scaler, model = load_artifacts(art_dir, device)
    print(f"[INFO] Loaded artifacts from {art_dir}")
    print(f"[INFO] Num features: {len(FEATURES)}")

    # Collect files
    pattern = str(inp_dir / ("**/" + args.pattern if args.recursive else args.pattern))
    files = sorted(glob.glob(pattern, recursive=args.recursive))
    files = [Path(f) for f in files if Path(f).is_file()]

    if not files:
        print(f"[WARN] No files matched pattern {args.pattern} in {inp_dir}")
        return

    print(f"[INFO] Found {len(files)} file(s). Scoring...")

    # Process
    total_rows = 0
    for fp in files:
        try:
            df_scored = score_parquet_file(
                fp, FEATURES, scaler, model, device,
                mass_const=args.mass_const, y_const=args.y_const
            )
            rel = fp.relative_to(inp_dir) if inp_dir in fp.parents or fp.parent == inp_dir else fp.name
            out_fp = out_dir / Path(rel).with_suffix(".parquet")
            out_fp.parent.mkdir(parents=True, exist_ok=True)
            df_scored.to_parquet(out_fp, index=False)
            total_rows += len(df_scored)
            print(f"  ✓ {fp.name:40s} -> {out_fp}  ({len(df_scored)} rows)")
        except Exception as e:
            print(f"  ✗ {fp.name}: {e}")

    print(f"[DONE] Scored {len(files)} file(s), {total_rows} total rows.")
    print(f"[OUT ] Output folder: {out_dir}")

if __name__ == "__main__":
    main()
