#!/usr/bin/env python3
# ================================================================
# Minimal PDNN (10 epochs) + Feature Importance (standalone)
# Robust loader with SIG_TPL + glob fallback and diagnostics
# ================================================================
import os, warnings, json, glob
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

# -----------------------------
# Config
# -----------------------------
SEED = 42
np.random.seed(SEED)

# Signal template (strict) and a root for glob fallback
# SIG_TPL = "../../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
SIG_TPL = "../../../output_parquet/final_production_Syst/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
SIG_SEARCH_ROOT = Path("../../../../output_parquet/final_production_Syst/merged").resolve()
SIG_FILENAME_CANDIDATES = ["NOTAG_merged.parquet", "merged.parquet", "*.parquet"]

# Background files
BACKGROUND_FILES = [
    "../../../output_root/v3_production/samples/postEE/GGJets.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt20To40.parquet",
    "../../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
]

# Mass/y grids (edit if needed)
MASS_POINTS = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
Y_VALUES    = [90, 95, 100, 125, 150, 200, 300, 400, 500, 600, 800]

# Training
N_EPOCHS          = 10
BATCH_SIZE_TRAIN  = 128
LR                = 1e-3
WEIGHT_DECAY      = 1e-4
WEIGHT_CLIP       = 10.0
USE_AMP           = True

# Eval / safety
EVAL_BATCH          = 32768
CPU_FALLBACK_ON_OOM = True

# Outputs
SAVE_OUTPUTS = False            # set True to write CSV/JSON
OUTDIR       = "artifacts_pdnn_fi"

# Verbose scanning
VERBOSE_SCAN = True

# Feature names (Res_* version)
WEIGHT_COL = "weight_central"
FEATURES_CORE = [
    # photons & diphoton
    "lead_eta","lead_phi","sublead_eta","sublead_phi","eta","phi",
    # jets, dijet, HH (Res)
    "Res_lead_bjet_eta","Res_lead_bjet_phi",
    "Res_sublead_bjet_eta","Res_sublead_bjet_phi",
    "Res_dijet_eta","Res_dijet_phi",
    "Res_HHbbggCandidate_eta","Res_HHbbggCandidate_phi",
    # angular distances (Res)
    "Res_DeltaR_j1g1","Res_DeltaR_j1g2",
    "Res_DeltaR_j2g1","Res_DeltaR_j2g2","Res_DeltaR_jg_min",
    # helicity / Collins–Soper (use |cos*|)
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
    # scaled pTs
    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",
]
FEATURES_FINAL = FEATURES_CORE + ["ptjj_over_mHH","ptHH_over_mHH","mass","y_value"]

# -----------------------------
# Torch / sklearn imports
# -----------------------------
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score

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

def ensure_photon_mva_columns(df: pd.DataFrame) -> pd.DataFrame:
    pairs = [("lead_mvaID_run3","lead_mvaID_nano"),
             ("sublead_mvaID_run3","sublead_mvaID_nano")]
    for want, alt in pairs:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    mHH = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float32")).replace(0, np.nan)
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
        if c in df.columns: df[c] = df[c].abs()

    for c in ["ptjj_over_mHH","ptHH_over_mHH","DeltaR_gg"]:
        df[c] = df[c].fillna(0)
    return df

def df_to_arrays(df: pd.DataFrame, feature_list):
    Xdf = df[feature_list].copy()
    Xdf = Xdf.fillna(Xdf.mean(numeric_only=True))
    Xdf = downcast_float_cols(Xdf)
    X = Xdf.values.astype(np.float32)
    y = df['label'].astype(np.int8).values
    w = df[WEIGHT_COL].astype(np.float32).values
    return X, y, w

def balance_per_group(df, seed=SEED, min_per_class=1):
    key = df['mass'].astype(int).astype(str) + "_" + df['y_value'].astype(int).astype(str)
    parts = []
    for _, sub in df.groupby(key, sort=False):
        vc = sub['label'].value_counts()
        if len(vc) < 2: continue
        n_min = vc.min()
        if n_min < min_per_class: continue
        s = sub[sub['label']==1]; b = sub[sub['label']==0]
        s_keep = s.sample(n=n_min, random_state=seed) if len(s)>n_min else s
        b_keep = b.sample(n=n_min, random_state=seed) if len(b)>n_min else b
        parts.append(pd.concat([s_keep, b_keep], ignore_index=True))
    if not parts:
        raise RuntimeError("Per-group balancing removed all groups.")
    return pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)

def _try_read_parquet(fp):
    try:
        return pd.read_parquet(fp)
    except Exception as e:
        if VERBOSE_SCAN:
            print(f"[WARN] Failed to read: {fp}\n       {type(e).__name__}: {e}")
        return None

def _parse_mass_y_from_path(p: Path):
    """
    Parse NMSSM_X{m}_Y{y} from any path segment (case-sensitive).
    Returns (mass:int or None, y:int or None)
    """
    for s in p.parts:
        if "NMSSM" in s and "_X" in s and "_Y" in s:
            try:
                # e.g. NMSSM_X650_Y90
                xs = s.split("_")
                xm = [t for t in xs if t.startswith("X")]
                yy = [t for t in xs if t.startswith("Y")]
                if xm and yy:
                    m = int(xm[0].lstrip("X"))
                    yv = int(yy[0].lstrip("Y"))
                    return m, yv
            except Exception:
                pass
    return None, None

# -----------------------------
# Load data (robust with diagnostics + glob fallback)
# -----------------------------
def collect_signal_from_tpl():
    rows = []; tried = 0; found = 0
    for m in MASS_POINTS:
        for yv in Y_VALUES:
            fp = SIG_TPL.format(m=m, y=yv)
            tried += 1
            if not os.path.exists(fp):
                if VERBOSE_SCAN: print(f"[MISS] {fp}")
                continue
            df = _try_read_parquet(fp)
            if df is None: continue
            found += 1
            df = ensure_photon_mva_columns(df)
            df = add_engineered_features(df)
            keep = [c for c in FEATURES_FINAL if c in df.columns]
            extras = [WEIGHT_COL] if WEIGHT_COL in df.columns else []
            cols = list(dict.fromkeys(keep + extras))
            if not cols:
                if VERBOSE_SCAN: print(f"[SKIP] No expected columns in: {fp}")
                continue
            df = df[cols].copy()
            df["mass"]=m; df["y_value"]=yv; df["label"]=1
            df = ensure_weight(df)
            rows.append(downcast_float_cols(df))
    if VERBOSE_SCAN:
        print(f"[Signal via TPL] tried={tried}, found_files={found}, rows={sum(map(len,rows)) if rows else 0}")
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

def collect_signal_via_glob():
    rows = []
    if VERBOSE_SCAN: print(f"[Scan] Searching under: {SIG_SEARCH_ROOT}")
    found_paths = set()
    for pat in SIG_FILENAME_CANDIDATES:
        for fp in glob.iglob(str(SIG_SEARCH_ROOT / "**" / pat), recursive=True):
            found_paths.add(fp)
    if VERBOSE_SCAN:
        print(f"[Scan] Candidate files found: {len(found_paths)}")
        for i, fp in enumerate(sorted(found_paths)[:15]): print(f"  [{i+1:02d}] {fp}")
        if len(found_paths) > 15: print(f"  ... (+{len(found_paths)-15} more)")
    for fp in sorted(found_paths):
        df = _try_read_parquet(fp)
        if df is None or df.empty: continue
        m, yv = _parse_mass_y_from_path(Path(fp))
        if m is None or yv is None:
            if VERBOSE_SCAN: print(f"[SKIP] Could not parse (mass,y) from: {fp}")
            continue
        df = ensure_photon_mva_columns(df)
        df = add_engineered_features(df)
        keep = [c for c in FEATURES_FINAL if c in df.columns]
        extras = [WEIGHT_COL] if WEIGHT_COL in df.columns else []
        cols = list(dict.fromkeys(keep + extras))
        if not cols:
            if VERBOSE_SCAN: print(f"[SKIP] No expected columns in: {fp}")
            continue
        df = df[cols].copy()
        df["mass"]=m; df["y_value"]=yv; df["label"]=1
        df = ensure_weight(df)
        rows.append(downcast_float_cols(df))
    if VERBOSE_SCAN:
        print(f"[Signal via GLOB] files_used={len(rows)}, rows={sum(map(len,rows)) if rows else 0}")
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

# Signal
signal_df = collect_signal_from_tpl()
if signal_df.empty:
    print("[INFO] Falling back to glob scanning for signal files…")
    signal_df = collect_signal_via_glob()
if signal_df.empty:
    print("\n[ERROR] No signal rows loaded.")
    print("Hints:")
    print("  • Check SIG_TPL and that those paths exist on EOS.")
    print(f"  • Or set SIG_SEARCH_ROOT correctly (current: {SIG_SEARCH_ROOT}).")
    print("  • Ensure filenames match one of:", ", ".join(SIG_FILENAME_CANDIDATES))
    print("  • Ensure directory names contain NMSSM_X{{m}}_Y{{y}} so (mass,y) can be parsed.")
    raise RuntimeError("No signal rows loaded after template and glob scan.")

# Background
bkg_parts = []; missing_bkg = []
for file_path in BACKGROUND_FILES:
    if not os.path.exists(file_path):
        missing_bkg.append(file_path); continue
    dfb = _try_read_parquet(file_path)
    if dfb is None or dfb.empty:
        if VERBOSE_SCAN: print(f"[WARN] Background file empty/unreadable: {file_path}")
        continue
    dfb = ensure_photon_mva_columns(dfb)
    dfb = add_engineered_features(dfb)
    keep = [c for c in FEATURES_FINAL if c in dfb.columns]
    extras = [WEIGHT_COL] if WEIGHT_COL in dfb.columns else []
    cols = list(dict.fromkeys(keep + extras))
    if not cols:
        if VERBOSE_SCAN: print(f"[SKIP] No expected columns in background: {file_path}")
        continue
    dfb = dfb[cols].copy()
    dfb["label"] = 0
    bkg_parts.append(downcast_float_cols(ensure_weight(dfb)))

if missing_bkg:
    print("[WARN] Missing background files:")
    for fp in missing_bkg: print(f"  - {fp}")

df_background = pd.concat(bkg_parts, ignore_index=True) if bkg_parts else pd.DataFrame()
if df_background.empty:
    raise RuntimeError("No background rows loaded. Check BACKGROUND_FILES.")

# Assign (mass,y) to background to match signal mix
sig_my = signal_df[["mass","y_value"]]
mix = sig_my.value_counts(normalize=True).reset_index()
mix.columns = ["mass","y_value","weight"]
sampled = mix.sample(n=len(df_background), replace=True, weights="weight", random_state=SEED).reset_index(drop=True)
df_background["mass"] = sampled["mass"].values
df_background["y_value"] = sampled["y_value"].values

# Combine and drop pure (mass,y) groups
df_all = pd.concat([signal_df, df_background], ignore_index=True)
key_all = df_all["mass"].astype(int).astype(str) + "_" + df_all["y_value"].astype(int).astype(str)
grp_nuniq = df_all.groupby(key_all)["label"].nunique()
good_keys = set(grp_nuniq[grp_nuniq==2].index)
mask_good = key_all.isin(good_keys)
dropped = int((~mask_good).sum())
if dropped: print(f"[INFO] Dropping {dropped} rows from pure (mass,y) groups before split.")
df_all = df_all.loc[mask_good].reset_index(drop=True)

# Final feature availability
available_features = [c for c in FEATURES_FINAL if c in df_all.columns]
missing = sorted(set(FEATURES_FINAL) - set(available_features))
if missing: print(f"[Note] Missing features ignored: {missing}")

# -----------------------------
# Splits by group (mass,y)
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

# Optional: balance within each (mass,y)
df_tr = balance_per_group(df_tr)
df_va = balance_per_group(df_va)
df_te = balance_per_group(df_te)

# -----------------------------
# Arrays + scaling (fit on TRAIN only)
# -----------------------------
X_tr_raw, y_tr, w_tr = df_to_arrays(df_tr, available_features)
X_va_raw, y_va, w_va = df_to_arrays(df_va, available_features)
X_te_raw, y_te, w_te = df_to_arrays(df_te, available_features)

scaler = StandardScaler()
X_tr = scaler.fit_transform(X_tr_raw).astype(np.float32)
X_va = scaler.transform(X_va_raw).astype(np.float32)
X_te = scaler.transform(X_te_raw).astype(np.float32)

# -----------------------------
# Model + training (10 epochs, no checkpoints)
# -----------------------------
class ParameterizedDNN(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d,128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128,64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64,32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32,1)
        )
    def forward(self, x): return self.net(x)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Device: {device}")
model = ParameterizedDNN(X_tr.shape[1]).to(device)

criterion = nn.BCEWithLogitsLoss(reduction='none')
optimizer = Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

class ArrayDataset(Dataset):
    def __init__(self, X, y, w): self.X=X; self.y=y; self.w=w
    def __len__(self): return len(self.X)
    def __getitem__(self, i):
        return (torch.tensor(self.X[i], dtype=torch.float32),
                torch.tensor(self.y[i], dtype=torch.float32),
                torch.tensor(self.w[i], dtype=torch.float32))

train_loader = DataLoader(ArrayDataset(X_tr, y_tr, w_tr),
                          batch_size=BATCH_SIZE_TRAIN, shuffle=True,
                          pin_memory=(device.type=="cuda"),
                          num_workers=2 if os.name!="nt" else 0)

@torch.no_grad()
def predict_batched(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP):
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
        return predict_batched(model, X_tensor, device, batch=EVAL_BATCH, use_amp=USE_AMP)
    except RuntimeError as e:
        if CPU_FALLBACK_ON_OOM and "CUDA out of memory" in str(e):
            print("[WARN] CUDA OOM → falling back to CPU (batched).")
            cpu = torch.device("cpu")
            cpu_model = model.to(cpu)
            X_cpu = X_tensor.to(cpu)
            return predict_batched(cpu_model, X_cpu, cpu, batch=max(8192, EVAL_BATCH), use_amp=False)
        raise

X_va_t = torch.tensor(X_va, dtype=torch.float32).to(device)
X_te_t = torch.tensor(X_te, dtype=torch.float32).to(device)

def _weighted_auc(y, p, w=None):
    return roc_auc_score(y, p, sample_weight=(w if w is not None else None))

use_amp_scaler = (device.type == "cuda")
scaler_amp = torch.amp.GradScaler("cuda", enabled=use_amp_scaler) if use_amp_scaler else torch.amp.GradScaler(enabled=False)

for epoch in range(N_EPOCHS):
    model.train()
    tot_loss, nseen = 0.0, 0
    for xb, yb, wb in train_loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        wb = wb.to(device, non_blocking=True)
        wb = torch.clamp(wb / (wb.mean() + 1e-8), max=WEIGHT_CLIP)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=USE_AMP and use_amp_scaler):
            logits = model(xb).view(-1)
            per_loss = criterion(logits, yb)
            loss = (per_loss * wb).mean()
        scaler_amp.scale(loss).backward()
        scaler_amp.step(optimizer)
        scaler_amp.update()

        bs = xb.size(0)
        tot_loss += float(loss.item()) * bs
        nseen += bs

    val_probs = safe_eval_probs(model, X_va_t, device)
    val_auc  = _weighted_auc(y_va, val_probs, w_va)
    val_acc  = accuracy_score(y_va, (val_probs > 0.5).astype(int))
    print(f"[Epoch {epoch+1:02d}/{N_EPOCHS}] TrainLoss={tot_loss/max(nseen,1):.4f} | ValAUC={val_auc:.4f} | ValAcc={val_acc:.4f}")

# -----------------------------
# Feature Importance
# -----------------------------
# Choose split to report (VAL or TEST)
SPLIT = "TEST"
if SPLIT == "VAL":
    X_imp, y_imp, w_imp = X_va, y_va, w_va
    df_split = df_va
    X_imp_t = X_va_t
    split_name = "VAL"
else:
    X_imp, y_imp, w_imp = X_te, y_te, w_te
    df_split = df_te
    X_imp_t = X_te_t
    split_name = "TEST"

INCLUDE_MASS_Y = True   # set False to exclude ("mass","y_value") from ranking
feat_names_imp = [f for f in available_features if INCLUDE_MASS_Y or f not in ("mass","y_value")]
name_to_idx = {f:i for i,f in enumerate(available_features)}

# Group codes for within-(mass,y) shuffles
group_codes = pd.factorize(
    df_split['mass'].astype(int).astype(str) + "_" + df_split['y_value'].astype(int).astype(str)
)[0]

def _groupwise_shuffle_inplace(X_block, group_codes, col, rng):
    for g in np.unique(group_codes):
        idx = (group_codes == g)
        vals = X_block[idx, col].copy()
        rng.shuffle(vals)
        X_block[idx, col] = vals

# Baseline AUC
base_probs = safe_eval_probs(model, X_imp_t, device)
base_auc = _weighted_auc(y_imp, base_probs, w_imp)
print(f"\n[FI] Baseline {split_name} AUC = {base_auc:.4f}")

# Permutation importance (AUC drop)
N_REPEATS = 5
rng = np.random.default_rng(SEED)
from collections import defaultdict
drops = defaultdict(list)

for fname in feat_names_imp:
    j = name_to_idx[fname]
    for _ in range(N_REPEATS):
        Xp = X_imp.copy()
        _groupwise_shuffle_inplace(Xp, group_codes, j, rng)
        Xp_t = torch.tensor(Xp, dtype=torch.float32).to(device)
        probs_p = safe_eval_probs(model, Xp_t, device)
        auc_p = _weighted_auc(y_imp, probs_p, w_imp)
        drops[fname].append(base_auc - auc_p)

perm_mean = {f: float(np.mean(v)) for f, v in drops.items()}
perm_std  = {f: float(np.std(v, ddof=1)) for f, v in drops.items()}

# Input-gradient saliency (convert to RAW space via 1/std)
model.eval()
inv_scale_full = 1.0 / scaler.scale_.astype(np.float64)
grads_accum = np.zeros(X_imp.shape[1], dtype=np.float64)
ptr, B = 0, 4096
n_chunks = 0
while ptr < X_imp.shape[0]:
    xb = torch.tensor(X_imp[ptr:ptr+B], dtype=torch.float32, device=device, requires_grad=True)
    logits = model(xb).view(-1)
    logits.sum().backward()
    g = xb.grad.detach().abs().mean(dim=0).double().cpu().numpy()
    grads_accum += g
    ptr += B
    n_chunks += 1
    model.zero_grad(set_to_none=True)

grads_raw = (grads_accum / max(1, n_chunks)) * inv_scale_full
sal = {f: float(grads_raw[name_to_idx[f]]) for f in feat_names_imp}
mmax = max(sal.values()) if sal else 1.0
sal_norm = {k: (v/mmax if mmax>0 else 0.0) for k,v in sal.items()}

# Print top-20
top_perm = sorted(perm_mean.items(), key=lambda t: t[1], reverse=True)[:20]
top_grad = sorted(sal_norm.items(),  key=lambda t: t[1], reverse=True)[:20]

print("\n[Permutation AUC drop — top 20]")
for k,v in top_perm:
    print(f"{k:28s} {v: .6f} (±{perm_std.get(k,0.0):.6f})")

print("\n[Gradient saliency (normalized) — top 20]")
for k,v in top_grad:
    print(f"{k:28s} {v: .6f}")

# -----------------------------
# Save tables + plots (robust; always build df_imp)
# -----------------------------
import matplotlib
matplotlib.use("Agg")  # allow plotting without X server
import matplotlib.pyplot as plt

os.makedirs(OUTDIR, exist_ok=True)

# Build unified importance table (always)
all_feats = list(sorted(set(feat_names_imp)))
df_imp = pd.DataFrame({
    "feature": all_feats,
    "perm_mean_auc_drop": [perm_mean.get(f, np.nan) for f in all_feats],
    "perm_std_auc_drop":  [perm_std.get(f,  np.nan) for f in all_feats],
    "grad_saliency_norm": [sal_norm.get(f,  np.nan) for f in all_feats],
})
df_imp = df_imp.sort_values(
    ["perm_mean_auc_drop", "grad_saliency_norm"],
    ascending=[False, False],
    na_position="last"
).reset_index(drop=True)

# Optional: write CSV/JSON
if SAVE_OUTPUTS:
    csv_path  = os.path.join(OUTDIR, f"feature_importance_{split_name.lower()}.csv")
    json_path = os.path.join(OUTDIR, f"feature_importance_{split_name.lower()}.json")
    df_imp.to_csv(csv_path, index=False)
    with open(json_path, "w") as f:
        json.dump({
            "split": split_name,
            "baseline_auc": float(base_auc),
            "permutation_importance": perm_mean,
            "permutation_importance_std": perm_std,
            "gradient_saliency_normalized": sal_norm,
            "table_order": df_imp["feature"].tolist()
        }, f, indent=2)
    print(f"\n[Saved] {csv_path}\n[Saved] {json_path}")

# --------- Plots (always saved if there is data) ---------
saved_paths = []

# 1) Permutation importance (top 25) with error bars
df_perm = df_imp.dropna(subset=["perm_mean_auc_drop"])
if not df_perm.empty:
    df_perm = df_perm.head(25)
    fig1 = plt.figure(figsize=(8, max(4, 0.35*len(df_perm))))
    plt.barh(
        df_perm["feature"][::-1],
        df_perm["perm_mean_auc_drop"][::-1],
        xerr=df_perm["perm_std_auc_drop"][::-1],
        capsize=3
    )
    plt.xlabel("AUC drop (higher = more important)")
    plt.title(f"Permutation Feature Importance — {split_name} (baseline AUC = {base_auc:.3f})")
    plt.tight_layout()
    perm_png = os.path.join(OUTDIR, f"feature_importance_permutation_{split_name.lower()}.png")
    perm_svg = os.path.join(OUTDIR, f"feature_importance_permutation_{split_name.lower()}.svg")
    plt.savefig(perm_png, dpi=200); saved_paths += [perm_png]
    plt.savefig(perm_svg);           saved_paths += [perm_svg]
    plt.close(fig1)
else:
    print("[INFO] No permutation-importance values to plot (all NaN).")

# 2) Gradient saliency (top 25)
df_grad = df_imp.dropna(subset=["grad_saliency_norm"])
if not df_grad.empty:
    df_grad = df_grad.sort_values("grad_saliency_norm", ascending=False).head(25)
    fig2 = plt.figure(figsize=(8, max(4, 0.35*len(df_grad))))
    plt.barh(
        df_grad["feature"][::-1],
        df_grad["grad_saliency_norm"][::-1]
    )
    plt.xlabel("Normalized saliency (0–1)")
    plt.title(f"Input-Gradient Saliency — {split_name}")
    plt.tight_layout()
    grad_png = os.path.join(OUTDIR, f"feature_importance_gradient_{split_name.lower()}.png")
    grad_svg = os.path.join(OUTDIR, f"feature_importance_gradient_{split_name.lower()}.svg")
    grad_pdf = os.path.join(OUTDIR, f"feature_importance_gradient_{split_name.lower()}.pdf")
    plt.savefig(grad_png, dpi=200); saved_paths += [grad_png]
    plt.savefig(grad_svg);           saved_paths += [grad_svg]
    plt.savefig(grad_pdf);           saved_paths += [grad_pdf]
    plt.close(fig2)
else:
    print("[INFO] No gradient-saliency values to plot (all NaN).")

# Summary of saves
if saved_paths:
    print("[Saved]")
    for p in saved_paths:
        print(" ", p)
else:
    print("[INFO] No plots were saved.")
