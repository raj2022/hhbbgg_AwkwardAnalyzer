# ================================================================
# Multiclass PDNN (Signal vs NRB vs ttH vs (VBFH+VH+TTGG))
# Group-safe splits by (mass,y), OOM-safe batched eval, small-normal init,
# CMS-like plotting, scaler persistence, diagnostics, and importance.
# ================================================================
import os, warnings, json, pickle, hashlib
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam, lr_scheduler

from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, roc_curve, auc, confusion_matrix, ConfusionMatrixDisplay,
    accuracy_score
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier

warnings.filterwarnings("ignore", category=UserWarning)

# -----------------------------
# CMS-like plotting style & palette
# -----------------------------
from matplotlib.colors import LinearSegmentedColormap
from cycler import cycler

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
CMS_BLUE     = "#2368B5"
CMS_RED      = "#C0392B"
CMS_ORANGE   = "#E67E22"
CMS_GREEN    = "#2E8B57"
CMS_PURPLE   = "#6C5CE7"
CMS_GRAY     = "#4D4D4D"
plt.rcParams["axes.prop_cycle"] = cycler(color=[
    CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE, "#1ABC9C", "#8E44AD",
    "#16A085", "#D35400", "#2C3E50"
])
cms_div = LinearSegmentedColormap.from_list("cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256)

# -----------------------------
# Config
# -----------------------------
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# data handling
BACKGROUND_FRAC     = 1.0     # keep all backgrounds
BALANCE_PER_GROUP   = True    # multiclass balancing per (mass,y)
MIN_PER_CLASS       = 5       # min per class inside a (mass,y) to keep the group

# model/training
USE_BATCHNORM       = False
BATCH_SIZE_TRAIN    = 128
LR                  = 1e-3
WEIGHT_CLIP         = 10.0
PATIENCE            = 50
MAX_EPOCHS          = 500
WEIGHT_DECAY        = 1e-4
SAVE_MODEL_PATH     = "best_pdnn_multiclass.pt"

# eval (OOM safety)
EVAL_BATCH          = 32768
USE_AMP_EVAL        = True
CPU_FALLBACK_ON_OOM = True

# debug toggles
DEBUG_ONE_BATCH             = False
DEBUG_SHUFFLE_TRAIN_LABELS  = False

# ablation
DROP_FEATURES = []  # e.g. ['Res_DeltaR_jg_min']

# mass/y grid
mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
y_values    = [90, 95, 100, 125, 150, 200, 300, 400, 500, 600, 800]

# -----------------------------
# Class map (IDs)
# -----------------------------
CLASS_NAMES = ["Signal", "NRB", "ttH", "VBFH+VH+TTGG"]
CLS_SIGNAL = 0
CLS_NRB    = 1
CLS_TTH    = 2
CLS_HHLIKE = 3  # (VBFH + VH + TTGG)
NUM_CLASSES = len(CLASS_NAMES)

# -----------------------------
# Inputs — SIGNAL parquet pattern (unchanged)
# -----------------------------
SIG_TPL = "../../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"

# -----------------------------
# Inputs — backgrounds by category (EDIT ME)
# -----------------------------
# Non-resonant backgrounds (NRB)
BKG_NRB_FILES = [
    "../../../output_root/v3_production/samples/postEE/GGJets.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt20To40.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
]

# ttH (Hadronic/Leptonic merged, add your exact file paths)
BKG_TTH_FILES = [
    "../../../output_root/v3_production/samples/postEE/ttHToGG.parquet",
]

# VBFH + VH + TTGG (Higgs-like + di-photon top pair; add paths)
BKG_HHLIKE_FILES = [
    "../../../output_root/v3_production/samples/postEE/VBFHToGG.parquet",
    "../../../output_root/v3_production/samples/postEE/VHToGG.parquet",
    "../../../output_root/v3_production/samples/postEE/TTGG.parquet",
]

# ============================
# Features (Res_* version)
# ============================
WEIGHT_COL = "weight_central"

FEATURES_CORE = [
    # photons & diphoton
    "lead_eta","lead_phi","sublead_eta","sublead_phi",
    "eta","phi",

    # jets, dijet, HH (Res)
    "Res_lead_bjet_eta","Res_lead_bjet_phi",
    "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
    "Res_dijet_eta","Res_dijet_phi",
    "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",

    # angular distances (Res)
    "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
    "Res_DeltaR_j2g1","Res_DeltaR_j2g2",
    "Res_DeltaR_jg_min",

    # helicity / Collins–Soper
    "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",

    # photon ID
    "lead_mvaID_run3","sublead_mvaID_run3",

    # counts & MET
    "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",

    # Δφ(jet,MET)
    "Res_DeltaPhi_j1MET","Res_DeltaPhi_j2MET",

    # χ² terms
    "Res_chi_t0","Res_chi_t1",

    # raw kinematics and masses
    "Res_dijet_pt","Res_dijet_mass",
    "Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",

    # scaled pT’s
    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
]

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    mHH = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
    mHH = mHH.replace(0, np.nan)

    df["ptjj_over_mHH"] = (df["Res_dijet_pt"] / mHH) if "Res_dijet_pt" in df.columns else 0.0
    df["ptHH_over_mHH"] = (df["Res_HHbbggCandidate_pt"] / mHH) if "Res_HHbbggCandidate_pt" in df.columns else 0.0

    if all(c in df.columns for c in ["lead_phi","sublead_phi","lead_eta","sublead_eta"]):
        dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
        dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
        deta = df["lead_eta"] - df["sublead_eta"]
        df["DeltaR_gg"] = np.sqrt(deta**2 + dphi**2)
    else:
        df["DeltaR_gg"] = 0.0

    for c in ["Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    for c in ["ptjj_over_mHH","ptHH_over_mHH","DeltaR_gg"]:
        df[c] = df[c].fillna(0)

    return df

def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
    pairs = [("lead_mvaID_run3","lead_mvaID_nano"),
             ("sublead_mvaID_run3","sublead_mvaID_nano")]
    for want, alt in pairs:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df

# include engineered features
FEATURES_CORE = FEATURES_CORE + ["ptjj_over_mHH","ptHH_over_mHH"]
FEATURES_FINAL = FEATURES_CORE + ["mass", "y_value"]

# -----------------------------
# Helpers
# -----------------------------
def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.select_dtypes(include=['float64']).columns:
        df[c] = df[c].astype('float32')
    return df

def ensure_weight(df: pd.DataFrame, weight_col=WEIGHT_COL) -> pd.DataFrame:
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df

def df_to_arrays(df: pd.DataFrame, feature_list):
    Xdf = df[feature_list].copy()
    Xdf = Xdf.fillna(Xdf.mean(numeric_only=True))
    Xdf = downcast_float_cols(Xdf)
    X = Xdf.values.astype(np.float32)
    y = df['label'].astype(np.int64).values
    w = df[WEIGHT_COL].astype('float32').values
    return X, y, w

def balance_per_group_multiclass(df, seed=SEED, min_per_class=MIN_PER_CLASS):
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    parts = []; dropped = 0
    for _, sub in df.groupby(key, sort=False):
        vc = sub['label'].value_counts()
        if (vc.index.nunique() < NUM_CLASSES) or (vc.min() < min_per_class):
            dropped += 1; continue
        n_keep = vc.min()
        chunks = []
        for c in range(NUM_CLASSES):
            sel = sub[sub['label']==c]
            keep = sel.sample(n=n_keep, random_state=seed) if len(sel)>n_keep else sel
            chunks.append(keep)
        parts.append(pd.concat(chunks, ignore_index=True))
    if not parts:
        raise RuntimeError("Balancing removed all groups; relax MIN_PER_CLASS or disable balancing.")
    out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    if dropped: print(f"[INFO] balance_per_group_multiclass: dropped {dropped} groups that lacked all classes or were tiny.")
    return out

def split_summary(df, name):
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    print(f"{name}: N={len(df):,}  class_counts={df['label'].value_counts().sort_index().to_dict()}  groups={key.nunique()}")

@torch.no_grad()
def predict_batched_softmax(model, X_tensor, device, batch=32768, use_amp=True):
    model.eval()
    N = X_tensor.shape[0]
    C = model.num_classes
    out = np.empty((N, C), dtype=np.float32)
    amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type=="cuda"))
    with amp_ctx:
        for i in range(0, N, batch):
            xb = X_tensor[i:i+batch].to(device, non_blocking=True)
            logits = model(xb)  # (B, C)
            probs = torch.softmax(logits, dim=1).detach().cpu().numpy()
            out[i:i+batch] = probs
    return out

def safe_eval_probs(model, X_tensor, device):
    try:
        return predict_batched_softmax(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL)
    except RuntimeError as e:
        if CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
            print("[WARN] CUDA OOM during eval → falling back to CPU (batched).")
            cpu_model = model.to(torch.device("cpu"))
            X_cpu = X_tensor.to(torch.device("cpu"))
            return predict_batched_softmax(cpu_model, X_cpu, torch.device("cpu"), batch=max(8192, EVAL_BATCH), use_amp=False)
        raise

# -----------------------------
# 1) Load SIGNAL
# -----------------------------
signal_rows = []
for mass in mass_points:
    for y in y_values:
        fp = SIG_TPL.format(m=mass, y=y)
        if not os.path.exists(fp): 
            continue
        try:
            try:
                cols = pd.read_parquet(fp, columns=None).columns
                need_raw = [
                    "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
                    "Res_lead_bjet_eta","Res_lead_bjet_phi",
                    "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
                    "Res_dijet_eta","Res_dijet_phi",
                    "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
                    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
                    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
                    "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
                    "Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
                    "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
                    "lead_mvaID_run3","sublead_mvaID_run3",
                    "lead_mvaID_nano","sublead_mvaID_nano",
                    "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
                    "Res_chi_t0","Res_chi_t1",
                    "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
                ]
                subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
                df = pd.read_parquet(fp, columns=subset)
            except Exception:
                df = pd.read_parquet(fp)

            df = ensure_photon_mva_columns(df)
            df = add_engineered_features(df)

            keep = [c for c in FEATURES_CORE if c in df.columns]
            extras = [WEIGHT_COL] if WEIGHT_COL in df.columns else []
            df = df[keep + extras].copy()
            df['mass']=mass; df['y_value']=y; df['label']=CLS_SIGNAL
            df = ensure_weight(df); df = downcast_float_cols(df)
            signal_rows.append(df)
        except Exception as e:
            print(f"[WARN] read fail {fp}: {e}")
signal_df = pd.concat(signal_rows, ignore_index=True) if signal_rows else pd.DataFrame()

# -----------------------------
# 2) Load BACKGROUNDS by category
# -----------------------------
def load_bkg_list(file_list, class_id, name="BKG"):
    parts = []
    for fp in file_list:
        if not os.path.exists(fp):
            print(f"[WARN] Missing {fp}")
            continue
        try:
            try:
                cols = pd.read_parquet(fp, columns=None).columns
                need_raw = [
                    "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
                    "Res_lead_bjet_eta","Res_lead_bjet_phi",
                    "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
                    "Res_dijet_eta","Res_dijet_phi",
                    "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
                    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
                    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
                    "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
                    "Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
                    "Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS",
                    "lead_mvaID_run3","sublead_mvaID_run3",
                    "lead_mvaID_nano","sublead_mvaID_nano",
                    "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
                    "Res_chi_t0","Res_chi_t1",
                    "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
                ]
                subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
                dfb = pd.read_parquet(fp, columns=subset)
            except Exception:
                dfb = pd.read_parquet(fp)

            dfb = ensure_photon_mva_columns(dfb)
            dfb = add_engineered_features(dfb)

            keep = [c for c in FEATURES_CORE if c in dfb.columns]
            extras = [WEIGHT_COL] if WEIGHT_COL in dfb.columns else []
            dfb = dfb[keep + extras].copy()
            dfb = ensure_weight(dfb)
            dfb['label'] = class_id
            dfb = downcast_float_cols(dfb)
            parts.append(dfb)
        except Exception as e:
            print(f"[WARN] read fail {fp}: {e}")
    if not parts:
        print(f"[WARN] No files loaded for {name}.")
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

df_nrb    = load_bkg_list(BKG_NRB_FILES,    CLS_NRB,    name="NRB")
df_tth    = load_bkg_list(BKG_TTH_FILES,    CLS_TTH,    name="ttH")
df_hhlike = load_bkg_list(BKG_HHLIKE_FILES, CLS_HHLIKE, name="(VBFH+VH+TTGG)")

# Optionally downsample backgrounds globally
for name, dfb in [("NRB", df_nrb), ("ttH", df_tth), ("VBFH+VH+TTGG", df_hhlike)]:
    if BACKGROUND_FRAC < 1.0 and not dfb.empty:
        n0 = len(dfb)
        dfb = dfb.sample(frac=BACKGROUND_FRAC, random_state=SEED).reset_index(drop=True)
        print(f"[INFO] Downsampled {name}: {n0} -> {len(dfb)}")
    if name == "NRB": df_nrb = dfb
    elif name == "ttH": df_tth = dfb
    else: df_hhlike = dfb

if signal_df.empty or (df_nrb.empty and df_tth.empty and df_hhlike.empty):
    raise RuntimeError(f"Empty data: signal={signal_df.empty}, all backgrounds empty={df_nrb.empty and df_tth.empty and df_hhlike.empty}")

# -----------------------------
# 3) Assign (mass,y) to backgrounds from signal mix
# -----------------------------
sig_my = signal_df[['mass','y_value']]
mix = sig_my.value_counts(normalize=True).reset_index()
mix.columns = ['mass','y_value','weight']

def assign_my(df_bkg, label_name):
    if df_bkg.empty: return df_bkg
    sampled = mix.sample(n=len(df_bkg), replace=True, weights='weight', random_state=SEED).reset_index(drop=True)
    df_bkg['mass']    = sampled['mass'].values
    df_bkg['y_value'] = sampled['y_value'].values
    # ensure coverage
    need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
    have = set(map(tuple, df_bkg[['mass','y_value']].drop_duplicates().values.tolist()))
    missing_keys = list(need - have)
    if missing_keys:
        K = min(len(missing_keys), len(df_bkg))
        for i,(m,y) in enumerate(missing_keys[:K]):
            df_bkg.loc[i,'mass']=m
            df_bkg.loc[i,'y_value']=y
    print(f"[INFO] Assigned (mass,y) to {label_name}: groups={df_bkg[['mass','y_value']].drop_duplicates().shape[0]}")
    return df_bkg

df_nrb    = assign_my(df_nrb,    "NRB")
df_tth    = assign_my(df_tth,    "ttH")
df_hhlike = assign_my(df_hhlike, "(VBFH+VH+TTGG)")

# -----------------------------
# 4) Combine, drop pure groups
# -----------------------------
df_all = pd.concat([signal_df, df_nrb, df_tth, df_hhlike], ignore_index=True)
key_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
grp_classes = df_all.groupby(key_all)['label'].nunique()
good_keys = set(grp_classes[grp_classes>=2].index)  # allow groups with >=2 classes to keep more data; strict balancing later
mask_good = key_all.isin(good_keys)
dropped = int((~mask_good).sum())
if dropped: print(f"[INFO] Dropping {dropped} rows from fully pure (mass,y) groups.")
df_all = df_all.loc[mask_good].reset_index(drop=True)

# -----------------------------
# 5) Feature list (+ ablation)
# -----------------------------
FEATURES_FINAL = FEATURES_CORE + ['mass','y_value']
if DROP_FEATURES:
    removed = [f for f in DROP_FEATURES if f in FEATURES_FINAL]
    if removed:
        print(f"[Ablation] Dropping features: {removed}")
        FEATURES_FINAL = [f for f in FEATURES_FINAL if f not in removed]
available_features = [c for c in FEATURES_FINAL if c in df_all.columns]
missing = sorted(set(FEATURES_FINAL) - set(available_features))
if missing: print(f"[Note] Missing features ignored: {missing}")

# -----------------------------
# 6) Group splits by (mass,y)
# -----------------------------
groups_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
gss_outer = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
idx_trval, idx_te = next(gss_outer.split(df_all, df_all['label'], groups_all))
df_trval = df_all.iloc[idx_trval].reset_index(drop=True)
df_te    = df_all.iloc[idx_te].reset_index(drop=True)

gss_inner = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
groups_trval = df_trval['mass'].astype(int).astype(str) + "_" + df_trval['y_value'].astype(int).astype(str)
idx_tr, idx_va = next(gss_inner.split(df_trval, df_trval['label'], groups_trval))
df_tr = df_trval.iloc[idx_tr].reset_index(drop=True)
df_va = df_trval.iloc[idx_va].reset_index(drop=True)

if BALANCE_PER_GROUP:
    df_tr = balance_per_group_multiclass(df_tr)
    # For VAL/TEST, keep more realistic class priors but drop tiny/pure groups softly:
    def prune_groups(df):
        key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
        parts=[]
        for _, sub in df.groupby(key, sort=False):
            vc = sub['label'].value_counts()
            if vc.index.nunique() < 2: continue  # drop fully pure
            parts.append(sub)
        return pd.concat(parts, ignore_index=True) if parts else df
    df_va = prune_groups(df_va)
    df_te = prune_groups(df_te)

def split_counts(df, name):
    print(f"{name}: N={len(df):,}  " + "  ".join([f"{i}:{(df['label']==i).sum():,}" for i in range(NUM_CLASSES)]))
split_counts(df_tr, "TRAIN"); split_counts(df_va, "VAL"); split_counts(df_te, "TEST")

# -----------------------------
# 7) Arrays + scaling (fit on TRAIN only)
# -----------------------------
X_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, available_features)
X_va_raw, y_va, w_va = df_to_arrays(df_va, available_features)
X_te_raw, y_te, w_te = df_to_arrays(df_te, available_features)

if DEBUG_SHUFFLE_TRAIN_LABELS:
    rng = np.random.default_rng(SEED+7)
    y_tr = rng.permutation(y_tr.copy())
    print("[DEBUG] Shuffled TRAIN labels. Val AUC should collapse.")

scaler = StandardScaler()
X_tr = scaler.fit_transform(X_tr_raw)
X_va = scaler.transform(X_va_raw)
X_te = scaler.transform(X_te_raw)

with open("scaler.pkl", "wb") as f: pickle.dump(scaler, f)
with open("features_used.json", "w") as f: json.dump({"features": available_features}, f, indent=2)
print("[INFO] Saved scaler to scaler.pkl and feature list to features_used.json")

# -----------------------------
# 8) Sanity checks
# -----------------------------
X_va_t_cpu = torch.tensor(X_va, dtype=torch.float32)
mae = float(np.mean(np.abs(X_va_t_cpu.numpy() - X_va)))
mx  = float(np.max(np.abs(X_va_t_cpu.numpy() - X_va)))
print(f"[Sanity] X_va tensor vs numpy: mean|diff|={mae:.3e}, max|diff|={mx:.3e}")

# -----------------------------
# 9) Model (multiclass) + small-normal init
# -----------------------------
def maybe_bn(n): 
    return nn.BatchNorm1d(n) if USE_BATCHNORM else nn.Identity()

class ParameterizedDNN_Multi(nn.Module):
    def __init__(self, d, num_classes):
        super().__init__()
        self.num_classes = num_classes
        self.net = nn.Sequential(
            nn.Linear(d, 128), maybe_bn(128), nn.ReLU(), nn.Dropout(0.30),
            nn.Linear(128, 64), maybe_bn(64), nn.ReLU(), nn.Dropout(0.30),
            nn.Linear(64, 32), maybe_bn(32), nn.ReLU(), nn.Dropout(0.20),
            nn.Linear(32, num_classes)  # logits
        )
    def forward(self, x): 
        return self.net(x)

def small_normal_zero_bias_(m):
    if isinstance(m, nn.Linear):
        nn.init.normal_(m.weight, mean=0.0, std=1e-2)
        if m.bias is not None:
            nn.init.constant_(m.bias, 0.0)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {device}")

model = ParameterizedDNN_Multi(X_tr.shape[1], NUM_CLASSES).cpu()
model.apply(small_normal_zero_bias_)

# Untrained macro OVR AUC (should be ~0.5 when averaged OVR; with 4 classes macro AUC ~0.5)
with torch.no_grad():
    p0 = torch.softmax(model(X_va_t_cpu), dim=1).numpy()
macro_auc0 = roc_auc_score(y_va, p0, multi_class="ovr", average="macro")
print(f"[Diag] Untrained macro AUC (VAL): {macro_auc0:.4f}")

# Baselines
lr = LogisticRegression(max_iter=300, multi_class="multinomial")
lr.fit(X_tr, y_tr)
auc_lr = roc_auc_score(y_va, lr.predict_proba(X_va), multi_class="ovr", average="macro")
print(f"[Diag] Logistic regression (multinomial) macro AUC: {auc_lr:.4f}")

gb = GradientBoostingClassifier(random_state=SEED)
gb.fit(X_tr, y_tr)
auc_gb = roc_auc_score(y_va, gb.predict_proba(X_va), multi_class="ovr", average="macro")
print(f"[Diag] GradientBoosting (OVR) macro AUC: {auc_gb:.4f}")

# Move model to device
model = model.to(device)

# -----------------------------
# 10) Tensors & DataLoader
# -----------------------------
class ArrayDataset(Dataset):
    def __init__(self, X, y, w): self.X=X; self.y=y; self.w=w
    def __len__(self): return len(self.X)
    def __getitem__(self, i):
        return (torch.tensor(self.X[i], dtype=torch.float32),
                torch.tensor(self.y[i], dtype=torch.long),
                torch.tensor(self.w[i], dtype=torch.float32))

train_loader = DataLoader(ArrayDataset(X_tr, y_tr, w_tr),
                          batch_size=BATCH_SIZE_TRAIN, shuffle=True,
                          pin_memory=(device.type=="cuda"),
                          num_workers=2 if os.name!="nt" else 0)

X_va_t = torch.tensor(X_va, dtype=torch.float32).to(device)
X_te_t = torch.tensor(X_te, dtype=torch.float32).to(device)

# -----------------------------
# 11) Loss/opt + AMP scaler
# -----------------------------
criterion_ce = nn.CrossEntropyLoss(reduction='none')
optimizer = Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
use_amp = (device.type == "cuda")
scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if use_amp else torch.amp.GradScaler(enabled=False)

# -----------------------------
# 12) Train (early stop on macro AUC)
# -----------------------------
history = {"train_loss": [], "val_macro_auc": [], "val_acc": []}
best_auc = -np.inf; epochs_since_best = 0

for epoch in range(MAX_EPOCHS):
    model.train()
    tot_loss, nseen = 0.0, 0
    for xb, yb, wb in train_loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        wb = wb.to(device, non_blocking=True)
        wb = torch.clamp(wb / (wb.mean() + 1e-8), max=WEIGHT_CLIP)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(xb)            # (B, C)
            per_loss = criterion_ce(logits, yb)  # (B,)
            loss = (per_loss * wb).mean()
        scaler_amp.scale(loss).backward()
        scaler_amp.step(optimizer)
        scaler_amp.update()

        bs = xb.size(0); tot_loss += float(loss.item()) * bs; nseen += bs
        if DEBUG_ONE_BATCH: break

    train_loss = tot_loss / max(nseen,1)

    # Validation (macro AUC)
    val_probs = safe_eval_probs(model, X_va_t, device)
    val_macro_auc = roc_auc_score(y_va, val_probs, multi_class="ovr", average="macro")
    val_acc = accuracy_score(y_va, np.argmax(val_probs, axis=1))

    history["train_loss"].append(train_loss)
    history["val_macro_auc"].append(val_macro_auc)
    history["val_acc"].append(val_acc)

    print(f"Epoch {epoch+1:03d} | TrainLoss: {train_loss:.4f} | ValMacroAUC: {val_macro_auc:.4f} | ValAcc: {val_acc:.4f}")
    scheduler.step(val_macro_auc)

    if val_macro_auc > best_auc + 1e-4:
        best_auc = val_macro_auc; epochs_since_best = 0
        torch.save(model.state_dict(), SAVE_MODEL_PATH)
        print(f"[INFO] New best ValMacroAUC: {best_auc:.4f} — model saved")
    else:
        epochs_since_best += 1
        if epochs_since_best >= PATIENCE:
            print(f"[INFO] Early stopping at epoch {epoch+1}."); break

# -----------------------------
# 13) Test + diagnostics & plots
# -----------------------------
if os.path.exists(SAVE_MODEL_PATH):
    try:
        state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(SAVE_MODEL_PATH, map_location=device)
    model.load_state_dict(state)
else:
    print("[WARN] No saved model found; using current in-memory weights.")

test_probs = safe_eval_probs(model, X_te_t, device)   # (N,C)
y_pred = np.argmax(test_probs, axis=1)

# Macro/micro AUCs
test_macro_auc = roc_auc_score(y_te, test_probs, multi_class="ovr", average="macro")
test_micro_auc = roc_auc_score(y_te, test_probs, multi_class="ovr", average="micro")
print(f"\n[Test] Macro AUC: {test_macro_auc:.6f} | Micro AUC: {test_micro_auc:.6f}")

# Per-class OVR AUC
per_class_auc = {}
for c in range(NUM_CLASSES):
    y_true_bin = (y_te == c).astype(int)
    auc_c = roc_auc_score(y_true_bin, test_probs[:, c])
    per_class_auc[CLASS_NAMES[c]] = float(auc_c)
print("[Test] Per-class OVR AUC:", per_class_auc)

# Confusion matrix (weighted not directly supported; show unweighted counts)
cm = confusion_matrix(y_te, y_pred, labels=list(range(NUM_CLASSES)))
disp = ConfusionMatrixDisplay(cm, display_labels=CLASS_NAMES)
fig, ax = plt.subplots(figsize=(6, 5)); disp.plot(ax=ax, cmap="Blues", values_format="d", colorbar=False)
plt.title("Confusion Matrix — Test (unweighted)")
plt.tight_layout(); plt.show()

# Score histograms per class (weighted)
bins = np.linspace(0.0, 1.0, 51)
for c in range(NUM_CLASSES):
    plt.figure()
    for k in range(NUM_CLASSES):
        mask = (y_te == k)
        w_k = w_te[mask] if w_te is not None else None
        plt.hist(test_probs[mask, c], bins=bins, weights=w_k, histtype='step', linewidth=2.0,
                 label=f"True {CLASS_NAMES[k]}")
    plt.xlabel(f"Predicted P({CLASS_NAMES[c]})"); plt.ylabel("Weighted events")
    plt.yscale('log')
    plt.title(f"Score distribution for class {CLASS_NAMES[c]} (Test)")
    plt.legend(); plt.tight_layout(); plt.show()

# ROC (OVR) — per class
plt.figure()
for c in range(NUM_CLASSES):
    y_true_bin = (y_te == c).astype(int)
    fpr, tpr, _ = roc_curve(y_true_bin, test_probs[:, c], sample_weight=w_te)
    auc_c = auc(fpr, tpr)
    plt.plot(fpr, tpr, lw=2.0, label=f"{CLASS_NAMES[c]} (AUC={auc_c:.3f})")
plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)
plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
plt.title("ROC — One-vs-Rest (Test)")
plt.legend(loc="lower right"); plt.tight_layout(); plt.show()

# Per-(mass,y) ROC overlay for Signal vs Rest (mimics previous per-sample overlay)
group_key = (df_te['mass'].astype(int).astype(str) + "_" + df_te['y_value'].astype(int).astype(str)).values
scores_sig = test_probs[:, CLS_SIGNAL]
labels_sig = (y_te == CLS_SIGNAL).astype(int)

plt.figure()
uniq_groups = np.unique(group_key)
legend_handles = []
for g in uniq_groups:
    idx = (group_key == g)
    if np.unique(labels_sig[idx]).size < 2:
        continue
    fpr_g, tpr_g, _ = roc_curve(labels_sig[idx], scores_sig[idx], sample_weight=(w_te[idx] if w_te is not None else None))
    auc_g = auc(fpr_g, tpr_g)
    h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.6, label=f"{g} (AUC {auc_g:.3f})")
    legend_handles.append((auc_g, h))
legend_handles.sort(key=lambda t: t[0], reverse=True)
handles_to_show = [h for _,h in legend_handles[:10]]
labels_to_show  = [h.get_label() for h in handles_to_show]
leg1 = plt.legend(handles_to_show, labels_to_show, title="Top (mass,y) groups", loc="lower right",
                  frameon=True, fontsize=8)
plt.gca().add_artist(leg1)
plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)
plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
plt.title("ROC by (mass,y) — Signal vs Rest (Test)")
plt.tight_layout(); plt.show()

# Correlation heatmap (unstandardized)
Xte_df = pd.DataFrame(X_te_raw, columns=available_features)
corr = Xte_df[ [c for c in available_features if c not in ("mass","y_value")] ].corr(method="pearson")
fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
im = ax.imshow(corr.values, cmap=cms_div, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
ax.set_xticks(np.arange(corr.shape[1])); ax.set_yticks(np.arange(corr.shape[0]))
ax.set_xticklabels(corr.columns, rotation=90); ax.set_yticklabels(corr.index)
ax.set_title("Pearson correlation (test, unweighted)")
cbar = plt.colorbar(im, ax=ax); cbar.set_label("Correlation")
plt.tight_layout(); plt.show()

# Training curves
plt.figure(); plt.plot(history["train_loss"], marker='o', color=CMS_BLUE)
plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
plt.tight_layout(); plt.show()

plt.figure(); 
plt.plot(history["val_macro_auc"], marker='o', label="Val Macro AUC", color=CMS_RED)
plt.title("Validation Macro AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
plt.legend(); plt.tight_layout(); plt.show()

# ===============================================================
# Feature importance (multiclass): permutation AUC (macro-OVR) and saliency
# ===============================================================
OUTDIR = "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN"
os.makedirs(OUTDIR, exist_ok=True)

def _weighted_macro_auc_ovr(y_true, P, w=None):
    return roc_auc_score(y_true, P, multi_class="ovr", average="macro",
                         sample_weight=(w if w is not None else None))

def _groupwise_shuffle_inplace(X_block, group_codes, col, rng):
    for g in np.unique(group_codes):
        idx = (group_codes == g)
        vals = X_block[idx, col].copy()
        rng.shuffle(vals)
        X_block[idx, col] = vals

@torch.no_grad()
def permutation_importance_auc(
    model, X_full, y, w, feature_names_to_permute, device, *,
    feature_index_map, group_codes=None, n_repeats=5, seed=SEED
):
    X_t = torch.tensor(X_full, dtype=torch.float32, device=device)
    base_probs = safe_eval_probs(model, X_t, device)
    base_auc = _weighted_macro_auc_ovr(y, base_probs, w)

    rng = np.random.default_rng(seed)
    drops = defaultdict(list)
    for fname in feature_names_to_permute:
        j = feature_index_map[fname]
        for _ in range(n_repeats):
            X_perm = X_full.copy()
            if group_codes is None:
                rng.shuffle(X_perm[:, j])
            else:
                _groupwise_shuffle_inplace(X_perm, group_codes, j, rng)
            Xp_t = torch.tensor(X_perm, dtype=torch.float32, device=device)
            probs_p = safe_eval_probs(model, Xp_t, device)
            auc_p = _weighted_macro_auc_ovr(y, probs_p, w)
            drops[fname].append(base_auc - auc_p)

    imp_mean = {f: float(np.mean(v)) for f, v in drops.items()}
    imp_std  = {f: float(np.std(v, ddof=1)) for f, v in drops.items()}
    return base_auc, imp_mean, imp_std

def plot_importance_bar(imp_mean, imp_err, title, filename, top_k=25, cms_color=CMS_BLUE):
    items = sorted(imp_mean.items(), key=lambda t: t[1], reverse=True)[:top_k]
    labels = [k for k,_ in items][::-1]
    vals   = [imp_mean[k] for k in labels]
    errs   = [imp_err.get(k, 0.0) for k in labels]
    plt.figure(figsize=(8.0, 0.4*len(labels)+1.5), dpi=110)
    plt.barh(range(len(labels)), vals, xerr=errs, color=cms_color, alpha=0.85)
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Mean AUC drop (macro OVR)"); plt.title(title)
    plt.tight_layout()
    png = os.path.join(OUTDIR, f"{filename}.png")
    pdf = os.path.join(OUTDIR, f"{filename}.pdf")
    plt.savefig(png, dpi=600); plt.savefig(pdf)
    plt.show()
    print(f"[Saved] {png}\n[Saved] {pdf}")

# Choose split for importance (TEST)
X_imp, y_imp, w_imp = X_te, y_te, w_te
df_split = df_te
feat_names_imp = list(available_features)  # include mass,y; set to exclude if desired
name_to_idx = {f: available_features.index(f) for f in available_features}
group_codes = pd.factorize(df_split['mass'].astype(int).astype(str) + "_" + df_split['y_value'].astype(int).astype(str))[0]

base_auc, imp_mean, imp_std = permutation_importance_auc(
    model, X_imp, y_imp, w_imp,
    feature_names_to_permute=feat_names_imp,
    device=device,
    feature_index_map=name_to_idx,
    group_codes=group_codes, n_repeats=5
)
print(f"[Permutation] Baseline TEST macro AUC = {base_auc:.4f}")
plot_importance_bar(imp_mean, imp_std, "Permutation importance (macro OVR AUC drop) — TEST",
                    "feature_importance_permutation_test", top_k=25, cms_color=CMS_BLUE)

# Input-gradient saliency (mean |∂logit_c / ∂x| aggregated across classes by L2 over logits)
def gradient_saliency_multiclass(model, X_full, device, scaler=None, batch=4096):
    model.eval()
    N, D = X_full.shape
    grads_accum = np.zeros(D, dtype=np.float64)
    n_seen = 0
    if scaler is not None and hasattr(scaler, "scale_"):
        inv_scale_full = 1.0 / np.asarray(scaler.scale_, dtype=np.float64)
        assert inv_scale_full.shape[0] == D
    else:
        inv_scale_full = np.ones(D, dtype=np.float64)

    ptr = 0
    while ptr < N:
        xb = torch.tensor(X_full[ptr:ptr+batch], dtype=torch.float32, device=device, requires_grad=True)
        logits = model(xb)                  # (B, C)
        # Use the L2 norm of logits to gather gradients across classes
        s = (logits**2).sum() * 0.5
        s.backward()
        g = xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()  # (D,)
        grads_accum += g; n_seen += 1; ptr += batch
        model.zero_grad(set_to_none=True)

    grads_mean = grads_accum / max(n_seen, 1)
    grads_raw = grads_mean * inv_scale_full
    return {f: float(val) for f, val in zip(available_features, grads_raw)}

sal = gradient_saliency_multiclass(model, X_imp, device, scaler=scaler, batch=4096)
# Normalize for plotting
mmax = max(sal.values()) if len(sal) else 1.0
sal_norm = {k: (v / mmax if mmax > 0 else 0.0) for k, v in sal.items()}

plot_importance_bar(sal_norm, {k:0.0 for k in sal_norm},
                    "Input-gradient saliency (normalized) — TEST",
                    "feature_importance_grad_test", top_k=25, cms_color=CMS_ORANGE)

# Save importances
all_feats = list(sorted(set(feat_names_imp)))
perm_mean_vec = np.array([imp_mean.get(f, np.nan) for f in all_feats], dtype=float)
perm_std_vec  = np.array([imp_std.get(f,  np.nan) for f in all_feats], dtype=float)
grad_norm_vec = np.array([sal_norm.get(f,  np.nan) for f in all_feats], dtype=float)

imp_df = pd.DataFrame({
    "feature": all_feats,
    "perm_mean_auc_drop": perm_mean_vec,
    "perm_std_auc_drop":  perm_std_vec,
    "grad_saliency_norm": grad_norm_vec,
}).sort_values(["perm_mean_auc_drop", "grad_saliency_norm"], ascending=[False, False], na_position="last")

csv_path  = os.path.join(OUTDIR, "feature_importance_test.csv")
json_path = os.path.join(OUTDIR, "feature_importance_test.json")
imp_df.to_csv(csv_path, index=False)
with open(json_path, "w") as f:
    json.dump({
        "split": "TEST",
        "baseline_macro_auc": float(base_auc),
        "permutation_importance": imp_mean,
        "permutation_importance_std": imp_std,
        "gradient_saliency_normalized": sal_norm,
        "table_order": imp_df["feature"].tolist()
    }, f, indent=2)
print(f"[Saved] {csv_path}\n[Saved] {json_path}")
