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
  python score_folder.py -i /path/to/folder --recursive
Optional:
  --artifacts /path/to/artifacts   (default: current directory)
  --output /path/to/output         (default: "<input>/scored")
  --pattern "*.parquet"            (default)
  --recursive                      (recurse into subfolders)
  --mass-const 600 --y-const 100   (fallback only for files where (mass, y)
                                     cannot be auto-detected from the path,
                                     e.g. background / data samples)

Mass-point auto-detection
--------------------------
Each file's own path is searched for an "X###_Y###" pattern (matching the
convention used elsewhere in the pipeline, e.g. NMSSM_X700_Y500/nominal/...).
If found, that file is scored at ITS OWN (mass, y) hypothesis, regardless
of --mass-const/--y-const. Those flags are used ONLY as a fallback for
files where no such pattern is found anywhere in the path (background and
data samples, which have no physical mass/y label of their own).

This matters because "mass"/"y_value" are not physical detector quantities
-- they are training-time labels assigned from the signal filename/folder,
and are never present in the raw analysis ntuples for EITHER signal or
background. Falling back to a single global constant for every file in a
recursive run would silently score every signal mass point except the one
matching the constant at the wrong hypothesis.
"""

import argparse
import glob
import gc
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import pickle

import pyarrow as pa
import pyarrow.parquet as pq


# -----------------------------
# Defaults / constants
# -----------------------------
SAVE_MODEL_NAME = "outputs/models/best_pdnn.pt"
SCALER_NAME     = "outputs/models/scaler.pkl"
# pDNN_v2.py's Config.FEATURES_PATH saves "features.json". Older runs / other
# scripts have used "features_used.json". Both are tried, in this order,
# so a mismatch here fails loudly (with the exact paths checked) rather
# than silently pointing at a stale/missing file.
FEATLIST_CANDIDATES = ["outputs/models/features.json", "outputs/models/features_used.json"]
WEIGHT_COL      = "weight_central"

MASS_CONST = 600
Y_CONST    = 100

BATCH_SIZE = 16384
USE_AMP    = True  # mixed precision on CUDA

# Matches e.g. "NMSSM_X700_Y500", "x300_y95", anywhere in the path.
MASS_Y_RE = re.compile(r"[Xx](\d+)_[Yy](\d+)")

# Known systematic-variation folder naming convention: ends in "_up"/"_down"
# (ScaleEB_Zee_down, jec_syst_Total_up, Smearing_down, ...). "nominal" is
# its own special case, matched separately below.
SYSTEMATIC_VARIATION_RE = re.compile(r"(_up|_down)$", re.IGNORECASE)


def classify_systematic(file_path: Path):
    """Identify which systematic-variation folder (if any) a file belongs to.

    Returns "nominal" if a parent directory is literally named "nominal",
    the matched folder name (e.g. "jec_syst_Total_up") if a parent
    directory matches the "_up"/"_down" naming convention, or None if
    neither is found anywhere in the path -- i.e. this file shows no
    evidence of belonging to a systematic-variation family at all (a flat
    background/data file under the old folder layout, for example), and
    should always be kept regardless of the --all-systematics setting.
    """
    parts = [file_path.parent.name] + [p.name for p in file_path.parents]
    for part in parts:
        if part.lower() == "nominal":
            return "nominal"
    for part in parts:
        if SYSTEMATIC_VARIATION_RE.search(part):
            return part
    return None


# -----------------------------
# Mass-point auto-detection
# -----------------------------
def detect_mass_y_from_path(file_path: Path):
    """Search every component of a file's path for an X###_Y### pattern.

    Returns (mass, y) as ints if found anywhere in the path (checking the
    file's parent directories first, then the filename itself), else None.
    """
    for part in [file_path.parent.name] + [p.name for p in file_path.parents] + [file_path.name]:
        m = MASS_Y_RE.search(part)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


# -----------------------------
# Helpers to match training-time preprocessing
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
        dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
        df["DeltaR_gg"] = np.sqrt((df["lead_eta"] - df["sublead_eta"]) ** 2 + dphi ** 2)
    else:
        df["DeltaR_gg"] = 0.0

    for c in ["Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    for c in ["ptjj_over_mHH", "ptHH_over_mHH", "DeltaR_gg"]:
        df[c] = pd.Series(df[c]).replace([np.inf, -np.inf], np.nan).fillna(0)

    return df


def ensure_weight(df: pd.DataFrame, weight_col: str = WEIGHT_COL) -> pd.DataFrame:
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df


def impute_like_training(x_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Fill NaNs by sampling from each column's own observed values.

    Matches pDNN_v2.py's df_to_arrays() imputation exactly (sampling from
    the observed marginal, not a flat 0.0 or a mean-fill), so inference-time
    missingness handling doesn't diverge from what the model was trained
    on. A flat 0.0 fill in particular can sit far outside a feature's real
    (post-scaling) distribution and bias predictions for any row with a
    missing value.
    """
    x_df = x_df.copy()
    for col in x_df.columns:
        n_missing = int(x_df[col].isna().sum())
        if n_missing == 0:
            continue
        observed = x_df[col].dropna().values
        fill_values = rng.choice(observed, size=n_missing, replace=True) if len(observed) > 0 else 0.0
        x_df.loc[x_df[col].isna(), col] = fill_values
    return x_df


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
            nn.Linear(128, 64), maybe_bn(64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 32), maybe_bn(32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 1)
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
        xb = X_torch[i:i + BATCH_SIZE].to(device, non_blocking=True)
        if device.type == "cuda" and USE_AMP:
            with torch.amp.autocast("cuda"):
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
    feat_path = None
    for candidate in FEATLIST_CANDIDATES:
        p = artifacts_dir / candidate
        if p.exists():
            feat_path = p
            break
    if feat_path is None:
        checked = "\n    ".join(str(artifacts_dir / c) for c in FEATLIST_CANDIDATES)
        raise FileNotFoundError(f"No features file found. Checked:\n    {checked}")

    scaler_path = artifacts_dir / SCALER_NAME
    model_path = artifacts_dir / SAVE_MODEL_NAME

    if not scaler_path.exists():
        raise FileNotFoundError(f"Missing scaler file:   {scaler_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model file:    {model_path}")

    with open(feat_path, "r") as f:
        FEATURES = json.load(f)["features"]
    print(f"[INFO] Feature list loaded from {feat_path}")

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
    out_path: Path,
    FEATURES,
    scaler,
    model,
    device: torch.device,
    mass_const: int = MASS_CONST,
    y_const: int = Y_CONST,
    chunk_size: int = 100_000,
    seed: int = 42,
):
    """
    Memory-safe parquet scoring: reads, scores, and writes chunk-by-chunk,
    never holding the full file in RAM.

    (mass, y) are auto-detected from the file's own path (e.g.
    NMSSM_X700_Y500/...) when possible; mass_const/y_const are used only
    as a fallback for files with no such pattern in their path.
    """
    detected = detect_mass_y_from_path(file_path)
    if detected is not None:
        mass_val, y_val = detected
        print(f"  [mass/y] {file_path.name}: auto-detected ({mass_val}, {y_val}) from path")
    else:
        mass_val, y_val = mass_const, y_const
        print(f"  [mass/y] {file_path.name}: no X###_Y### pattern in path, "
              f"using fallback ({mass_val}, {y_val})")

    rng = np.random.default_rng(seed)
    parquet_file = pq.ParquetFile(file_path)
    writer = None

    for batch in parquet_file.iter_batches(batch_size=chunk_size):
        df = batch.to_pandas()

        df = ensure_photon_mva_columns(df)
        df = add_engineered_features(df)
        df = ensure_weight(df)

        # Always set mass/y_value to the resolved hypothesis for this file
        # (overwrite rather than "if missing", since a stray identically-
        # named column from upstream processing should not silently win).
        df["mass"] = mass_val
        df["y_value"] = y_val

        for f in FEATURES:
            if f not in df.columns:
                df[f] = np.nan  # let imputation handle it consistently, not a silent 0.0

        X = impute_like_training(df[FEATURES], rng)
        X_scaled = scaler.transform(X.values).astype("float32")
        X_t = torch.from_numpy(X_scaled)

        scores = predict_batched(model, X_t, device=device)
        df["pDNN_score"] = scores

        table = pa.Table.from_pandas(df, preserve_index=False)

        if writer is None:
            writer = pq.ParquetWriter(out_path, table.schema)
        writer.write_table(table)

        del df, X, X_scaled, X_t, scores, table
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()

    if writer is not None:
        writer.close()


# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Score all Parquet files in a folder with a trained Parameterized DNN.")
    ap.add_argument("-i", "--input", required=True, help="Input folder containing .parquet files")
    ap.add_argument("-o", "--output", default=None, help="Output folder for scored Parquets (default: <input>/scored)")
    ap.add_argument("--artifacts", default=".", help="Folder with best_pdnn.pt, scaler.pkl, features(.json|_used.json)")
    ap.add_argument("--pattern", default="*.parquet", help='Glob pattern for input files (default: "*.parquet")')
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--mass-const", type=int, default=MASS_CONST,
                     help=f"Fallback mass for files with no X###_Y### in their path, e.g. background/data "
                          f"(default: {MASS_CONST})")
    ap.add_argument("--y-const", type=int, default=Y_CONST,
                     help=f"Fallback y_value for files with no X###_Y### in their path (default: {Y_CONST})")
    ap.add_argument("--all-systematics", action="store_true",
                     help="Also score files under systematic-variation subfolders (e.g. "
                          "jec_syst_Total_up, Smearing_down, ScaleEE_Zee_up). Default: "
                          "score only 'nominal' (plus any file with no systematic-folder "
                          "structure at all, e.g. flat background/data files).")
    ap.add_argument("--min-mass", type=int, default=300,
                     help="Only score signal files with X >= this value (default: 300). "
                          "Files with no detectable X/Y in their path (background/data) "
                          "are always kept regardless of this setting.")
    ap.add_argument("--min-y", type=int, default=90,
                     help="Only score signal files with Y >= this value (default: 90). "
                          "Files with no detectable X/Y in their path (background/data) "
                          "are always kept regardless of this setting.")
    args = ap.parse_args()

    inp_dir = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve() if args.output else (inp_dir / "scored")
    art_dir = Path(args.artifacts).expanduser().resolve()

    if not inp_dir.is_dir():
        raise ValueError(f"Input is not a folder: {inp_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    FEATURES, scaler, model = load_artifacts(art_dir, device)
    print(f"[INFO] Loaded artifacts from {art_dir}")
    print(f"[INFO] Num features: {len(FEATURES)}")

    pattern = str(inp_dir / ("**/" + args.pattern if args.recursive else args.pattern))
    files = sorted(glob.glob(pattern, recursive=args.recursive))
    files = [Path(f) for f in files if Path(f).is_file()]

    if not files:
        print(f"[WARN] No files matched pattern {args.pattern} in {inp_dir}")
        return

    if not args.all_systematics:
        kept, skipped_systs = [], set()
        for fp in files:
            syst = classify_systematic(fp)
            if syst is None or syst == "nominal":
                kept.append(fp)
            else:
                skipped_systs.add(syst)
        if skipped_systs:
            print(f"[INFO] Restricting to 'nominal' (pass --all-systematics to also score "
                  f"the {len(files) - len(kept)} file(s) found under systematic-variation "
                  f"folders): {sorted(skipped_systs)}")
        files = kept

    # Restrict to the in-scope signal grid: X >= min-mass, Y > min-y.
    # Files with no detectable (mass, y) in their path -- background/data --
    # are always kept; this restriction only applies to signal mass points.
    kept, skipped_mass = [], []
    for fp in files:
        detected = detect_mass_y_from_path(fp)
        if detected is None:
            kept.append(fp)
            continue
        mass_val, y_val = detected
        if mass_val >= args.min_mass and y_val >= args.min_y:
            kept.append(fp)
        else:
            skipped_mass.append((fp, mass_val, y_val))
    if skipped_mass:
        print(f"[INFO] Skipping {len(skipped_mass)} file(s) outside the in-scope signal grid "
              f"(X >= {args.min_mass}, Y >= {args.min_y}):")
        for fp, m, y in skipped_mass:
            print(f"    (X={m}, Y={y}): {fp}")
    files = kept

    if not files:
        print("[WARN] No files left to score after filtering to 'nominal'. "
              "Pass --all-systematics if that's not what you intended.")
        return

    print(f"[INFO] Found {len(files)} file(s). Scoring...")

    total_rows = 0
    for fp in files:
        try:
            rel = fp.relative_to(inp_dir) if inp_dir in fp.parents or fp.parent == inp_dir else fp.name
            out_fp = out_dir / Path(rel).with_suffix(".parquet")
            out_fp.parent.mkdir(parents=True, exist_ok=True)

            score_parquet_file(
                file_path=fp,
                out_path=out_fp,
                FEATURES=FEATURES,
                scaler=scaler,
                model=model,
                device=device,
                mass_const=args.mass_const,
                y_const=args.y_const,
            )

            row_count = pq.ParquetFile(out_fp).metadata.num_rows
            total_rows += row_count
            print(f"  {fp.name:40s} -> {out_fp}  ({row_count} rows)")

        except Exception as e:
            print(f"  [ERROR] {fp}: {e}")

    print(f"[DONE] Scored {len(files)} file(s), {total_rows} total rows.")
    print(f"[OUT ] Output folder: {out_dir}")


if __name__ == "__main__":
    main()