# #!/usr/bin/env python
# # =============================================================================
# # pDNN_v2.py
# #
# # Parameterized Deep Neural Network (pDNN) for the CMS HH -> bbgg resonant
# # search (NMSSM).  Production-quality refactor of the original working
# # training script.  Physics, training strategy, and outputs are preserved;
# # this file focuses on software-engineering quality (modularity, typing,
# # documentation, reproducibility).
# #
# # Run with:
# #     python pDNN_v2.py
# # =============================================================================

# from __future__ import annotations

# # =============================================================================
# # 1. IMPORTS
# # =============================================================================
# import json
# import os
# import pickle
# import warnings
# from collections import defaultdict
# from dataclasses import dataclass
# from datetime import datetime, timezone
# from typing import Dict, List, Optional, Sequence, Tuple

# import numpy as np
# import pandas as pd
# import torch
# import torch.nn as nn
# from cycler import cycler
# from matplotlib.colors import LinearSegmentedColormap
# from scipy.stats import ks_2samp
# from sklearn.metrics import (
#     accuracy_score,
#     auc,
#     brier_score_loss,
#     classification_report,
#     confusion_matrix,
#     roc_auc_score,
#     roc_curve,
# )
# from sklearn.model_selection import GroupShuffleSplit
# from sklearn.preprocessing import StandardScaler
# from torch.optim import AdamW
# from torch.optim.lr_scheduler import ReduceLROnPlateau
# from torch.utils.data import DataLoader, Dataset

# import matplotlib

# matplotlib.use("Agg")  # safe for batch / non-interactive execution
# import matplotlib.pyplot as plt  # noqa: E402

# warnings.filterwarnings("ignore", category=UserWarning)


# # =============================================================================
# # 2. CONFIGURATION
# #
# # Every tunable parameter for the analysis lives here. Nothing below this
# # section should define a "magic number" constant outside of this class.
# # =============================================================================
# @dataclass(frozen=True)
# class Config:
#     """Single source of truth for all pDNN configuration."""

#     # --- reproducibility ---
#     SEED: int = 42

#     # --- inputs ---
#     SIG_TPL: str = (
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/NMSSM_X{m}_Y{y}.parquet"
#     )
#     BACKGROUND_FILES: Tuple[str, ...] = (
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/GGJets_MGG-40to80.parquet",
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/GGJets_MGG-80.parquet",
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/DDQCDGJET_Rescaled.parquet",
#     )
#     MASS_POINTS: Tuple[int, ...] = (300, 400, 500, 550, 600, 650, 700, 800, 900, 1000)
#     Y_VALUES: Tuple[int, ...] = (90, 95, 100, 125, 150, 200, 300, 400, 500, 600, 800)
#     WEIGHT_COL: str = "weight_central"

#     # --- data handling ---
#     BACKGROUND_FRAC: float = 1.0          # 1.0 = keep all background
#     BALANCE_PER_GROUP: bool = True        # balance S=B inside each (mass,y) after split
#     TEST_SIZE: float = 0.20               # outer split (train+val vs test)
#     VAL_SIZE: float = 0.20                # inner split (train vs val)
#     DROP_FEATURES: Tuple[str, ...] = ()   # optional ablation
#     ENABLE_CORR_PRUNING: bool = True      # drop redundant (highly correlated) features
#     CORR_PRUNE_THRESHOLD: float = 0.95    # |Pearson r|, computed on real (non-imputed) values

#     # --- model architecture ---
#     HIDDEN_LAYERS: Tuple[int, ...] = (128, 64, 32)
#     DROPOUT: Tuple[float, ...] = (0.3, 0.3, 0.2)
#     USE_BATCHNORM: bool = False
#     INIT_WEIGHT_STD: float = 1e-2         # small-normal init (stabilizes early training)

#     # --- training ---
#     BATCH_SIZE: int = 128
#     LEARNING_RATE: float = 1e-3
#     WEIGHT_DECAY: float = 1e-4
#     MAX_EPOCHS: int = 500
#     PATIENCE: int = 5
#     WEIGHT_CLIP: float = 10.0
#     LR_PATIENCE: int = 5
#     LR_FACTOR: float = 0.5
#     USE_AMP: bool = True                  # mixed precision on CUDA (train + eval)

#     # --- evaluation ---
#     EVAL_BATCH: int = 32768
#     CPU_FALLBACK_ON_OOM: bool = True
#     N_PERMUTATION_REPEATS: int = 5
#     INCLUDE_MASS_Y_IN_IMPORTANCE: bool = True

#     # --- physics validation (mass sculpting) ---
#     # Column used as the resonance-mass proxy for sculpting checks. Not all
#     # ntuples carry a dedicated diphoton mass column, so a short candidate
#     # list is tried in order; the first one present in the dataframe is used.
#     MASS_SCULPT_CANDIDATES: Tuple[str, ...] = (
#         "diphoton_mass", "mass_gg", "CMS_hgg_mass", "mgg", "Res_HHbbggCandidate_mass",
#     )
#     SCORE_CUTS: Tuple[float, ...] = (0.0, 0.3, 0.5, 0.7, 0.9)

#     # --- debug toggles ---
#     DEBUG_ONE_BATCH: bool = False
#     DEBUG_SHUFFLE_TRAIN_LABELS: bool = False

#     # --- outputs ---
#     OUTPUT_DIR: str = "outputs"
#     SAVE_MODEL: bool = True

#     # derived (filled in __post_init__ equivalent via property)
#     @property
#     def MODEL_DIR(self) -> str:
#         return os.path.join(self.OUTPUT_DIR, "models")

#     @property
#     def PLOT_DIR(self) -> str:
#         return os.path.join(self.OUTPUT_DIR, "plots")

#     @property
#     def LOG_DIR(self) -> str:
#         return os.path.join(self.OUTPUT_DIR, "logs")

#     @property
#     def MODEL_PATH(self) -> str:
#         return os.path.join(self.MODEL_DIR, "best_pdnn.pt")

#     @property
#     def SCALER_PATH(self) -> str:
#         return os.path.join(self.MODEL_DIR, "scaler.pkl")

#     @property
#     def FEATURES_PATH(self) -> str:
#         return os.path.join(self.MODEL_DIR, "features.json")


# CFG = Config()

# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# np.random.seed(CFG.SEED)
# torch.manual_seed(CFG.SEED)
# torch.cuda.manual_seed_all(CFG.SEED)
# torch.backends.cudnn.deterministic = True
# torch.backends.cudnn.benchmark = False


# # =============================================================================
# # 3. PLOT STYLE
# # =============================================================================
# CMS_BLUE = "#2368B5"
# CMS_RED = "#C0392B"
# CMS_ORANGE = "#E67E22"
# CMS_GREEN = "#2E8B57"
# CMS_PURPLE = "#6C5CE7"
# CMS_GRAY = "#4D4D4D"

# CMS_DIVERGING_CMAP = LinearSegmentedColormap.from_list(
#     "cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256
# )


# def apply_cms_plot_style() -> None:
#     """Apply the CMS-like matplotlib style used throughout this script."""
#     plt.rcParams.update({
#         "figure.figsize": (7.5, 5.5),
#         "figure.dpi": 110,
#         "axes.grid": True,
#         "grid.alpha": 0.30,
#         "axes.titlesize": 14,
#         "axes.labelsize": 12,
#         "legend.fontsize": 10,
#         "xtick.labelsize": 10,
#         "ytick.labelsize": 10,
#         "lines.linewidth": 2.0,
#     })
#     plt.rcParams["axes.prop_cycle"] = cycler(color=[
#         CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE,
#         "#1ABC9C", "#8E44AD", "#16A085", "#D35400", "#2C3E50",
#     ])


# # =============================================================================
# # 4. FEATURE DEFINITIONS
# # =============================================================================
# FEATURES_CORE: List[str] = [
#     "lead_eta", "lead_phi", "sublead_eta", "sublead_phi",
#     "Res_dijet_eta", "Res_dijet_phi",
#     "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi", "Res_HHbbggCandidate_pt",
#     "Res_dijet_mass_DNNreg",
#     "Res_DeltaR_jg_min",
#     "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
#     "lead_mvaID",
#     "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi", "Njets2p5",
#     "Res_DeltaPhi_j1MET", "Res_DeltaPhi_j2MET",
#     "Res_chi_t0", "Res_chi_t1",
#     "Res_dijet_pt", "Res_dijet_mass",
#     "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
#     "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
#     "sigma_m_over_m",
#     "Res_M_X",
#     "lead_r9", "sublead_r9",
#     # engineered (added by add_engineered_features)
#     "ptjj_over_mHH", "ptHH_over_mHH",
# ]

# # Raw columns worth requesting explicitly when reading parquet files (keeps
# # I/O light while guaranteeing everything needed for engineered features
# # and fallbacks is available).
# RAW_COLUMNS_OF_INTEREST: List[str] = [
#     "lead_eta", "lead_phi", "sublead_eta", "sublead_phi", "eta", "phi",
#     "Res_lead_bjet_eta", "Res_lead_bjet_phi",
#     "Res_sublead_bjet_eta", "Res_sublead_bjet_phi",
#     "Res_dijet_eta", "Res_dijet_phi",
#     "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi",
#     "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
#     "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
#     "Res_DeltaR_j1g1", "Res_DeltaR_j1g2",
#     "Res_DeltaR_j2g1", "Res_DeltaR_j2g2", "Res_DeltaR_jg_min",
#     "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
#     "lead_mvaID_run3", "sublead_mvaID_run3",
#     "lead_mvaID_nano", "sublead_mvaID_nano",
#     "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
#     "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi",
#     "Res_chi_t0", "Res_chi_t1",
#     "Res_dijet_pt", "Res_HHbbggCandidate_pt", "Res_HHbbggCandidate_mass",
#     "mass",  # raw diphoton invariant mass -> renamed to "diphoton_mass" in _prepare_raw
#              # to avoid colliding with the "mass" column used for the signal grid point.
# ]


# # =============================================================================
# # 5. UTILITY FUNCTIONS
# # =============================================================================
# def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
#     """Downcast all float64 columns to float32 in place (memory/speed)."""
#     for c in df.select_dtypes(include=["float64"]).columns:
#         df[c] = df[c].astype("float32")
#     return df


# def ensure_weight(df: pd.DataFrame, weight_col: str = CFG.WEIGHT_COL) -> pd.DataFrame:
#     """Guarantee an event-weight column exists (defaults to 1.0)."""
#     if weight_col not in df.columns:
#         df[weight_col] = 1.0
#     return df


# def group_key(df: pd.DataFrame) -> pd.Series:
#     """Build the (mass, y_value) string group key used for grouped splits."""
#     return df["mass"].astype(int).astype(str) + "_" + df["y_value"].astype(int).astype(str)


# def df_to_arrays(df: pd.DataFrame, feature_list: Sequence[str], seed: int = CFG.SEED) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
#     """Convert a dataframe split into (X, y, w) numpy arrays for modeling.

#     Missing values are imputed by sampling from each column's own observed
#     distribution, not by mean-filling. Mean-filling collapses every event
#     missing a given quantity (e.g. events without a resolved dijet) onto
#     the *same* value in every affected column simultaneously; since those
#     events tend to be missing several related columns at once, that
#     manufactures artificial near-1.0 correlation between otherwise
#     unrelated features (an imputation artifact, not real physics).
#     Sampling from the observed marginal avoids that collapse.
#     """
#     x_df = df[list(feature_list)].copy()
#     rng = np.random.default_rng(seed)
#     for col in x_df.columns:
#         n_missing = int(x_df[col].isna().sum())
#         if n_missing == 0:
#             continue
#         observed = x_df[col].dropna().values
#         fill_values = rng.choice(observed, size=n_missing, replace=True) if len(observed) > 0 else 0.0
#         x_df.loc[x_df[col].isna(), col] = fill_values
#     x_df = downcast_float_cols(x_df)
#     x = x_df.values
#     y = df["label"].astype(np.int8).values
#     w = df[CFG.WEIGHT_COL].astype("float32").values
#     return x, y, w


# def balance_groups(df: pd.DataFrame, seed: int = CFG.SEED, min_per_class: int = 1) -> pd.DataFrame:
#     """Down-sample signal/background to equal counts within each (mass,y) group.

#     Groups with fewer than ``min_per_class`` events in either class are
#     dropped entirely (pure groups cannot be balanced).
#     """
#     key = group_key(df)
#     parts, dropped = [], 0
#     for _, sub in df.groupby(key, sort=False):
#         vc = sub["label"].value_counts()
#         if len(vc) < 2 or vc.min() < min_per_class:
#             dropped += 1
#             continue
#         n_min = vc.min()
#         sig = sub[sub["label"] == 1]
#         bkg = sub[sub["label"] == 0]
#         sig_keep = sig.sample(n=n_min, random_state=seed) if len(sig) > n_min else sig
#         bkg_keep = bkg.sample(n=n_min, random_state=seed) if len(bkg) > n_min else bkg
#         parts.append(pd.concat([sig_keep, bkg_keep], ignore_index=True))

#     if not parts:
#         raise RuntimeError("Per-group balancing removed all groups; relax constraints or inspect data.")

#     out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
#     if dropped:
#         print(f"[INFO] balance_groups: dropped {dropped} tiny/pure groups in this split.")
#     return out


# def check_groups(df: pd.DataFrame, name: str) -> None:
#     """Assert both classes are present and warn about any remaining pure groups."""
#     key = group_key(df)
#     bad = [(k, int(g["label"].iloc[0]), len(g)) for k, g in df.groupby(key) if g["label"].nunique() < 2]
#     if bad:
#         print(f"[WARN] {name}: {len(bad)} pure (mass,y) groups remain. Examples: {bad[:5]}")
#     assert df["label"].nunique() == 2, f"{name} has only one class!"


# def split_summary(df: pd.DataFrame, name: str) -> None:
#     """Print a one-line summary (N, class counts, #groups) for a split."""
#     key = group_key(df)
#     print(f"{name}: N={len(df):,}  counts={df['label'].value_counts().to_dict()}  groups={key.nunique()}")


# @torch.no_grad()
# def predict_batched(model: nn.Module, x_tensor: torch.Tensor, device: torch.device,
#                      batch: int = CFG.EVAL_BATCH, use_amp: bool = True) -> np.ndarray:
#     """Run the model over ``x_tensor`` in chunks and return sigmoid probabilities."""
#     model.eval()
#     n = x_tensor.shape[0]
#     out = np.empty(n, dtype=np.float32)
#     amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type == "cuda"))
#     with amp_ctx:
#         for i in range(0, n, batch):
#             xb = x_tensor[i:i + batch].to(device, non_blocking=True)
#             logits = model(xb).view(-1)
#             out[i:i + batch] = torch.sigmoid(logits).detach().cpu().numpy()
#     return out


# def safe_eval_probs(model: nn.Module, x_tensor: torch.Tensor, device: torch.device) -> np.ndarray:
#     """``predict_batched`` with automatic CPU fallback on CUDA OOM."""
#     try:
#         return predict_batched(model, x_tensor, device, batch=CFG.EVAL_BATCH, use_amp=CFG.USE_AMP)
#     except RuntimeError as e:
#         if CFG.CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
#             print("[WARN] CUDA OOM during eval -> falling back to CPU (batched).")
#             cpu_model = model.to(torch.device("cpu"))
#             x_cpu = x_tensor.to(torch.device("cpu"))
#             return predict_batched(cpu_model, x_cpu, torch.device("cpu"),
#                                     batch=max(8192, CFG.EVAL_BATCH), use_amp=False)
#         raise


# # =============================================================================
# # 6. ENGINEERED FEATURES
# # =============================================================================
# def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
#     """Fill in ``*_mvaID_run3`` from ``*_mvaID_nano`` when only the nano version exists."""
#     pairs = [("lead_mvaID_run3", "lead_mvaID_nano"), ("sublead_mvaID_run3", "sublead_mvaID_nano")]
#     for want, alt in pairs:
#         if want not in df.columns and alt in df.columns:
#             df[want] = df[alt]
#     return df


# def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
#     """Add ptjj/mHH, ptHH/mHH, DeltaR(gg), and |cos theta*| variables.

#     Uses protected division (NaN/inf-safe) throughout, matching the
#     original analysis definitions.
#     """
#     m_hh = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
#     m_hh = m_hh.replace(0, np.nan)

#     df["ptjj_over_mHH"] = df["Res_dijet_pt"] / m_hh if "Res_dijet_pt" in df.columns else 0.0
#     df["ptHH_over_mHH"] = (
#         df["Res_HHbbggCandidate_pt"] / m_hh if "Res_HHbbggCandidate_pt" in df.columns else 0.0
#     )

#     if all(c in df.columns for c in ["lead_phi", "sublead_phi", "lead_eta", "sublead_eta"]):
#         dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
#         dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
#         deta = df["lead_eta"] - df["sublead_eta"]
#         df["DeltaR_gg"] = np.sqrt(deta ** 2 + dphi ** 2)
#     else:
#         df["DeltaR_gg"] = 0.0

#     for c in ["Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS"]:
#         if c in df.columns:
#             df[c] = df[c].abs()

#     for c in ["ptjj_over_mHH", "ptHH_over_mHH", "DeltaR_gg"]:
#         df[c] = pd.Series(df[c]).replace([np.inf, -np.inf], np.nan).fillna(0)

#     return df


# # =============================================================================
# # 7. DATA LOADING
# # =============================================================================
# def _read_parquet_slim(file_path: str) -> pd.DataFrame:
#     """Read a parquet file, requesting only the columns we might need.

#     Falls back to reading the entire file if the column-subset read fails
#     for any reason (e.g. schema surprises).
#     """
#     try:
#         cols = pd.read_parquet(file_path, columns=None).columns
#         subset = [c for c in (set(RAW_COLUMNS_OF_INTEREST) | {CFG.WEIGHT_COL}) if c in cols]
#         return pd.read_parquet(file_path, columns=subset)
#     except Exception:
#         return pd.read_parquet(file_path)


# def _prepare_raw(df: pd.DataFrame) -> pd.DataFrame:
#     """Shared preprocessing applied to every raw sample before feature selection.

#     Renames the raw diphoton-mass column (``mass``, per the ntuple schema)
#     to ``diphoton_mass`` immediately, since ``mass`` is later overwritten
#     with the signal-grid mass point (e.g. 300, 400, ... GeV) in
#     ``load_signal`` / ``load_background``. Without this rename the real
#     diphoton mass would be silently clobbered before mass-sculpting
#     validation ever sees it.
#     """
#     if "mass" in df.columns:
#         df = df.rename(columns={"mass": "diphoton_mass"})
#     df = ensure_photon_mva_columns(df)
#     df = add_engineered_features(df)
#     keep = [c for c in FEATURES_CORE if c in df.columns]
#     extras = [c for c in (CFG.WEIGHT_COL, "diphoton_mass") if c in df.columns]
#     return df[keep + extras].copy()


# def load_signal(cfg: Config = CFG) -> pd.DataFrame:
#     """Load and label all available signal (mass, y) parquet samples.

#     Missing files are silently skipped (not all grid points necessarily
#     exist on disk). Missing optional columns are handled gracefully by
#     ``_prepare_raw`` / ``add_engineered_features``.
#     """
#     rows = []
#     for mass in cfg.MASS_POINTS:
#         for y in cfg.Y_VALUES:
#             fp = cfg.SIG_TPL.format(m=mass, y=y)
#             if not os.path.exists(fp):
#                 continue
#             try:
#                 df = _prepare_raw(_read_parquet_slim(fp))
#                 df["mass"], df["y_value"], df["label"] = mass, y, 1
#                 df = downcast_float_cols(ensure_weight(df, cfg.WEIGHT_COL))
#                 rows.append(df)
#             except Exception as e:
#                 print(f"[WARN] read fail {fp}: {e}")
#     signal_df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
#     if signal_df.empty:
#         raise RuntimeError("No signal samples could be loaded.")
#     return signal_df


# def load_background(cfg: Config = CFG) -> pd.DataFrame:
#     """Load and label all configured background parquet files."""
#     parts = []
#     for file_path in cfg.BACKGROUND_FILES:
#         if not os.path.exists(file_path):
#             print(f"[WARN] Missing {file_path}")
#             continue
#         try:
#             df = _prepare_raw(_read_parquet_slim(file_path))
#             df = ensure_weight(df, cfg.WEIGHT_COL)
#             df["label"] = 0
#             parts.append(downcast_float_cols(df))
#         except Exception as e:
#             print(f"[WARN] read fail {file_path}: {e}")

#     bkg_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
#     if bkg_df.empty:
#         raise RuntimeError("No background samples could be loaded.")
#     if cfg.BACKGROUND_FRAC < 1.0:
#         bkg_df = bkg_df.sample(frac=cfg.BACKGROUND_FRAC, random_state=cfg.SEED).reset_index(drop=True)
#     return bkg_df


# def assign_background_parameters(signal_df: pd.DataFrame, background_df: pd.DataFrame,
#                                   seed: int = CFG.SEED) -> pd.DataFrame:
#     """Assign each background event a (mass, y_value) drawn from the signal mixture.

#     This is what turns an un-parameterized background sample into a
#     parameterized one, matching the (mass,y) distribution of the signal so
#     the network sees background at every mass hypothesis it is trained on.
#     Every (mass,y) point present in signal is guaranteed at least one
#     background event (fills in any missing combinations explicitly).
#     """
#     background_df = background_df.copy()
#     sig_my = signal_df[["mass", "y_value"]]
#     mix = sig_my.value_counts(normalize=True).reset_index()
#     mix.columns = ["mass", "y_value", "weight"]
#     sampled = mix.sample(n=len(background_df), replace=True, weights="weight", random_state=seed).reset_index(drop=True)
#     background_df["mass"] = sampled["mass"].values
#     background_df["y_value"] = sampled["y_value"].values

#     need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
#     have = set(map(tuple, background_df[["mass", "y_value"]].drop_duplicates().values.tolist()))
#     missing = list(need - have)
#     if missing:
#         k = min(len(missing), len(background_df))
#         for i, (m, y) in enumerate(missing[:k]):
#             background_df.loc[i, "mass"] = m
#             background_df.loc[i, "y_value"] = y
#     return background_df


# # =============================================================================
# # 8. DATASET PREPARATION
# # =============================================================================
# def prepare_dataframe(signal_df: pd.DataFrame, background_df: pd.DataFrame) -> pd.DataFrame:
#     """Combine signal + parameterized background and drop globally-pure (mass,y) groups."""
#     df_all = pd.concat([signal_df, background_df], ignore_index=True)
#     key = group_key(df_all)
#     nuniq = df_all.groupby(key)["label"].nunique()
#     good_keys = set(nuniq[nuniq == 2].index)
#     mask = key.isin(good_keys)
#     dropped = int((~mask).sum())
#     if dropped:
#         print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
#     return df_all.loc[mask].reset_index(drop=True)


# def resolve_feature_list(df_all: pd.DataFrame, cfg: Config = CFG) -> List[str]:
#     """Compute the final ('mass','y_value' + physics) feature list, honoring ablation config."""
#     features_final = FEATURES_CORE + ["mass", "y_value"]
#     if cfg.DROP_FEATURES:
#         removed = [f for f in cfg.DROP_FEATURES if f in features_final]
#         if removed:
#             print(f"[Ablation] Dropping features: {removed}")
#             features_final = [f for f in features_final if f not in removed]

#     available = [c for c in features_final if c in df_all.columns]
#     missing = sorted(set(features_final) - set(available))
#     if missing:
#         print(f"[Note] Missing features ignored: {missing}")
#     return available


# def split_dataset(df_all: pd.DataFrame, cfg: Config = CFG) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
#     """Group-disjoint train/val/test split using (mass,y) as the group key.

#     Uses ``GroupShuffleSplit`` twice (outer test split, inner val split) so
#     that no (mass,y) point leaks between splits. Optionally balances
#     signal/background counts within each (mass,y) group per split.
#     """
#     groups_all = group_key(df_all)
#     gss_outer = GroupShuffleSplit(n_splits=1, test_size=cfg.TEST_SIZE, random_state=cfg.SEED)
#     idx_trval, idx_te = next(gss_outer.split(df_all, df_all["label"], groups_all))
#     df_trval = df_all.iloc[idx_trval].reset_index(drop=True)
#     df_te = df_all.iloc[idx_te].reset_index(drop=True)

#     gss_inner = GroupShuffleSplit(n_splits=1, test_size=cfg.VAL_SIZE, random_state=cfg.SEED)
#     groups_trval = group_key(df_trval)
#     idx_tr, idx_va = next(gss_inner.split(df_trval, df_trval["label"], groups_trval))
#     df_tr = df_trval.iloc[idx_tr].reset_index(drop=True)
#     df_va = df_trval.iloc[idx_va].reset_index(drop=True)

#     if cfg.BALANCE_PER_GROUP:
#         df_tr = balance_groups(df_tr, seed=cfg.SEED)
#         df_va = balance_groups(df_va, seed=cfg.SEED)
#         df_te = balance_groups(df_te, seed=cfg.SEED)

#     for df, name in [(df_tr, "TRAIN"), (df_va, "VAL"), (df_te, "TEST")]:
#         split_summary(df, name)
#         check_groups(df, name)

#     set_tr, set_va, set_te = (set(group_key(d).unique()) for d in (df_tr, df_va, df_te))
#     print(f"Overlap Train-Val: {len(set_tr & set_va)}")
#     print(f"Overlap Train-Test: {len(set_tr & set_te)}")
#     print(f"Overlap Val-Test: {len(set_va & set_te)}")

#     return df_tr, df_va, df_te


# # =============================================================================
# # 9. SCALING
# # =============================================================================
# def scale_features(
#     df_tr: pd.DataFrame, df_va: pd.DataFrame, df_te: pd.DataFrame,
#     feature_list: Sequence[str], cfg: Config = CFG,
# ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray,
#            np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
#     """Fit a StandardScaler on TRAIN only, transform all splits, and persist it to disk."""
#     x_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, feature_list)
#     x_va_raw, y_va, w_va = df_to_arrays(df_va, feature_list)
#     x_te_raw, y_te, w_te = df_to_arrays(df_te, feature_list)

#     if cfg.DEBUG_SHUFFLE_TRAIN_LABELS:
#         rng = np.random.default_rng(cfg.SEED + 7)
#         y_tr = rng.permutation(y_tr.copy())
#         print("[DEBUG] Shuffled TRAIN labels. Val AUC should be ~0.5.")

#     scaler = StandardScaler()
#     x_tr = scaler.fit_transform(x_tr_raw)
#     x_va = scaler.transform(x_va_raw)
#     x_te = scaler.transform(x_te_raw)

#     os.makedirs(cfg.MODEL_DIR, exist_ok=True)
#     with open(cfg.SCALER_PATH, "wb") as f:
#         pickle.dump(scaler, f)
#     with open(cfg.FEATURES_PATH, "w") as f:
#         json.dump({"features": list(feature_list)}, f, indent=2)
#     print(f"[INFO] Saved scaler to {cfg.SCALER_PATH} and feature list to {cfg.FEATURES_PATH}")

#     return x_tr, x_va, x_te, y_tr, y_va, y_te, w_tr, w_va, w_te, scaler


# def leakage_audit(x_va: np.ndarray, y_va: np.ndarray, feature_list: Sequence[str]) -> None:
#     """Print per-feature single-variable AUC on VAL to flag potential leakage."""
#     print("\n[Leakage audit on VAL] per-feature AUC:")
#     for i, f in enumerate(feature_list):
#         auc_f = roc_auc_score(y_va, x_va[:, i])
#         flag = " <-- suspicious" if (auc_f > 0.95 or auc_f < 0.05) else ""
#         print(f"{f:24s} AUC={auc_f:.4f}{flag}")
#     i_mass, i_y = feature_list.index("mass"), feature_list.index("y_value")
#     my_auc = roc_auc_score(y_va, 0.5 * x_va[:, i_mass] + 0.5 * x_va[:, i_y])
#     print(f"AUC using only (mass,y) on VAL: {my_auc:.4f}")


# # =============================================================================
# # 10. DATASET / DATALOADER
# # =============================================================================
# class ArrayDataset(Dataset):
#     """Simple in-memory (X, y, w) dataset for PyTorch DataLoader."""

#     def __init__(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> None:
#         self.x, self.y, self.w = x, y, w

#     def __len__(self) -> int:
#         return len(self.x)

#     def __getitem__(self, i: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
#         return (
#             torch.tensor(self.x[i], dtype=torch.float32),
#             torch.tensor(self.y[i], dtype=torch.float32),
#             torch.tensor(self.w[i], dtype=torch.float32),
#         )


# def build_dataloaders(
#     x_tr: np.ndarray, y_tr: np.ndarray, w_tr: np.ndarray,
#     x_va: np.ndarray, x_te: np.ndarray, device: torch.device, cfg: Config = CFG,
# ) -> Tuple[DataLoader, torch.Tensor, torch.Tensor]:
#     """Build the training DataLoader plus pre-loaded VAL/TEST tensors on ``device``."""
#     train_loader = DataLoader(
#         ArrayDataset(x_tr, y_tr, w_tr),
#         batch_size=cfg.BATCH_SIZE, shuffle=True,
#         pin_memory=(device.type == "cuda"),
#         num_workers=2 if os.name != "nt" else 0,
#     )
#     x_va_t = torch.tensor(x_va, dtype=torch.float32).to(device)
#     x_te_t = torch.tensor(x_te, dtype=torch.float32).to(device)
#     return train_loader, x_va_t, x_te_t


# # =============================================================================
# # 11. PARAMETERIZED DNN
# # =============================================================================
# class ParameterizedDNN(nn.Module):
#     """Feed-forward parameterized classifier with configurable depth/width.

#     ``mass`` and ``y_value`` are ordinary input features, which is what
#     makes the network "parameterized": a single model learns S(x; mass, y)
#     across the full signal grid, and can be evaluated at any (mass, y)
#     hypothesis (including ones never seen in training) for background-only
#     events.
#     """

#     def __init__(self, n_features: int, hidden_layers: Sequence[int] = CFG.HIDDEN_LAYERS,
#                  dropout: Sequence[float] = CFG.DROPOUT, use_batchnorm: bool = CFG.USE_BATCHNORM) -> None:
#         super().__init__()
#         if len(dropout) != len(hidden_layers):
#             raise ValueError("dropout and hidden_layers must have the same length")

#         layers: List[nn.Module] = []
#         in_dim = n_features
#         for width, p in zip(hidden_layers, dropout):
#             layers.append(nn.Linear(in_dim, width))
#             layers.append(nn.BatchNorm1d(width) if use_batchnorm else nn.Identity())
#             layers.append(nn.ReLU())
#             layers.append(nn.Dropout(p))
#             in_dim = width
#         layers.append(nn.Linear(in_dim, 1))  # logits only (no sigmoid)
#         self.net = nn.Sequential(*layers)

#     def forward(self, x: torch.Tensor) -> torch.Tensor:
#         return self.net(x)


# def xavier_init_(module: nn.Module) -> None:
#     """Xavier/Glorot initialization for Linear layers (biases set to zero)."""
#     if isinstance(module, nn.Linear):
#         nn.init.xavier_uniform_(module.weight)
#         if module.bias is not None:
#             nn.init.zeros_(module.bias)


# def small_normal_zero_bias_(module: nn.Module, std: float = CFG.INIT_WEIGHT_STD) -> None:
#     """Small-normal weight init used for the untrained-model diagnostic (Val AUC ~ 0.5)."""
#     if isinstance(module, nn.Linear):
#         nn.init.normal_(module.weight, mean=0.0, std=std)
#         if module.bias is not None:
#             nn.init.constant_(module.bias, 0.0)


# # =============================================================================
# # 12. TRAINING ENGINE
# # =============================================================================
# def train_one_epoch(
#     model: nn.Module, loader: DataLoader, criterion: nn.Module, optimizer: torch.optim.Optimizer,
#     scaler_amp: torch.amp.GradScaler, device: torch.device, use_amp: bool, cfg: Config = CFG,
# ) -> float:
#     """Run one training epoch with weighted BCE loss; returns the mean training loss."""
#     model.train()
#     total_loss, n_seen = 0.0, 0
#     for xb, yb, wb in loader:
#         xb, yb, wb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True), wb.to(device, non_blocking=True)
#         wb = torch.clamp(wb / (wb.mean() + 1e-8), max=cfg.WEIGHT_CLIP)

#         optimizer.zero_grad(set_to_none=True)
#         with torch.amp.autocast(device_type=device.type, enabled=use_amp):
#             logits = model(xb).view(-1)
#             per_loss = criterion(logits, yb)
#             loss = (per_loss * wb).mean()
#         scaler_amp.scale(loss).backward()
#         scaler_amp.step(optimizer)
#         scaler_amp.update()

#         bs = xb.size(0)
#         total_loss += float(loss.item()) * bs
#         n_seen += bs
#         if cfg.DEBUG_ONE_BATCH:
#             break
#     return total_loss / max(n_seen, 1)


# def evaluate(model: nn.Module, x_tensor: torch.Tensor, y: np.ndarray, device: torch.device) -> Tuple[float, float, np.ndarray]:
#     """Compute (AUC, accuracy, probabilities) for a given split."""
#     probs = safe_eval_probs(model, x_tensor, device)
#     auc_val = roc_auc_score(y, probs)
#     acc_val = accuracy_score(y, (probs > 0.5).astype(int))
#     return auc_val, acc_val, probs


# def predict(model: nn.Module, x: np.ndarray, device: torch.device) -> np.ndarray:
#     """Return sigmoid probabilities for a raw (already-scaled) feature matrix."""
#     x_t = torch.tensor(x, dtype=torch.float32, device=device)
#     return safe_eval_probs(model, x_t, device)


# def train_model(
#     model: nn.Module, train_loader: DataLoader, x_va_t: torch.Tensor, y_va: np.ndarray,
#     device: torch.device, cfg: Config = CFG,
# ) -> Dict[str, List[float]]:
#     """Full training loop: weighted BCE + AdamW + ReduceLROnPlateau + early stopping.

#     The best model (by validation AUC) is checkpointed to ``cfg.MODEL_PATH``
#     and reloaded into ``model`` at the end.
#     """
#     criterion = nn.BCEWithLogitsLoss(reduction="none")
#     optimizer = AdamW(model.parameters(), lr=cfg.LEARNING_RATE, weight_decay=cfg.WEIGHT_DECAY)
#     scheduler = ReduceLROnPlateau(optimizer, mode="max", factor=cfg.LR_FACTOR, patience=cfg.LR_PATIENCE)
#     use_amp = cfg.USE_AMP and device.type == "cuda"
#     scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if device.type == "cuda" else torch.amp.GradScaler(enabled=False)

#     os.makedirs(cfg.MODEL_DIR, exist_ok=True)
#     history: Dict[str, List[float]] = {"train_loss": [], "val_auc": [], "val_acc": []}
#     best_auc, epochs_since_best = -np.inf, 0

#     for epoch in range(cfg.MAX_EPOCHS):
#         train_loss = train_one_epoch(model, train_loader, criterion, optimizer, scaler_amp, device, use_amp, cfg)
#         val_auc, val_acc, _ = evaluate(model, x_va_t, y_va, device)

#         history["train_loss"].append(train_loss)
#         history["val_auc"].append(val_auc)
#         history["val_acc"].append(val_acc)
#         print(f"Epoch {epoch + 1:03d} | TrainLoss: {train_loss:.4f} | ValAUC: {val_auc:.4f} | ValAcc: {val_acc:.4f}")
#         scheduler.step(val_auc)

#         if val_auc > best_auc + 1e-4:
#             best_auc, epochs_since_best = val_auc, 0
#             if cfg.SAVE_MODEL:
#                 torch.save(model.state_dict(), cfg.MODEL_PATH)
#                 print(f"[INFO] New best ValAUC: {best_auc:.4f} -- model saved")
#         else:
#             epochs_since_best += 1
#             if epochs_since_best >= cfg.PATIENCE:
#                 print(f"[INFO] Early stopping at epoch {epoch + 1}.")
#                 break

#     if cfg.SAVE_MODEL and os.path.exists(cfg.MODEL_PATH):
#         state = torch.load(cfg.MODEL_PATH, map_location=device, weights_only=True)
#         model.load_state_dict(state)
#     else:
#         print("[WARN] No saved model found; using current in-memory weights.")

#     return history


# # =============================================================================
# # 13. EVALUATION (plots, feature importance, diagnostics)
# # =============================================================================
# def _savefig(fig_dir: str, filename: str) -> None:
#     os.makedirs(fig_dir, exist_ok=True)
#     plt.savefig(os.path.join(fig_dir, f"{filename}.png"), dpi=600)
#     plt.savefig(os.path.join(fig_dir, f"{filename}.pdf"))
#     print(f"[Saved] {os.path.join(fig_dir, filename)}.{{png,pdf}}")
#     plt.close()


# def plot_training_history(history: Dict[str, List[float]], cfg: Config = CFG) -> None:
#     """Plot & save the training-loss curve."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     plt.figure()
#     plt.plot(history["train_loss"], marker="o", color=CMS_BLUE)
#     plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
#     plt.tight_layout()
#     _savefig(out_dir, "training_loss")


# def plot_validation_auc(history: Dict[str, List[float]], cfg: Config = CFG) -> None:
#     """Plot & save the validation-AUC curve (group-disjoint)."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     plt.figure()
#     plt.plot(history["val_auc"], marker="o", label="Val AUC", color=CMS_RED)
#     plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
#     plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "validation_auc")


# def plot_roc_curve(test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray,
#                     df_te: pd.DataFrame, cfg: Config = CFG, max_legend: int = 10) -> float:
#     """Overall + per-(mass,y) ROC curve on TEST; returns the overall (weighted) test AUC."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "ROC")
#     fpr_all, tpr_all, _ = roc_curve(y_te, test_probs, sample_weight=w_te)
#     test_auc = auc(fpr_all, tpr_all)
#     print(f"\nTest AUC (overall, weighted): {test_auc:.6f}")

#     plt.figure()
#     plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
#     plt.plot([0, 1], [0, 1], linestyle="--", color=CMS_GRAY, lw=1)
#     plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
#     plt.title("ROC -- Test (group-disjoint)")

#     mass_arr = df_te["mass"].astype(int).values
#     y_arr = df_te["y_value"].astype(int).values
#     handles = []
#     for m, yv in np.unique(np.c_[mass_arr, y_arr], axis=0):
#         idx = (mass_arr == m) & (y_arr == yv)
#         if np.unique(y_te[idx]).size < 2:
#             continue
#         fpr_g, tpr_g, _ = roc_curve(y_te[idx], test_probs[idx], sample_weight=w_te[idx] if w_te is not None else None)
#         auc_g = auc(fpr_g, tpr_g)
#         h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.4, label=f"NMSSM_X{m}_Y{yv} (AUC {auc_g:.3f})")
#         handles.append((auc_g, h))
#     handles.sort(key=lambda t: t[0], reverse=True)
#     top = handles[:max_legend]
#     if top:
#         leg = plt.legend([h for _, h in top], [h.get_label() for _, h in top],
#                           title="Top groups", loc="lower right", frameon=True, fontsize=8)
#         plt.gca().add_artist(leg)
#     plt.tight_layout()
#     _savefig(out_dir, "ROC_test")
#     return test_auc


# def plot_score_distribution(test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG) -> None:
#     """Unweighted, weighted (log-y), and shape-normalized signal/background score plots."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     sig_mask, bkg_mask = (y_te == 1), (y_te == 0)
#     w_sig = w_te[sig_mask] if w_te is not None else None
#     w_bkg = w_te[bkg_mask] if w_te is not None else None
#     bins = np.linspace(0.0, 1.0, 51)

#     plt.figure()
#     plt.hist(test_probs[sig_mask], bins=bins, histtype="step", lw=2.0, label="Signal", color=CMS_BLUE)
#     plt.hist(test_probs[bkg_mask], bins=bins, histtype="step", lw=2.0, label="Background", color=CMS_RED)
#     plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
#     plt.title("Signal vs Background -- Test (unweighted)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "score_distribution_unweighted")

#     plt.figure()
#     plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype="step", lw=2.0, label="Signal", color=CMS_BLUE)
#     plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype="step", lw=2.0, label="Background", color=CMS_RED)
#     plt.yscale("log"); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
#     plt.title("Signal vs Background -- Test (weighted)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "score_distribution_weighted_log")

#     plt.figure()
#     plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype="step", lw=2.0,
#              label="Signal (shape)", color=CMS_BLUE)
#     plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype="step", lw=2.0,
#              label="Background (shape)", color=CMS_RED)
#     plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
#     plt.title("Signal vs Background -- Test (weighted, shape-normalized)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "score_distribution_shape_normalized")


# def _weighted_auc(y: np.ndarray, p: np.ndarray, w: Optional[np.ndarray] = None) -> float:
#     return roc_auc_score(y, p, sample_weight=w)


# def _groupwise_shuffle_inplace(x_block: np.ndarray, group_codes: np.ndarray, col: int, rng: np.random.Generator) -> None:
#     """Shuffle column ``col`` within each group (preserves per-(mass,y) marginal)."""
#     for g in np.unique(group_codes):
#         idx = group_codes == g
#         vals = x_block[idx, col].copy()
#         rng.shuffle(vals)
#         x_block[idx, col] = vals


# @torch.no_grad()
# def permutation_importance(
#     model: nn.Module, x_full: np.ndarray, y: np.ndarray, w: np.ndarray,
#     feature_names: Sequence[str], feature_index_map: Dict[str, int], device: torch.device,
#     group_codes: Optional[np.ndarray] = None, n_repeats: int = CFG.N_PERMUTATION_REPEATS,
#     seed: int = CFG.SEED,
# ) -> Tuple[float, Dict[str, float], Dict[str, float]]:
#     """Group-aware permutation importance: AUC drop when each feature is shuffled.

#     Shuffling is performed within each (mass,y) group (when ``group_codes``
#     is given) so the marginal distribution of mass/y is preserved and the
#     importance reflects the physics feature itself, not group leakage.
#     """
#     x_t = torch.tensor(x_full, dtype=torch.float32, device=device)
#     base_auc = _weighted_auc(y, safe_eval_probs(model, x_t, device), w)

#     rng = np.random.default_rng(seed)
#     drops: Dict[str, List[float]] = defaultdict(list)
#     for fname in feature_names:
#         j = feature_index_map[fname]
#         for _ in range(n_repeats):
#             x_perm = x_full.copy()
#             if group_codes is None:
#                 rng.shuffle(x_perm[:, j])
#             else:
#                 _groupwise_shuffle_inplace(x_perm, group_codes, j, rng)
#             xp_t = torch.tensor(x_perm, dtype=torch.float32, device=device)
#             auc_p = _weighted_auc(y, safe_eval_probs(model, xp_t, device), w)
#             drops[fname].append(base_auc - auc_p)

#     imp_mean = {f: float(np.mean(v)) for f, v in drops.items()}
#     imp_std = {f: float(np.std(v, ddof=1)) if len(v) > 1 else 0.0 for f, v in drops.items()}
#     return base_auc, imp_mean, imp_std


# def gradient_saliency(model: nn.Module, x_full: np.ndarray, feature_names_report: Sequence[str],
#                        feature_index_map: Dict[str, int], device: torch.device,
#                        scaler: Optional[StandardScaler] = None, batch: int = 4096) -> Dict[str, float]:
#     """Mean |d logit / d x_raw| per feature, converted back to raw feature scale."""
#     model.eval()
#     n, d = x_full.shape
#     grads_accum = np.zeros(d, dtype=np.float64)
#     n_seen = 0
#     inv_scale = (1.0 / np.asarray(scaler.scale_, dtype=np.float64)) if (scaler is not None and hasattr(scaler, "scale_")) else np.ones(d)

#     ptr = 0
#     while ptr < n:
#         xb = torch.tensor(x_full[ptr:ptr + batch], dtype=torch.float32, device=device, requires_grad=True)
#         logits = model(xb).view(-1)
#         logits.sum().backward()
#         grads_accum += xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()
#         n_seen += 1
#         ptr += batch
#         model.zero_grad(set_to_none=True)

#     grads_raw = (grads_accum / max(n_seen, 1)) * inv_scale
#     return {f: float(grads_raw[feature_index_map[f]]) for f in feature_names_report}


# def plot_feature_importance(
#     imp_mean: Dict[str, float], imp_std: Dict[str, float], title: str, filename: str,
#     cfg: Config = CFG, top_k: int = 25, cms_color: str = CMS_BLUE,
# ) -> None:
#     """Horizontal bar chart of feature importances (used for both permutation and saliency)."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "FeatureImportance")
#     items = sorted(imp_mean.items(), key=lambda t: t[1], reverse=True)[:top_k]
#     labels = [k for k, _ in items][::-1]
#     vals = [imp_mean[k] for k in labels]
#     errs = [imp_std.get(k, 0.0) for k in labels]

#     plt.figure(figsize=(8.0, 0.4 * len(labels) + 1.5), dpi=110)
#     plt.barh(range(len(labels)), vals, xerr=errs, color=cms_color, alpha=0.85)
#     plt.yticks(range(len(labels)), labels)
#     plt.xlabel("Mean AUC drop (permutation)" if "saliency" not in filename else "Normalized saliency")
#     plt.title(title)
#     plt.tight_layout()
#     _savefig(out_dir, filename)


# def plot_correlation_heatmap(df_te: pd.DataFrame, feature_list: Sequence[str], cfg: Config = CFG) -> pd.DataFrame:
#     """Pearson correlation heatmap of physics features (excludes mass/y_value).

#     Computed on the real (pre-imputation) values using pairwise-complete
#     observations, so events missing a given quantity simply drop out of
#     that pair's correlation instead of being imputed first. Imputed values
#     would otherwise manufacture spurious correlation between features that
#     happen to be undefined for the same events (e.g. anything requiring a
#     resolved dijet system).
#     """
#     out_dir = os.path.join(cfg.PLOT_DIR, "FeatureImportance")
#     cols = [c for c in feature_list if c not in ("mass", "y_value")]
#     corr = df_te[cols].corr(method="pearson")  # pandas .corr() uses pairwise-complete obs by default

#     fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
#     im = ax.imshow(corr.values, cmap=CMS_DIVERGING_CMAP, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
#     ax.set_xticks(np.arange(corr.shape[1])); ax.set_yticks(np.arange(corr.shape[0]))
#     ax.set_xticklabels(corr.columns, rotation=90); ax.set_yticklabels(corr.index)
#     ax.set_title("Pearson correlation (test, real values, pairwise-complete)")
#     plt.colorbar(im, ax=ax).set_label("Correlation")
#     plt.tight_layout()
#     _savefig(out_dir, "variable_correlation")
#     return corr


# def prune_correlated_features(
#     df_ref: pd.DataFrame, feature_list: Sequence[str], y_ref: np.ndarray, cfg: Config = CFG,
# ) -> Tuple[List[str], List[Tuple[str, str, float]]]:
#     """Drop redundant features from correlated pairs, keeping the more predictive one.

#     This is deliberately *not* a blanket "remove anything correlated" pass
#     -- neural nets are largely robust to correlated inputs, unlike linear
#     models, so correlation alone isn't a good reason to drop a physics
#     feature. Only pairs at or above ``cfg.CORR_PRUNE_THRESHOLD`` (computed
#     on real, non-imputed values) are considered redundant. For each such
#     pair, the feature with the lower single-variable AUC against the label
#     is dropped, so the more informative variable is always kept. ``mass``
#     and ``y_value`` are always exempt.
#     """
#     keep_cols = [c for c in feature_list if c not in ("mass", "y_value")]
#     corr = df_ref[keep_cols].corr(method="pearson").abs()

#     single_auc: Dict[str, float] = {}
#     for c in keep_cols:
#         vals = df_ref[c].values
#         mask = ~pd.isna(vals)
#         if mask.sum() < 10 or np.unique(y_ref[mask]).size < 2:
#             single_auc[c] = 0.5
#             continue
#         try:
#             single_auc[c] = max(roc_auc_score(y_ref[mask], vals[mask]),
#                                  1 - roc_auc_score(y_ref[mask], vals[mask]))
#         except ValueError:
#             single_auc[c] = 0.5

#     to_drop: set = set()
#     dropped_pairs: List[Tuple[str, str, float]] = []
#     n = len(keep_cols)
#     for i in range(n):
#         ci = keep_cols[i]
#         if ci in to_drop:
#             continue
#         for j in range(i + 1, n):
#             cj = keep_cols[j]
#             if cj in to_drop:
#                 continue
#             r = corr.loc[ci, cj]
#             if pd.notna(r) and r >= cfg.CORR_PRUNE_THRESHOLD:
#                 loser = ci if single_auc[ci] < single_auc[cj] else cj
#                 to_drop.add(loser)
#                 dropped_pairs.append((ci, cj, float(r)))

#     pruned = [f for f in feature_list if f not in to_drop]
#     if to_drop:
#         print(f"[Correlation pruning] threshold={cfg.CORR_PRUNE_THRESHOLD}: "
#               f"dropping {len(to_drop)} redundant feature(s): {sorted(to_drop)}")
#         for a, b, r in dropped_pairs:
#             print(f"    {a} <-> {b}: |r|={r:.3f}")
#     else:
#         print(f"[Correlation pruning] threshold={cfg.CORR_PRUNE_THRESHOLD}: no features exceeded the threshold.")
#     return pruned, dropped_pairs


# def run_extended_diagnostics(model: nn.Module, y_te: np.ndarray, test_probs: np.ndarray, cfg: Config = CFG) -> Dict[str, object]:
#     """Confusion matrix, calibration curve, classification report, Brier score."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     preds = (test_probs > 0.5).astype(int)
#     cm = confusion_matrix(y_te, preds)
#     report = classification_report(y_te, preds, target_names=["Background", "Signal"], output_dict=True)
#     brier = brier_score_loss(y_te, test_probs)

#     plt.figure(figsize=(4.5, 4.0))
#     plt.imshow(cm, cmap=CMS_DIVERGING_CMAP)
#     for i in range(2):
#         for j in range(2):
#             plt.text(j, i, str(cm[i, j]), ha="center", va="center")
#     plt.xticks([0, 1], ["Background", "Signal"]); plt.yticks([0, 1], ["Background", "Signal"])
#     plt.xlabel("Predicted"); plt.ylabel("True"); plt.title("Confusion matrix (Test)")
#     plt.tight_layout()
#     _savefig(out_dir, "confusion_matrix")

#     # calibration curve (10 equal-width bins)
#     bins = np.linspace(0, 1, 11)
#     bin_idx = np.digitize(test_probs, bins) - 1
#     bin_idx = np.clip(bin_idx, 0, 9)
#     frac_pos = [y_te[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(10)]
#     mean_pred = [test_probs[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(10)]

#     plt.figure()
#     plt.plot(mean_pred, frac_pos, marker="o", color=CMS_BLUE, label="Model")
#     plt.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect calibration")
#     plt.xlabel("Mean predicted probability"); plt.ylabel("Fraction of positives")
#     plt.title("Calibration curve (Test)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "calibration_curve")

#     print(f"[Diag] Brier score (Test): {brier:.4f}")
#     return {"confusion_matrix": cm.tolist(), "classification_report": report, "brier_score": float(brier)}


# # =============================================================================
# # 14. PHYSICS VALIDATION (mass sculpting)
# # =============================================================================
# def _find_mass_sculpt_column(df: pd.DataFrame, cfg: Config = CFG) -> Optional[str]:
#     for c in cfg.MASS_SCULPT_CANDIDATES:
#         if c in df.columns:
#             return c
#     return None


# def plot_mass_after_score(
#     mass_values: np.ndarray, scores: np.ndarray, weights: np.ndarray, labels: np.ndarray,
#     mass_col_name: str, cfg: Config = CFG,
# ) -> None:
#     """Overlay the background mass spectrum before/after successive score cuts.

#     A well-behaved discriminant should not sculpt a peak/edge into the
#     smoothly-falling background mass spectrum. This is the primary check
#     against a resonant bump being manufactured by the classifier.
#     """
#     out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
#     bkg = labels == 0
#     m_bkg, s_bkg, w_bkg = mass_values[bkg], scores[bkg], (weights[bkg] if weights is not None else None)
#     lo, hi = np.nanpercentile(m_bkg, [1, 99])
#     bins = np.linspace(lo, hi, 40)

#     plt.figure()
#     for cut in cfg.SCORE_CUTS:
#         sel = s_bkg >= cut
#         if sel.sum() < 5:
#             continue
#         w_sel = w_bkg[sel] if w_bkg is not None else None
#         plt.hist(m_bkg[sel], bins=bins, weights=w_sel, density=True, histtype="step", lw=1.8,
#                   label=f"score >= {cut:.1f} (N={int(sel.sum())})")
#     plt.xlabel(mass_col_name); plt.ylabel("Density (shape-normalized)")
#     plt.title("Background mass sculpting vs. score cut")
#     plt.legend(fontsize=8); plt.tight_layout()
#     _savefig(out_dir, "mass_sculpting_shapes")


# def run_mass_sculpting(
#     df_te: pd.DataFrame, test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG,
# ) -> Dict[str, object]:
#     """Run the full mass-sculpting physics-validation suite on the TEST split.

#     Produces:
#       - background mass-shape overlay for a series of score cuts
#       - weighted Kolmogorov-Smirnov test (no-cut vs each score-cut shape)
#       - signal/background efficiency vs. score-cut table
#       - efficiency-vs-score and S/B-style ratio plot

#     If no known mass-proxy column is available in the dataframe, the checks
#     are skipped gracefully (with a clear message) rather than failing.
#     """
#     mass_col = _find_mass_sculpt_column(df_te, cfg)
#     if mass_col is None:
#         print("[WARN] run_mass_sculpting: no mass-proxy column found in "
#               f"{cfg.MASS_SCULPT_CANDIDATES}; skipping mass sculpting validation.")
#         return {"status": "skipped", "reason": "no mass column available"}

#     out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
#     mass_values = df_te[mass_col].to_numpy(dtype=float)
#     plot_mass_after_score(mass_values, test_probs, w_te, y_te, mass_col, cfg)

#     sig_mask, bkg_mask = (y_te == 1), (y_te == 0)
#     m_bkg_all = mass_values[bkg_mask]
#     ks_results, eff_table = {}, []

#     for cut in cfg.SCORE_CUTS:
#         sel_sig = sig_mask & (test_probs >= cut)
#         sel_bkg = bkg_mask & (test_probs >= cut)
#         sig_eff = float(w_te[sel_sig].sum() / max(w_te[sig_mask].sum(), 1e-12))
#         bkg_eff = float(w_te[sel_bkg].sum() / max(w_te[bkg_mask].sum(), 1e-12))
#         eff_table.append({"score_cut": cut, "signal_efficiency": sig_eff, "background_efficiency": bkg_eff})

#         m_cut = mass_values[sel_bkg]
#         if len(m_cut) > 5 and len(m_bkg_all) > 5:
#             stat, pval = ks_2samp(m_bkg_all, m_cut)
#             ks_results[f"cut_{cut:.1f}"] = {"ks_stat": float(stat), "p_value": float(pval)}

#     # efficiency vs score cut
#     plt.figure()
#     cuts = [row["score_cut"] for row in eff_table]
#     plt.plot(cuts, [row["signal_efficiency"] for row in eff_table], marker="o", color=CMS_BLUE, label="Signal efficiency")
#     plt.plot(cuts, [row["background_efficiency"] for row in eff_table], marker="o", color=CMS_RED, label="Background efficiency")
#     plt.xlabel("Score cut"); plt.ylabel("Efficiency")
#     plt.title("Efficiency vs. score cut (Test)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "efficiency_vs_score")

#     # ratio plot (signal eff / background eff, i.e. rejection power)
#     plt.figure()
#     ratio = [row["signal_efficiency"] / max(row["background_efficiency"], 1e-12) for row in eff_table]
#     plt.plot(cuts, ratio, marker="o", color=CMS_GREEN)
#     plt.yscale("log"); plt.xlabel("Score cut"); plt.ylabel("Signal eff / Background eff")
#     plt.title("Rejection power vs. score cut (Test)"); plt.tight_layout()
#     _savefig(out_dir, "efficiency_ratio_vs_score")

#     print("[Physics validation] Weighted KS tests (background mass shape, no-cut vs cut):")
#     for k, v in ks_results.items():
#         print(f"  {k}: KS={v['ks_stat']:.4f}  p={v['p_value']:.4g}")

#     # per-(mass,y) split validation: overall efficiency table by group at score>=0.5
#     per_group = []
#     if {"mass", "y_value"}.issubset(df_te.columns):
#         key = group_key(df_te)
#         for g in np.unique(key):
#             idx = (key == g).values
#             if np.unique(y_te[idx]).size < 2:
#                 continue
#             sig_idx = idx & sig_mask
#             bkg_idx = idx & bkg_mask
#             sel_sig = sig_idx & (test_probs >= 0.5)
#             sel_bkg = bkg_idx & (test_probs >= 0.5)
#             per_group.append({
#                 "group": g,
#                 "signal_efficiency_at_0.5": float(w_te[sel_sig].sum() / max(w_te[sig_idx].sum(), 1e-12)) if sig_idx.any() else None,
#                 "background_efficiency_at_0.5": float(w_te[sel_bkg].sum() / max(w_te[bkg_idx].sum(), 1e-12)) if bkg_idx.any() else None,
#             })

#     return {
#         "status": "ok",
#         "mass_column_used": mass_col,
#         "efficiency_table": eff_table,
#         "ks_tests": ks_results,
#         "per_group_efficiency_at_0.5": per_group,
#     }


# # =============================================================================
# # 15. LOGGING / OUTPUT PERSISTENCE
# # =============================================================================
# def save_outputs(
#     cfg: Config, history: Dict[str, List[float]], metrics: Dict[str, object], feature_list: Sequence[str],
# ) -> None:
#     """Persist config, training history, and evaluation metrics for reproducibility."""
#     os.makedirs(cfg.LOG_DIR, exist_ok=True)

#     config_snapshot = {
#         "seed": cfg.SEED,
#         "torch_version": torch.__version__,
#         "cuda_version": torch.version.cuda,
#         "device": str(DEVICE),
#         "feature_list": list(feature_list),
#         "timestamp": datetime.now(timezone.utc).isoformat(),
#         "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
#     }
#     with open(os.path.join(cfg.LOG_DIR, "config.json"), "w") as f:
#         json.dump(config_snapshot, f, indent=2, default=str)
#     with open(os.path.join(cfg.LOG_DIR, "history.json"), "w") as f:
#         json.dump(history, f, indent=2)
#     with open(os.path.join(cfg.LOG_DIR, "metrics.json"), "w") as f:
#         json.dump(metrics, f, indent=2, default=str)

#     print(f"[INFO] Saved config/history/metrics to {cfg.LOG_DIR}/")


# # =============================================================================
# # 16. MAIN
# # =============================================================================
# def main() -> None:
#     """End-to-end pDNN training + evaluation + physics-validation pipeline."""
#     cfg = CFG
#     apply_cms_plot_style()
#     for d in (cfg.OUTPUT_DIR, cfg.MODEL_DIR, cfg.PLOT_DIR, cfg.LOG_DIR):
#         os.makedirs(d, exist_ok=True)
#     print(f"[INFO] Using device: {DEVICE}")

#     # ---- Data loading & preparation ----
#     signal_df = load_signal(cfg)
#     background_df = load_background(cfg)
#     background_df = assign_background_parameters(signal_df, background_df, seed=cfg.SEED)
#     df_all = prepare_dataframe(signal_df, background_df)
#     feature_list = resolve_feature_list(df_all, cfg)

#     if cfg.ENABLE_CORR_PRUNING:
#         feature_list, dropped_corr_pairs = prune_correlated_features(
#             df_all, feature_list, df_all["label"].values, cfg
#         )
#     else:
#         dropped_corr_pairs = []

#     df_tr, df_va, df_te = split_dataset(df_all, cfg)

#     # ---- Scaling ----
#     x_tr, x_va, x_te, y_tr, y_va, y_te, w_tr, w_va, w_te, scaler = scale_features(
#         df_tr, df_va, df_te, feature_list, cfg
#     )
#     leakage_audit(x_va, y_va, feature_list)

#     # ---- Model & dataloaders ----
#     train_loader, x_va_t, x_te_t = build_dataloaders(x_tr, y_tr, w_tr, x_va, x_te, DEVICE, cfg)
#     model = ParameterizedDNN(x_tr.shape[1], cfg.HIDDEN_LAYERS, cfg.DROPOUT, cfg.USE_BATCHNORM)
#     model.apply(xavier_init_)
#     model = model.to(DEVICE)

#     # ---- Training ----
#     history = train_model(model, train_loader, x_va_t, y_va, DEVICE, cfg)
#     plot_training_history(history, cfg)
#     plot_validation_auc(history, cfg)

#     # ---- Test-set evaluation ----
#     test_probs = predict(model, x_te, DEVICE)
#     test_auc = plot_roc_curve(test_probs, y_te, w_te, df_te, cfg)
#     plot_score_distribution(test_probs, y_te, w_te, cfg)
#     plot_correlation_heatmap(df_te, feature_list, cfg)
#     diag_metrics = run_extended_diagnostics(model, y_te, test_probs, cfg)

#     i_mass, i_y = feature_list.index("mass"), feature_list.index("y_value")
#     my_auc_test = roc_auc_score(y_te, 0.5 * x_te[:, i_mass] + 0.5 * x_te[:, i_y])
#     print(f"AUC using only (mass,y) on TEST: {my_auc_test:.4f}")

#     # ---- Feature importance ----
#     name_to_idx = {f: feature_list.index(f) for f in feature_list}
#     feat_names_imp = [f for f in feature_list if cfg.INCLUDE_MASS_Y_IN_IMPORTANCE or f not in ("mass", "y_value")]
#     group_codes = pd.factorize(group_key(df_te))[0]

#     base_auc, imp_mean, imp_std = permutation_importance(
#         model, x_te, y_te, w_te, feat_names_imp, name_to_idx, DEVICE,
#         group_codes=group_codes, n_repeats=cfg.N_PERMUTATION_REPEATS, seed=cfg.SEED,
#     )
#     print(f"[Permutation] Baseline TEST AUC = {base_auc:.4f}")
#     plot_feature_importance(imp_mean, imp_std, "Permutation importance (AUC drop) -- TEST",
#                              "feature_importance_permutation_test", cfg, cms_color=CMS_BLUE)

#     sal = gradient_saliency(model, x_te, feat_names_imp, name_to_idx, DEVICE, scaler=scaler)
#     sal_max = max(sal.values()) if sal else 1.0
#     sal_norm = {k: (v / sal_max if sal_max > 0 else 0.0) for k, v in sal.items()}
#     plot_feature_importance(sal_norm, {k: 0.0 for k in sal_norm}, "Input-gradient saliency (normalized) -- TEST",
#                              "feature_importance_saliency_test", cfg, cms_color=CMS_ORANGE)

#     importance_table = pd.DataFrame({
#         "feature": feat_names_imp,
#         "perm_mean_auc_drop": [imp_mean.get(f, np.nan) for f in feat_names_imp],
#         "perm_std_auc_drop": [imp_std.get(f, np.nan) for f in feat_names_imp],
#         "grad_saliency_norm": [sal_norm.get(f, np.nan) for f in feat_names_imp],
#     }).sort_values(["perm_mean_auc_drop", "grad_saliency_norm"], ascending=[False, False], na_position="last")
#     importance_table.to_csv(os.path.join(cfg.PLOT_DIR, "FeatureImportance", "feature_importance_test.csv"), index=False)

#     # ---- Physics validation (mass sculpting) ----
#     sculpting_results = run_mass_sculpting(df_te, test_probs, y_te, w_te, cfg)

#     # ---- Persist everything ----
#     metrics = {
#         "test_auc_weighted": float(test_auc),
#         "mass_y_only_auc_val": float(roc_auc_score(y_va, 0.5 * x_va[:, i_mass] + 0.5 * x_va[:, i_y])),
#         "mass_y_only_auc_test": float(my_auc_test),
#         "permutation_baseline_auc": float(base_auc),
#         "permutation_importance_mean": imp_mean,
#         "permutation_importance_std": imp_std,
#         "gradient_saliency_normalized": sal_norm,
#         "diagnostics": diag_metrics,
#         "mass_sculpting": sculpting_results,
#         "correlation_pruning": {
#             "enabled": cfg.ENABLE_CORR_PRUNING,
#             "threshold": cfg.CORR_PRUNE_THRESHOLD,
#             "dropped_pairs": dropped_corr_pairs,
#             "final_feature_list": feature_list,
#         },
#     }
#     save_outputs(cfg, history, metrics, feature_list)

#     print("\n[DONE] pDNN_v2 pipeline complete.")
#     print(f"       Best model:  {cfg.MODEL_PATH}")
#     print(f"       Scaler:      {cfg.SCALER_PATH}")
#     print(f"       Plots:       {cfg.PLOT_DIR}")
#     print(f"       Logs:        {cfg.LOG_DIR}")


# if __name__ == "__main__":
#     main()
# #!/usr/bin/env python
# # =============================================================================
# # pDNN_v2.py
# #
# # Parameterized Deep Neural Network (pDNN) for the CMS HH -> bbgg resonant
# # search (NMSSM).  Production-quality refactor of the original working
# # training script.  Physics, training strategy, and outputs are preserved;
# # this file focuses on software-engineering quality (modularity, typing,
# # documentation, reproducibility).
# #
# # Run with:
# #     python pDNN_v2.py
# # =============================================================================

# #!/usr/bin/env python
# # =============================================================================
# # pDNN_v2.py
# #
# # Parameterized Deep Neural Network (pDNN) for the CMS HH -> bbgg resonant
# # search (NMSSM).  Production-quality refactor of the original working
# # training script.  Physics, training strategy, and outputs are preserved;
# # this file focuses on software-engineering quality (modularity, typing,
# # documentation, reproducibility).
# #
# # Run with:
# #     python pDNN_v2.py
# # =============================================================================

# from __future__ import annotations

# # =============================================================================
# # 1. IMPORTS
# # =============================================================================
# import json
# import os
# import pickle
# import warnings
# from collections import defaultdict
# from dataclasses import dataclass
# from datetime import datetime, timezone
# from typing import Dict, List, Optional, Sequence, Tuple

# import numpy as np
# import pandas as pd
# import torch
# import torch.nn as nn
# from cycler import cycler
# from matplotlib.colors import LinearSegmentedColormap
# from scipy.stats import kstwobign
# from sklearn.metrics import (
#     accuracy_score,
#     auc,
#     brier_score_loss,
#     classification_report,
#     confusion_matrix,
#     roc_auc_score,
#     roc_curve,
# )
# from sklearn.model_selection import GroupShuffleSplit
# from sklearn.preprocessing import StandardScaler
# from torch.optim import AdamW
# from torch.optim.lr_scheduler import ReduceLROnPlateau
# from torch.utils.data import DataLoader, Dataset

# import matplotlib

# matplotlib.use("Agg")  # safe for batch / non-interactive execution
# import matplotlib.pyplot as plt  # noqa: E402

# warnings.filterwarnings("ignore", category=UserWarning)


# # =============================================================================
# # 2. CONFIGURATION
# #
# # Every tunable parameter for the analysis lives here. Nothing below this
# # section should define a "magic number" constant outside of this class.
# # =============================================================================
# @dataclass(frozen=True)
# class Config:
#     """Single source of truth for all pDNN configuration."""

#     # --- reproducibility ---
#     SEED: int = 42

#     # --- inputs ---
#     SIG_TPL: str = (
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/NMSSM_X{m}_Y{y}.parquet"
#     )
#     BACKGROUND_FILES: Tuple[str, ...] = (
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/GGJets_MGG-40to80.parquet",
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/GGJets_MGG-80.parquet",
#         "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_root/"
#         "sample_final_nominal/postEE/DDQCDGJET_Rescaled.parquet",
#     )
#     MASS_POINTS: Tuple[int, ...] = (300, 400, 500, 550, 600, 650, 700, 800, 900, 1000)
#     Y_VALUES: Tuple[int, ...] = (90, 95, 100, 125, 150, 200, 300, 400, 500, 600, 800)
#     WEIGHT_COL: str = "weight_central"

#     # --- data handling ---
#     BACKGROUND_FRAC: float = 1.0          # 1.0 = keep all background
#     BALANCE_PER_GROUP: bool = True        # balance S=B inside each (mass,y) after split
#     TEST_SIZE: float = 0.20               # outer split (train+val vs test)
#     VAL_SIZE: float = 0.20                # inner split (train vs val)
#     DROP_FEATURES: Tuple[str, ...] = ()   # optional ablation
#     ENABLE_CORR_PRUNING: bool = True      # drop redundant (highly correlated) features
#     CORR_PRUNE_THRESHOLD: float = 0.95    # |Pearson r|, computed on real (non-imputed) values

#     # --- model architecture ---
#     HIDDEN_LAYERS: Tuple[int, ...] = (128, 64, 32)
#     DROPOUT: Tuple[float, ...] = (0.3, 0.3, 0.2)
#     USE_BATCHNORM: bool = False
#     INIT_WEIGHT_STD: float = 1e-2         # small-normal init (stabilizes early training)

#     # --- training ---
#     BATCH_SIZE: int = 128
#     LEARNING_RATE: float = 1e-3
#     WEIGHT_DECAY: float = 1e-4
#     MAX_EPOCHS: int = 500
#     PATIENCE: int = 5
#     WEIGHT_CLIP: float = 10.0
#     LR_PATIENCE: int = 5
#     LR_FACTOR: float = 0.5
#     USE_AMP: bool = True                  # mixed precision on CUDA (train + eval)

#     # --- evaluation ---
#     EVAL_BATCH: int = 32768
#     CPU_FALLBACK_ON_OOM: bool = True
#     N_PERMUTATION_REPEATS: int = 5
#     INCLUDE_MASS_Y_IN_IMPORTANCE: bool = True

#     # --- physics validation (mass sculpting) ---
#     # Column used as the resonance-mass proxy for sculpting checks. Not all
#     # ntuples carry a dedicated diphoton mass column, so a short candidate
#     # list is tried in order; the first one present in the dataframe is used.
#     MASS_SCULPT_CANDIDATES: Tuple[str, ...] = (
#         "diphoton_mass", "mass_gg", "CMS_hgg_mass", "mgg", "Res_HHbbggCandidate_mass",
#     )
#     SCORE_CUTS: Tuple[float, ...] = (0.0, 0.3, 0.5, 0.7, 0.9)

#     # --- debug toggles ---
#     DEBUG_ONE_BATCH: bool = False
#     DEBUG_SHUFFLE_TRAIN_LABELS: bool = False

#     # --- outputs ---
#     OUTPUT_DIR: str = "outputs"
#     SAVE_MODEL: bool = True

#     # derived (filled in __post_init__ equivalent via property)
#     @property
#     def MODEL_DIR(self) -> str:
#         return os.path.join(self.OUTPUT_DIR, "models")

#     @property
#     def PLOT_DIR(self) -> str:
#         return os.path.join(self.OUTPUT_DIR, "plots")

#     @property
#     def LOG_DIR(self) -> str:
#         return os.path.join(self.OUTPUT_DIR, "logs")

#     @property
#     def MODEL_PATH(self) -> str:
#         return os.path.join(self.MODEL_DIR, "best_pdnn.pt")

#     @property
#     def SCALER_PATH(self) -> str:
#         return os.path.join(self.MODEL_DIR, "scaler.pkl")

#     @property
#     def FEATURES_PATH(self) -> str:
#         return os.path.join(self.MODEL_DIR, "features.json")


# CFG = Config()

# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# np.random.seed(CFG.SEED)
# torch.manual_seed(CFG.SEED)
# torch.cuda.manual_seed_all(CFG.SEED)
# torch.backends.cudnn.deterministic = True
# torch.backends.cudnn.benchmark = False


# # =============================================================================
# # 3. PLOT STYLE
# # =============================================================================
# CMS_BLUE = "#2368B5"
# CMS_RED = "#C0392B"
# CMS_ORANGE = "#E67E22"
# CMS_GREEN = "#2E8B57"
# CMS_PURPLE = "#6C5CE7"
# CMS_GRAY = "#4D4D4D"

# CMS_DIVERGING_CMAP = LinearSegmentedColormap.from_list(
#     "cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256
# )


# def apply_cms_plot_style() -> None:
#     """Apply the CMS-like matplotlib style used throughout this script."""
#     plt.rcParams.update({
#         "figure.figsize": (7.5, 5.5),
#         "figure.dpi": 110,
#         "axes.grid": True,
#         "grid.alpha": 0.30,
#         "axes.titlesize": 14,
#         "axes.labelsize": 12,
#         "legend.fontsize": 10,
#         "xtick.labelsize": 10,
#         "ytick.labelsize": 10,
#         "lines.linewidth": 2.0,
#     })
#     plt.rcParams["axes.prop_cycle"] = cycler(color=[
#         CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE,
#         "#1ABC9C", "#8E44AD", "#16A085", "#D35400", "#2C3E50",
#     ])


# # =============================================================================
# # 4. FEATURE DEFINITIONS
# # =============================================================================
# FEATURES_CORE: List[str] = [
#     "lead_eta", "lead_phi", "sublead_eta", "sublead_phi",
#     "Res_dijet_eta", "Res_dijet_phi",
#     "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi", "Res_HHbbggCandidate_pt",
#     "Res_dijet_mass_DNNreg",
#     "Res_DeltaR_jg_min",
#     "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
#     "lead_mvaID",
#     "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi", "Njets2p5",
#     "Res_DeltaPhi_j1MET", "Res_DeltaPhi_j2MET",
#     "Res_chi_t0", "Res_chi_t1",
#     "Res_dijet_pt", "Res_dijet_mass",
#     "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
#     "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
#     "sigma_m_over_m",
#     "Res_M_X",
#     "lead_r9", "sublead_r9",
#     "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
#     # engineered (added by add_engineered_features)
#     "ptjj_over_mHH", "ptHH_over_mHH",
# ]

# # Raw columns worth requesting explicitly when reading parquet files (keeps
# # I/O light while guaranteeing everything needed for engineered features
# # and fallbacks is available).
# RAW_COLUMNS_OF_INTEREST: List[str] = [
#     "lead_eta", "lead_phi", "sublead_eta", "sublead_phi", "eta", "phi",
#     "Res_lead_bjet_eta", "Res_lead_bjet_phi",
#     "Res_sublead_bjet_eta", "Res_sublead_bjet_phi",
#     "Res_dijet_eta", "Res_dijet_phi",
#     "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi",
#     "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
#     "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
#     "Res_DeltaR_j1g1", "Res_DeltaR_j1g2",
#     "Res_DeltaR_j2g1", "Res_DeltaR_j2g2", "Res_DeltaR_jg_min",
#     "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
#     "lead_mvaID_run3", "sublead_mvaID_run3",
#     "lead_mvaID_nano", "sublead_mvaID_nano",
#     "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
#     "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi",
#     "Res_chi_t0", "Res_chi_t1",
#     "Res_dijet_pt", "Res_HHbbggCandidate_pt", "Res_HHbbggCandidate_mass",
#     "mass",  # raw diphoton invariant mass -> renamed to "diphoton_mass" in _prepare_raw
#              # to avoid colliding with the "mass" column used for the signal grid point.
# ]


# # =============================================================================
# # 5. UTILITY FUNCTIONS
# # =============================================================================
# def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
#     """Downcast all float64 columns to float32 in place (memory/speed)."""
#     for c in df.select_dtypes(include=["float64"]).columns:
#         df[c] = df[c].astype("float32")
#     return df


# def ensure_weight(df: pd.DataFrame, weight_col: str = CFG.WEIGHT_COL) -> pd.DataFrame:
#     """Guarantee an event-weight column exists (defaults to 1.0)."""
#     if weight_col not in df.columns:
#         df[weight_col] = 1.0
#     return df


# def group_key(df: pd.DataFrame) -> pd.Series:
#     """Build the (mass, y_value) string group key used for grouped splits."""
#     return df["mass"].astype(int).astype(str) + "_" + df["y_value"].astype(int).astype(str)


# def df_to_arrays(df: pd.DataFrame, feature_list: Sequence[str], seed: int = CFG.SEED) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
#     """Convert a dataframe split into (X, y, w) numpy arrays for modeling.

#     Missing values are imputed by sampling from each column's own observed
#     distribution, not by mean-filling. Mean-filling collapses every event
#     missing a given quantity (e.g. events without a resolved dijet) onto
#     the *same* value in every affected column simultaneously; since those
#     events tend to be missing several related columns at once, that
#     manufactures artificial near-1.0 correlation between otherwise
#     unrelated features (an imputation artifact, not real physics).
#     Sampling from the observed marginal avoids that collapse.
#     """
#     x_df = df[list(feature_list)].copy()
#     rng = np.random.default_rng(seed)
#     for col in x_df.columns:
#         n_missing = int(x_df[col].isna().sum())
#         if n_missing == 0:
#             continue
#         observed = x_df[col].dropna().values
#         fill_values = rng.choice(observed, size=n_missing, replace=True) if len(observed) > 0 else 0.0
#         x_df.loc[x_df[col].isna(), col] = fill_values
#     x_df = downcast_float_cols(x_df)
#     x = x_df.values
#     y = df["label"].astype(np.int8).values
#     w = df[CFG.WEIGHT_COL].astype("float32").values
#     return x, y, w


# def balance_groups(df: pd.DataFrame, seed: int = CFG.SEED, min_per_class: int = 1) -> pd.DataFrame:
#     """Down-sample signal/background to equal counts within each (mass,y) group.

#     Groups with fewer than ``min_per_class`` events in either class are
#     dropped entirely (pure groups cannot be balanced).
#     """
#     key = group_key(df)
#     parts, dropped = [], 0
#     for _, sub in df.groupby(key, sort=False):
#         vc = sub["label"].value_counts()
#         if len(vc) < 2 or vc.min() < min_per_class:
#             dropped += 1
#             continue
#         n_min = vc.min()
#         sig = sub[sub["label"] == 1]
#         bkg = sub[sub["label"] == 0]
#         sig_keep = sig.sample(n=n_min, random_state=seed) if len(sig) > n_min else sig
#         bkg_keep = bkg.sample(n=n_min, random_state=seed) if len(bkg) > n_min else bkg
#         parts.append(pd.concat([sig_keep, bkg_keep], ignore_index=True))

#     if not parts:
#         raise RuntimeError("Per-group balancing removed all groups; relax constraints or inspect data.")

#     out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
#     if dropped:
#         print(f"[INFO] balance_groups: dropped {dropped} tiny/pure groups in this split.")
#     return out


# def check_groups(df: pd.DataFrame, name: str) -> None:
#     """Assert both classes are present and warn about any remaining pure groups."""
#     key = group_key(df)
#     bad = [(k, int(g["label"].iloc[0]), len(g)) for k, g in df.groupby(key) if g["label"].nunique() < 2]
#     if bad:
#         print(f"[WARN] {name}: {len(bad)} pure (mass,y) groups remain. Examples: {bad[:5]}")
#     assert df["label"].nunique() == 2, f"{name} has only one class!"


# def split_summary(df: pd.DataFrame, name: str) -> None:
#     """Print a one-line summary (N, class counts, #groups) for a split."""
#     key = group_key(df)
#     print(f"{name}: N={len(df):,}  counts={df['label'].value_counts().to_dict()}  groups={key.nunique()}")


# @torch.no_grad()
# def predict_batched(model: nn.Module, x_tensor: torch.Tensor, device: torch.device,
#                      batch: int = CFG.EVAL_BATCH, use_amp: bool = True) -> np.ndarray:
#     """Run the model over ``x_tensor`` in chunks and return sigmoid probabilities."""
#     model.eval()
#     n = x_tensor.shape[0]
#     out = np.empty(n, dtype=np.float32)
#     amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type == "cuda"))
#     with amp_ctx:
#         for i in range(0, n, batch):
#             xb = x_tensor[i:i + batch].to(device, non_blocking=True)
#             logits = model(xb).view(-1)
#             out[i:i + batch] = torch.sigmoid(logits).detach().cpu().numpy()
#     return out


# def safe_eval_probs(model: nn.Module, x_tensor: torch.Tensor, device: torch.device) -> np.ndarray:
#     """``predict_batched`` with automatic CPU fallback on CUDA OOM."""
#     try:
#         return predict_batched(model, x_tensor, device, batch=CFG.EVAL_BATCH, use_amp=CFG.USE_AMP)
#     except RuntimeError as e:
#         if CFG.CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
#             print("[WARN] CUDA OOM during eval -> falling back to CPU (batched).")
#             cpu_model = model.to(torch.device("cpu"))
#             x_cpu = x_tensor.to(torch.device("cpu"))
#             return predict_batched(cpu_model, x_cpu, torch.device("cpu"),
#                                     batch=max(8192, CFG.EVAL_BATCH), use_amp=False)
#         raise


# # =============================================================================
# # 6. ENGINEERED FEATURES
# # =============================================================================
# def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
#     """Fill in ``*_mvaID_run3`` from ``*_mvaID_nano`` when only the nano version exists."""
#     pairs = [("lead_mvaID_run3", "lead_mvaID_nano"), ("sublead_mvaID_run3", "sublead_mvaID_nano")]
#     for want, alt in pairs:
#         if want not in df.columns and alt in df.columns:
#             df[want] = df[alt]
#     return df


# def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
#     """Add ptjj/mHH, ptHH/mHH, DeltaR(gg), and |cos theta*| variables.

#     Uses protected division (NaN/inf-safe) throughout, matching the
#     original analysis definitions.
#     """
#     m_hh = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
#     m_hh = m_hh.replace(0, np.nan)

#     df["ptjj_over_mHH"] = df["Res_dijet_pt"] / m_hh if "Res_dijet_pt" in df.columns else 0.0
#     df["ptHH_over_mHH"] = (
#         df["Res_HHbbggCandidate_pt"] / m_hh if "Res_HHbbggCandidate_pt" in df.columns else 0.0
#     )

#     if all(c in df.columns for c in ["lead_phi", "sublead_phi", "lead_eta", "sublead_eta"]):
#         dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
#         dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
#         deta = df["lead_eta"] - df["sublead_eta"]
#         df["DeltaR_gg"] = np.sqrt(deta ** 2 + dphi ** 2)
#     else:
#         df["DeltaR_gg"] = 0.0

#     for c in ["Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS"]:
#         if c in df.columns:
#             df[c] = df[c].abs()

#     for c in ["ptjj_over_mHH", "ptHH_over_mHH", "DeltaR_gg"]:
#         df[c] = pd.Series(df[c]).replace([np.inf, -np.inf], np.nan).fillna(0)

#     return df


# # =============================================================================
# # 7. DATA LOADING
# # =============================================================================
# def _read_parquet_slim(file_path: str) -> pd.DataFrame:
#     """Read a parquet file, requesting only the columns we might need.

#     Falls back to reading the entire file if the column-subset read fails
#     for any reason (e.g. schema surprises).
#     """
#     try:
#         cols = pd.read_parquet(file_path, columns=None).columns
#         subset = [c for c in (set(RAW_COLUMNS_OF_INTEREST) | {CFG.WEIGHT_COL}) if c in cols]
#         return pd.read_parquet(file_path, columns=subset)
#     except Exception:
#         return pd.read_parquet(file_path)


# def _prepare_raw(df: pd.DataFrame) -> pd.DataFrame:
#     """Shared preprocessing applied to every raw sample before feature selection.

#     Renames the raw diphoton-mass column (``mass``, per the ntuple schema)
#     to ``diphoton_mass`` immediately, since ``mass`` is later overwritten
#     with the signal-grid mass point (e.g. 300, 400, ... GeV) in
#     ``load_signal`` / ``load_background``. Without this rename the real
#     diphoton mass would be silently clobbered before mass-sculpting
#     validation ever sees it.
#     """
#     if "mass" in df.columns:
#         df = df.rename(columns={"mass": "diphoton_mass"})
#     df = ensure_photon_mva_columns(df)
#     df = add_engineered_features(df)
#     keep = [c for c in FEATURES_CORE if c in df.columns]
#     extras = [c for c in (CFG.WEIGHT_COL, "diphoton_mass") if c in df.columns]
#     return df[keep + extras].copy()


# def load_signal(cfg: Config = CFG) -> pd.DataFrame:
#     """Load and label all available signal (mass, y) parquet samples.

#     Missing files are silently skipped (not all grid points necessarily
#     exist on disk). Missing optional columns are handled gracefully by
#     ``_prepare_raw`` / ``add_engineered_features``.
#     """
#     rows = []
#     for mass in cfg.MASS_POINTS:
#         for y in cfg.Y_VALUES:
#             fp = cfg.SIG_TPL.format(m=mass, y=y)
#             if not os.path.exists(fp):
#                 continue
#             try:
#                 df = _prepare_raw(_read_parquet_slim(fp))
#                 df["mass"], df["y_value"], df["label"] = mass, y, 1
#                 df = downcast_float_cols(ensure_weight(df, cfg.WEIGHT_COL))
#                 rows.append(df)
#             except Exception as e:
#                 print(f"[WARN] read fail {fp}: {e}")
#     signal_df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
#     if signal_df.empty:
#         raise RuntimeError("No signal samples could be loaded.")
#     return signal_df


# def load_background(cfg: Config = CFG) -> pd.DataFrame:
#     """Load and label all configured background parquet files."""
#     parts = []
#     for file_path in cfg.BACKGROUND_FILES:
#         if not os.path.exists(file_path):
#             print(f"[WARN] Missing {file_path}")
#             continue
#         try:
#             df = _prepare_raw(_read_parquet_slim(file_path))
#             df = ensure_weight(df, cfg.WEIGHT_COL)
#             df["label"] = 0
#             parts.append(downcast_float_cols(df))
#         except Exception as e:
#             print(f"[WARN] read fail {file_path}: {e}")

#     bkg_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
#     if bkg_df.empty:
#         raise RuntimeError("No background samples could be loaded.")
#     if cfg.BACKGROUND_FRAC < 1.0:
#         bkg_df = bkg_df.sample(frac=cfg.BACKGROUND_FRAC, random_state=cfg.SEED).reset_index(drop=True)
#     return bkg_df


# def assign_background_parameters(signal_df: pd.DataFrame, background_df: pd.DataFrame,
#                                   seed: int = CFG.SEED) -> pd.DataFrame:
#     """Assign each background event a (mass, y_value) drawn from the signal mixture.

#     This is what turns an un-parameterized background sample into a
#     parameterized one, matching the (mass,y) distribution of the signal so
#     the network sees background at every mass hypothesis it is trained on.
#     Every (mass,y) point present in signal is guaranteed at least one
#     background event (fills in any missing combinations explicitly).
#     """
#     background_df = background_df.copy()
#     sig_my = signal_df[["mass", "y_value"]]
#     mix = sig_my.value_counts(normalize=True).reset_index()
#     mix.columns = ["mass", "y_value", "weight"]
#     sampled = mix.sample(n=len(background_df), replace=True, weights="weight", random_state=seed).reset_index(drop=True)
#     background_df["mass"] = sampled["mass"].values
#     background_df["y_value"] = sampled["y_value"].values

#     need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
#     have = set(map(tuple, background_df[["mass", "y_value"]].drop_duplicates().values.tolist()))
#     missing = list(need - have)
#     if missing:
#         k = min(len(missing), len(background_df))
#         for i, (m, y) in enumerate(missing[:k]):
#             background_df.loc[i, "mass"] = m
#             background_df.loc[i, "y_value"] = y
#     return background_df


# # =============================================================================
# # 8. DATASET PREPARATION
# # =============================================================================
# def prepare_dataframe(signal_df: pd.DataFrame, background_df: pd.DataFrame) -> pd.DataFrame:
#     """Combine signal + parameterized background and drop globally-pure (mass,y) groups."""
#     df_all = pd.concat([signal_df, background_df], ignore_index=True)
#     key = group_key(df_all)
#     nuniq = df_all.groupby(key)["label"].nunique()
#     good_keys = set(nuniq[nuniq == 2].index)
#     mask = key.isin(good_keys)
#     dropped = int((~mask).sum())
#     if dropped:
#         print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
#     return df_all.loc[mask].reset_index(drop=True)


# def resolve_feature_list(df_all: pd.DataFrame, cfg: Config = CFG) -> List[str]:
#     """Compute the final ('mass','y_value' + physics) feature list, honoring ablation config."""
#     features_final = FEATURES_CORE + ["mass", "y_value"]
#     if cfg.DROP_FEATURES:
#         removed = [f for f in cfg.DROP_FEATURES if f in features_final]
#         if removed:
#             print(f"[Ablation] Dropping features: {removed}")
#             features_final = [f for f in features_final if f not in removed]

#     available = [c for c in features_final if c in df_all.columns]
#     missing = sorted(set(features_final) - set(available))
#     if missing:
#         print(f"[Note] Missing features ignored: {missing}")
#     return available


# def split_dataset(df_all: pd.DataFrame, cfg: Config = CFG) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
#     """Group-disjoint train/val/test split using (mass,y) as the group key.

#     Uses ``GroupShuffleSplit`` twice (outer test split, inner val split) so
#     that no (mass,y) point leaks between splits. Optionally balances
#     signal/background counts within each (mass,y) group per split.
#     """
#     groups_all = group_key(df_all)
#     gss_outer = GroupShuffleSplit(n_splits=1, test_size=cfg.TEST_SIZE, random_state=cfg.SEED)
#     idx_trval, idx_te = next(gss_outer.split(df_all, df_all["label"], groups_all))
#     df_trval = df_all.iloc[idx_trval].reset_index(drop=True)
#     df_te = df_all.iloc[idx_te].reset_index(drop=True)

#     gss_inner = GroupShuffleSplit(n_splits=1, test_size=cfg.VAL_SIZE, random_state=cfg.SEED)
#     groups_trval = group_key(df_trval)
#     idx_tr, idx_va = next(gss_inner.split(df_trval, df_trval["label"], groups_trval))
#     df_tr = df_trval.iloc[idx_tr].reset_index(drop=True)
#     df_va = df_trval.iloc[idx_va].reset_index(drop=True)

#     if cfg.BALANCE_PER_GROUP:
#         df_tr = balance_groups(df_tr, seed=cfg.SEED)
#         df_va = balance_groups(df_va, seed=cfg.SEED)
#         df_te = balance_groups(df_te, seed=cfg.SEED)

#     for df, name in [(df_tr, "TRAIN"), (df_va, "VAL"), (df_te, "TEST")]:
#         split_summary(df, name)
#         check_groups(df, name)

#     set_tr, set_va, set_te = (set(group_key(d).unique()) for d in (df_tr, df_va, df_te))
#     print(f"Overlap Train-Val: {len(set_tr & set_va)}")
#     print(f"Overlap Train-Test: {len(set_tr & set_te)}")
#     print(f"Overlap Val-Test: {len(set_va & set_te)}")

#     return df_tr, df_va, df_te


# # =============================================================================
# # 9. SCALING
# # =============================================================================
# def scale_features(
#     df_tr: pd.DataFrame, df_va: pd.DataFrame, df_te: pd.DataFrame,
#     feature_list: Sequence[str], cfg: Config = CFG,
# ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray,
#            np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
#     """Fit a StandardScaler on TRAIN only, transform all splits, and persist it to disk."""
#     x_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, feature_list)
#     x_va_raw, y_va, w_va = df_to_arrays(df_va, feature_list)
#     x_te_raw, y_te, w_te = df_to_arrays(df_te, feature_list)

#     if cfg.DEBUG_SHUFFLE_TRAIN_LABELS:
#         rng = np.random.default_rng(cfg.SEED + 7)
#         y_tr = rng.permutation(y_tr.copy())
#         print("[DEBUG] Shuffled TRAIN labels. Val AUC should be ~0.5.")

#     scaler = StandardScaler()
#     x_tr = scaler.fit_transform(x_tr_raw)
#     x_va = scaler.transform(x_va_raw)
#     x_te = scaler.transform(x_te_raw)

#     os.makedirs(cfg.MODEL_DIR, exist_ok=True)
#     with open(cfg.SCALER_PATH, "wb") as f:
#         pickle.dump(scaler, f)
#     with open(cfg.FEATURES_PATH, "w") as f:
#         json.dump({"features": list(feature_list)}, f, indent=2)
#     print(f"[INFO] Saved scaler to {cfg.SCALER_PATH} and feature list to {cfg.FEATURES_PATH}")

#     return x_tr, x_va, x_te, y_tr, y_va, y_te, w_tr, w_va, w_te, scaler


# def leakage_audit(x_va: np.ndarray, y_va: np.ndarray, feature_list: Sequence[str]) -> None:
#     """Print per-feature single-variable AUC on VAL to flag potential leakage."""
#     print("\n[Leakage audit on VAL] per-feature AUC:")
#     for i, f in enumerate(feature_list):
#         auc_f = roc_auc_score(y_va, x_va[:, i])
#         flag = " <-- suspicious" if (auc_f > 0.95 or auc_f < 0.05) else ""
#         print(f"{f:24s} AUC={auc_f:.4f}{flag}")
#     i_mass, i_y = feature_list.index("mass"), feature_list.index("y_value")
#     my_auc = roc_auc_score(y_va, 0.5 * x_va[:, i_mass] + 0.5 * x_va[:, i_y])
#     print(f"AUC using only (mass,y) on VAL: {my_auc:.4f}")


# # =============================================================================
# # 10. DATASET / DATALOADER
# # =============================================================================
# class ArrayDataset(Dataset):
#     """Simple in-memory (X, y, w) dataset for PyTorch DataLoader."""

#     def __init__(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> None:
#         self.x, self.y, self.w = x, y, w

#     def __len__(self) -> int:
#         return len(self.x)

#     def __getitem__(self, i: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
#         return (
#             torch.tensor(self.x[i], dtype=torch.float32),
#             torch.tensor(self.y[i], dtype=torch.float32),
#             torch.tensor(self.w[i], dtype=torch.float32),
#         )


# def build_dataloaders(
#     x_tr: np.ndarray, y_tr: np.ndarray, w_tr: np.ndarray,
#     x_va: np.ndarray, x_te: np.ndarray, device: torch.device, cfg: Config = CFG,
# ) -> Tuple[DataLoader, torch.Tensor, torch.Tensor]:
#     """Build the training DataLoader plus pre-loaded VAL/TEST tensors on ``device``."""
#     train_loader = DataLoader(
#         ArrayDataset(x_tr, y_tr, w_tr),
#         batch_size=cfg.BATCH_SIZE, shuffle=True,
#         pin_memory=(device.type == "cuda"),
#         num_workers=2 if os.name != "nt" else 0,
#     )
#     x_va_t = torch.tensor(x_va, dtype=torch.float32).to(device)
#     x_te_t = torch.tensor(x_te, dtype=torch.float32).to(device)
#     return train_loader, x_va_t, x_te_t


# # =============================================================================
# # 11. PARAMETERIZED DNN
# # =============================================================================
# class ParameterizedDNN(nn.Module):
#     """Feed-forward parameterized classifier with configurable depth/width.

#     ``mass`` and ``y_value`` are ordinary input features, which is what
#     makes the network "parameterized": a single model learns S(x; mass, y)
#     across the full signal grid, and can be evaluated at any (mass, y)
#     hypothesis (including ones never seen in training) for background-only
#     events.
#     """

#     def __init__(self, n_features: int, hidden_layers: Sequence[int] = CFG.HIDDEN_LAYERS,
#                  dropout: Sequence[float] = CFG.DROPOUT, use_batchnorm: bool = CFG.USE_BATCHNORM) -> None:
#         super().__init__()
#         if len(dropout) != len(hidden_layers):
#             raise ValueError("dropout and hidden_layers must have the same length")

#         layers: List[nn.Module] = []
#         in_dim = n_features
#         for width, p in zip(hidden_layers, dropout):
#             layers.append(nn.Linear(in_dim, width))
#             layers.append(nn.BatchNorm1d(width) if use_batchnorm else nn.Identity())
#             layers.append(nn.ReLU())
#             layers.append(nn.Dropout(p))
#             in_dim = width
#         layers.append(nn.Linear(in_dim, 1))  # logits only (no sigmoid)
#         self.net = nn.Sequential(*layers)

#     def forward(self, x: torch.Tensor) -> torch.Tensor:
#         return self.net(x)


# def xavier_init_(module: nn.Module) -> None:
#     """Xavier/Glorot initialization for Linear layers (biases set to zero)."""
#     if isinstance(module, nn.Linear):
#         nn.init.xavier_uniform_(module.weight)
#         if module.bias is not None:
#             nn.init.zeros_(module.bias)


# def small_normal_zero_bias_(module: nn.Module, std: float = CFG.INIT_WEIGHT_STD) -> None:
#     """Small-normal weight init used for the untrained-model diagnostic (Val AUC ~ 0.5)."""
#     if isinstance(module, nn.Linear):
#         nn.init.normal_(module.weight, mean=0.0, std=std)
#         if module.bias is not None:
#             nn.init.constant_(module.bias, 0.0)


# # =============================================================================
# # 12. TRAINING ENGINE
# # =============================================================================
# def train_one_epoch(
#     model: nn.Module, loader: DataLoader, criterion: nn.Module, optimizer: torch.optim.Optimizer,
#     scaler_amp: torch.amp.GradScaler, device: torch.device, use_amp: bool, cfg: Config = CFG,
# ) -> float:
#     """Run one training epoch with weighted BCE loss; returns the mean training loss."""
#     model.train()
#     total_loss, n_seen = 0.0, 0
#     for xb, yb, wb in loader:
#         xb, yb, wb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True), wb.to(device, non_blocking=True)
#         wb = torch.clamp(wb / (wb.mean() + 1e-8), max=cfg.WEIGHT_CLIP)

#         optimizer.zero_grad(set_to_none=True)
#         with torch.amp.autocast(device_type=device.type, enabled=use_amp):
#             logits = model(xb).view(-1)
#             per_loss = criterion(logits, yb)
#             loss = (per_loss * wb).mean()
#         scaler_amp.scale(loss).backward()
#         scaler_amp.step(optimizer)
#         scaler_amp.update()

#         bs = xb.size(0)
#         total_loss += float(loss.item()) * bs
#         n_seen += bs
#         if cfg.DEBUG_ONE_BATCH:
#             break
#     return total_loss / max(n_seen, 1)


# def evaluate(model: nn.Module, x_tensor: torch.Tensor, y: np.ndarray, device: torch.device) -> Tuple[float, float, np.ndarray]:
#     """Compute (AUC, accuracy, probabilities) for a given split."""
#     probs = safe_eval_probs(model, x_tensor, device)
#     auc_val = roc_auc_score(y, probs)
#     acc_val = accuracy_score(y, (probs > 0.5).astype(int))
#     return auc_val, acc_val, probs


# def predict(model: nn.Module, x: np.ndarray, device: torch.device) -> np.ndarray:
#     """Return sigmoid probabilities for a raw (already-scaled) feature matrix."""
#     x_t = torch.tensor(x, dtype=torch.float32, device=device)
#     return safe_eval_probs(model, x_t, device)


# def train_model(
#     model: nn.Module, train_loader: DataLoader, x_va_t: torch.Tensor, y_va: np.ndarray,
#     device: torch.device, cfg: Config = CFG,
# ) -> Dict[str, List[float]]:
#     """Full training loop: weighted BCE + AdamW + ReduceLROnPlateau + early stopping.

#     The best model (by validation AUC) is checkpointed to ``cfg.MODEL_PATH``
#     and reloaded into ``model`` at the end.
#     """
#     criterion = nn.BCEWithLogitsLoss(reduction="none")
#     optimizer = AdamW(model.parameters(), lr=cfg.LEARNING_RATE, weight_decay=cfg.WEIGHT_DECAY)
#     scheduler = ReduceLROnPlateau(optimizer, mode="max", factor=cfg.LR_FACTOR, patience=cfg.LR_PATIENCE)
#     use_amp = cfg.USE_AMP and device.type == "cuda"
#     scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if device.type == "cuda" else torch.amp.GradScaler(enabled=False)

#     os.makedirs(cfg.MODEL_DIR, exist_ok=True)
#     history: Dict[str, List[float]] = {"train_loss": [], "val_auc": [], "val_acc": []}
#     best_auc, epochs_since_best = -np.inf, 0

#     for epoch in range(cfg.MAX_EPOCHS):
#         train_loss = train_one_epoch(model, train_loader, criterion, optimizer, scaler_amp, device, use_amp, cfg)
#         val_auc, val_acc, _ = evaluate(model, x_va_t, y_va, device)

#         history["train_loss"].append(train_loss)
#         history["val_auc"].append(val_auc)
#         history["val_acc"].append(val_acc)
#         print(f"Epoch {epoch + 1:03d} | TrainLoss: {train_loss:.4f} | ValAUC: {val_auc:.4f} | ValAcc: {val_acc:.4f}")
#         scheduler.step(val_auc)

#         if val_auc > best_auc + 1e-4:
#             best_auc, epochs_since_best = val_auc, 0
#             if cfg.SAVE_MODEL:
#                 torch.save(model.state_dict(), cfg.MODEL_PATH)
#                 print(f"[INFO] New best ValAUC: {best_auc:.4f} -- model saved")
#         else:
#             epochs_since_best += 1
#             if epochs_since_best >= cfg.PATIENCE:
#                 print(f"[INFO] Early stopping at epoch {epoch + 1}.")
#                 break

#     if cfg.SAVE_MODEL and os.path.exists(cfg.MODEL_PATH):
#         state = torch.load(cfg.MODEL_PATH, map_location=device, weights_only=True)
#         model.load_state_dict(state)
#     else:
#         print("[WARN] No saved model found; using current in-memory weights.")

#     return history


# # =============================================================================
# # 13. EVALUATION (plots, feature importance, diagnostics)
# # =============================================================================
# def _savefig(fig_dir: str, filename: str) -> None:
#     os.makedirs(fig_dir, exist_ok=True)
#     plt.savefig(os.path.join(fig_dir, f"{filename}.png"), dpi=600)
#     plt.savefig(os.path.join(fig_dir, f"{filename}.pdf"))
#     print(f"[Saved] {os.path.join(fig_dir, filename)}.{{png,pdf}}")
#     plt.close()


# def plot_training_history(history: Dict[str, List[float]], cfg: Config = CFG) -> None:
#     """Plot & save the training-loss curve."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     plt.figure()
#     plt.plot(history["train_loss"], marker="o", color=CMS_BLUE)
#     plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
#     plt.tight_layout()
#     _savefig(out_dir, "training_loss")


# def plot_validation_auc(history: Dict[str, List[float]], cfg: Config = CFG) -> None:
#     """Plot & save the validation-AUC curve (group-disjoint)."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     plt.figure()
#     plt.plot(history["val_auc"], marker="o", label="Val AUC", color=CMS_RED)
#     plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
#     plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "validation_auc")


# def plot_roc_curve(test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray,
#                     df_te: pd.DataFrame, cfg: Config = CFG, max_legend: int = 10) -> float:
#     """Overall + per-(mass,y) ROC curve on TEST; returns the overall (weighted) test AUC."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "ROC")
#     fpr_all, tpr_all, _ = roc_curve(y_te, test_probs, sample_weight=w_te)
#     test_auc = auc(fpr_all, tpr_all)
#     print(f"\nTest AUC (overall, weighted): {test_auc:.6f}")

#     plt.figure()
#     plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
#     plt.plot([0, 1], [0, 1], linestyle="--", color=CMS_GRAY, lw=1)
#     plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
#     plt.title("ROC -- Test (group-disjoint)")

#     mass_arr = df_te["mass"].astype(int).values
#     y_arr = df_te["y_value"].astype(int).values
#     handles = []
#     for m, yv in np.unique(np.c_[mass_arr, y_arr], axis=0):
#         idx = (mass_arr == m) & (y_arr == yv)
#         if np.unique(y_te[idx]).size < 2:
#             continue
#         fpr_g, tpr_g, _ = roc_curve(y_te[idx], test_probs[idx], sample_weight=w_te[idx] if w_te is not None else None)
#         auc_g = auc(fpr_g, tpr_g)
#         h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.4, label=f"NMSSM_X{m}_Y{yv} (AUC {auc_g:.3f})")
#         handles.append((auc_g, h))
#     handles.sort(key=lambda t: t[0], reverse=True)
#     top = handles[:max_legend]
#     if top:
#         leg = plt.legend([h for _, h in top], [h.get_label() for _, h in top],
#                           title="Top groups", loc="lower right", frameon=True, fontsize=8)
#         plt.gca().add_artist(leg)
#     plt.tight_layout()
#     _savefig(out_dir, "ROC_test")
#     return test_auc


# def _score_dist_panel(ax, probs, y, w, title, ylabel, log_y=False, density=False):
#     """Draw one signal-vs-background score histogram panel onto ``ax``."""
#     sig_mask, bkg_mask = (y == 1), (y == 0)
#     w_sig = w[sig_mask] if w is not None else None
#     w_bkg = w[bkg_mask] if w is not None else None
#     bins = np.linspace(0.0, 1.0, 51)

#     ax.hist(probs[sig_mask], bins=bins, weights=w_sig, density=density,
#             histtype="step", lw=2.0, label="Signal", color=CMS_BLUE)
#     ax.hist(probs[bkg_mask], bins=bins, weights=w_bkg, density=density,
#             histtype="step", lw=2.0, label="Background", color=CMS_RED)
#     if log_y:
#         ax.set_yscale("log")
#     ax.set_xlabel("DNN output (probability)")
#     ax.set_ylabel(ylabel)
#     ax.set_title(title)
#     ax.legend()


# def plot_score_distribution(
#     train_probs: np.ndarray, y_tr: np.ndarray, w_tr: np.ndarray,
#     test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG,
# ) -> None:
#     """Signal-vs-background score distributions, Train and Test shown side by side.

#     Three variants are produced (unweighted, weighted log-y, weighted
#     shape-normalized), each as a single figure with two panels: Train on
#     the left, Test on the right, using identical binning/axes so the two
#     can be compared directly at a glance.
#     """
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")

#     variants = [
#         ("score_distribution_unweighted", "Events", False, False,
#          "Signal vs Background -- Train (unweighted)", "Signal vs Background -- Test (unweighted)"),
#         ("score_distribution_weighted_log", "Weighted events", True, False,
#          "Signal vs Background -- Train (weighted)", "Signal vs Background -- Test (weighted)"),
#         ("score_distribution_shape_normalized", "Density", False, True,
#          "Signal vs Background -- Train (shape)", "Signal vs Background -- Test (shape)"),
#     ]

#     for filename, ylabel, log_y, density, title_tr, title_te in variants:
#         fig, (ax_tr, ax_te) = plt.subplots(1, 2, figsize=(13.5, 5.0), sharey=not log_y)
#         _score_dist_panel(ax_tr, train_probs, y_tr, w_tr, title_tr, ylabel, log_y=log_y, density=density)
#         _score_dist_panel(ax_te, test_probs, y_te, w_te, title_te, ylabel, log_y=log_y, density=density)
#         plt.tight_layout()
#         _savefig(out_dir, filename)
#         plt.close(fig)


# def _weighted_auc(y: np.ndarray, p: np.ndarray, w: Optional[np.ndarray] = None) -> float:
#     return roc_auc_score(y, p, sample_weight=w)


# def _groupwise_shuffle_inplace(x_block: np.ndarray, group_codes: np.ndarray, col: int, rng: np.random.Generator) -> None:
#     """Shuffle column ``col`` within each group (preserves per-(mass,y) marginal)."""
#     for g in np.unique(group_codes):
#         idx = group_codes == g
#         vals = x_block[idx, col].copy()
#         rng.shuffle(vals)
#         x_block[idx, col] = vals


# @torch.no_grad()
# def permutation_importance(
#     model: nn.Module, x_full: np.ndarray, y: np.ndarray, w: np.ndarray,
#     feature_names: Sequence[str], feature_index_map: Dict[str, int], device: torch.device,
#     group_codes: Optional[np.ndarray] = None, n_repeats: int = CFG.N_PERMUTATION_REPEATS,
#     seed: int = CFG.SEED,
# ) -> Tuple[float, Dict[str, float], Dict[str, float]]:
#     """Group-aware permutation importance: AUC drop when each feature is shuffled.

#     Shuffling is performed within each (mass,y) group (when ``group_codes``
#     is given) so the marginal distribution of mass/y is preserved and the
#     importance reflects the physics feature itself, not group leakage.
#     """
#     x_t = torch.tensor(x_full, dtype=torch.float32, device=device)
#     base_auc = _weighted_auc(y, safe_eval_probs(model, x_t, device), w)

#     rng = np.random.default_rng(seed)
#     drops: Dict[str, List[float]] = defaultdict(list)
#     for fname in feature_names:
#         j = feature_index_map[fname]
#         for _ in range(n_repeats):
#             x_perm = x_full.copy()
#             if group_codes is None:
#                 rng.shuffle(x_perm[:, j])
#             else:
#                 _groupwise_shuffle_inplace(x_perm, group_codes, j, rng)
#             xp_t = torch.tensor(x_perm, dtype=torch.float32, device=device)
#             auc_p = _weighted_auc(y, safe_eval_probs(model, xp_t, device), w)
#             drops[fname].append(base_auc - auc_p)

#     imp_mean = {f: float(np.mean(v)) for f, v in drops.items()}
#     imp_std = {f: float(np.std(v, ddof=1)) if len(v) > 1 else 0.0 for f, v in drops.items()}
#     return base_auc, imp_mean, imp_std


# def gradient_saliency(model: nn.Module, x_full: np.ndarray, feature_names_report: Sequence[str],
#                        feature_index_map: Dict[str, int], device: torch.device,
#                        scaler: Optional[StandardScaler] = None, batch: int = 4096) -> Dict[str, float]:
#     """Mean |d logit / d x_raw| per feature, converted back to raw feature scale."""
#     model.eval()
#     n, d = x_full.shape
#     grads_accum = np.zeros(d, dtype=np.float64)
#     n_seen = 0
#     inv_scale = (1.0 / np.asarray(scaler.scale_, dtype=np.float64)) if (scaler is not None and hasattr(scaler, "scale_")) else np.ones(d)

#     ptr = 0
#     while ptr < n:
#         xb = torch.tensor(x_full[ptr:ptr + batch], dtype=torch.float32, device=device, requires_grad=True)
#         logits = model(xb).view(-1)
#         logits.sum().backward()
#         grads_accum += xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()
#         n_seen += 1
#         ptr += batch
#         model.zero_grad(set_to_none=True)

#     grads_raw = (grads_accum / max(n_seen, 1)) * inv_scale
#     return {f: float(grads_raw[feature_index_map[f]]) for f in feature_names_report}


# def plot_feature_importance(
#     imp_mean: Dict[str, float], imp_std: Dict[str, float], title: str, filename: str,
#     cfg: Config = CFG, top_k: int = 25, cms_color: str = CMS_BLUE,
# ) -> None:
#     """Horizontal bar chart of feature importances (used for both permutation and saliency)."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "FeatureImportance")
#     items = sorted(imp_mean.items(), key=lambda t: t[1], reverse=True)[:top_k]
#     labels = [k for k, _ in items][::-1]
#     vals = [imp_mean[k] for k in labels]
#     errs = [imp_std.get(k, 0.0) for k in labels]

#     plt.figure(figsize=(8.0, 0.4 * len(labels) + 1.5), dpi=110)
#     plt.barh(range(len(labels)), vals, xerr=errs, color=cms_color, alpha=0.85)
#     plt.yticks(range(len(labels)), labels)
#     plt.xlabel("Mean AUC drop (permutation)" if "saliency" not in filename else "Normalized saliency")
#     plt.title(title)
#     plt.tight_layout()
#     _savefig(out_dir, filename)


# def plot_correlation_heatmap(df_te: pd.DataFrame, feature_list: Sequence[str], cfg: Config = CFG) -> pd.DataFrame:
#     """Pearson correlation heatmap of physics features (excludes mass/y_value).

#     Computed on the real (pre-imputation) values using pairwise-complete
#     observations, so events missing a given quantity simply drop out of
#     that pair's correlation instead of being imputed first. Imputed values
#     would otherwise manufacture spurious correlation between features that
#     happen to be undefined for the same events (e.g. anything requiring a
#     resolved dijet system).
#     """
#     out_dir = os.path.join(cfg.PLOT_DIR, "FeatureImportance")
#     cols = [c for c in feature_list if c not in ("mass", "y_value")]
#     corr = df_te[cols].corr(method="pearson")  # pandas .corr() uses pairwise-complete obs by default

#     fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
#     im = ax.imshow(corr.values, cmap=CMS_DIVERGING_CMAP, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
#     ax.set_xticks(np.arange(corr.shape[1])); ax.set_yticks(np.arange(corr.shape[0]))
#     ax.set_xticklabels(corr.columns, rotation=90); ax.set_yticklabels(corr.index)
#     ax.set_title("Pearson correlation (test, real values, pairwise-complete)")
#     plt.colorbar(im, ax=ax).set_label("Correlation")
#     plt.tight_layout()
#     _savefig(out_dir, "variable_correlation")
#     return corr


# def prune_correlated_features(
#     df_ref: pd.DataFrame, feature_list: Sequence[str], y_ref: np.ndarray, cfg: Config = CFG,
# ) -> Tuple[List[str], List[Tuple[str, str, float]]]:
#     """Drop redundant features from correlated pairs, keeping the more predictive one.

#     This is deliberately *not* a blanket "remove anything correlated" pass
#     -- neural nets are largely robust to correlated inputs, unlike linear
#     models, so correlation alone isn't a good reason to drop a physics
#     feature. Only pairs at or above ``cfg.CORR_PRUNE_THRESHOLD`` (computed
#     on real, non-imputed values) are considered redundant. For each such
#     pair, the feature with the lower single-variable AUC against the label
#     is dropped, so the more informative variable is always kept. ``mass``
#     and ``y_value`` are always exempt.
#     """
#     keep_cols = [c for c in feature_list if c not in ("mass", "y_value")]
#     corr = df_ref[keep_cols].corr(method="pearson").abs()

#     single_auc: Dict[str, float] = {}
#     for c in keep_cols:
#         vals = df_ref[c].values
#         mask = ~pd.isna(vals)
#         if mask.sum() < 10 or np.unique(y_ref[mask]).size < 2:
#             single_auc[c] = 0.5
#             continue
#         try:
#             single_auc[c] = max(roc_auc_score(y_ref[mask], vals[mask]),
#                                  1 - roc_auc_score(y_ref[mask], vals[mask]))
#         except ValueError:
#             single_auc[c] = 0.5

#     to_drop: set = set()
#     dropped_pairs: List[Tuple[str, str, float]] = []
#     n = len(keep_cols)
#     for i in range(n):
#         ci = keep_cols[i]
#         if ci in to_drop:
#             continue
#         for j in range(i + 1, n):
#             cj = keep_cols[j]
#             if cj in to_drop:
#                 continue
#             r = corr.loc[ci, cj]
#             if pd.notna(r) and r >= cfg.CORR_PRUNE_THRESHOLD:
#                 loser = ci if single_auc[ci] < single_auc[cj] else cj
#                 to_drop.add(loser)
#                 dropped_pairs.append((ci, cj, float(r)))

#     pruned = [f for f in feature_list if f not in to_drop]
#     if to_drop:
#         print(f"[Correlation pruning] threshold={cfg.CORR_PRUNE_THRESHOLD}: "
#               f"dropping {len(to_drop)} redundant feature(s): {sorted(to_drop)}")
#         for a, b, r in dropped_pairs:
#             print(f"    {a} <-> {b}: |r|={r:.3f}")
#     else:
#         print(f"[Correlation pruning] threshold={cfg.CORR_PRUNE_THRESHOLD}: no features exceeded the threshold.")
#     return pruned, dropped_pairs


# def run_extended_diagnostics(model: nn.Module, y_te: np.ndarray, test_probs: np.ndarray, cfg: Config = CFG) -> Dict[str, object]:
#     """Confusion matrix, calibration curve, classification report, Brier score."""
#     out_dir = os.path.join(cfg.PLOT_DIR, "Training")
#     preds = (test_probs > 0.5).astype(int)
#     cm = confusion_matrix(y_te, preds)
#     report = classification_report(y_te, preds, target_names=["Background", "Signal"], output_dict=True)
#     brier = brier_score_loss(y_te, test_probs)

#     plt.figure(figsize=(4.5, 4.0))
#     plt.imshow(cm, cmap=CMS_DIVERGING_CMAP)
#     for i in range(2):
#         for j in range(2):
#             plt.text(j, i, str(cm[i, j]), ha="center", va="center")
#     plt.xticks([0, 1], ["Background", "Signal"]); plt.yticks([0, 1], ["Background", "Signal"])
#     plt.xlabel("Predicted"); plt.ylabel("True"); plt.title("Confusion matrix (Test)")
#     plt.tight_layout()
#     _savefig(out_dir, "confusion_matrix")

#     # calibration curve (10 equal-width bins)
#     bins = np.linspace(0, 1, 11)
#     bin_idx = np.digitize(test_probs, bins) - 1
#     bin_idx = np.clip(bin_idx, 0, 9)
#     frac_pos = [y_te[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(10)]
#     mean_pred = [test_probs[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(10)]

#     plt.figure()
#     plt.plot(mean_pred, frac_pos, marker="o", color=CMS_BLUE, label="Model")
#     plt.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect calibration")
#     plt.xlabel("Mean predicted probability"); plt.ylabel("Fraction of positives")
#     plt.title("Calibration curve (Test)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "calibration_curve")

#     print(f"[Diag] Brier score (Test): {brier:.4f}")
#     return {"confusion_matrix": cm.tolist(), "classification_report": report, "brier_score": float(brier)}


# # =============================================================================
# # 14. PHYSICS VALIDATION (mass sculpting)
# # =============================================================================
# def _find_mass_sculpt_column(df: pd.DataFrame, cfg: Config = CFG) -> Optional[str]:
#     for c in cfg.MASS_SCULPT_CANDIDATES:
#         if c in df.columns:
#             return c
#     return None


# def weighted_ks_2samp(
#     values_a: np.ndarray, weights_a: np.ndarray, values_b: np.ndarray, weights_b: np.ndarray,
# ) -> Tuple[float, float, float, float]:
#     """Weighted two-sample Kolmogorov-Smirnov test.

#     ``scipy.stats.ks_2samp`` does not support event weights, so a manual
#     implementation is used here: the KS statistic D is the maximum absolute
#     difference between the two samples' weighted empirical CDFs, evaluated
#     at the pooled set of observed values. The p-value uses the standard
#     asymptotic Kolmogorov distribution, with each sample's weights folded
#     into an *effective* sample size ``n_eff = (sum w)^2 / sum(w^2)`` --
#     the same effective-entries convention ROOT's weighted KolmogorovTest
#     uses -- rather than the (statistically wrong) raw event count.

#     Returns (D, p_value, n_eff_a, n_eff_b).
#     """
#     values_a = np.asarray(values_a, dtype=float)
#     values_b = np.asarray(values_b, dtype=float)
#     weights_a = np.asarray(weights_a, dtype=float)
#     weights_b = np.asarray(weights_b, dtype=float)

#     if len(values_a) == 0 or len(values_b) == 0:
#         return float("nan"), float("nan"), 0.0, 0.0

#     order_a = np.argsort(values_a)
#     order_b = np.argsort(values_b)
#     va, wa = values_a[order_a], weights_a[order_a]
#     vb, wb = values_b[order_b], weights_b[order_b]

#     cdf_a = np.cumsum(wa) / wa.sum()
#     cdf_b = np.cumsum(wb) / wb.sum()

#     pooled = np.union1d(va, vb)
#     # right-continuous step-function CDF evaluated on the pooled grid
#     cdf_a_pooled = cdf_a[np.searchsorted(va, pooled, side="right") - 1]
#     cdf_a_pooled = np.where(np.searchsorted(va, pooled, side="right") == 0, 0.0, cdf_a_pooled)
#     cdf_b_pooled = cdf_b[np.searchsorted(vb, pooled, side="right") - 1]
#     cdf_b_pooled = np.where(np.searchsorted(vb, pooled, side="right") == 0, 0.0, cdf_b_pooled)

#     d_stat = float(np.max(np.abs(cdf_a_pooled - cdf_b_pooled)))

#     n_eff_a = float(wa.sum() ** 2 / np.sum(wa ** 2)) if np.sum(wa ** 2) > 0 else 0.0
#     n_eff_b = float(wb.sum() ** 2 / np.sum(wb ** 2)) if np.sum(wb ** 2) > 0 else 0.0
#     if n_eff_a <= 0 or n_eff_b <= 0:
#         return d_stat, float("nan"), n_eff_a, n_eff_b

#     n_e = n_eff_a * n_eff_b / (n_eff_a + n_eff_b)
#     p_value = float(kstwobign.sf(d_stat * np.sqrt(n_e)))
#     return d_stat, p_value, n_eff_a, n_eff_b


# def plot_mass_after_score(
#     mass_values: np.ndarray, scores: np.ndarray, weights: np.ndarray, labels: np.ndarray,
#     mass_col_name: str, cfg: Config = CFG,
# ) -> None:
#     """Overlay the background mass spectrum before/after successive score cuts.

#     A well-behaved discriminant should not sculpt a peak/edge into the
#     smoothly-falling background mass spectrum. This is the primary check
#     against a resonant bump being manufactured by the classifier.
#     """
#     out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
#     bkg = labels == 0
#     m_bkg, s_bkg, w_bkg = mass_values[bkg], scores[bkg], (weights[bkg] if weights is not None else None)
#     lo, hi = np.nanpercentile(m_bkg, [1, 99])
#     bins = np.linspace(lo, hi, 40)

#     plt.figure()
#     for cut in cfg.SCORE_CUTS:
#         sel = s_bkg >= cut
#         if sel.sum() < 5:
#             continue
#         w_sel = w_bkg[sel] if w_bkg is not None else None
#         plt.hist(m_bkg[sel], bins=bins, weights=w_sel, density=True, histtype="step", lw=1.8,
#                   label=f"score >= {cut:.1f} (N={int(sel.sum())})")
#     plt.xlabel(mass_col_name); plt.ylabel("Density (shape-normalized)")
#     plt.title("Background mass sculpting vs. score cut")
#     plt.legend(fontsize=8); plt.tight_layout()
#     _savefig(out_dir, "mass_sculpting_shapes")


# def run_mass_sculpting(
#     df_te: pd.DataFrame, test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG,
# ) -> Dict[str, object]:
#     """Run the full mass-sculpting physics-validation suite on the TEST split.

#     Produces:
#       - background mass-shape overlay for a series of score cuts
#       - weighted Kolmogorov-Smirnov test (no-cut vs each score-cut shape)
#       - signal/background efficiency vs. score-cut table
#       - efficiency-vs-score and S/B-style ratio plot

#     If no known mass-proxy column is available in the dataframe, the checks
#     are skipped gracefully (with a clear message) rather than failing.
#     """
#     mass_col = _find_mass_sculpt_column(df_te, cfg)
#     if mass_col is None:
#         print("[WARN] run_mass_sculpting: no mass-proxy column found in "
#               f"{cfg.MASS_SCULPT_CANDIDATES}; skipping mass sculpting validation.")
#         return {"status": "skipped", "reason": "no mass column available"}

#     out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
#     mass_values = df_te[mass_col].to_numpy(dtype=float)
#     plot_mass_after_score(mass_values, test_probs, w_te, y_te, mass_col, cfg)

#     sig_mask, bkg_mask = (y_te == 1), (y_te == 0)
#     m_bkg_all = mass_values[bkg_mask]
#     ks_results, eff_table = {}, []

#     for cut in cfg.SCORE_CUTS:
#         sel_sig = sig_mask & (test_probs >= cut)
#         sel_bkg = bkg_mask & (test_probs >= cut)
#         sig_eff = float(w_te[sel_sig].sum() / max(w_te[sig_mask].sum(), 1e-12))
#         bkg_eff = float(w_te[sel_bkg].sum() / max(w_te[bkg_mask].sum(), 1e-12))
#         eff_table.append({"score_cut": cut, "signal_efficiency": sig_eff, "background_efficiency": bkg_eff})

#         m_cut = mass_values[sel_bkg]
#         w_cut = w_te[sel_bkg]
#         w_bkg_all = w_te[bkg_mask]
#         if len(m_cut) > 5 and len(m_bkg_all) > 5:
#             stat, pval, n_eff_all, n_eff_cut = weighted_ks_2samp(m_bkg_all, w_bkg_all, m_cut, w_cut)
#             ks_results[f"cut_{cut:.1f}"] = {
#                 "ks_stat": stat, "p_value": pval,
#                 "n_eff_no_cut": n_eff_all, "n_eff_this_cut": n_eff_cut,
#             }

#     # efficiency vs score cut
#     plt.figure()
#     cuts = [row["score_cut"] for row in eff_table]
#     plt.plot(cuts, [row["signal_efficiency"] for row in eff_table], marker="o", color=CMS_BLUE, label="Signal efficiency")
#     plt.plot(cuts, [row["background_efficiency"] for row in eff_table], marker="o", color=CMS_RED, label="Background efficiency")
#     plt.xlabel("Score cut"); plt.ylabel("Efficiency")
#     plt.title("Efficiency vs. score cut (Test)"); plt.legend(); plt.tight_layout()
#     _savefig(out_dir, "efficiency_vs_score")

#     # ratio plot (signal eff / background eff, i.e. rejection power)
#     plt.figure()
#     ratio = [row["signal_efficiency"] / max(row["background_efficiency"], 1e-12) for row in eff_table]
#     plt.plot(cuts, ratio, marker="o", color=CMS_GREEN)
#     plt.yscale("log"); plt.xlabel("Score cut"); plt.ylabel("Signal eff / Background eff")
#     plt.title("Rejection power vs. score cut (Test)"); plt.tight_layout()
#     _savefig(out_dir, "efficiency_ratio_vs_score")

#     print("[Physics validation] Weighted KS tests (background mass shape, no-cut vs cut):")
#     for k, v in ks_results.items():
#         print(f"  {k}: KS={v['ks_stat']:.4f}  p={v['p_value']:.4g}  "
#               f"(n_eff no-cut={v['n_eff_no_cut']:.0f}, n_eff this-cut={v['n_eff_this_cut']:.0f})")

#     # per-(mass,y) split validation: overall efficiency table by group at score>=0.5
#     per_group = []
#     if {"mass", "y_value"}.issubset(df_te.columns):
#         key = group_key(df_te)
#         for g in np.unique(key):
#             idx = (key == g).values
#             if np.unique(y_te[idx]).size < 2:
#                 continue
#             sig_idx = idx & sig_mask
#             bkg_idx = idx & bkg_mask
#             sel_sig = sig_idx & (test_probs >= 0.5)
#             sel_bkg = bkg_idx & (test_probs >= 0.5)
#             per_group.append({
#                 "group": g,
#                 "signal_efficiency_at_0.5": float(w_te[sel_sig].sum() / max(w_te[sig_idx].sum(), 1e-12)) if sig_idx.any() else None,
#                 "background_efficiency_at_0.5": float(w_te[sel_bkg].sum() / max(w_te[bkg_idx].sum(), 1e-12)) if bkg_idx.any() else None,
#             })

#     return {
#         "status": "ok",
#         "mass_column_used": mass_col,
#         "efficiency_table": eff_table,
#         "ks_tests": ks_results,
#         "per_group_efficiency_at_0.5": per_group,
#     }


# # =============================================================================
# # 15. LOGGING / OUTPUT PERSISTENCE
# # =============================================================================
# def save_outputs(
#     cfg: Config, history: Dict[str, List[float]], metrics: Dict[str, object], feature_list: Sequence[str],
# ) -> None:
#     """Persist config, training history, and evaluation metrics for reproducibility."""
#     os.makedirs(cfg.LOG_DIR, exist_ok=True)

#     config_snapshot = {
#         "seed": cfg.SEED,
#         "torch_version": torch.__version__,
#         "cuda_version": torch.version.cuda,
#         "device": str(DEVICE),
#         "feature_list": list(feature_list),
#         "timestamp": datetime.now(timezone.utc).isoformat(),
#         "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
#     }
#     with open(os.path.join(cfg.LOG_DIR, "config.json"), "w") as f:
#         json.dump(config_snapshot, f, indent=2, default=str)
#     with open(os.path.join(cfg.LOG_DIR, "history.json"), "w") as f:
#         json.dump(history, f, indent=2)
#     with open(os.path.join(cfg.LOG_DIR, "metrics.json"), "w") as f:
#         json.dump(metrics, f, indent=2, default=str)

#     print(f"[INFO] Saved config/history/metrics to {cfg.LOG_DIR}/")


# # =============================================================================
# # 16. MAIN
# # =============================================================================
# def main() -> None:
#     """End-to-end pDNN training + evaluation + physics-validation pipeline."""
#     cfg = CFG
#     apply_cms_plot_style()
#     for d in (cfg.OUTPUT_DIR, cfg.MODEL_DIR, cfg.PLOT_DIR, cfg.LOG_DIR):
#         os.makedirs(d, exist_ok=True)
#     print(f"[INFO] Using device: {DEVICE}")

#     # ---- Data loading & preparation ----
#     signal_df = load_signal(cfg)
#     background_df = load_background(cfg)
#     background_df = assign_background_parameters(signal_df, background_df, seed=cfg.SEED)
#     df_all = prepare_dataframe(signal_df, background_df)
#     feature_list = resolve_feature_list(df_all, cfg)

#     if cfg.ENABLE_CORR_PRUNING:
#         feature_list, dropped_corr_pairs = prune_correlated_features(
#             df_all, feature_list, df_all["label"].values, cfg
#         )
#     else:
#         dropped_corr_pairs = []

#     df_tr, df_va, df_te = split_dataset(df_all, cfg)

#     # ---- Scaling ----
#     x_tr, x_va, x_te, y_tr, y_va, y_te, w_tr, w_va, w_te, scaler = scale_features(
#         df_tr, df_va, df_te, feature_list, cfg
#     )
#     leakage_audit(x_va, y_va, feature_list)

#     # ---- Model & dataloaders ----
#     train_loader, x_va_t, x_te_t = build_dataloaders(x_tr, y_tr, w_tr, x_va, x_te, DEVICE, cfg)
#     model = ParameterizedDNN(x_tr.shape[1], cfg.HIDDEN_LAYERS, cfg.DROPOUT, cfg.USE_BATCHNORM)
#     model.apply(xavier_init_)
#     model = model.to(DEVICE)

#     # ---- Training ----
#     history = train_model(model, train_loader, x_va_t, y_va, DEVICE, cfg)
#     plot_training_history(history, cfg)
#     plot_validation_auc(history, cfg)

#     # ---- Test-set evaluation ----
#     test_probs = predict(model, x_te, DEVICE)
#     train_probs = predict(model, x_tr, DEVICE)
#     test_auc = plot_roc_curve(test_probs, y_te, w_te, df_te, cfg)
#     plot_score_distribution(train_probs, y_tr, w_tr, test_probs, y_te, w_te, cfg)
#     plot_correlation_heatmap(df_te, feature_list, cfg)
#     diag_metrics = run_extended_diagnostics(model, y_te, test_probs, cfg)

#     i_mass, i_y = feature_list.index("mass"), feature_list.index("y_value")
#     my_auc_test = roc_auc_score(y_te, 0.5 * x_te[:, i_mass] + 0.5 * x_te[:, i_y])
#     print(f"AUC using only (mass,y) on TEST: {my_auc_test:.4f}")

#     # ---- Feature importance ----
#     name_to_idx = {f: feature_list.index(f) for f in feature_list}
#     feat_names_imp = [f for f in feature_list if cfg.INCLUDE_MASS_Y_IN_IMPORTANCE or f not in ("mass", "y_value")]
#     group_codes = pd.factorize(group_key(df_te))[0]

#     base_auc, imp_mean, imp_std = permutation_importance(
#         model, x_te, y_te, w_te, feat_names_imp, name_to_idx, DEVICE,
#         group_codes=group_codes, n_repeats=cfg.N_PERMUTATION_REPEATS, seed=cfg.SEED,
#     )
#     print(f"[Permutation] Baseline TEST AUC = {base_auc:.4f}")
#     plot_feature_importance(imp_mean, imp_std, "Permutation importance (AUC drop) -- TEST",
#                              "feature_importance_permutation_test", cfg, cms_color=CMS_BLUE)

#     sal = gradient_saliency(model, x_te, feat_names_imp, name_to_idx, DEVICE, scaler=scaler)
#     sal_max = max(sal.values()) if sal else 1.0
#     sal_norm = {k: (v / sal_max if sal_max > 0 else 0.0) for k, v in sal.items()}
#     plot_feature_importance(sal_norm, {k: 0.0 for k in sal_norm}, "Input-gradient saliency (normalized) -- TEST",
#                              "feature_importance_saliency_test", cfg, cms_color=CMS_ORANGE)

#     importance_table = pd.DataFrame({
#         "feature": feat_names_imp,
#         "perm_mean_auc_drop": [imp_mean.get(f, np.nan) for f in feat_names_imp],
#         "perm_std_auc_drop": [imp_std.get(f, np.nan) for f in feat_names_imp],
#         "grad_saliency_norm": [sal_norm.get(f, np.nan) for f in feat_names_imp],
#     }).sort_values(["perm_mean_auc_drop", "grad_saliency_norm"], ascending=[False, False], na_position="last")
#     importance_table.to_csv(os.path.join(cfg.PLOT_DIR, "FeatureImportance", "feature_importance_test.csv"), index=False)

#     # ---- Physics validation (mass sculpting) ----
#     sculpting_results = run_mass_sculpting(df_te, test_probs, y_te, w_te, cfg)

#     # ---- Persist everything ----
#     metrics = {
#         "test_auc_weighted": float(test_auc),
#         "mass_y_only_auc_val": float(roc_auc_score(y_va, 0.5 * x_va[:, i_mass] + 0.5 * x_va[:, i_y])),
#         "mass_y_only_auc_test": float(my_auc_test),
#         "permutation_baseline_auc": float(base_auc),
#         "permutation_importance_mean": imp_mean,
#         "permutation_importance_std": imp_std,
#         "gradient_saliency_normalized": sal_norm,
#         "diagnostics": diag_metrics,
#         "mass_sculpting": sculpting_results,
#         "correlation_pruning": {
#             "enabled": cfg.ENABLE_CORR_PRUNING,
#             "threshold": cfg.CORR_PRUNE_THRESHOLD,
#             "dropped_pairs": dropped_corr_pairs,
#             "final_feature_list": feature_list,
#         },
#     }
#     save_outputs(cfg, history, metrics, feature_list)

#     print("\n[DONE] pDNN_v2 pipeline complete.")
#     print(f"       Best model:  {cfg.MODEL_PATH}")
#     print(f"       Scaler:      {cfg.SCALER_PATH}")
#     print(f"       Plots:       {cfg.PLOT_DIR}")
#     print(f"       Logs:        {cfg.LOG_DIR}")


# if __name__ == "__main__":
#     main()


#!/usr/bin/env python
# =============================================================================
# pDNN_v2.py
#
# Parameterized Deep Neural Network (pDNN) for the CMS HH -> bbgg resonant
# search (NMSSM).  Production-quality refactor of the original working
# training script.  Physics, training strategy, and outputs are preserved;
# this file focuses on software-engineering quality (modularity, typing,
# documentation, reproducibility).
#
# Run with:
#     python pDNN_v2.py
# =============================================================================

from __future__ import annotations

# =============================================================================
# 1. IMPORTS
# =============================================================================
import json
import os
import pickle
import warnings
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import kstwobign
from sklearn.metrics import (
    accuracy_score,
    auc,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset

import matplotlib

matplotlib.use("Agg")  # safe for batch / non-interactive execution
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore", category=UserWarning)


# =============================================================================
# 2. CONFIGURATION
#
# Every tunable parameter for the analysis lives here. Nothing below this
# section should define a "magic number" constant outside of this class.
# =============================================================================
@dataclass(frozen=True)
class Config:
    """Single source of truth for all pDNN configuration."""

    # --- reproducibility ---
    SEED: int = 42

    # --- inputs ---
    # Signal: nested <mass_point>/nominal/NOTAG_merged.parquet layout
    # (HiggsDNA-style production), NOT the old flat one-file-per-point
    # convention this previously pointed at.
    SIG_TPL: str = (
        "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
        "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
    )

    # Background: this is a NON-RESONANT training -- the pDNN's background
    # set is restricted to smoothly-falling continuum backgrounds only
    # (data-driven QCD+GJet, prompt diphoton continuum). The resonant
    # single-Higgs backgrounds (ggH/VBF H/VH/bbH/ttH -> gg, which peak at
    # 125 GeV rather than falling smoothly) are deliberately NOT included
    # here -- rejecting those is not this network's job (that's the ttH
    # killer's role, and/or the fit's own resonant-background modeling).
    #
    # Three confirmed files, each one level deep in its own subfolder under
    # BACKGROUND_BASE_DIR (NOT flat, and NOT the same nesting depth as the
    # signal grid):
    #   GGJets_MGG-80/NOTAG_merged.parquet          raw MC diphoton continuum
    #   DDQCCDGJets/DDQCDGJets_Rescaled.parquet      data-driven QCD+GJet template
    #   DDQCCDGJets/GGJets_MGG-80_Rescaled.parquet   rescaled GGJets reference the
    #                                                 DD method itself needs -- a
    #                                                 distinct file from the raw
    #                                                 GGJets_MGG-80 entry above,
    #                                                 despite the similar name.
    BACKGROUND_BASE_DIR: str = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE"
    BACKGROUND_FILENAMES: Tuple[str, ...] = (
        "GGJets_MGG-80/NOTAG_merged.parquet",
        "DDQCCDGJets/DDQCDGJets_Rescaled.parquet",
        "DDQCCDGJets/GGJets_MGG-80_Rescaled.parquet",
    )

    @property
    def BACKGROUND_FILES(self) -> Tuple[str, ...]:
        """Full file paths, derived from BACKGROUND_BASE_DIR + BACKGROUND_FILENAMES."""
        return tuple(
            os.path.join(self.BACKGROUND_BASE_DIR, filename)
            for filename in self.BACKGROUND_FILENAMES
        )

    # Full confirmed 196-point signal grid (X >= 300, Y >= 90). NOTE: this
    # grid is NOT rectangular -- each X has its own list of valid Y values
    # (e.g. X=300 only goes up to Y=170, while X=1000 goes up to Y=800).
    # MASS_POINTS/Y_VALUES below are the UNION of all X's and all Y's
    # respectively; load_signal()'s nested loop tries every (X, Y)
    # combination in their cross-product (16 x 18 = 288), of which only
    # the 196 that actually exist on disk are found -- the other 92 are
    # silently and correctly skipped via the existing os.path.exists()
    # check in load_signal(), not an error. A diagnostic summary count is
    # printed at the end of load_signal() so this is visible, not silent.
    MASS_POINTS: Tuple[int, ...] = (
        300, 320, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000,
    )
    Y_VALUES: Tuple[int, ...] = (
        90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800,
    )
    WEIGHT_COL: str = "weight_central"

    # --- data handling ---
    BACKGROUND_FRAC: float = 1.0          # 1.0 = keep all background
    BALANCE_PER_GROUP: bool = True        # balance S=B inside each (mass,y) after split
    TEST_SIZE: float = 0.20               # outer split (train+val vs test)
    VAL_SIZE: float = 0.20                # inner split (train vs val)
    DROP_FEATURES: Tuple[str, ...] = ()   # optional ablation
    ENABLE_CORR_PRUNING: bool = True      # drop redundant (highly correlated) features
    CORR_PRUNE_THRESHOLD: float = 0.95    # |Pearson r|, computed on real (non-imputed) values

    # --- model architecture ---
    HIDDEN_LAYERS: Tuple[int, ...] = (128, 64, 32)
    DROPOUT: Tuple[float, ...] = (0.3, 0.3, 0.2)
    USE_BATCHNORM: bool = False
    INIT_WEIGHT_STD: float = 1e-2         # small-normal init (stabilizes early training)

    # --- training ---
    BATCH_SIZE: int = 128
    LEARNING_RATE: float = 1e-3
    WEIGHT_DECAY: float = 1e-4
    MAX_EPOCHS: int = 500
    PATIENCE: int = 5
    WEIGHT_CLIP: float = 10.0
    LR_PATIENCE: int = 5
    LR_FACTOR: float = 0.5
    USE_AMP: bool = True                  # mixed precision on CUDA (train + eval)

    # --- evaluation ---
    EVAL_BATCH: int = 32768
    CPU_FALLBACK_ON_OOM: bool = True
    N_PERMUTATION_REPEATS: int = 5
    INCLUDE_MASS_Y_IN_IMPORTANCE: bool = True

    # --- physics validation (mass sculpting) ---
    # Column used as the resonance-mass proxy for sculpting checks. Not all
    # ntuples carry a dedicated diphoton mass column, so a short candidate
    # list is tried in order; the first one present in the dataframe is used.
    MASS_SCULPT_CANDIDATES: Tuple[str, ...] = (
        "diphoton_mass", "mass_gg", "CMS_hgg_mass", "mgg", "Res_HHbbggCandidate_mass",
    )
    SCORE_CUTS: Tuple[float, ...] = (0.0, 0.3, 0.5, 0.7, 0.9)

    # --- debug toggles ---
    DEBUG_ONE_BATCH: bool = False
    DEBUG_SHUFFLE_TRAIN_LABELS: bool = False

    # --- outputs ---
    OUTPUT_DIR: str = "outputs"
    SAVE_MODEL: bool = True

    # derived (filled in __post_init__ equivalent via property)
    @property
    def MODEL_DIR(self) -> str:
        return os.path.join(self.OUTPUT_DIR, "models")

    @property
    def PLOT_DIR(self) -> str:
        return os.path.join(self.OUTPUT_DIR, "plots")

    @property
    def LOG_DIR(self) -> str:
        return os.path.join(self.OUTPUT_DIR, "logs")

    @property
    def MODEL_PATH(self) -> str:
        return os.path.join(self.MODEL_DIR, "best_pdnn.pt")

    @property
    def SCALER_PATH(self) -> str:
        return os.path.join(self.MODEL_DIR, "scaler.pkl")

    @property
    def FEATURES_PATH(self) -> str:
        return os.path.join(self.MODEL_DIR, "features.json")


CFG = Config()

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

np.random.seed(CFG.SEED)
torch.manual_seed(CFG.SEED)
torch.cuda.manual_seed_all(CFG.SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False


# =============================================================================
# 3. PLOT STYLE
# =============================================================================
CMS_BLUE = "#2368B5"
CMS_RED = "#C0392B"
CMS_ORANGE = "#E67E22"
CMS_GREEN = "#2E8B57"
CMS_PURPLE = "#6C5CE7"
CMS_GRAY = "#4D4D4D"

CMS_DIVERGING_CMAP = LinearSegmentedColormap.from_list(
    "cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256
)


def apply_cms_plot_style() -> None:
    """Apply the CMS-like matplotlib style used throughout this script."""
    plt.rcParams.update({
        "figure.figsize": (7.5, 5.5),
        "figure.dpi": 110,
        "axes.grid": True,
        "grid.alpha": 0.30,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "lines.linewidth": 2.0,
    })
    plt.rcParams["axes.prop_cycle"] = cycler(color=[
        CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE,
        "#1ABC9C", "#8E44AD", "#16A085", "#D35400", "#2C3E50",
    ])


# =============================================================================
# 4. FEATURE DEFINITIONS
# =============================================================================
FEATURES_CORE: List[str] = [
    "lead_eta", "lead_phi", "sublead_eta", "sublead_phi",
    "Res_dijet_eta", "Res_dijet_phi",
    "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi", "Res_HHbbggCandidate_pt",
    "Res_dijet_mass_DNNreg",
    "Res_DeltaR_jg_min",
    "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
    "lead_mvaID",
    "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi", "Njets2p5",
    "Res_DeltaPhi_j1MET", "Res_DeltaPhi_j2MET",
    "Res_chi_t0", "Res_chi_t1",
    "Res_dijet_pt", "Res_dijet_mass",
    "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
    "sigma_m_over_m",
    "Res_M_X",
    "lead_r9", "sublead_r9",
    "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
    # engineered (added by add_engineered_features)
    "ptjj_over_mHH", "ptHH_over_mHH",
]

# Raw columns worth requesting explicitly when reading parquet files (keeps
# I/O light while guaranteeing everything needed for engineered features
# and fallbacks is available).
RAW_COLUMNS_OF_INTEREST: List[str] = [
    "lead_eta", "lead_phi", "sublead_eta", "sublead_phi", "eta", "phi",
    "Res_lead_bjet_eta", "Res_lead_bjet_phi",
    "Res_sublead_bjet_eta", "Res_sublead_bjet_phi",
    "Res_dijet_eta", "Res_dijet_phi",
    "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi",
    "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
    "Res_DeltaR_j1g1", "Res_DeltaR_j1g2",
    "Res_DeltaR_j2g1", "Res_DeltaR_j2g2", "Res_DeltaR_jg_min",
    "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
    "lead_mvaID_run3", "sublead_mvaID_run3",
    "lead_mvaID_nano", "sublead_mvaID_nano",
    "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
    "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi",
    "Res_chi_t0", "Res_chi_t1",
    "Res_dijet_pt", "Res_HHbbggCandidate_pt", "Res_HHbbggCandidate_mass",
    "mass",  # raw diphoton invariant mass -> renamed to "diphoton_mass" in _prepare_raw
             # to avoid colliding with the "mass" column used for the signal grid point.
]


# =============================================================================
# 5. UTILITY FUNCTIONS
# =============================================================================
def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast all float64 columns to float32 in place (memory/speed)."""
    for c in df.select_dtypes(include=["float64"]).columns:
        df[c] = df[c].astype("float32")
    return df


def ensure_weight(df: pd.DataFrame, weight_col: str = CFG.WEIGHT_COL) -> pd.DataFrame:
    """Guarantee an event-weight column exists (defaults to 1.0)."""
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df


def group_key(df: pd.DataFrame) -> pd.Series:
    """Build the (mass, y_value) string group key used for grouped splits."""
    return df["mass"].astype(int).astype(str) + "_" + df["y_value"].astype(int).astype(str)


def df_to_arrays(df: pd.DataFrame, feature_list: Sequence[str], seed: int = CFG.SEED) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a dataframe split into (X, y, w) numpy arrays for modeling.

    Missing values are imputed by sampling from each column's own observed
    distribution, not by mean-filling. Mean-filling collapses every event
    missing a given quantity (e.g. events without a resolved dijet) onto
    the *same* value in every affected column simultaneously; since those
    events tend to be missing several related columns at once, that
    manufactures artificial near-1.0 correlation between otherwise
    unrelated features (an imputation artifact, not real physics).
    Sampling from the observed marginal avoids that collapse.
    """
    x_df = df[list(feature_list)].copy()
    rng = np.random.default_rng(seed)
    for col in x_df.columns:
        n_missing = int(x_df[col].isna().sum())
        if n_missing == 0:
            continue
        observed = x_df[col].dropna().values
        fill_values = rng.choice(observed, size=n_missing, replace=True) if len(observed) > 0 else 0.0
        x_df.loc[x_df[col].isna(), col] = fill_values
    x_df = downcast_float_cols(x_df)
    x = x_df.values
    y = df["label"].astype(np.int8).values
    w = df[CFG.WEIGHT_COL].astype("float32").values
    return x, y, w


def balance_groups(df: pd.DataFrame, seed: int = CFG.SEED, min_per_class: int = 1) -> pd.DataFrame:
    """Down-sample signal/background to equal counts within each (mass,y) group.

    Groups with fewer than ``min_per_class`` events in either class are
    dropped entirely (pure groups cannot be balanced).
    """
    key = group_key(df)
    parts, dropped = [], 0
    for _, sub in df.groupby(key, sort=False):
        vc = sub["label"].value_counts()
        if len(vc) < 2 or vc.min() < min_per_class:
            dropped += 1
            continue
        n_min = vc.min()
        sig = sub[sub["label"] == 1]
        bkg = sub[sub["label"] == 0]
        sig_keep = sig.sample(n=n_min, random_state=seed) if len(sig) > n_min else sig
        bkg_keep = bkg.sample(n=n_min, random_state=seed) if len(bkg) > n_min else bkg
        parts.append(pd.concat([sig_keep, bkg_keep], ignore_index=True))

    if not parts:
        raise RuntimeError("Per-group balancing removed all groups; relax constraints or inspect data.")

    out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    if dropped:
        print(f"[INFO] balance_groups: dropped {dropped} tiny/pure groups in this split.")
    return out


def check_groups(df: pd.DataFrame, name: str) -> None:
    """Assert both classes are present and warn about any remaining pure groups."""
    key = group_key(df)
    bad = [(k, int(g["label"].iloc[0]), len(g)) for k, g in df.groupby(key) if g["label"].nunique() < 2]
    if bad:
        print(f"[WARN] {name}: {len(bad)} pure (mass,y) groups remain. Examples: {bad[:5]}")
    assert df["label"].nunique() == 2, f"{name} has only one class!"


def split_summary(df: pd.DataFrame, name: str) -> None:
    """Print a one-line summary (N, class counts, #groups) for a split."""
    key = group_key(df)
    print(f"{name}: N={len(df):,}  counts={df['label'].value_counts().to_dict()}  groups={key.nunique()}")


@torch.no_grad()
def predict_batched(model: nn.Module, x_tensor: torch.Tensor, device: torch.device,
                     batch: int = CFG.EVAL_BATCH, use_amp: bool = True) -> np.ndarray:
    """Run the model over ``x_tensor`` in chunks and return sigmoid probabilities.

    IMPORTANT: under CUDA autocast, the forward pass runs in float16. If
    sigmoid() is applied while still inside the autocast context, the
    resulting probability is computed at float16 precision -- coarse
    enough (~5e-4 near 1.0) to produce a visibly quantized "comb" pattern
    in the score distribution's tail and to saturate to exactly 1.0 far
    more readily than float32 does. This is the identical bug found and
    fixed in inference_PDnn_updated.py's predict_batched(); it existed
    here too, independently, since this function -- not that script's --
    is what generates test_probs for every evaluation and physics
    validation in this file (ROC curve, score distributions, mass
    sculpting, etc.). Logits are explicitly upcast to float32 and
    sigmoid is applied OUTSIDE the autocast context below, so autocast
    still speeds up the forward pass itself, but the probability actually
    used downstream is computed at full precision.
    """
    model.eval()
    n = x_tensor.shape[0]
    out = np.empty(n, dtype=np.float32)
    amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type == "cuda"))
    for i in range(0, n, batch):
        xb = x_tensor[i:i + batch].to(device, non_blocking=True)
        with amp_ctx:
            logits = model(xb).view(-1)
        logits = logits.float()  # upcast BEFORE sigmoid, not after
        out[i:i + batch] = torch.sigmoid(logits).detach().cpu().numpy()
    return out


def safe_eval_probs(model: nn.Module, x_tensor: torch.Tensor, device: torch.device) -> np.ndarray:
    """``predict_batched`` with automatic CPU fallback on CUDA OOM."""
    try:
        return predict_batched(model, x_tensor, device, batch=CFG.EVAL_BATCH, use_amp=CFG.USE_AMP)
    except RuntimeError as e:
        if CFG.CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
            print("[WARN] CUDA OOM during eval -> falling back to CPU (batched).")
            cpu_model = model.to(torch.device("cpu"))
            x_cpu = x_tensor.to(torch.device("cpu"))
            return predict_batched(cpu_model, x_cpu, torch.device("cpu"),
                                    batch=max(8192, CFG.EVAL_BATCH), use_amp=False)
        raise


# =============================================================================
# 6. ENGINEERED FEATURES
# =============================================================================
def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fill in ``*_mvaID_run3`` from ``*_mvaID_nano`` when only the nano version exists."""
    pairs = [("lead_mvaID_run3", "lead_mvaID_nano"), ("sublead_mvaID_run3", "sublead_mvaID_nano")]
    for want, alt in pairs:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add ptjj/mHH, ptHH/mHH, DeltaR(gg), and |cos theta*| variables.

    Uses protected division (NaN/inf-safe) throughout, matching the
    original analysis definitions.
    """
    m_hh = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
    m_hh = m_hh.replace(0, np.nan)

    df["ptjj_over_mHH"] = df["Res_dijet_pt"] / m_hh if "Res_dijet_pt" in df.columns else 0.0
    df["ptHH_over_mHH"] = (
        df["Res_HHbbggCandidate_pt"] / m_hh if "Res_HHbbggCandidate_pt" in df.columns else 0.0
    )

    if all(c in df.columns for c in ["lead_phi", "sublead_phi", "lead_eta", "sublead_eta"]):
        dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
        dphi = np.where(dphi > np.pi, 2 * np.pi - dphi, dphi)
        deta = df["lead_eta"] - df["sublead_eta"]
        df["DeltaR_gg"] = np.sqrt(deta ** 2 + dphi ** 2)
    else:
        df["DeltaR_gg"] = 0.0

    for c in ["Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    for c in ["ptjj_over_mHH", "ptHH_over_mHH", "DeltaR_gg"]:
        df[c] = pd.Series(df[c]).replace([np.inf, -np.inf], np.nan).fillna(0)

    return df


# =============================================================================
# 7. DATA LOADING
# =============================================================================
def _read_parquet_slim(file_path: str) -> pd.DataFrame:
    """Read a parquet file, requesting only the columns we might need.

    Falls back to reading the entire file if the column-subset read fails
    for any reason (e.g. schema surprises).
    """
    try:
        cols = pd.read_parquet(file_path, columns=None).columns
        subset = [c for c in (set(RAW_COLUMNS_OF_INTEREST) | {CFG.WEIGHT_COL}) if c in cols]
        return pd.read_parquet(file_path, columns=subset)
    except Exception:
        return pd.read_parquet(file_path)


def _prepare_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Shared preprocessing applied to every raw sample before feature selection.

    Renames the raw diphoton-mass column (``mass``, per the ntuple schema)
    to ``diphoton_mass`` immediately, since ``mass`` is later overwritten
    with the signal-grid mass point (e.g. 300, 400, ... GeV) in
    ``load_signal`` / ``load_background``. Without this rename the real
    diphoton mass would be silently clobbered before mass-sculpting
    validation ever sees it.
    """
    if "mass" in df.columns:
        df = df.rename(columns={"mass": "diphoton_mass"})
    df = ensure_photon_mva_columns(df)
    df = add_engineered_features(df)
    keep = [c for c in FEATURES_CORE if c in df.columns]
    extras = [c for c in (CFG.WEIGHT_COL, "diphoton_mass") if c in df.columns]
    return df[keep + extras].copy()


def load_signal(cfg: Config = CFG) -> pd.DataFrame:
    """Load and label all available signal (mass, y) parquet samples.

    MASS_POINTS/Y_VALUES together form a rectangular cross-product, but
    the real signal grid is NOT rectangular (see the comment beside those
    fields in Config) -- most (X, Y) combinations tried here are expected
    to not exist on disk and are silently skipped, not an error. A
    found/skipped/found-vs-expected summary is printed at the end so this
    is visible rather than fully silent; missing optional columns in a
    found file are still handled gracefully by ``_prepare_raw`` /
    ``add_engineered_features``.
    """
    rows = []
    n_tried = n_found = n_skipped_missing = 0
    found_points = []
    for mass in cfg.MASS_POINTS:
        for y in cfg.Y_VALUES:
            n_tried += 1
            fp = cfg.SIG_TPL.format(m=mass, y=y)
            if not os.path.exists(fp):
                n_skipped_missing += 1
                continue
            try:
                df = _prepare_raw(_read_parquet_slim(fp))
                df["mass"], df["y_value"], df["label"] = mass, y, 1
                df = downcast_float_cols(ensure_weight(df, cfg.WEIGHT_COL))
                rows.append(df)
                n_found += 1
                found_points.append((mass, y))
            except Exception as e:
                print(f"[WARN] read fail {fp}: {e}")
    print(f"[INFO] load_signal: found {n_found}/{n_tried} (X,Y) combinations tried "
          f"({n_skipped_missing} did not exist on disk -- expected, given the "
          f"non-rectangular grid; see check_missing_masses.py to cross-check "
          f"against the full expected 196-point list).")
    signal_df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if signal_df.empty:
        raise RuntimeError("No signal samples could be loaded.")
    return signal_df


def load_background(cfg: Config = CFG) -> pd.DataFrame:
    """Load and label all configured background parquet files."""
    # Diagnostic: flag any .parquet file present ANYWHERE under
    # BACKGROUND_BASE_DIR (recursive, since configured files are nested
    # one level deep in their own subfolders, not flat) that is NOT in the
    # explicit BACKGROUND_FILENAMES list -- e.g. the resonant single-Higgs
    # backgrounds deliberately excluded from this non-resonant training
    # (bbHtoGG/, ttHtoGG/, etc.), or anything genuinely missed. Purely
    # informational -- nothing extra is loaded.
    try:
        base = Path(cfg.BACKGROUND_BASE_DIR)
        present_files = {
            str(p.relative_to(base)) for p in base.rglob("*.parquet") if p.is_file()
        }
        configured_files = set(cfg.BACKGROUND_FILENAMES)
        unconfigured = sorted(present_files - configured_files)
        if unconfigured:
            print(f"[INFO] {len(unconfigured)} .parquet file(s) present under {cfg.BACKGROUND_BASE_DIR} "
                  f"but NOT in BACKGROUND_FILENAMES (not loaded -- this is a non-resonant training, so "
                  f"resonant single-Higgs backgrounds are expected to show up here; add explicitly only "
                  f"if intentional): {unconfigured}")
    except OSError as e:
        print(f"[WARN] Could not scan {cfg.BACKGROUND_BASE_DIR} for the unconfigured-file "
              f"diagnostic: {e}")

    parts = []
    for file_path in cfg.BACKGROUND_FILES:
        if not os.path.exists(file_path):
            print(f"[WARN] Missing {file_path}")
            continue
        try:
            df = _prepare_raw(_read_parquet_slim(file_path))
            df = ensure_weight(df, cfg.WEIGHT_COL)
            df["label"] = 0
            parts.append(downcast_float_cols(df))
        except Exception as e:
            print(f"[WARN] read fail {file_path}: {e}")

    bkg_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if bkg_df.empty:
        raise RuntimeError("No background samples could be loaded.")
    if cfg.BACKGROUND_FRAC < 1.0:
        bkg_df = bkg_df.sample(frac=cfg.BACKGROUND_FRAC, random_state=cfg.SEED).reset_index(drop=True)
    return bkg_df


def assign_background_parameters(signal_df: pd.DataFrame, background_df: pd.DataFrame,
                                  seed: int = CFG.SEED) -> pd.DataFrame:
    """Assign each background event a (mass, y_value) drawn from the signal mixture.

    This is what turns an un-parameterized background sample into a
    parameterized one, matching the (mass,y) distribution of the signal so
    the network sees background at every mass hypothesis it is trained on.
    Every (mass,y) point present in signal is guaranteed at least one
    background event (fills in any missing combinations explicitly).
    """
    background_df = background_df.copy()
    sig_my = signal_df[["mass", "y_value"]]
    mix = sig_my.value_counts(normalize=True).reset_index()
    mix.columns = ["mass", "y_value", "weight"]
    sampled = mix.sample(n=len(background_df), replace=True, weights="weight", random_state=seed).reset_index(drop=True)
    background_df["mass"] = sampled["mass"].values
    background_df["y_value"] = sampled["y_value"].values

    need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
    have = set(map(tuple, background_df[["mass", "y_value"]].drop_duplicates().values.tolist()))
    missing = list(need - have)
    if missing:
        k = min(len(missing), len(background_df))
        for i, (m, y) in enumerate(missing[:k]):
            background_df.loc[i, "mass"] = m
            background_df.loc[i, "y_value"] = y
    return background_df


# =============================================================================
# 8. DATASET PREPARATION
# =============================================================================
def prepare_dataframe(signal_df: pd.DataFrame, background_df: pd.DataFrame) -> pd.DataFrame:
    """Combine signal + parameterized background and drop globally-pure (mass,y) groups."""
    df_all = pd.concat([signal_df, background_df], ignore_index=True)
    key = group_key(df_all)
    nuniq = df_all.groupby(key)["label"].nunique()
    good_keys = set(nuniq[nuniq == 2].index)
    mask = key.isin(good_keys)
    dropped = int((~mask).sum())
    if dropped:
        print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
    return df_all.loc[mask].reset_index(drop=True)


def resolve_feature_list(df_all: pd.DataFrame, cfg: Config = CFG) -> List[str]:
    """Compute the final ('mass','y_value' + physics) feature list, honoring ablation config."""
    features_final = FEATURES_CORE + ["mass", "y_value"]
    if cfg.DROP_FEATURES:
        removed = [f for f in cfg.DROP_FEATURES if f in features_final]
        if removed:
            print(f"[Ablation] Dropping features: {removed}")
            features_final = [f for f in features_final if f not in removed]

    available = [c for c in features_final if c in df_all.columns]
    missing = sorted(set(features_final) - set(available))
    if missing:
        print(f"[Note] Missing features ignored: {missing}")
    return available


def split_dataset(df_all: pd.DataFrame, cfg: Config = CFG) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Group-disjoint train/val/test split using (mass,y) as the group key.

    Uses ``GroupShuffleSplit`` twice (outer test split, inner val split) so
    that no (mass,y) point leaks between splits. Optionally balances
    signal/background counts within each (mass,y) group per split.
    """
    groups_all = group_key(df_all)
    gss_outer = GroupShuffleSplit(n_splits=1, test_size=cfg.TEST_SIZE, random_state=cfg.SEED)
    idx_trval, idx_te = next(gss_outer.split(df_all, df_all["label"], groups_all))
    df_trval = df_all.iloc[idx_trval].reset_index(drop=True)
    df_te = df_all.iloc[idx_te].reset_index(drop=True)

    gss_inner = GroupShuffleSplit(n_splits=1, test_size=cfg.VAL_SIZE, random_state=cfg.SEED)
    groups_trval = group_key(df_trval)
    idx_tr, idx_va = next(gss_inner.split(df_trval, df_trval["label"], groups_trval))
    df_tr = df_trval.iloc[idx_tr].reset_index(drop=True)
    df_va = df_trval.iloc[idx_va].reset_index(drop=True)

    if cfg.BALANCE_PER_GROUP:
        df_tr = balance_groups(df_tr, seed=cfg.SEED)
        df_va = balance_groups(df_va, seed=cfg.SEED)
        df_te = balance_groups(df_te, seed=cfg.SEED)

    for df, name in [(df_tr, "TRAIN"), (df_va, "VAL"), (df_te, "TEST")]:
        split_summary(df, name)
        check_groups(df, name)

    set_tr, set_va, set_te = (set(group_key(d).unique()) for d in (df_tr, df_va, df_te))
    print(f"Overlap Train-Val: {len(set_tr & set_va)}")
    print(f"Overlap Train-Test: {len(set_tr & set_te)}")
    print(f"Overlap Val-Test: {len(set_va & set_te)}")

    return df_tr, df_va, df_te


# =============================================================================
# 9. SCALING
# =============================================================================
def scale_features(
    df_tr: pd.DataFrame, df_va: pd.DataFrame, df_te: pd.DataFrame,
    feature_list: Sequence[str], cfg: Config = CFG,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    """Fit a StandardScaler on TRAIN only, transform all splits, and persist it to disk."""
    x_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, feature_list)
    x_va_raw, y_va, w_va = df_to_arrays(df_va, feature_list)
    x_te_raw, y_te, w_te = df_to_arrays(df_te, feature_list)

    if cfg.DEBUG_SHUFFLE_TRAIN_LABELS:
        rng = np.random.default_rng(cfg.SEED + 7)
        y_tr = rng.permutation(y_tr.copy())
        print("[DEBUG] Shuffled TRAIN labels. Val AUC should be ~0.5.")

    scaler = StandardScaler()
    x_tr = scaler.fit_transform(x_tr_raw)
    x_va = scaler.transform(x_va_raw)
    x_te = scaler.transform(x_te_raw)

    os.makedirs(cfg.MODEL_DIR, exist_ok=True)
    with open(cfg.SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    with open(cfg.FEATURES_PATH, "w") as f:
        json.dump({"features": list(feature_list)}, f, indent=2)
    print(f"[INFO] Saved scaler to {cfg.SCALER_PATH} and feature list to {cfg.FEATURES_PATH}")

    return x_tr, x_va, x_te, y_tr, y_va, y_te, w_tr, w_va, w_te, scaler


def leakage_audit(x_va: np.ndarray, y_va: np.ndarray, feature_list: Sequence[str]) -> None:
    """Print per-feature single-variable AUC on VAL to flag potential leakage."""
    print("\n[Leakage audit on VAL] per-feature AUC:")
    for i, f in enumerate(feature_list):
        auc_f = roc_auc_score(y_va, x_va[:, i])
        flag = " <-- suspicious" if (auc_f > 0.95 or auc_f < 0.05) else ""
        print(f"{f:24s} AUC={auc_f:.4f}{flag}")
    i_mass, i_y = feature_list.index("mass"), feature_list.index("y_value")
    my_auc = roc_auc_score(y_va, 0.5 * x_va[:, i_mass] + 0.5 * x_va[:, i_y])
    print(f"AUC using only (mass,y) on VAL: {my_auc:.4f}")


# =============================================================================
# 10. DATASET / DATALOADER
# =============================================================================
class ArrayDataset(Dataset):
    """Simple in-memory (X, y, w) dataset for PyTorch DataLoader."""

    def __init__(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> None:
        self.x, self.y, self.w = x, y, w

    def __len__(self) -> int:
        return len(self.x)

    def __getitem__(self, i: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            torch.tensor(self.x[i], dtype=torch.float32),
            torch.tensor(self.y[i], dtype=torch.float32),
            torch.tensor(self.w[i], dtype=torch.float32),
        )


def build_dataloaders(
    x_tr: np.ndarray, y_tr: np.ndarray, w_tr: np.ndarray,
    x_va: np.ndarray, x_te: np.ndarray, device: torch.device, cfg: Config = CFG,
) -> Tuple[DataLoader, torch.Tensor, torch.Tensor]:
    """Build the training DataLoader plus pre-loaded VAL/TEST tensors on ``device``."""
    train_loader = DataLoader(
        ArrayDataset(x_tr, y_tr, w_tr),
        batch_size=cfg.BATCH_SIZE, shuffle=True,
        pin_memory=(device.type == "cuda"),
        num_workers=2 if os.name != "nt" else 0,
    )
    x_va_t = torch.tensor(x_va, dtype=torch.float32).to(device)
    x_te_t = torch.tensor(x_te, dtype=torch.float32).to(device)
    return train_loader, x_va_t, x_te_t


# =============================================================================
# 11. PARAMETERIZED DNN
# =============================================================================
class ParameterizedDNN(nn.Module):
    """Feed-forward parameterized classifier with configurable depth/width.

    ``mass`` and ``y_value`` are ordinary input features, which is what
    makes the network "parameterized": a single model learns S(x; mass, y)
    across the full signal grid, and can be evaluated at any (mass, y)
    hypothesis (including ones never seen in training) for background-only
    events.
    """

    def __init__(self, n_features: int, hidden_layers: Sequence[int] = CFG.HIDDEN_LAYERS,
                 dropout: Sequence[float] = CFG.DROPOUT, use_batchnorm: bool = CFG.USE_BATCHNORM) -> None:
        super().__init__()
        if len(dropout) != len(hidden_layers):
            raise ValueError("dropout and hidden_layers must have the same length")

        layers: List[nn.Module] = []
        in_dim = n_features
        for width, p in zip(hidden_layers, dropout):
            layers.append(nn.Linear(in_dim, width))
            layers.append(nn.BatchNorm1d(width) if use_batchnorm else nn.Identity())
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(p))
            in_dim = width
        layers.append(nn.Linear(in_dim, 1))  # logits only (no sigmoid)
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def xavier_init_(module: nn.Module) -> None:
    """Xavier/Glorot initialization for Linear layers (biases set to zero)."""
    if isinstance(module, nn.Linear):
        nn.init.xavier_uniform_(module.weight)
        if module.bias is not None:
            nn.init.zeros_(module.bias)


def small_normal_zero_bias_(module: nn.Module, std: float = CFG.INIT_WEIGHT_STD) -> None:
    """Small-normal weight init used for the untrained-model diagnostic (Val AUC ~ 0.5)."""
    if isinstance(module, nn.Linear):
        nn.init.normal_(module.weight, mean=0.0, std=std)
        if module.bias is not None:
            nn.init.constant_(module.bias, 0.0)


# =============================================================================
# 12. TRAINING ENGINE
# =============================================================================
def train_one_epoch(
    model: nn.Module, loader: DataLoader, criterion: nn.Module, optimizer: torch.optim.Optimizer,
    scaler_amp: torch.amp.GradScaler, device: torch.device, use_amp: bool, cfg: Config = CFG,
) -> float:
    """Run one training epoch with weighted BCE loss; returns the mean training loss."""
    model.train()
    total_loss, n_seen = 0.0, 0
    for xb, yb, wb in loader:
        xb, yb, wb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True), wb.to(device, non_blocking=True)
        wb = torch.clamp(wb / (wb.mean() + 1e-8), max=cfg.WEIGHT_CLIP)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(xb).view(-1)
            per_loss = criterion(logits, yb)
            loss = (per_loss * wb).mean()
        scaler_amp.scale(loss).backward()
        scaler_amp.step(optimizer)
        scaler_amp.update()

        bs = xb.size(0)
        total_loss += float(loss.item()) * bs
        n_seen += bs
        if cfg.DEBUG_ONE_BATCH:
            break
    return total_loss / max(n_seen, 1)


def evaluate(model: nn.Module, x_tensor: torch.Tensor, y: np.ndarray, device: torch.device) -> Tuple[float, float, np.ndarray]:
    """Compute (AUC, accuracy, probabilities) for a given split."""
    probs = safe_eval_probs(model, x_tensor, device)
    auc_val = roc_auc_score(y, probs)
    acc_val = accuracy_score(y, (probs > 0.5).astype(int))
    return auc_val, acc_val, probs


def predict(model: nn.Module, x: np.ndarray, device: torch.device) -> np.ndarray:
    """Return sigmoid probabilities for a raw (already-scaled) feature matrix."""
    x_t = torch.tensor(x, dtype=torch.float32, device=device)
    return safe_eval_probs(model, x_t, device)


def train_model(
    model: nn.Module, train_loader: DataLoader, x_va_t: torch.Tensor, y_va: np.ndarray,
    device: torch.device, cfg: Config = CFG,
) -> Dict[str, List[float]]:
    """Full training loop: weighted BCE + AdamW + ReduceLROnPlateau + early stopping.

    The best model (by validation AUC) is checkpointed to ``cfg.MODEL_PATH``
    and reloaded into ``model`` at the end.
    """
    criterion = nn.BCEWithLogitsLoss(reduction="none")
    optimizer = AdamW(model.parameters(), lr=cfg.LEARNING_RATE, weight_decay=cfg.WEIGHT_DECAY)
    scheduler = ReduceLROnPlateau(optimizer, mode="max", factor=cfg.LR_FACTOR, patience=cfg.LR_PATIENCE)
    use_amp = cfg.USE_AMP and device.type == "cuda"
    scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if device.type == "cuda" else torch.amp.GradScaler(enabled=False)

    os.makedirs(cfg.MODEL_DIR, exist_ok=True)
    history: Dict[str, List[float]] = {"train_loss": [], "val_auc": [], "val_acc": []}
    best_auc, epochs_since_best = -np.inf, 0

    for epoch in range(cfg.MAX_EPOCHS):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, scaler_amp, device, use_amp, cfg)
        val_auc, val_acc, _ = evaluate(model, x_va_t, y_va, device)

        history["train_loss"].append(train_loss)
        history["val_auc"].append(val_auc)
        history["val_acc"].append(val_acc)
        print(f"Epoch {epoch + 1:03d} | TrainLoss: {train_loss:.4f} | ValAUC: {val_auc:.4f} | ValAcc: {val_acc:.4f}")
        scheduler.step(val_auc)

        if val_auc > best_auc + 1e-4:
            best_auc, epochs_since_best = val_auc, 0
            if cfg.SAVE_MODEL:
                torch.save(model.state_dict(), cfg.MODEL_PATH)
                print(f"[INFO] New best ValAUC: {best_auc:.4f} -- model saved")
        else:
            epochs_since_best += 1
            if epochs_since_best >= cfg.PATIENCE:
                print(f"[INFO] Early stopping at epoch {epoch + 1}.")
                break

    if cfg.SAVE_MODEL and os.path.exists(cfg.MODEL_PATH):
        state = torch.load(cfg.MODEL_PATH, map_location=device, weights_only=True)
        model.load_state_dict(state)
    else:
        print("[WARN] No saved model found; using current in-memory weights.")

    return history


# =============================================================================
# 13. EVALUATION (plots, feature importance, diagnostics)
# =============================================================================
def _savefig(fig_dir: str, filename: str) -> None:
    os.makedirs(fig_dir, exist_ok=True)
    plt.savefig(os.path.join(fig_dir, f"{filename}.png"), dpi=600)
    plt.savefig(os.path.join(fig_dir, f"{filename}.pdf"))
    print(f"[Saved] {os.path.join(fig_dir, filename)}.{{png,pdf}}")
    plt.close()


def plot_training_history(history: Dict[str, List[float]], cfg: Config = CFG) -> None:
    """Plot & save the training-loss curve."""
    out_dir = os.path.join(cfg.PLOT_DIR, "Training")
    plt.figure()
    plt.plot(history["train_loss"], marker="o", color=CMS_BLUE)
    plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
    plt.tight_layout()
    _savefig(out_dir, "training_loss")


def plot_validation_auc(history: Dict[str, List[float]], cfg: Config = CFG) -> None:
    """Plot & save the validation-AUC curve (group-disjoint)."""
    out_dir = os.path.join(cfg.PLOT_DIR, "Training")
    plt.figure()
    plt.plot(history["val_auc"], marker="o", label="Val AUC", color=CMS_RED)
    plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
    plt.legend(); plt.tight_layout()
    _savefig(out_dir, "validation_auc")


def plot_roc_curve(test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray,
                    df_te: pd.DataFrame, cfg: Config = CFG, max_legend: int = 10) -> float:
    """Overall + per-(mass,y) ROC curve on TEST; returns the overall (weighted) test AUC."""
    out_dir = os.path.join(cfg.PLOT_DIR, "ROC")
    fpr_all, tpr_all, _ = roc_curve(y_te, test_probs, sample_weight=w_te)
    test_auc = auc(fpr_all, tpr_all)
    print(f"\nTest AUC (overall, weighted): {test_auc:.6f}")

    plt.figure()
    plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
    plt.plot([0, 1], [0, 1], linestyle="--", color=CMS_GRAY, lw=1)
    plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
    plt.title("ROC -- Test (group-disjoint)")

    mass_arr = df_te["mass"].astype(int).values
    y_arr = df_te["y_value"].astype(int).values
    handles = []
    for m, yv in np.unique(np.c_[mass_arr, y_arr], axis=0):
        idx = (mass_arr == m) & (y_arr == yv)
        if np.unique(y_te[idx]).size < 2:
            continue
        fpr_g, tpr_g, _ = roc_curve(y_te[idx], test_probs[idx], sample_weight=w_te[idx] if w_te is not None else None)
        auc_g = auc(fpr_g, tpr_g)
        h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.4, label=f"NMSSM_X{m}_Y{yv} (AUC {auc_g:.3f})")
        handles.append((auc_g, h))
    handles.sort(key=lambda t: t[0], reverse=True)
    top = handles[:max_legend]
    if top:
        leg = plt.legend([h for _, h in top], [h.get_label() for _, h in top],
                          title="Top groups", loc="lower right", frameon=True, fontsize=8)
        plt.gca().add_artist(leg)
    plt.tight_layout()
    _savefig(out_dir, "ROC_test")
    return test_auc


def _score_dist_panel(ax, probs, y, w, title, ylabel, log_y=False, density=False):
    """Draw one signal-vs-background score histogram panel onto ``ax``."""
    sig_mask, bkg_mask = (y == 1), (y == 0)
    w_sig = w[sig_mask] if w is not None else None
    w_bkg = w[bkg_mask] if w is not None else None
    bins = np.linspace(0.0, 1.0, 51)

    ax.hist(probs[sig_mask], bins=bins, weights=w_sig, density=density,
            histtype="step", lw=2.0, label="Signal", color=CMS_BLUE)
    ax.hist(probs[bkg_mask], bins=bins, weights=w_bkg, density=density,
            histtype="step", lw=2.0, label="Background", color=CMS_RED)
    if log_y:
        ax.set_yscale("log")
    ax.set_xlabel("DNN output (probability)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()


def plot_score_distribution(
    train_probs: np.ndarray, y_tr: np.ndarray, w_tr: np.ndarray,
    test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG,
) -> None:
    """Signal-vs-background score distributions, Train and Test shown side by side.

    Three variants are produced (unweighted, weighted log-y, weighted
    shape-normalized), each as a single figure with two panels: Train on
    the left, Test on the right, using identical binning/axes so the two
    can be compared directly at a glance.
    """
    out_dir = os.path.join(cfg.PLOT_DIR, "Training")

    variants = [
        ("score_distribution_unweighted", "Events", False, False,
         "Signal vs Background -- Train (unweighted)", "Signal vs Background -- Test (unweighted)"),
        ("score_distribution_weighted_log", "Weighted events", True, False,
         "Signal vs Background -- Train (weighted)", "Signal vs Background -- Test (weighted)"),
        ("score_distribution_shape_normalized", "Density", False, True,
         "Signal vs Background -- Train (shape)", "Signal vs Background -- Test (shape)"),
    ]

    for filename, ylabel, log_y, density, title_tr, title_te in variants:
        fig, (ax_tr, ax_te) = plt.subplots(1, 2, figsize=(13.5, 5.0), sharey=not log_y)
        _score_dist_panel(ax_tr, train_probs, y_tr, w_tr, title_tr, ylabel, log_y=log_y, density=density)
        _score_dist_panel(ax_te, test_probs, y_te, w_te, title_te, ylabel, log_y=log_y, density=density)
        plt.tight_layout()
        _savefig(out_dir, filename)
        plt.close(fig)


def _weighted_auc(y: np.ndarray, p: np.ndarray, w: Optional[np.ndarray] = None) -> float:
    return roc_auc_score(y, p, sample_weight=w)


def _groupwise_shuffle_inplace(x_block: np.ndarray, group_codes: np.ndarray, col: int, rng: np.random.Generator) -> None:
    """Shuffle column ``col`` within each group (preserves per-(mass,y) marginal)."""
    for g in np.unique(group_codes):
        idx = group_codes == g
        vals = x_block[idx, col].copy()
        rng.shuffle(vals)
        x_block[idx, col] = vals


@torch.no_grad()
def permutation_importance(
    model: nn.Module, x_full: np.ndarray, y: np.ndarray, w: np.ndarray,
    feature_names: Sequence[str], feature_index_map: Dict[str, int], device: torch.device,
    group_codes: Optional[np.ndarray] = None, n_repeats: int = CFG.N_PERMUTATION_REPEATS,
    seed: int = CFG.SEED,
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    """Group-aware permutation importance: AUC drop when each feature is shuffled.

    Shuffling is performed within each (mass,y) group (when ``group_codes``
    is given) so the marginal distribution of mass/y is preserved and the
    importance reflects the physics feature itself, not group leakage.
    """
    x_t = torch.tensor(x_full, dtype=torch.float32, device=device)
    base_auc = _weighted_auc(y, safe_eval_probs(model, x_t, device), w)

    rng = np.random.default_rng(seed)
    drops: Dict[str, List[float]] = defaultdict(list)
    for fname in feature_names:
        j = feature_index_map[fname]
        for _ in range(n_repeats):
            x_perm = x_full.copy()
            if group_codes is None:
                rng.shuffle(x_perm[:, j])
            else:
                _groupwise_shuffle_inplace(x_perm, group_codes, j, rng)
            xp_t = torch.tensor(x_perm, dtype=torch.float32, device=device)
            auc_p = _weighted_auc(y, safe_eval_probs(model, xp_t, device), w)
            drops[fname].append(base_auc - auc_p)

    imp_mean = {f: float(np.mean(v)) for f, v in drops.items()}
    imp_std = {f: float(np.std(v, ddof=1)) if len(v) > 1 else 0.0 for f, v in drops.items()}
    return base_auc, imp_mean, imp_std


def gradient_saliency(model: nn.Module, x_full: np.ndarray, feature_names_report: Sequence[str],
                       feature_index_map: Dict[str, int], device: torch.device,
                       scaler: Optional[StandardScaler] = None, batch: int = 4096) -> Dict[str, float]:
    """Mean |d logit / d x_raw| per feature, converted back to raw feature scale."""
    model.eval()
    n, d = x_full.shape
    grads_accum = np.zeros(d, dtype=np.float64)
    n_seen = 0
    inv_scale = (1.0 / np.asarray(scaler.scale_, dtype=np.float64)) if (scaler is not None and hasattr(scaler, "scale_")) else np.ones(d)

    ptr = 0
    while ptr < n:
        xb = torch.tensor(x_full[ptr:ptr + batch], dtype=torch.float32, device=device, requires_grad=True)
        logits = model(xb).view(-1)
        logits.sum().backward()
        grads_accum += xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()
        n_seen += 1
        ptr += batch
        model.zero_grad(set_to_none=True)

    grads_raw = (grads_accum / max(n_seen, 1)) * inv_scale
    return {f: float(grads_raw[feature_index_map[f]]) for f in feature_names_report}


def plot_feature_importance(
    imp_mean: Dict[str, float], imp_std: Dict[str, float], title: str, filename: str,
    cfg: Config = CFG, top_k: int = 25, cms_color: str = CMS_BLUE,
) -> None:
    """Horizontal bar chart of feature importances (used for both permutation and saliency)."""
    out_dir = os.path.join(cfg.PLOT_DIR, "FeatureImportance")
    items = sorted(imp_mean.items(), key=lambda t: t[1], reverse=True)[:top_k]
    labels = [k for k, _ in items][::-1]
    vals = [imp_mean[k] for k in labels]
    errs = [imp_std.get(k, 0.0) for k in labels]

    plt.figure(figsize=(8.0, 0.4 * len(labels) + 1.5), dpi=110)
    plt.barh(range(len(labels)), vals, xerr=errs, color=cms_color, alpha=0.85)
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Mean AUC drop (permutation)" if "saliency" not in filename else "Normalized saliency")
    plt.title(title)
    plt.tight_layout()
    _savefig(out_dir, filename)


def plot_correlation_heatmap(df_te: pd.DataFrame, feature_list: Sequence[str], cfg: Config = CFG) -> pd.DataFrame:
    """Pearson correlation heatmap of physics features (excludes mass/y_value).

    Computed on the real (pre-imputation) values using pairwise-complete
    observations, so events missing a given quantity simply drop out of
    that pair's correlation instead of being imputed first. Imputed values
    would otherwise manufacture spurious correlation between features that
    happen to be undefined for the same events (e.g. anything requiring a
    resolved dijet system).
    """
    out_dir = os.path.join(cfg.PLOT_DIR, "FeatureImportance")
    cols = [c for c in feature_list if c not in ("mass", "y_value")]
    corr = df_te[cols].corr(method="pearson")  # pandas .corr() uses pairwise-complete obs by default

    fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
    im = ax.imshow(corr.values, cmap=CMS_DIVERGING_CMAP, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
    ax.set_xticks(np.arange(corr.shape[1])); ax.set_yticks(np.arange(corr.shape[0]))
    ax.set_xticklabels(corr.columns, rotation=90); ax.set_yticklabels(corr.index)
    ax.set_title("Pearson correlation (test, real values, pairwise-complete)")
    plt.colorbar(im, ax=ax).set_label("Correlation")
    plt.tight_layout()
    _savefig(out_dir, "variable_correlation")
    return corr


def prune_correlated_features(
    df_ref: pd.DataFrame, feature_list: Sequence[str], y_ref: np.ndarray, cfg: Config = CFG,
) -> Tuple[List[str], List[Tuple[str, str, float]]]:
    """Drop redundant features from correlated pairs, keeping the more predictive one.

    This is deliberately *not* a blanket "remove anything correlated" pass
    -- neural nets are largely robust to correlated inputs, unlike linear
    models, so correlation alone isn't a good reason to drop a physics
    feature. Only pairs at or above ``cfg.CORR_PRUNE_THRESHOLD`` (computed
    on real, non-imputed values) are considered redundant. For each such
    pair, the feature with the lower single-variable AUC against the label
    is dropped, so the more informative variable is always kept. ``mass``
    and ``y_value`` are always exempt.
    """
    keep_cols = [c for c in feature_list if c not in ("mass", "y_value")]
    corr = df_ref[keep_cols].corr(method="pearson").abs()

    single_auc: Dict[str, float] = {}
    for c in keep_cols:
        vals = df_ref[c].values
        mask = ~pd.isna(vals)
        if mask.sum() < 10 or np.unique(y_ref[mask]).size < 2:
            single_auc[c] = 0.5
            continue
        try:
            single_auc[c] = max(roc_auc_score(y_ref[mask], vals[mask]),
                                 1 - roc_auc_score(y_ref[mask], vals[mask]))
        except ValueError:
            single_auc[c] = 0.5

    to_drop: set = set()
    dropped_pairs: List[Tuple[str, str, float]] = []
    n = len(keep_cols)
    for i in range(n):
        ci = keep_cols[i]
        if ci in to_drop:
            continue
        for j in range(i + 1, n):
            cj = keep_cols[j]
            if cj in to_drop:
                continue
            r = corr.loc[ci, cj]
            if pd.notna(r) and r >= cfg.CORR_PRUNE_THRESHOLD:
                loser = ci if single_auc[ci] < single_auc[cj] else cj
                to_drop.add(loser)
                dropped_pairs.append((ci, cj, float(r)))

    pruned = [f for f in feature_list if f not in to_drop]
    if to_drop:
        print(f"[Correlation pruning] threshold={cfg.CORR_PRUNE_THRESHOLD}: "
              f"dropping {len(to_drop)} redundant feature(s): {sorted(to_drop)}")
        for a, b, r in dropped_pairs:
            print(f"    {a} <-> {b}: |r|={r:.3f}")
    else:
        print(f"[Correlation pruning] threshold={cfg.CORR_PRUNE_THRESHOLD}: no features exceeded the threshold.")
    return pruned, dropped_pairs


def run_extended_diagnostics(model: nn.Module, y_te: np.ndarray, test_probs: np.ndarray, cfg: Config = CFG) -> Dict[str, object]:
    """Confusion matrix, calibration curve, classification report, Brier score."""
    out_dir = os.path.join(cfg.PLOT_DIR, "Training")
    preds = (test_probs > 0.5).astype(int)
    cm = confusion_matrix(y_te, preds)
    report = classification_report(y_te, preds, target_names=["Background", "Signal"], output_dict=True)
    brier = brier_score_loss(y_te, test_probs)

    plt.figure(figsize=(4.5, 4.0))
    plt.imshow(cm, cmap=CMS_DIVERGING_CMAP)
    for i in range(2):
        for j in range(2):
            plt.text(j, i, str(cm[i, j]), ha="center", va="center")
    plt.xticks([0, 1], ["Background", "Signal"]); plt.yticks([0, 1], ["Background", "Signal"])
    plt.xlabel("Predicted"); plt.ylabel("True"); plt.title("Confusion matrix (Test)")
    plt.tight_layout()
    _savefig(out_dir, "confusion_matrix")

    # calibration curve (10 equal-width bins)
    bins = np.linspace(0, 1, 11)
    bin_idx = np.digitize(test_probs, bins) - 1
    bin_idx = np.clip(bin_idx, 0, 9)
    frac_pos = [y_te[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(10)]
    mean_pred = [test_probs[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(10)]

    plt.figure()
    plt.plot(mean_pred, frac_pos, marker="o", color=CMS_BLUE, label="Model")
    plt.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect calibration")
    plt.xlabel("Mean predicted probability"); plt.ylabel("Fraction of positives")
    plt.title("Calibration curve (Test)"); plt.legend(); plt.tight_layout()
    _savefig(out_dir, "calibration_curve")

    print(f"[Diag] Brier score (Test): {brier:.4f}")
    return {"confusion_matrix": cm.tolist(), "classification_report": report, "brier_score": float(brier)}


# =============================================================================
# 14. PHYSICS VALIDATION (mass sculpting)
# =============================================================================
def _find_mass_sculpt_column(df: pd.DataFrame, cfg: Config = CFG) -> Optional[str]:
    for c in cfg.MASS_SCULPT_CANDIDATES:
        if c in df.columns:
            return c
    return None


def weighted_ks_2samp(
    values_a: np.ndarray, weights_a: np.ndarray, values_b: np.ndarray, weights_b: np.ndarray,
) -> Tuple[float, float, float, float]:
    """Weighted two-sample Kolmogorov-Smirnov test.

    ``scipy.stats.ks_2samp`` does not support event weights, so a manual
    implementation is used here: the KS statistic D is the maximum absolute
    difference between the two samples' weighted empirical CDFs, evaluated
    at the pooled set of observed values. The p-value uses the standard
    asymptotic Kolmogorov distribution, with each sample's weights folded
    into an *effective* sample size ``n_eff = (sum w)^2 / sum(w^2)`` --
    the same effective-entries convention ROOT's weighted KolmogorovTest
    uses -- rather than the (statistically wrong) raw event count.

    Returns (D, p_value, n_eff_a, n_eff_b).
    """
    values_a = np.asarray(values_a, dtype=float)
    values_b = np.asarray(values_b, dtype=float)
    weights_a = np.asarray(weights_a, dtype=float)
    weights_b = np.asarray(weights_b, dtype=float)

    if len(values_a) == 0 or len(values_b) == 0:
        return float("nan"), float("nan"), 0.0, 0.0

    order_a = np.argsort(values_a)
    order_b = np.argsort(values_b)
    va, wa = values_a[order_a], weights_a[order_a]
    vb, wb = values_b[order_b], weights_b[order_b]

    cdf_a = np.cumsum(wa) / wa.sum()
    cdf_b = np.cumsum(wb) / wb.sum()

    pooled = np.union1d(va, vb)
    # right-continuous step-function CDF evaluated on the pooled grid
    cdf_a_pooled = cdf_a[np.searchsorted(va, pooled, side="right") - 1]
    cdf_a_pooled = np.where(np.searchsorted(va, pooled, side="right") == 0, 0.0, cdf_a_pooled)
    cdf_b_pooled = cdf_b[np.searchsorted(vb, pooled, side="right") - 1]
    cdf_b_pooled = np.where(np.searchsorted(vb, pooled, side="right") == 0, 0.0, cdf_b_pooled)

    d_stat = float(np.max(np.abs(cdf_a_pooled - cdf_b_pooled)))

    n_eff_a = float(wa.sum() ** 2 / np.sum(wa ** 2)) if np.sum(wa ** 2) > 0 else 0.0
    n_eff_b = float(wb.sum() ** 2 / np.sum(wb ** 2)) if np.sum(wb ** 2) > 0 else 0.0
    if n_eff_a <= 0 or n_eff_b <= 0:
        return d_stat, float("nan"), n_eff_a, n_eff_b

    n_e = n_eff_a * n_eff_b / (n_eff_a + n_eff_b)
    p_value = float(kstwobign.sf(d_stat * np.sqrt(n_e)))
    return d_stat, p_value, n_eff_a, n_eff_b


def plot_mass_after_score(
    mass_values: np.ndarray, scores: np.ndarray, weights: np.ndarray, labels: np.ndarray,
    mass_col_name: str, cfg: Config = CFG, x_min: Optional[float] = None,
) -> None:
    """Overlay the background mass spectrum before/after successive score cuts.

    A well-behaved discriminant should not sculpt a peak/edge into the
    smoothly-falling background mass spectrum. This is the primary check
    against a resonant bump being manufactured by the classifier.

    x_min: optional fixed lower x-axis bound, overriding the default
    data-driven 1st-percentile lower bound.
    """
    out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
    bkg = labels == 0
    m_bkg, s_bkg, w_bkg = mass_values[bkg], scores[bkg], (weights[bkg] if weights is not None else None)
    lo, hi = np.nanpercentile(m_bkg, [1, 99])
    if x_min is not None:
        lo = x_min
    bins = np.linspace(lo, hi, 40)

    plt.figure()
    for cut in cfg.SCORE_CUTS:
        sel = s_bkg >= cut
        if sel.sum() < 5:
            continue
        w_sel = w_bkg[sel] if w_bkg is not None else None
        plt.hist(m_bkg[sel], bins=bins, weights=w_sel, density=True, histtype="step", lw=1.8,
                  label=f"score >= {cut:.1f} (N={int(sel.sum())})")
    plt.xlabel(mass_col_name); plt.ylabel("Density (shape-normalized)")
    plt.title("Background mass sculpting vs. score cut")
    plt.legend(fontsize=8); plt.tight_layout()
    _savefig(out_dir, "mass_sculpting_shapes")


def run_mass_sculpting(
    df_te: pd.DataFrame, test_probs: np.ndarray, y_te: np.ndarray, w_te: np.ndarray, cfg: Config = CFG,
) -> Dict[str, object]:
    """Run the full mass-sculpting physics-validation suite on the TEST split.

    Produces:
      - background mass-shape overlay for a series of score cuts
      - weighted Kolmogorov-Smirnov test (no-cut vs each score-cut shape)
      - signal/background efficiency vs. score-cut table
      - efficiency-vs-score and S/B-style ratio plot

    If no known mass-proxy column is available in the dataframe, the checks
    are skipped gracefully (with a clear message) rather than failing.
    """
    mass_col = _find_mass_sculpt_column(df_te, cfg)
    if mass_col is None:
        print("[WARN] run_mass_sculpting: no mass-proxy column found in "
              f"{cfg.MASS_SCULPT_CANDIDATES}; skipping mass sculpting validation.")
        return {"status": "skipped", "reason": "no mass column available"}

    out_dir = os.path.join(cfg.PLOT_DIR, "MassSculpting")
    mass_values = df_te[mass_col].to_numpy(dtype=float)
    plot_mass_after_score(mass_values, test_probs, w_te, y_te, mass_col, cfg, x_min=95.0)

    sig_mask, bkg_mask = (y_te == 1), (y_te == 0)
    m_bkg_all = mass_values[bkg_mask]
    ks_results, eff_table = {}, []

    for cut in cfg.SCORE_CUTS:
        sel_sig = sig_mask & (test_probs >= cut)
        sel_bkg = bkg_mask & (test_probs >= cut)
        sig_eff = float(w_te[sel_sig].sum() / max(w_te[sig_mask].sum(), 1e-12))
        bkg_eff = float(w_te[sel_bkg].sum() / max(w_te[bkg_mask].sum(), 1e-12))
        eff_table.append({"score_cut": cut, "signal_efficiency": sig_eff, "background_efficiency": bkg_eff})

        m_cut = mass_values[sel_bkg]
        w_cut = w_te[sel_bkg]
        w_bkg_all = w_te[bkg_mask]
        if len(m_cut) > 5 and len(m_bkg_all) > 5:
            stat, pval, n_eff_all, n_eff_cut = weighted_ks_2samp(m_bkg_all, w_bkg_all, m_cut, w_cut)
            ks_results[f"cut_{cut:.1f}"] = {
                "ks_stat": stat, "p_value": pval,
                "n_eff_no_cut": n_eff_all, "n_eff_this_cut": n_eff_cut,
            }

    # efficiency vs score cut
    plt.figure()
    cuts = [row["score_cut"] for row in eff_table]
    plt.plot(cuts, [row["signal_efficiency"] for row in eff_table], marker="o", color=CMS_BLUE, label="Signal efficiency")
    plt.plot(cuts, [row["background_efficiency"] for row in eff_table], marker="o", color=CMS_RED, label="Background efficiency")
    plt.xlabel("Score cut"); plt.ylabel("Efficiency")
    plt.title("Efficiency vs. score cut (Test)"); plt.legend(); plt.tight_layout()
    _savefig(out_dir, "efficiency_vs_score")

    # ratio plot (signal eff / background eff, i.e. rejection power)
    plt.figure()
    ratio = [row["signal_efficiency"] / max(row["background_efficiency"], 1e-12) for row in eff_table]
    plt.plot(cuts, ratio, marker="o", color=CMS_GREEN)
    plt.yscale("log"); plt.xlabel("Score cut"); plt.ylabel("Signal eff / Background eff")
    plt.title("Rejection power vs. score cut (Test)"); plt.tight_layout()
    _savefig(out_dir, "efficiency_ratio_vs_score")

    print("[Physics validation] Weighted KS tests (background mass shape, no-cut vs cut):")
    for k, v in ks_results.items():
        print(f"  {k}: KS={v['ks_stat']:.4f}  p={v['p_value']:.4g}  "
              f"(n_eff no-cut={v['n_eff_no_cut']:.0f}, n_eff this-cut={v['n_eff_this_cut']:.0f})")

    # per-(mass,y) split validation: overall efficiency table by group at score>=0.5
    per_group = []
    if {"mass", "y_value"}.issubset(df_te.columns):
        key = group_key(df_te)
        for g in np.unique(key):
            idx = (key == g).values
            if np.unique(y_te[idx]).size < 2:
                continue
            sig_idx = idx & sig_mask
            bkg_idx = idx & bkg_mask
            sel_sig = sig_idx & (test_probs >= 0.5)
            sel_bkg = bkg_idx & (test_probs >= 0.5)
            per_group.append({
                "group": g,
                "signal_efficiency_at_0.5": float(w_te[sel_sig].sum() / max(w_te[sig_idx].sum(), 1e-12)) if sig_idx.any() else None,
                "background_efficiency_at_0.5": float(w_te[sel_bkg].sum() / max(w_te[bkg_idx].sum(), 1e-12)) if bkg_idx.any() else None,
            })

    return {
        "status": "ok",
        "mass_column_used": mass_col,
        "efficiency_table": eff_table,
        "ks_tests": ks_results,
        "per_group_efficiency_at_0.5": per_group,
    }


# =============================================================================
# 15. LOGGING / OUTPUT PERSISTENCE
# =============================================================================
def save_outputs(
    cfg: Config, history: Dict[str, List[float]], metrics: Dict[str, object], feature_list: Sequence[str],
) -> None:
    """Persist config, training history, and evaluation metrics for reproducibility."""
    os.makedirs(cfg.LOG_DIR, exist_ok=True)

    config_snapshot = {
        "seed": cfg.SEED,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "device": str(DEVICE),
        "feature_list": list(feature_list),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.__dict__.items()},
    }
    with open(os.path.join(cfg.LOG_DIR, "config.json"), "w") as f:
        json.dump(config_snapshot, f, indent=2, default=str)
    with open(os.path.join(cfg.LOG_DIR, "history.json"), "w") as f:
        json.dump(history, f, indent=2)
    with open(os.path.join(cfg.LOG_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(f"[INFO] Saved config/history/metrics to {cfg.LOG_DIR}/")


# =============================================================================
# 16. MAIN
# =============================================================================
def main() -> None:
    """End-to-end pDNN training + evaluation + physics-validation pipeline."""
    cfg = CFG
    apply_cms_plot_style()
    for d in (cfg.OUTPUT_DIR, cfg.MODEL_DIR, cfg.PLOT_DIR, cfg.LOG_DIR):
        os.makedirs(d, exist_ok=True)
    print(f"[INFO] Using device: {DEVICE}")

    # ---- Data loading & preparation ----
    signal_df = load_signal(cfg)
    background_df = load_background(cfg)
    background_df = assign_background_parameters(signal_df, background_df, seed=cfg.SEED)
    df_all = prepare_dataframe(signal_df, background_df)
    feature_list = resolve_feature_list(df_all, cfg)

    if cfg.ENABLE_CORR_PRUNING:
        feature_list, dropped_corr_pairs = prune_correlated_features(
            df_all, feature_list, df_all["label"].values, cfg
        )
    else:
        dropped_corr_pairs = []

    df_tr, df_va, df_te = split_dataset(df_all, cfg)

    # ---- Scaling ----
    x_tr, x_va, x_te, y_tr, y_va, y_te, w_tr, w_va, w_te, scaler = scale_features(
        df_tr, df_va, df_te, feature_list, cfg
    )
    leakage_audit(x_va, y_va, feature_list)

    # ---- Model & dataloaders ----
    train_loader, x_va_t, x_te_t = build_dataloaders(x_tr, y_tr, w_tr, x_va, x_te, DEVICE, cfg)
    model = ParameterizedDNN(x_tr.shape[1], cfg.HIDDEN_LAYERS, cfg.DROPOUT, cfg.USE_BATCHNORM)
    model.apply(xavier_init_)
    model = model.to(DEVICE)

    # ---- Training ----
    history = train_model(model, train_loader, x_va_t, y_va, DEVICE, cfg)
    plot_training_history(history, cfg)
    plot_validation_auc(history, cfg)

    # ---- Test-set evaluation ----
    test_probs = predict(model, x_te, DEVICE)
    train_probs = predict(model, x_tr, DEVICE)
    test_auc = plot_roc_curve(test_probs, y_te, w_te, df_te, cfg)
    plot_score_distribution(train_probs, y_tr, w_tr, test_probs, y_te, w_te, cfg)
    plot_correlation_heatmap(df_te, feature_list, cfg)
    diag_metrics = run_extended_diagnostics(model, y_te, test_probs, cfg)

    i_mass, i_y = feature_list.index("mass"), feature_list.index("y_value")
    my_auc_test = roc_auc_score(y_te, 0.5 * x_te[:, i_mass] + 0.5 * x_te[:, i_y])
    print(f"AUC using only (mass,y) on TEST: {my_auc_test:.4f}")

    # ---- Feature importance ----
    name_to_idx = {f: feature_list.index(f) for f in feature_list}
    feat_names_imp = [f for f in feature_list if cfg.INCLUDE_MASS_Y_IN_IMPORTANCE or f not in ("mass", "y_value")]
    group_codes = pd.factorize(group_key(df_te))[0]

    base_auc, imp_mean, imp_std = permutation_importance(
        model, x_te, y_te, w_te, feat_names_imp, name_to_idx, DEVICE,
        group_codes=group_codes, n_repeats=cfg.N_PERMUTATION_REPEATS, seed=cfg.SEED,
    )
    print(f"[Permutation] Baseline TEST AUC = {base_auc:.4f}")
    plot_feature_importance(imp_mean, imp_std, "Permutation importance (AUC drop) -- TEST",
                             "feature_importance_permutation_test", cfg, cms_color=CMS_BLUE)

    sal = gradient_saliency(model, x_te, feat_names_imp, name_to_idx, DEVICE, scaler=scaler)
    sal_max = max(sal.values()) if sal else 1.0
    sal_norm = {k: (v / sal_max if sal_max > 0 else 0.0) for k, v in sal.items()}
    plot_feature_importance(sal_norm, {k: 0.0 for k in sal_norm}, "Input-gradient saliency (normalized) -- TEST",
                             "feature_importance_saliency_test", cfg, cms_color=CMS_ORANGE)

    importance_table = pd.DataFrame({
        "feature": feat_names_imp,
        "perm_mean_auc_drop": [imp_mean.get(f, np.nan) for f in feat_names_imp],
        "perm_std_auc_drop": [imp_std.get(f, np.nan) for f in feat_names_imp],
        "grad_saliency_norm": [sal_norm.get(f, np.nan) for f in feat_names_imp],
    }).sort_values(["perm_mean_auc_drop", "grad_saliency_norm"], ascending=[False, False], na_position="last")
    importance_table.to_csv(os.path.join(cfg.PLOT_DIR, "FeatureImportance", "feature_importance_test.csv"), index=False)

    # ---- Physics validation (mass sculpting) ----
    sculpting_results = run_mass_sculpting(df_te, test_probs, y_te, w_te, cfg)

    # ---- Persist everything ----
    metrics = {
        "test_auc_weighted": float(test_auc),
        "mass_y_only_auc_val": float(roc_auc_score(y_va, 0.5 * x_va[:, i_mass] + 0.5 * x_va[:, i_y])),
        "mass_y_only_auc_test": float(my_auc_test),
        "permutation_baseline_auc": float(base_auc),
        "permutation_importance_mean": imp_mean,
        "permutation_importance_std": imp_std,
        "gradient_saliency_normalized": sal_norm,
        "diagnostics": diag_metrics,
        "mass_sculpting": sculpting_results,
        "correlation_pruning": {
            "enabled": cfg.ENABLE_CORR_PRUNING,
            "threshold": cfg.CORR_PRUNE_THRESHOLD,
            "dropped_pairs": dropped_corr_pairs,
            "final_feature_list": feature_list,
        },
    }
    save_outputs(cfg, history, metrics, feature_list)

    print("\n[DONE] pDNN_v2 pipeline complete.")
    print(f"       Best model:  {cfg.MODEL_PATH}")
    print(f"       Scaler:      {cfg.SCALER_PATH}")
    print(f"       Plots:       {cfg.PLOT_DIR}")
    print(f"       Logs:        {cfg.LOG_DIR}")


if __name__ == "__main__":
    main()