# ++++++++++++++++++++++++++++
# Working pDNN with all plots (10/27/2025)
# Shivam Raj
# ---------------------



# ================================================================
# Parameterized DNN (PDNN) with group-safe splits, diagnostics,
# OOM-safe batched eval, small-normal init, and consistency gate.
# Now using the *Res_* variables everywhere (no nonRes_* left).
# ================================================================
import os, hashlib, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam, lr_scheduler

from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve, auc
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import GradientBoostingClassifier

warnings.filterwarnings("ignore", category=UserWarning)


# ---- CMS-like plotting style & palette ----
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

# colors (picked to match the slide vibe)
CMS_BLUE     = "#2368B5"   # main blue
CMS_RED      = "#C0392B"   # strong red
CMS_ORANGE   = "#E67E22"
CMS_GREEN    = "#2E8B57"
CMS_PURPLE   = "#6C5CE7"
CMS_GRAY     = "#4D4D4D"

# sequence for multi-lines (per-sample ROC)
plt.rcParams["axes.prop_cycle"] = cycler(color=[
    CMS_BLUE, CMS_RED, CMS_ORANGE, CMS_GREEN, CMS_PURPLE, "#1ABC9C", "#8E44AD",
    "#16A085", "#D35400", "#2C3E50"
])

# diverging colormap (blue ↔ white ↔ red) for correlation
cms_div = LinearSegmentedColormap.from_list(
    "cms_div", ["#1f77b4", "#f7f7f7", "#d62728"], N=256
)


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
BACKGROUND_FRAC     = 1.0    # 1.0 = keep all background
BALANCE_PER_GROUP   = True   # balance S=B inside each (mass,y) *after* split

# model/training
USE_BATCHNORM       = False  # BN off for stability
BATCH_SIZE_TRAIN    = 128
LR                  = 1e-3
WEIGHT_CLIP         = 10.0
PATIENCE            = 5
MAX_EPOCHS          = 500   # Changing the training from 100 epochs to 500 
WEIGHT_DECAY        = 1e-4
SAVE_MODEL_PATH     = "best_pdnn.pt"

# eval (OOM safety)
EVAL_BATCH          = 32768
USE_AMP_EVAL        = True
CPU_FALLBACK_ON_OOM = True

# debug toggles
DEBUG_ONE_BATCH             = False  # train only one minibatch per epoch
DEBUG_SHUFFLE_TRAIN_LABELS  = False  # train with shuffled labels → Val AUC ≈ 0.5

# optional ablation: drop features by name (before arrays are built)
DROP_FEATURES = []  # e.g., ['Res_sublead_bjet_pt','Res_lead_bjet_pt','Res_pholead_PtOverM','Res_DeltaR_jg_min']

# mass/y grid
mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
y_values    = [90, 95, 100, 125, 150, 200, 300, 400, 500, 600, 800] 
# updated the signal Y masses from 60, 70, 80, 90, 95, 100,... --> 90, 95,....

# -----------------------------
# Inputs
# -----------------------------
# SIGNAL parquet pattern (per mass,y set)
# SIG_TPL = "../../../output_parquet/v3_production/production_v3/2022_postEE_102425/merged/NMSSM_X{m}_Y{y}/NOTAG_merged.parquet"
SIG_TPL = "../../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"

# BACKGROUND is parquet
background_files = [
    "../../../output_root/v3_production/samples/postEE/GGJets.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt20To40.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
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

    # photon ID + b-tag
    "lead_mvaID_run3","sublead_mvaID_run3",
    # "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",

    # counts & MET
    "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",

    # Δφ(jet,MET)
    "Res_DeltaPhi_j1MET","Res_DeltaPhi_j2MET",

    # χ² terms
    "Res_chi_t0","Res_chi_t1",

    # raw kinematics and masses (for pT/m variables from the paper)
    "Res_dijet_pt","Res_dijet_mass",
    "Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",

    # scaled pT’s required by the paper
    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
]
 

# --- engineered features (from Res_* kinematics) ---
def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    mHH = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32"))
    mHH = mHH.replace(0, np.nan)

    if "Res_dijet_pt" in df.columns:
        df["ptjj_over_mHH"] = df["Res_dijet_pt"] / mHH
    else:
        df["ptjj_over_mHH"] = 0.0

    if "Res_HHbbggCandidate_pt" in df.columns:
        df["ptHH_over_mHH"] = df["Res_HHbbggCandidate_pt"] / mHH
    else:
        df["ptHH_over_mHH"] = 0.0

    # ΔR(γγ) from photon kinematics
    if all(c in df.columns for c in ["lead_phi","sublead_phi","lead_eta","sublead_eta"]):
        dphi = np.abs(df["lead_phi"] - df["sublead_phi"])
        dphi = np.where(dphi > np.pi, 2*np.pi - dphi, dphi)
        deta = df["lead_eta"] - df["sublead_eta"]
        df["DeltaR_gg"] = np.sqrt(deta**2 + dphi**2)
    else:
        df["DeltaR_gg"] = 0.0

    # absolute cos* (if you want |cosθ*|)
    for c in ["Res_CosThetaStar_gg","Res_CosThetaStar_jj","Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    for c in ["ptjj_over_mHH","ptHH_over_mHH","DeltaR_gg"]:
        df[c] = df[c].fillna(0)

    return df

# photon ID fallback (if only *_mvaID_nano exists)
def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
    pairs = [("lead_mvaID_run3","lead_mvaID_nano"),
             ("sublead_mvaID_run3","sublead_mvaID_nano")]
    for want, alt in pairs:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df

# include engineered names in features
FEATURES_CORE = FEATURES_CORE + [
                                "ptjj_over_mHH",
                                "ptHH_over_mHH",
                                #  "DeltaR_gg"
                                 ]
FEATURES_FINAL = FEATURES_CORE 
                    # +
                    # ["mass",
                    #  "y_value"]

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
    X = Xdf.values
    y = df['label'].astype(np.int8).values
    w = df[WEIGHT_COL].astype('float32').values
    return X, y, w

def balance_per_group(df, seed=SEED, min_per_class=1):
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    parts = []; dropped = 0
    for _, sub in df.groupby(key, sort=False):
        vc = sub['label'].value_counts()
        if len(vc) < 2: dropped += 1; continue
        n_min = vc.min()
        if n_min < min_per_class: dropped += 1; continue
        s = sub[sub['label']==1]; b = sub[sub['label']==0]
        s_keep = s.sample(n=n_min, random_state=seed) if len(s)>n_min else s
        b_keep = b.sample(n=n_min, random_state=seed) if len(b)>n_min else b
        parts.append(pd.concat([s_keep, b_keep], ignore_index=True))
    if not parts:
        raise RuntimeError("Per-group balancing removed all groups; relax constraints or inspect data.")
    out = pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    if dropped: print(f"[INFO] balance_per_group: dropped {dropped} tiny/pure groups in this split.")
    return out

def check_groups(df, name):
    groups = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    bad = [(k, int(g['label'].iloc[0]), len(g)) for k,g in df.groupby(groups) if g['label'].nunique()<2]
    if bad:
        print(f"[WARN] {name}: {len(bad)} pure (mass,y) groups remain. Examples: {bad[:5]}")
    assert df['label'].nunique()==2, f"{name} has only one class!"

def split_summary(df, name):
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    print(f"{name}: N={len(df):,}  counts={df['label'].value_counts().to_dict()}  groups={key.nunique()}")

@torch.no_grad()
def predict_batched(model, X_tensor, device, batch=32768, use_amp=True):
    model.eval()
    N = X_tensor.shape[0]
    out = np.empty(N, dtype=np.float32)
    amp_ctx = torch.amp.autocast(device_type=device.type, enabled=(use_amp and device.type=="cuda"))
    with amp_ctx:
        for i in range(0, N, batch):
            xb = X_tensor[i:i+batch].to(device, non_blocking=True)
            logits = model(xb).view(-1)
            out[i:i+batch] = torch.sigmoid(logits).detach().cpu().numpy()
    return out

def safe_eval_probs(model, X_tensor, device):
    try:
        return predict_batched(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL)
    except RuntimeError as e:
        if CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
            print("[WARN] CUDA OOM during eval → falling back to CPU (batched).")
            cpu_model = model.to(torch.device("cpu"))
            X_cpu = X_tensor.to(torch.device("cpu"))
            return predict_batched(cpu_model, X_cpu, torch.device("cpu"), batch=max(8192, EVAL_BATCH), use_amp=False)
        raise

# -----------------------------
# 1) Load SIGNAL (Parquet, per mass/y) — compute engineered features first
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
                    "lead_mvaID_nano","sublead_mvaID_nano",  # fallback source
                    "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
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
            df['mass']=mass; df['y_value']=y; df['label']=1
            df = ensure_weight(df); df = downcast_float_cols(df)
            signal_rows.append(df)
        except Exception as e:
            print(f"[WARN] read fail {fp}: {e}")
signal_df = pd.concat(signal_rows, ignore_index=True) if signal_rows else pd.DataFrame()

# -----------------------------
# 2) Load BACKGROUND (Parquet) — compute engineered features first
# -----------------------------
bkg_parts = []
for file_path in background_files:
    if not os.path.exists(file_path):
        print(f"[WARN] Missing {file_path}")
        continue
    try:
        try:
            cols = pd.read_parquet(file_path, columns=None).columns
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
                "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
                "n_leptons","n_jets","puppiMET_pt","puppiMET_phi",
                "Res_chi_t0","Res_chi_t1",
                "Res_dijet_pt","Res_HHbbggCandidate_pt","Res_HHbbggCandidate_mass",
            ]
            subset = [c for c in (set(need_raw) | {WEIGHT_COL}) if c in cols]
            dfb = pd.read_parquet(file_path, columns=subset)
        except Exception:
            dfb = pd.read_parquet(file_path)

        dfb = ensure_photon_mva_columns(dfb)
        dfb = add_engineered_features(dfb)

        keep = [c for c in FEATURES_CORE if c in dfb.columns]
        extras = [WEIGHT_COL] if WEIGHT_COL in dfb.columns else []
        dfb = dfb[keep + extras].copy()
        dfb = ensure_weight(dfb)
        dfb['label'] = 0
        dfb = downcast_float_cols(dfb)
        bkg_parts.append(dfb)
    except Exception as e:
        print(f"[WARN] read fail {file_path}: {e}")
df_background = pd.concat(bkg_parts, ignore_index=True) if bkg_parts else pd.DataFrame()
if BACKGROUND_FRAC < 1.0 and not df_background.empty:
    df_background = df_background.sample(frac=BACKGROUND_FRAC, random_state=SEED).reset_index(drop=True)

if signal_df.empty or df_background.empty:
    raise RuntimeError(f"Empty data: signal={signal_df.empty}, background={df_background.empty}")

# -----------------------------
# 3) Assign (mass,y) to BACKGROUND ~ signal mix, ensure coverage
# -----------------------------
sig_my = signal_df[['mass','y_value']]
mix = sig_my.value_counts(normalize=True).reset_index()
mix.columns = ['mass','y_value','weight']
sampled = mix.sample(n=len(df_background), replace=True, weights='weight', random_state=SEED).reset_index(drop=True)
df_background['mass']    = sampled['mass'].values
df_background['y_value'] = sampled['y_value'].values

need = set(map(tuple, sig_my.drop_duplicates().values.tolist()))
have = set(map(tuple, df_background[['mass','y_value']].drop_duplicates().values.tolist()))
missing_keys = list(need - have)
if missing_keys:
    K = min(len(missing_keys), len(df_background))
    for i,(m,y) in enumerate(missing_keys[:K]):
        df_background.loc[i,'mass']=m
        df_background.loc[i,'y_value']=y

# -----------------------------
# 4) Combine, drop pure (mass,y) groups globally
# -----------------------------
df_all = pd.concat([signal_df, df_background], ignore_index=True)
key_all = df_all['mass'].astype(int).astype(str) + "_" + df_all['y_value'].astype(int).astype(str)
grp_nuniq = df_all.groupby(key_all)['label'].nunique()
good_keys = set(grp_nuniq[grp_nuniq==2].index)
mask_good = key_all.isin(good_keys)
dropped = int((~mask_good).sum())
if dropped: print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
df_all = df_all.loc[mask_good].reset_index(drop=True)

# -----------------------------
# 5) Feature list (final) + optional ablation
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
    df_tr = balance_per_group(df_tr)
    df_va = balance_per_group(df_va)
    df_te = balance_per_group(df_te)

split_summary(df_tr, "TRAIN")
split_summary(df_va, "VAL")
split_summary(df_te, "TEST")
check_groups(df_tr, "TRAIN"); check_groups(df_va, "VAL"); check_groups(df_te, "TEST")

set_tr = set((df_tr['mass'].astype(int).astype(str)+"_"+df_tr['y_value'].astype(int).astype(str)).unique())
set_va = set((df_va['mass'].astype(int).astype(str)+"_"+df_va['y_value'].astype(int).astype(str)).unique())
set_te = set((df_te['mass'].astype(int).astype(str)+"_"+df_te['y_value'].astype(int).astype(str)).unique())
print("Overlap Train∩Val:", len(set_tr & set_va))
print("Overlap Train∩Test:", len(set_tr & set_te))
print("Overlap Val∩Test:", len(set_va & set_te))

# -----------------------------
# 7) Arrays + scaling (fit on TRAIN only)
# -----------------------------
X_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, available_features)
X_va_raw, y_va, w_va = df_to_arrays(df_va, available_features)
X_te_raw, y_te, w_te = df_to_arrays(df_te, available_features)

if DEBUG_SHUFFLE_TRAIN_LABELS:
    rng = np.random.default_rng(SEED+7)
    y_tr = rng.permutation(y_tr.copy())
    print("[DEBUG] Shuffled TRAIN labels. Val AUC should ≈ 0.5.")

scaler = StandardScaler()
X_tr = scaler.fit_transform(X_tr_raw)
X_va = scaler.transform(X_va_raw)
X_te = scaler.transform(X_te_raw)

# >>> SAVE THE SCALER (and feature order) <<<
import pickle, json
with open("scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)                       # saves the fitted StandardScaler

# (optional but recommended) save the feature order used by the scaler
with open("features_used.json", "w") as f:
    json.dump({"features": available_features}, f, indent=2)
print("[INFO] Saved scaler to scaler.pkl and feature list to features_used.json")

# -----------------------------
# 8) Leakage audit on VAL
# -----------------------------
print("\n[Leakage audit on VAL] per-feature AUC:")
for i, f in enumerate(available_features):
    auc_f = roc_auc_score(y_va, X_va[:, i])
    flag = " <-- suspicious" if (auc_f > 0.95 or auc_f < 0.05) else ""
    print(f"{f:24s} AUC={auc_f:.4f}{flag}")
i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
print(f"AUC using only (mass,y) on VAL: {roc_auc_score(y_va, 0.5*X_va[:, i_mass] + 0.5*X_va[:, i_y]):.4f}")

# -----------------------------
# 9) Hard sanity checks (before training)
# -----------------------------
X_va_t_cpu = torch.tensor(X_va, dtype=torch.float32)
mae = float(np.mean(np.abs(X_va_t_cpu.numpy() - X_va)))
mx  = float(np.max(np.abs(X_va_t_cpu.numpy() - X_va)))
print(f"[Sanity-0] X_va tensor vs numpy: mean|diff|={mae:.3e}, max|diff|={mx:.3e} (expect ~0)")

p_const = np.full_like(y_va, 0.5, dtype=np.float32)
print(f"[Sanity-1] Constant 0.5 predictor AUC: {roc_auc_score(y_va, p_const):.4f} (expect 0.5)")

class IdentityNet(nn.Module):
    def __init__(self, d): 
        super().__init__(); 
        self.fc = nn.Linear(d, 1)
    def forward(self, x): 
        return self.fc(x)

lin_model = IdentityNet(X_tr.shape[1]).cpu()
nn.init.kaiming_uniform_(lin_model.fc.weight, a=0.0, nonlinearity='linear')
nn.init.constant_(lin_model.fc.bias, 0.0)
with torch.no_grad():
    z_lin = lin_model(X_va_t_cpu).view(-1); p_lin = torch.sigmoid(z_lin).numpy()
print(f"[Sanity-2] Linear head only AUC: {roc_auc_score(y_va, p_lin):.4f} (should be ~0.5)")

# -----------------------------
# 10) Model + small-normal init + untrained diagnostics
# -----------------------------
def maybe_bn(n): 
    return nn.BatchNorm1d(n) if USE_BATCHNORM else nn.Identity()

class ParameterizedDNN(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 128), maybe_bn(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128,64), maybe_bn(64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64,32), maybe_bn(32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 1)  # logits only
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

# Build on CPU, init, diagnostics, then move to device
model = ParameterizedDNN(X_tr.shape[1]).cpu()
model.apply(small_normal_zero_bias_)
with torch.no_grad():
    z0 = model(X_va_t_cpu).view(-1); p0 = torch.sigmoid(z0).numpy()
auc0 = roc_auc_score(y_va, p0)
print(f"[Diag] Untrained model Val AUC (expect ~0.5): {auc0:.4f}")
print(f"[Diag] p0 stats: min={float(p0.min()):.6f} max={float(p0.max()):.6f} mean={float(p0.mean()):.6f} std={float(p0.std()):.6f}")

# Baselines (VAL)
lr = LogisticRegression(max_iter=300); lr.fit(X_tr, y_tr)
auc_lr = roc_auc_score(y_va, lr.predict_proba(X_va)[:,1])
print(f"[Diag] Logistic regression Val AUC: {auc_lr:.4f}")
dt = DecisionTreeClassifier(max_depth=3, random_state=SEED); dt.fit(X_tr, y_tr)
auc_dt = roc_auc_score(y_va, dt.predict_proba(X_va)[:,1])
print(f"[Diag] DecisionTree(max_depth=3) Val AUC: {auc_dt:.4f}")
gb = GradientBoostingClassifier(random_state=SEED); gb.fit(X_tr, y_tr)
auc_gb = roc_auc_score(y_va, gb.predict_proba(X_va)[:,1])
print(f"[Diag] GradientBoosting Val AUC: {auc_gb:.4f}")

BASELINE_MAX = max(auc_lr, auc_dt, auc_gb)
if BASELINE_MAX <= 0.55:
    print(f"[Gate] Baselines are weak (max={BASELINE_MAX:.3f}). If DNN ValAUC exceeds 0.98, we'll abort and dump diagnostics.")
    enable_consistency_gate = True
else:
    enable_consistency_gate = False

# Move model to device for training
model = model.to(device)

# -----------------------------
# 11) Tensors & DataLoader
# -----------------------------
class ArrayDataset(Dataset):
    def __init__(self, X, y, w): 
        self.X=X; self.y=y; self.w=w
    def __len__(self): 
        return len(self.X)
    def __getitem__(self, i):
        return (torch.tensor(self.X[i], dtype=torch.float32),
                torch.tensor(self.y[i], dtype=torch.float32),
                torch.tensor(self.w[i], dtype=torch.float32))

train_loader = DataLoader(ArrayDataset(X_tr, y_tr, w_tr),
                          batch_size=BATCH_SIZE_TRAIN, shuffle=True,
                          pin_memory=(device.type=="cuda"),
                          num_workers=2 if os.name!="nt" else 0)

X_va_t = torch.tensor(X_va, dtype=torch.float32).to(device)
X_te_t = torch.tensor(X_te, dtype=torch.float32).to(device)

# -----------------------------
# 12) Loss/opt + AMP scaler
# -----------------------------
criterion = nn.BCEWithLogitsLoss(reduction='none')
optimizer = Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
use_amp = (device.type == "cuda")
scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp) if use_amp else torch.amp.GradScaler(enabled=False)
# if device.type == "cuda":
#     scaler_amp = torch.cuda.amp.GradScaler(enabled=True)
# else:
#     scaler_amp = torch.amp.GradScaler(enabled=False)


# -----------------------------
# 13) Train (early stop on Val AUC)
# -----------------------------
history = {"train_loss": [], "val_auc": [], "val_acc": []}
best_auc = -np.inf; epochs_since_best = 0

for epoch in range(MAX_EPOCHS):
    model.train()
    tot_loss, nseen = 0.0, 0
    for bi, (xb, yb, wb) in enumerate(train_loader):
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        wb = wb.to(device, non_blocking=True)
        wb = torch.clamp(wb / (wb.mean() + 1e-8), max=WEIGHT_CLIP)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(xb).view(-1)
            per_loss = criterion(logits, yb)
            loss = (per_loss * wb).mean()
        scaler_amp.scale(loss).backward()
        scaler_amp.step(optimizer)
        scaler_amp.update()

        bs = xb.size(0); tot_loss += float(loss.item()) * bs; nseen += bs
        if DEBUG_ONE_BATCH: break

    train_loss = tot_loss / max(nseen,1)

    # Validation
    val_probs = safe_eval_probs(model, X_va_t, device)
    val_auc = roc_auc_score(y_va, val_probs)
    val_acc = accuracy_score(y_va, (val_probs > 0.5).astype(int))

    history["train_loss"].append(train_loss)
    history["val_auc"].append(val_auc)
    history["val_acc"].append(val_acc)

    print(f"Epoch {epoch+1:02d} | TrainLoss: {train_loss:.4f} | ValAUC: {val_auc:.4f} | ValAcc: {val_acc:.4f}")
    scheduler.step(val_auc)

    # Consistency gate
    if enable_consistency_gate and val_auc >= 0.98:
        print("[Gate] DNN ValAUC is suspiciously high while baselines are ~0.5. Aborting for safety.")
        from scipy.stats import spearmanr
        ranks = []
        for i, f in enumerate(available_features):
            try:
                r = spearmanr(X_va[:, i], val_probs).statistic
            except Exception:
                r = np.nan
            ranks.append((f, r))
        ranks = sorted(ranks, key=lambda t: -abs(t[1]))[:10]
        print("[Gate] Top |Spearman| feature ↔ score on VAL:")
        for f, r in ranks:
            print(f"  {f:24s}  r={r:+.4f}")
        torch.save(model.state_dict(), SAVE_MODEL_PATH)
        with open("GATE_ABORTED", "w") as f: f.write("1\n")
        break

    # Early stopping
    if val_auc > best_auc + 1e-4:
        best_auc = val_auc; epochs_since_best = 0
        torch.save(model.state_dict(), SAVE_MODEL_PATH)
        print(f"[INFO] New best ValAUC: {best_auc:.4f} — model saved")
    else:
        epochs_since_best += 1
        if epochs_since_best >= PATIENCE:
            print(f"[INFO] Early stopping at epoch {epoch+1}."); break

# -----------------------------
# 14) Test + separation plots
# -----------------------------
if os.path.exists("GATE_ABORTED"):
    print("[INFO] Consistency gate aborted training early; proceeding with saved snapshot.")

if os.path.exists(SAVE_MODEL_PATH):
    try:
        state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(SAVE_MODEL_PATH, map_location=device)
    model.load_state_dict(state)
else:
    print("[WARN] No saved model found; using current in-memory weights.")

test_probs = safe_eval_probs(model, X_te_t, device)
fpr, tpr, _ = roc_curve(y_te, test_probs)
test_auc = auc(fpr, tpr)
print(f"\nTest AUC: {test_auc:.6f}")

i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
w_sig = w_te[sig_mask] if w_te is not None else None
w_bkg = w_te[bkg_mask] if w_te is not None else None
print(f"\n[Separation diagnostics — TEST]")
print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
if w_sig is not None:
    print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

bins = np.linspace(0.0, 1.0, 51)
plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=1.6, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=1.6, label="Background")
plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
plt.title("Signal vs Background — Test (UNWEIGHTED)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Signal_vs_Background—Test(UNWEIGHTED).png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Signal_vs_Background—Test(UNWEIGHTED).pdf")
plt.show()

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=1.6, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=1.6, label="Background")
plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
plt.title("Signal vs Background — Test (WEIGHTED, log y)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Signal_vs_Background—Test_log(WEIGHTED).png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Signal_vs_Background—Test_log(WEIGHTED).pdf")
plt.show()

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=1.6, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=1.6, label="Background")
plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
plt.title("Signal vs Background — Test (WEIGHTED, SHAPE-NORMALIZED)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Signal_vs_Background—Test(WEIGHTED).png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Signal_vs_Background—Test(WEIGHTED).pdf")
plt.show()

plt.figure()
plt.plot(fpr, tpr, label=f"AUC = {test_auc:.4f}")
plt.plot([0,1],[0,1],'k--',lw=1)
plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
plt.title("ROC — Test (group-disjoint)"); plt.legend(); plt.grid(True, alpha=0.3)
plt.tight_layout(); 
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/ROC.png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/ROC.pdf")
plt.show()

plt.figure(); plt.plot(history["train_loss"], marker='o')
plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
plt.grid(True, alpha=0.3); plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Training_loss.png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Training_loss.pdf")
plt.show()

plt.figure(); plt.plot(history["val_auc"], marker='o', label="Val AUC")
plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
plt.grid(True, alpha=0.3); plt.legend(); plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/validation_AUC.png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/Validation_AUC.pdf")
plt.show()


# -----------------------------
# 14) Test + diagnostics & plots (with CMS palette)
# -----------------------------
if os.path.exists("GATE_ABORTED"):
    print("[INFO] Consistency gate aborted training early; proceeding with saved snapshot.")

if os.path.exists(SAVE_MODEL_PATH):
    try:
        state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(SAVE_MODEL_PATH, map_location=device)
    model.load_state_dict(state)
else:
    print("[WARN] No saved model found; using current in-memory weights.")

test_probs = safe_eval_probs(model, X_te_t, device)

# --- Overall ROC ---
fpr_all, tpr_all, thr_all = roc_curve(y_te, test_probs, sample_weight=w_te)
test_auc = auc(fpr_all, tpr_all)
print(f"\nTest AUC (overall): {test_auc:.6f}")

# quick check: (mass,y) only
i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

# masks & counts
sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
w_sig = w_te[sig_mask] if w_te is not None else None
w_bkg = w_te[bkg_mask] if w_te is not None else None
print(f"\n[Separation diagnostics — TEST]")
print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
if w_sig is not None:
    print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

# ---------- Separation histograms (CMS colors) ----------
bins = np.linspace(0.0, 1.0, 51)

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=2.0,
         label="Signal", color=CMS_BLUE)
plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=2.0,
         label="Background", color=CMS_RED)
plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
plt.title("Signal vs Background — Test (unweighted)")
plt.legend()
plt.tight_layout(); plt.show()

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=2.0,
         label="Signal", color=CMS_BLUE)
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=2.0,
         label="Background", color=CMS_RED)
plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
plt.title("Signal vs Background — Test (weighted)")
plt.legend()
plt.tight_layout(); plt.show()

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=2.0,
         label="Signal (shape)", color=CMS_BLUE)
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=2.0,
         label="Background (shape)", color=CMS_RED)
plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
plt.title("Signal vs Background — Test (weighted, shape-normalized)")
plt.legend()
plt.tight_layout(); plt.show()

# ---------- ROC: overall + per-(mass,y) ----------
# overall first
plt.figure()
plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)
plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
plt.title("ROC — Test (group-disjoint)")

# per (mass, y): overlay thin translucent lines
group_key = (df_te['mass'].astype(int).astype(str) + "_" +
             df_te['y_value'].astype(int).astype(str)).values
scores = test_probs
labels = y_te
weights = w_te

# sort groups for stable legend
uniq_groups = np.unique(group_key)
legend_handles = []
for g in uniq_groups:
    idx = (group_key == g)
    if np.unique(labels[idx]).size < 2:
        continue
    fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx],
                                sample_weight=(weights[idx] if weights is not None else None))
    auc_g = auc(fpr_g, tpr_g)
    h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.6, label=f"{g} (AUC {auc_g:.3f})")
    legend_handles.append((auc_g, h))

# only keep top ~10 groups in legend to avoid clutter
legend_handles.sort(key=lambda t: t[0], reverse=True)
handles_to_show = [h for _,h in legend_handles[:10]]
labels_to_show  = [h.get_label() for h in handles_to_show]
leg1 = plt.legend(handles_to_show, labels_to_show, title="Top groups", loc="lower right",
                  frameon=True, fontsize=8)
plt.gca().add_artist(leg1)
plt.tight_layout(); plt.show()

# ---------- Correlation heatmap (Test, unweighted) ----------
# Build a DataFrame of the features used on TEST
Xte_df = pd.DataFrame(X_te_raw, columns=available_features)
# We want correlation in the original (unstandardized) scale, so use X_te_raw not X_te
corr = Xte_df[ [c for c in available_features if c not in ("mass","y_value")] ].corr(method="pearson")
fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
im = ax.imshow(corr.values, cmap=cms_div, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
ax.set_xticks(np.arange(corr.shape[1]))
ax.set_yticks(np.arange(corr.shape[0]))
ax.set_xticklabels(corr.columns, rotation=90)
ax.set_yticklabels(corr.index)
ax.set_title("Pearson correlation (test, unweighted)")
cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Correlation")
plt.tight_layout(); plt.show()

# ---------- Training curves ----------
plt.figure(); plt.plot(history["train_loss"], marker='o', color=CMS_BLUE)
plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
plt.tight_layout(); plt.show()

plt.figure(); 
plt.plot(history["val_auc"], marker='o', label="Val AUC", color=CMS_RED)
plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
plt.legend(); plt.tight_layout(); plt.show()




# -----------------------------
# 14) Test + diagnostics & plots (with CMS palette)
# -----------------------------
if os.path.exists("GATE_ABORTED"):
    print("[INFO] Consistency gate aborted training early; proceeding with saved snapshot.")

if os.path.exists(SAVE_MODEL_PATH):
    try:
        state = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(SAVE_MODEL_PATH, map_location=device)
    model.load_state_dict(state)
else:
    print("[WARN] No saved model found; using current in-memory weights.")

test_probs = safe_eval_probs(model, X_te_t, device)

# --- Overall ROC ---
fpr_all, tpr_all, thr_all = roc_curve(y_te, test_probs, sample_weight=w_te)
test_auc = auc(fpr_all, tpr_all)
print(f"\nTest AUC (overall): {test_auc:.6f}")

# quick check: (mass,y) only
i_mass = available_features.index('mass'); i_y = available_features.index('y_value')
print(f"AUC using only (mass,y) on TEST: {roc_auc_score(y_te, 0.5*X_te[:, i_mass] + 0.5*X_te[:, i_y]):.4f}")

# masks & counts
sig_mask = (y_te == 1); bkg_mask = (y_te == 0)
w_sig = w_te[sig_mask] if w_te is not None else None
w_bkg = w_te[bkg_mask] if w_te is not None else None
print(f"\n[Separation diagnostics — TEST]")
print(f"Unweighted counts:   S={int(sig_mask.sum()):,}  B={int(bkg_mask.sum()):,}")
if w_sig is not None:
    print(f"Total test weights:  S={float(np.sum(w_sig)):.3e}  B={float(np.sum(w_bkg)):.3e}")

# ---------- Separation histograms (CMS colors) ----------
bins = np.linspace(0.0, 1.0, 51)

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=2.0,
         label="Signal", color=CMS_BLUE)
plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=2.0,
         label="Background", color=CMS_RED)
plt.xlabel("DNN output (probability)"); plt.ylabel("Events")
plt.title("Signal vs Background — Test (unweighted)")
plt.legend()
plt.tight_layout(); plt.show()

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=2.0,
         label="Signal", color=CMS_BLUE)
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=2.0,
         label="Background", color=CMS_RED)
plt.yscale('log'); plt.xlabel("DNN output (probability)"); plt.ylabel("Weighted events")
plt.title("Signal vs Background — Test (weighted)")
plt.legend()
plt.tight_layout(); plt.show()

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=2.0,
         label="Signal (shape)", color=CMS_BLUE)
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=2.0,
         label="Background (shape)", color=CMS_RED)
plt.xlabel("DNN output (probability)"); plt.ylabel("Density")
plt.title("Signal vs Background — Test (weighted, shape-normalized)")
plt.legend()
plt.tight_layout(); plt.show()

# ---------- ROC: overall + per-(mass,y) ----------
# overall first
plt.figure()
plt.plot(fpr_all, tpr_all, label=f"All (AUC = {test_auc:.3f})", color=CMS_BLUE, lw=2.4)
plt.plot([0,1],[0,1], linestyle='--', color=CMS_GRAY, lw=1)
plt.xlabel("Background efficiency"); plt.ylabel("Signal efficiency")
plt.title("ROC — Test (group-disjoint)")

# per (mass, y): overlay thin translucent lines
group_key = (df_te['mass'].astype(int).astype(str) + "_" +
             df_te['y_value'].astype(int).astype(str)).values
scores = test_probs
labels = y_te
weights = w_te

# sort groups for stable legend
group_key = np.array(list(zip(df_te['mass'].astype(int).values,
                              df_te['y_value'].astype(int).values)))
uniq_groups = np.unique(group_key, axis=0)

legend_handles = []
for m, yv in uniq_groups:
    idx = (group_key[:,0] == m) & (group_key[:,1] == yv)
    if np.unique(labels[idx]).size < 2:
        continue
    fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx],
                                sample_weight=(weights[idx] if weights is not None else None))
    auc_g = auc(fpr_g, tpr_g)
    h, = plt.plot(fpr_g, tpr_g, alpha=0.35, lw=1.6, label=f"NMSSM_X{m}_Y{yv} (AUC {auc_g:.3f})")
    legend_handles.append((auc_g, h))


# only keep top ~10 groups in legend to avoid clutter
legend_handles.sort(key=lambda t: t[0], reverse=True)
handles_to_show = [h for _,h in legend_handles[:10]]
labels_to_show  = [h.get_label() for h in handles_to_show]
leg1 = plt.legend(handles_to_show, labels_to_show, title="Top groups", loc="lower right",
                  frameon=True, fontsize=8)
plt.gca().add_artist(leg1)
plt.tight_layout(); plt.show()

# ---------- Correlation heatmap (Test, unweighted) ----------
# Build a DataFrame of the features used on TEST
Xte_df = pd.DataFrame(X_te_raw, columns=available_features)
# We want correlation in the original (unstandardized) scale, so use X_te_raw not X_te
corr = Xte_df[ [c for c in available_features if c not in ("mass","y_value")] ].corr(method="pearson")
fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=110)
im = ax.imshow(corr.values, cmap=cms_div, vmin=-1.0, vmax=1.0, interpolation="nearest", aspect="auto")
ax.set_xticks(np.arange(corr.shape[1]))
ax.set_yticks(np.arange(corr.shape[0]))
ax.set_xticklabels(corr.columns, rotation=90)
ax.set_yticklabels(corr.index)
ax.set_title("Pearson correlation (test, unweighted)")
cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Correlation")
plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/variable_correlation.png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/variable_correlation.pdf")
plt.show()

# ---------- Training curves ----------
plt.figure(); plt.plot(history["train_loss"], marker='o', color=CMS_BLUE)
plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/training_loss.png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/training_loss.pdf")
plt.show()


plt.figure(); 
plt.plot(history["val_auc"], marker='o', label="Val AUC", color=CMS_RED)
plt.title("Validation AUC (group-disjoint)"); plt.xlabel("Epoch"); plt.ylabel("AUC")
plt.legend()
plt.tight_layout()
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/validation_accuracy.png", dpi = 600)
plt.savefig("/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN/validation_accuracy.pdf")
plt.show()




# # ===============================================================
# # Feature importance
# # ===============================================================

# print("==================================================")
# print("Moving to feature importance")
# print("==================================================")

# # ============================
# # Feature importance utilities
# # ============================
# from collections import defaultdict
# import json

# OUTDIR = "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN"
# os.makedirs(OUTDIR, exist_ok=True)

# def _weighted_auc(y, p, w=None):
#     return roc_auc_score(y, p, sample_weight=(w if w is not None else None))

# def _groupwise_shuffle_inplace(X_block, groups, col, rng):
#     """
#     Shuffle column 'col' within each group to preserve per-(mass,y) marginals.
#     Works with either 1-D (N,) group codes or 2-D (N,K) group columns.
#     """
#     groups = np.asarray(groups)
#     if groups.ndim == 2:
#         uniq = np.unique(groups, axis=0)
#         for g in uniq:
#             idx = np.all(groups == g, axis=1)           # -> 1-D boolean mask
#             vals = X_block[idx, col].copy()
#             rng.shuffle(vals)
#             X_block[idx, col] = vals
#     else:
#         for g in np.unique(groups):
#             idx = (groups == g)
#             vals = X_block[idx, col].copy()
#             rng.shuffle(vals)
#             X_block[idx, col] = vals

# @torch.no_grad()
# def permutation_importance_auc(
#     model, X, y, w, feature_names, device, groups=None,
#     n_repeats=5, batch=EVAL_BATCH, use_amp=USE_AMP_EVAL, seed=SEED
# ):
#     """
#     Return (base_auc, imp_mean_dict, imp_std_dict)
#     where imp_mean/std are AUC drops (baseline - permuted) per feature.
#     """
#     # Baseline
#     X_t = torch.tensor(X, dtype=torch.float32, device=device)
#     base_probs = safe_eval_probs(model, X_t, device)
#     base_auc = _weighted_auc(y, base_probs, w)

#     rng = np.random.default_rng(seed)
#     drops = defaultdict(list)

#     for j, f in enumerate(feature_names):
#         for _ in range(n_repeats):
#             X_perm = X.copy()
#             if groups is None:
#                 # Global column shuffle as fallback
#                 rng.shuffle(X_perm[:, j])
#             else:
#                 _groupwise_shuffle_inplace(X_perm, groups, j, rng)

#             Xp_t = torch.tensor(X_perm, dtype=torch.float32, device=device)
#             probs_p = safe_eval_probs(model, Xp_t, device)
#             auc_p = _weighted_auc(y, probs_p, w)
#             drops[f].append(base_auc - auc_p)

#     imp_mean = {f: float(np.mean(v)) for f, v in drops.items()}
#     imp_std  = {f: float(np.std(v, ddof=1)) for f, v in drops.items()}
#     return base_auc, imp_mean, imp_std

# def plot_importance_bar(imp_mean, imp_err, title, filename, top_k=25, cms_color=CMS_BLUE):
#     items = sorted(imp_mean.items(), key=lambda t: t[1], reverse=True)[:top_k]
#     labels = [k for k,_ in items][::-1]
#     vals   = [imp_mean[k] for k in labels]
#     errs   = [imp_err.get(k, 0.0) for k in labels]

#     plt.figure(figsize=(8.0, 0.4*len(labels)+1.5), dpi=110)
#     plt.barh(range(len(labels)), vals, xerr=errs, color=cms_color, alpha=0.85)
#     plt.yticks(range(len(labels)), labels)
#     plt.xlabel("Mean AUC drop (permutation)")
#     plt.title(title)
#     plt.tight_layout()
#     png = os.path.join(OUTDIR, f"{filename}.png")
#     pdf = os.path.join(OUTDIR, f"{filename}.pdf")
#     plt.savefig(png, dpi=600); plt.savefig(pdf)
#     plt.show()
#     print(f"[Saved] {png}\n[Saved] {pdf}")

# # ---------------
# # PERMUTATION AUC
# # ---------------
# # Choose the split to report (VAL is common for model selection; TEST for final)
# SPLIT = "TEST"  # or "VAL"
# if SPLIT == "VAL":
#     X_imp, y_imp, w_imp = X_va, y_va, w_va
#     df_split = df_va
#     split_name = "VAL"
# else:
#     X_imp, y_imp, w_imp = X_te, y_te, w_te
#     df_split = df_te
#     split_name = "TEST"

# # Optional: exclude mass/y from the ranking if you only want physics features
# INCLUDE_MY = True
# feat_names_imp = [f for f in available_features if INCLUDE_MY or f not in ("mass","y_value")]
# cols = [available_features.index(f) for f in feat_names_imp]
# X_imp_sel = X_imp[:, cols].copy()

# # --- Group keys for within-group shuffles ---
# # Use compact 1-D integer codes for speed & correctness.
# group_codes = pd.factorize(
#     df_split['mass'].astype(int).astype(str) + "_" + df_split['y_value'].astype(int).astype(str)
# )[0]  # shape (N,), dtype int

# # If you ever prefer a 2-D grouping array instead, you may pass:
# # group_keys_2d = np.c_[df_split['mass'].astype(int).values, df_split['y_value'].astype(int).values]
# # (the shuffle function supports both)

# # Compute permutation importances
# base_auc, imp_mean, imp_std = permutation_importance_auc(
#     model,
#     X_imp_sel, y_imp, w_imp,
#     feature_names=feat_names_imp,
#     device=device,
#     groups=group_codes,
#     n_repeats=5
# )
# print(f"[Permutation] Baseline {split_name} AUC = {base_auc:.4f}")

# plot_importance_bar(
#     imp_mean, imp_std,
#     title=f"Permutation importance (AUC drop) — {split_name}",
#     filename=f"feature_importance_permutation_{split_name.lower()}",
#     top_k=25, cms_color=CMS_BLUE
# )

# # -----------------------
# # INPUT-GRADIENT SALIENCY
# # -----------------------
# def gradient_saliency(model, X, feature_names, device, scaler=None, batch=4096):
#     """
#     Returns importance ~ mean(|d logit / d x_raw|) per feature.
#     If 'scaler' is provided (StandardScaler), converts gradients from standardized to raw space.
#     """
#     model.eval()
#     N, D = X.shape
#     grads_accum = np.zeros(D, dtype=np.float64)
#     n_seen = 0

#     # Map grad wrt standardized x to raw x: d/dx_raw = d/dx_std * 1/std
#     if scaler is not None and hasattr(scaler, "scale_"):
#         inv_scale = 1.0 / np.asarray(scaler.scale_)
#         inv_scale = inv_scale[[available_features.index(f) for f in feature_names]]
#     else:
#         inv_scale = np.ones(D, dtype=np.float64)

#     ptr = 0
#     while ptr < N:
#         xb = torch.tensor(X[ptr:ptr+batch], dtype=torch.float32, device=device, requires_grad=True)
#         logits = model(xb).view(-1)  # logits (before sigmoid)
#         s = logits.sum()
#         s.backward()
#         g = xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()  # mean |grad| over batch
#         grads_accum += g
#         n_seen += 1
#         ptr += batch
#         model.zero_grad(set_to_none=True)

#     grads_mean = grads_accum / max(n_seen, 1)
#     grads_raw = grads_mean * inv_scale
#     return {f: float(val) for f, val in zip(feature_names, grads_raw)}

# sal = gradient_saliency(model, X_imp_sel, feat_names_imp, device, scaler=scaler, batch=4096)

# # Normalize for nicer plotting (max=1)
# mmax = max(sal.values()) if len(sal) else 1.0
# sal_norm = {k: (v / mmax if mmax > 0 else 0.0) for k, v in sal.items()}

# plot_importance_bar(
#     sal_norm, {k:0.0 for k in sal_norm},
#     title=f"Input-gradient saliency (normalized) — {split_name}",
#     filename=f"feature_importance_grad_{split_name.lower()}",
#     top_k=25, cms_color=CMS_ORANGE
# )

# # ================================
# # Save importances (CSV + JSON)
# # ================================
# # Ensure OUTDIR exists (define if not already)
# os.makedirs(OUTDIR, exist_ok=True)

# # Build a single table with both permutation and gradient saliency
# all_feats = list(sorted(set(feat_names_imp)))
# perm_mean_vec = np.array([imp_mean.get(f, np.nan) for f in all_feats], dtype=float)
# perm_std_vec  = np.array([imp_std.get(f,  np.nan) for f in all_feats], dtype=float)
# grad_norm_vec = np.array([sal_norm.get(f,  np.nan) for f in all_feats], dtype=float)

# imp_df = pd.DataFrame({
#     "feature": all_feats,
#     "perm_mean_auc_drop": perm_mean_vec,
#     "perm_std_auc_drop":  perm_std_vec,
#     "grad_saliency_norm": grad_norm_vec,
# })

# # Nice ordering: by permutation mean drop desc, then gradient desc
# imp_df = imp_df.sort_values(
#     ["perm_mean_auc_drop", "grad_saliency_norm"],
#     ascending=[False, False],
#     na_position="last"
# )

# # File names include split name to avoid collisions
# csv_path  = os.path.join(OUTDIR, f"feature_importance_{split_name.lower()}.csv")
# json_path = os.path.join(OUTDIR, f"feature_importance_{split_name.lower()}.json")

# imp_df.to_csv(csv_path, index=False)

# with open(json_path, "w") as f:
#     json.dump({
#         "split": split_name,
#         "baseline_auc": float(base_auc),
#         "permutation_importance": imp_mean,
#         "permutation_importance_std": imp_std,
#         "gradient_saliency_normalized": sal_norm,
#         "table_order": imp_df["feature"].tolist()
#     }, f, indent=2)

# print(f"[Saved] {csv_path}")
# print(f"[Saved] {json_path}")

## ===========================
## Feature importance (fixed)
## ===========================

print("==================================================")
print("Moving to feature importance")
print("==================================================")

from collections import defaultdict
import json

OUTDIR = "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/pDNN"
os.makedirs(OUTDIR, exist_ok=True)

def _weighted_auc(y, p, w=None):
    return roc_auc_score(y, p, sample_weight=(w if w is not None else None))

def _groupwise_shuffle_inplace(X_block, group_codes, col, rng):
    """
    Shuffle column 'col' within each group (preserves per-(mass,y) marginal).
    group_codes must be 1-D integer codes (use pd.factorize).
    """
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
    """
    Compute permutation importance as AUC drop for a subset of features,
    while always feeding the model with the FULL feature matrix X_full.

    Args:
      - feature_names_to_permute: list[str] (names as in available_features or a subset)
      - feature_index_map: dict[name] -> int (column index in X_full / available_features)
      - group_codes: 1-D array of ints encoding (mass,y) groups; if None, global shuffle
    Returns:
      base_auc, mean_drop_dict, std_drop_dict
    """
    # Baseline AUC (full features)
    X_t = torch.tensor(X_full, dtype=torch.float32, device=device)
    base_probs = safe_eval_probs(model, X_t, device)
    base_auc = _weighted_auc(y, base_probs, w)

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
            auc_p = _weighted_auc(y, probs_p, w)
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
    plt.xlabel("Mean AUC drop (permutation)")
    plt.title(title)
    plt.tight_layout()
    png = os.path.join(OUTDIR, f"{filename}.png")
    pdf = os.path.join(OUTDIR, f"{filename}.pdf")
    plt.savefig(png, dpi=600); plt.savefig(pdf)
    plt.show()
    print(f"[Saved] {png}\n[Saved] {pdf}")

# --------------------------
# Choose split for importance
# --------------------------
SPLIT = "TEST"  # or "VAL"
if SPLIT == "VAL":
    X_imp, y_imp, w_imp = X_va, y_va, w_va
    df_split = df_va
    split_name = "VAL"
else:
    X_imp, y_imp, w_imp = X_te, y_te, w_te
    df_split = df_te
    split_name = "TEST"

# Which features to rank?
INCLUDE_MY = True  # set False to exclude mass,y from the ranking
feat_names_imp = [f for f in available_features if INCLUDE_MY or f not in ("mass","y_value")]

# Map names -> column indices in the FULL feature order
name_to_idx = {f: available_features.index(f) for f in available_features}

# Group codes (1-D) for within-(mass,y) shuffles
group_codes = pd.factorize(
    df_split['mass'].astype(int).astype(str) + "_" + df_split['y_value'].astype(int).astype(str)
)[0]

# ---------- Permutation importance ----------
base_auc, imp_mean, imp_std = permutation_importance_auc(
    model,
    X_imp, y_imp, w_imp,
    feature_names_to_permute=feat_names_imp,
    device=device,
    feature_index_map=name_to_idx,
    group_codes=group_codes,
    n_repeats=5
)
print(f"[Permutation] Baseline {split_name} AUC = {base_auc:.4f}")

plot_importance_bar(
    imp_mean, imp_std,
    title=f"Permutation importance (AUC drop) — {split_name}",
    filename=f"feature_importance_permutation_{split_name.lower()}",
    top_k=25, cms_color=CMS_BLUE
)

# ---------- Input-gradient saliency ----------
def gradient_saliency(model, X_full, feature_names_report, device, scaler=None, batch=4096):
    """
    Compute mean |d logit / d x_raw| per feature (reported only for feature_names_report).
    Gradients are taken w.r.t. the standardized inputs fed to the model, then converted
    back to raw scale via 1/std from the fitted StandardScaler.
    """
    model.eval()
    N, D = X_full.shape
    grads_accum = np.zeros(D, dtype=np.float64)
    n_seen = 0

    # inv_scale aligned to the FULL feature order
    if scaler is not None and hasattr(scaler, "scale_"):
        inv_scale_full = 1.0 / np.asarray(scaler.scale_, dtype=np.float64)
        if inv_scale_full.shape[0] != D:
            raise RuntimeError("Scaler has different number of features than X_full.")
    else:
        inv_scale_full = np.ones(D, dtype=np.float64)

    ptr = 0
    while ptr < N:
        xb = torch.tensor(X_full[ptr:ptr+batch], dtype=torch.float32, device=device, requires_grad=True)
        logits = model(xb).view(-1)
        s = logits.sum()
        s.backward()
        g = xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()  # shape (D,)
        grads_accum += g
        n_seen += 1
        ptr += batch
        model.zero_grad(set_to_none=True)

    grads_mean = grads_accum / max(n_seen, 1)
    grads_raw = grads_mean * inv_scale_full  # convert to raw space

    # Report only requested features (but using their full indices)
    return {f: float(grads_raw[name_to_idx[f]]) for f in feature_names_report}

sal = gradient_saliency(model, X_imp, feat_names_imp, device, scaler=scaler, batch=4096)

# Normalize saliency for plotting (max = 1 over reported features)
mmax = max(sal.values()) if len(sal) else 1.0
sal_norm = {k: (v / mmax if mmax > 0 else 0.0) for k, v in sal.items()}

plot_importance_bar(
    sal_norm, {k:0.0 for k in sal_norm},
    title=f"Input-gradient saliency (normalized) — {split_name}",
    filename=f"feature_importance_grad_{split_name.lower()}",
    top_k=25, cms_color=CMS_ORANGE
)

# ---------- Save both importances ----------
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

csv_path  = os.path.join(OUTDIR, f"feature_importance_{split_name.lower()}.csv")
json_path = os.path.join(OUTDIR, f"feature_importance_{split_name.lower()}.json")

imp_df.to_csv(csv_path, index=False)
with open(json_path, "w") as f:
    json.dump({
        "split": split_name,
        "baseline_auc": float(base_auc),
        "permutation_importance": imp_mean,
        "permutation_importance_std": imp_std,
        "gradient_saliency_normalized": sal_norm,
        "table_order": imp_df["feature"].tolist()
    }, f, indent=2)

print(f"[Saved] {csv_path}")
print(f"[Saved] {json_path}")





# -----------------------------
# Extra: Signal eff vs Background eff (ROC) — overall + per-(mass,y)
# -----------------------------
from sklearn.metrics import roc_curve, auc

def plot_eff_vs_eff(
    scores, labels, weights=None, df_groups=None,
    title_prefix="ROC — Test", out_prefix="ROC_eff_vs_eff",
    cms_color_main=CMS_BLUE, cms_color_bg=CMS_GRAY,
    save_dir=OUTDIR, overlay_per_group=True, max_legend=10
):
    """
    scores: 1-D array of model probabilities (float)
    labels: 1-D array of 0/1 labels
    weights: optional 1-D array of event weights (same length) or None
    df_groups: optional DataFrame with columns ['mass','y_value'] aligned with scores/labels.
               If provided and overlay_per_group True, per-(mass,y) ROCs will be drawn.
    """

    # overall ROC (both weighted & unweighted)
    # unweighted
    fpr_unw, tpr_unw, thr_unw = roc_curve(labels, scores)
    auc_unw = auc(fpr_unw, tpr_unw)

    # weighted (if weights present)
    if weights is not None:
        try:
            fpr_w, tpr_w, thr_w = roc_curve(labels, scores, sample_weight=weights)
            auc_w = auc(fpr_w, tpr_w)
            have_weighted = True
        except Exception as e:
            print("[WARN] weighted ROC failed:", e)
            fpr_w, tpr_w, auc_w = None, None, None
            have_weighted = False
    else:
        fpr_w, tpr_w, auc_w = None, None, None
        have_weighted = False

    # Start figure
    plt.figure(figsize=(7.2,5.0), dpi=110)
    # plot main (choose weighted curve if available as primary)
    if have_weighted:
        plt.plot(fpr_w, tpr_w, label=f"All (weighted) AUC={auc_w:.3f}", color=cms_color_main, lw=2.6)
        plt.plot(fpr_unw, tpr_unw, linestyle='--', label=f"All (unweighted) AUC={auc_unw:.3f}", color=cms_color_main, alpha=0.6, lw=1.6)
    else:
        plt.plot(fpr_unw, tpr_unw, label=f"All AUC={auc_unw:.3f}", color=cms_color_main, lw=2.6)

    # diagonal
    plt.plot([0,1],[0,1], linestyle='--', color=cms_color_bg, lw=1)

    # per-(mass,y) overlay
    legend_handles = []
    if overlay_per_group and (df_groups is not None):
        # compact group key
        group_key = (df_groups['mass'].astype(int).astype(str) + "_" + df_groups['y_value'].astype(int).astype(str)).values
        uniq = np.unique(group_key)
        for g in uniq:
            idx = (group_key == g)
            if np.unique(labels[idx]).size < 2:
                continue
            try:
                if weights is not None:
                    fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx], sample_weight=weights[idx])
                else:
                    fpr_g, tpr_g, _ = roc_curve(labels[idx], scores[idx])
            except Exception:
                continue
            auc_g = auc(fpr_g, tpr_g)
            h, = plt.plot(fpr_g, tpr_g, alpha=0.30, lw=1.2, label=f"{g} (AUC {auc_g:.3f})")
            legend_handles.append((auc_g, h))

        # keep only top-N groups in legend to avoid clutter
        legend_handles.sort(key=lambda t: t[0], reverse=True)
        handles_to_show = [h for _, h in legend_handles[:max_legend]]
        labels_to_show = [h.get_label() for h in handles_to_show]
        if handles_to_show:
            leg1 = plt.legend(handles_to_show, labels_to_show, title="Top groups", loc="lower right", frameon=True, fontsize=8)
            plt.gca().add_artist(leg1)

    plt.xlabel("Background efficiency (FPR)")
    plt.ylabel("Signal efficiency (TPR)")
    plt.title(f"{title_prefix} — eff(S) vs eff(B)")
    plt.grid(True, alpha=0.25)
    # overall legend
    plt.legend(loc="lower left", fontsize=9)
    plt.tight_layout()

    # save both versions (weighted/unweighted filenames)
    base = os.path.join(save_dir, out_prefix)
    png = base + ".png"
    pdf = base + ".pdf"
    plt.savefig(png, dpi=600)
    plt.savefig(pdf)
    print(f"[Saved] {png}\n[Saved] {pdf}")
    plt.show()

# -----------------------------
# Call the function for TEST split
# -----------------------------
# Ensure OUTDIR exists (OUTDIR used elsewhere in your script; if not, adjust)
os.makedirs(OUTDIR, exist_ok=True)

# scores = test_probs (already computed)
# labels = y_te
# weights = w_te (may be None)
# df_groups = df_te (the DataFrame holding mass,y for test)

plot_eff_vs_eff(
    scores=test_probs,
    labels=y_te,
    weights=w_te if (w_te is not None and len(w_te)==len(y_te)) else None,
    df_groups=df_te,
    title_prefix="ROC — Test (group-disjoint)",
    out_prefix="ROC_eff_vs_eff_test",
    overlay_per_group=True,
    max_legend=10
)