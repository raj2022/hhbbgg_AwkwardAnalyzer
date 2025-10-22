import os
import numpy as np
import pandas as pd
import uproot
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample
from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve, auc

# -----------------------------
# Config
# -----------------------------
SEED = 42
np.random.seed(SEED)

# Torch seeds for reproducibility
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# If you want to keep background smaller for memory, use < 1.0 (e.g., 0.3).
# Set to 1.0 for no pre-reduction.
BACKGROUND_FRAC = 0.3

mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
y_values   = [60, 70, 80, 90, 95, 100, 125, 150, 200]

background_files = [
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GGJets/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt20To40/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt40/preselection"),
]

# Model input features (mass, y_value appended later)
FEATURES_CORE = [
    'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
    'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi',
    'sublead_bjet_eta', 'sublead_bjet_phi',
    # 'sublead_bjet_PNetB', 
    # 'lead_bjet_PNetB',
    'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
    'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
    # 'lead_pho_mvaID',
    # 'sublead_pho_mvaID'
]
FEATURES_FINAL = FEATURES_CORE + ['mass', 'y_value']
WEIGHT_COL = 'weight_preselection'

# -----------------------------
# Helpers
# -----------------------------
def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Downcast float64 to float32 to reduce memory footprint."""
    for c in df.select_dtypes(include=['float64']).columns:
        df[c] = df[c].astype('float32')
    return df

def ensure_weight(df: pd.DataFrame, weight_col=WEIGHT_COL) -> pd.DataFrame:
    if weight_col not in df.columns:
        df[weight_col] = 1.0
    return df

# -----------------------------
# 1) Load SIGNAL (Parquet), per mass/y_value
# -----------------------------
signal_data = []
for mass in mass_points:
    for y in y_values:
        file_path = f"../../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"
        if os.path.exists(file_path):
            try:
                # Read schema once to choose subset of columns
                try:
                    cols_in_file = pd.read_parquet(file_path, columns=None).columns
                    subset_cols = [c for c in (FEATURES_CORE + [WEIGHT_COL]) if c in cols_in_file]
                    df_sig = pd.read_parquet(file_path, columns=subset_cols)
                except Exception:
                    df_sig = pd.read_parquet(file_path)

                # Keep only needed columns
                keep_cols = [c for c in FEATURES_CORE if c in df_sig.columns]
                extras = [WEIGHT_COL] if WEIGHT_COL in df_sig.columns else []
                df_sig = df_sig[keep_cols + extras].copy()

                # Add mass/y/label
                df_sig['mass'] = mass
                df_sig['y_value'] = y
                df_sig['label'] = 1

                # Ensure weight
                df_sig = ensure_weight(df_sig)

                # Downcast to float32
                df_sig = downcast_float_cols(df_sig)

                signal_data.append(df_sig)
            except Exception as e:
                print(f"Warning: Could not read {file_path}. Error: {e}")

signal_df = pd.concat(signal_data, ignore_index=True) if signal_data else pd.DataFrame()

# -----------------------------
# 2) Load BACKGROUND (ROOT/UpROOT)
# -----------------------------
background_data = []
for file_path, tree_name in background_files:
    if not os.path.exists(file_path):
        print(f"Warning: Missing file {file_path}")
        continue
    try:
        with uproot.open(file_path) as f:
            if tree_name not in f:
                print(f"Warning: Tree {tree_name} not found in {file_path}")
                continue
            tree = f[tree_name]

            requested = list(set(FEATURES_CORE + [WEIGHT_COL]))
            df_bkg = tree.arrays(filter_name=requested, library="pd")

            df_bkg = ensure_weight(df_bkg)
            df_bkg['label'] = 0

            keep_cols = [c for c in FEATURES_CORE if c in df_bkg.columns]
            df_bkg = df_bkg[keep_cols + [WEIGHT_COL, 'label']].copy()

            df_bkg = downcast_float_cols(df_bkg)

            background_data.append(df_bkg)
    except Exception as e:
        print(f"Warning: Could not read {file_path} ({tree_name}). Error: {e}")

df_background = pd.concat(background_data, ignore_index=True) if background_data else pd.DataFrame()

# Optionally pre-reduce background for memory
if BACKGROUND_FRAC < 1.0 and not df_background.empty:
    df_background = df_background.sample(frac=BACKGROUND_FRAC, random_state=SEED).reset_index(drop=True)

# -----------------------------
# 3) Match (mass, y_value) for BACKGROUND to SIGNAL distribution
# -----------------------------
if signal_df.empty or df_background.empty:
    raise RuntimeError(f"Empty data: signal_df empty? {signal_df.empty}, df_background empty? {df_background.empty}")

sig_mass_y = signal_df[['mass', 'y_value']].copy()
value_counts = sig_mass_y.value_counts(normalize=True).reset_index()
value_counts.columns = ['mass', 'y_value', 'weight']  # sampling prob

# Sample (mass,y) for each background row, following the signal distribution
sampled_mass_y = value_counts.sample(
    n=len(df_background),
    replace=True,
    weights='weight',
    random_state=SEED
).reset_index(drop=True)

df_background['mass'] = sampled_mass_y['mass'].values
df_background['y_value'] = sampled_mass_y['y_value'].values

# -----------------------------
# 4) Balance by DOWNSAMPLING the majority class
# -----------------------------
n_sig = len(signal_df)
n_bkg = len(df_background)

if n_sig == 0 or n_bkg == 0:
    raise RuntimeError(f"Empty class detected: n_sig={n_sig}, n_bkg={n_bkg}")

if n_sig > n_bkg:
    # Downsample signal to match background
    signal_bal = resample(signal_df, replace=False, n_samples=n_bkg, random_state=SEED)
    background_bal = df_background
    print(f"[Balance] Downsampling signal: {n_sig} → {n_bkg}")
elif n_bkg > n_sig:
    # Downsample background to match signal
    background_bal = resample(df_background, replace=False, n_samples=n_sig, random_state=SEED)
    signal_bal = signal_df
    print(f"[Balance] Downsampling background: {n_bkg} → {n_sig}")
else:
    signal_bal = signal_df
    background_bal = df_background
    print(f"[Balance] Already balanced: n_sig = n_bkg = {n_sig}")

df_combined = pd.concat([signal_bal, background_bal], ignore_index=True)

# -----------------------------
# 5) Prepare arrays, split, scale
# -----------------------------
available_features = [c for c in FEATURES_FINAL if c in df_combined.columns]
missing = sorted(set(FEATURES_FINAL) - set(available_features))
if missing:
    print(f"Note: Missing features (will be ignored): {missing}")

# Impute NaNs with per-column mean, then build X
df_features = df_combined[available_features].copy()
df_features = df_features.fillna(df_features.mean(numeric_only=True))
df_features = downcast_float_cols(df_features)

X = df_features.values
y = df_combined['label'].astype(np.int8).values
w_pre = df_combined[WEIGHT_COL].astype('float32').values

# ---- NEW: Do a train/val/test split (validate early stop on Val AUC)
X_tr, X_te, y_tr, y_te, w_tr_pre, w_te_pre = train_test_split(
    X, y, w_pre, test_size=0.20, random_state=SEED, stratify=y
)
X_tr, X_va, y_tr, y_va, w_tr_pre, w_va_pre = train_test_split(
    X_tr, y_tr, w_tr_pre, test_size=0.20, random_state=SEED, stratify=y_tr
)

# Scale (fit on train only)
scaler = StandardScaler()
X_tr = scaler.fit_transform(X_tr)
X_va = scaler.transform(X_va)
X_te = scaler.transform(X_te)

# Diagnostics
print("\n=== Diagnostics ===")
print("Signal shape (raw):    ", signal_df.shape)
print("Background shape (raw):", df_background.shape)
print("Combined (balanced):   ", df_combined.shape)
print("Class distribution (combined):\n", df_combined['label'].value_counts())
print("\nFeature matrix:")
print("X_tr:", X_tr.shape, " X_va:", X_va.shape, " X_te:", X_te.shape)
print("y_tr:", y_tr.shape, " y_va:", y_va.shape, " y_te:", y_te.shape)

# -------------------------------
# Dataset & DataLoader
# -------------------------------
class LazyDataset(Dataset):
    def __init__(self, X, y, w):
        self.X = X
        self.y = y
        self.w = w

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        x = torch.tensor(self.X[idx], dtype=torch.float32)
        y = torch.tensor(self.y[idx], dtype=torch.float32)
        w = torch.tensor(self.w[idx], dtype=torch.float32)
        return x, y, w

train_dataset = LazyDataset(X_tr, y_tr, w_tr_pre)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {device}")

train_loader = DataLoader(
    train_dataset,
    batch_size=256,
    shuffle=True,
    pin_memory=(device.type == "cuda"),
    num_workers=2 if os.name != "nt" else 0
)

# Keep val/test as tensors for fast evaluation
X_va_tensor = torch.tensor(X_va, dtype=torch.float32).to(device)
y_va_tensor = torch.tensor(y_va, dtype=torch.float32).to(device)

X_te_tensor = torch.tensor(X_te, dtype=torch.float32).to(device)
y_te_tensor = torch.tensor(y_te, dtype=torch.float32).to(device)

# Also keep test weights for plotting/optional metrics
w_te_tensor = torch.tensor(w_te_pre, dtype=torch.float32).to(device)

# -------------------------------
# PDNN
# -------------------------------
# class ParameterizedDNN(nn.Module):
#     def __init__(self, input_dim):
#         super().__init__()
#         self.model = nn.Sequential(
#             nn.Linear(input_dim, 50),
#             nn.ReLU(),
#             nn.BatchNorm1d(50),
#             nn.Dropout(0.3),
#             nn.Linear(50, 50),
#             nn.ReLU(),
#             nn.BatchNorm1d(8),
#             nn.Dropout(0.3),
#             nn.Linear(8, 1)
#         )

#     def forward(self, x):
#         return self.model(x)

import torch
import torch.nn as nn

class ParameterizedDNN(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 32),   # Linear(N_features, 50)
            nn.BatchNorm1d(32),
            nn.Dropout(0.4),           # Dropout
            nn.ReLU(),                  # ELU
            nn.Linear(32, 16),        # Linear(50, 50)
            nn.BatchNorm1d(16),
            nn.Dropout(0.4),           # Dropout
            nn.ReLU(),                  # ELU
            nn.Linear(16, 8),         # Linear(50, 50)
            nn.BatchNorm1d(8),
            nn.Dropout(0.4),           # Dropout
            nn.ReLU(),                  # ELU
            nn.Linear(8, 1),          # Linear(50, 1)
            nn.Sigmoid()               # Sigmoid
        )

    def forward(self, x):
        return self.model(x)


# -------------------------------
# Train (AMP + early stopping on VAL AUC)
# -------------------------------
use_amp = torch.cuda.is_available()
scaler_amp = torch.cuda.amp.GradScaler(enabled=use_amp)

model = ParameterizedDNN(X_tr.shape[1]).to(device)
if hasattr(torch, "compile"):
    try:
        model = torch.compile(model)
    except Exception:
        pass

# BCE with logits; we use per-event weights explicitly (normalized per batch)
criterion = nn.BCEWithLogitsLoss(reduction='none')
optimizer = Adam(model.parameters(), lr=0.001)

history = {"train_loss": [], "val_auc": [], "val_acc": []}
best_auc = -np.inf
best_epoch = 0
patience = 20
max_epochs = 100


for epoch in range(max_epochs):
    model.train()
    epoch_loss = 0.0

    for xb, yb, wb in train_loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        wb = wb.to(device, non_blocking=True)

        # ---- FIX: normalize and optionally clip event weights to stabilize training
        wb = wb / (wb.mean() + 1e-8)
        wb = torch.clamp(wb, max=10.0)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(xb).view(-1)
            per_event_loss = criterion(logits, yb)          # [B]
            weighted_loss = (per_event_loss * wb).mean()    # scalar

        scaler_amp.scale(weighted_loss).backward()
        scaler_amp.step(optimizer)
        scaler_amp.update()

        epoch_loss += float(weighted_loss.item())

    # ---- Validation metrics
    model.eval()
    with torch.no_grad():
        val_logits = model(X_va_tensor).view(-1)
        val_probs  = torch.sigmoid(val_logits).cpu().numpy()
    val_auc = roc_auc_score(y_va, val_probs)
    val_acc = accuracy_score(y_va, (val_probs > 0.5).astype(int))

    history["train_loss"].append(epoch_loss)
    history["val_auc"].append(val_auc)
    history["val_acc"].append(val_acc)

    print(f"Epoch {epoch+1:02d} | TrainLoss: {epoch_loss:.4f} | ValAUC: {val_auc:.4f} | ValAcc: {val_acc:.4f}", flush=True)

    if val_auc > best_auc + 1e-4:
        best_auc = val_auc
        best_epoch = epoch
        torch.save(model.state_dict(), "best_pdnn.pt")
        print(f"[INFO] New best ValAUC: {best_auc:.4f} — model saved")
    elif epoch - best_epoch >= patience:
        print(f"[INFO] Early stopping at epoch {epoch+1} (no ValAUC improvement for {patience} epochs).")
        break

# -------------------------------
# Evaluation on TEST
# -------------------------------
model.load_state_dict(torch.load("best_pdnn.pt", map_location=device))
model.eval()

with torch.no_grad():
    test_outputs = model(X_te_tensor).view(-1)
    test_probs = torch.sigmoid(test_outputs).cpu().numpy()

y_test_np = y_te
print("\n=== Test diagnostics ===")
unique_labels_all = np.unique(y, return_counts=True)
unique_labels_test = np.unique(y_test_np, return_counts=True)
print("Unique labels in whole set:", unique_labels_all)
print("Unique labels in test set :", unique_labels_test)
print("Any NaNs in test_probs?", np.isnan(test_probs).any())
print("test_probs range:", float(np.min(test_probs)), "→", float(np.max(test_probs)))

# # Masks for plotting
# sig_mask = (y_test_np == 1)
# bkg_mask = (y_test_np == 0)
# print("Test counts -> Signal:", sig_mask.sum(), " Background:", bkg_mask.sum())

with torch.no_grad():
    test_outputs = model(X_te_tensor).view(-1)
    test_probs = torch.sigmoid(test_outputs).cpu().numpy()
    
    
# Masks for plotting
sig_mask = (y_test_np == 1)
bkg_mask = (y_test_np == 0)

# Diagnostics: counts vs total weights
n_sig, n_bkg = int(sig_mask.sum()), int(bkg_mask.sum())
W_sig = float(w_te_pre[sig_mask].sum()) if 'w_te_pre' in globals() else float('nan')
W_bkg = float(w_te_pre[bkg_mask].sum()) if 'w_te_pre' in globals() else float('nan')
print(f"Test counts (unweighted):  S={n_sig}, B={n_bkg}")
print(f"Test total weights:        S={W_sig:.3e}, B={W_bkg:.3e}")


# ---- Robust separation plot (shared bins, step hist, optional weights)
bins = np.linspace(0.0, 1.0, 51)
w_sig = w_te_pre[sig_mask] if 'w_te_pre' in globals() else None
w_bkg = w_te_pre[bkg_mask] if 'w_te_pre' in globals() else None

plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=1.5, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=1.5, label="Background")
plt.xlabel("Model output (probability)")
plt.ylabel("Events")
plt.title("Signal vs Background — Test set")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# ROC + AUC on test
fpr, tpr, _ = roc_curve(y_test_np, test_probs)
roc_auc = auc(fpr, tpr)
print(f"Test AUC: {roc_auc:.6f}")

plt.figure()
plt.plot(fpr, tpr, label=f"ROC Curve (AUC = {roc_auc:.4f})")
plt.plot([0, 1], [0, 1], 'k--', lw=1)
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve — Test set")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Training curves
plt.figure()
plt.plot(history["train_loss"], marker='o')
plt.title("Training Loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

plt.figure()
plt.plot(history["val_acc"], marker='o')
plt.title("Validation Accuracy")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

plt.figure()
plt.plot(history["val_auc"], marker='o')
plt.title("Validation AUC")
plt.xlabel("Epoch")
plt.ylabel("AUC")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()



bins = np.linspace(0.0, 1.0, 51)
w_sig = w_te_pre[sig_mask] if 'w_te_pre' in globals() else None
w_bkg = w_te_pre[bkg_mask] if 'w_te_pre' in globals() else None

# 1) Unweighted shapes (equal number of events)
plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, histtype='step', linewidth=1.5, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, histtype='step', linewidth=1.5, label="Background")
plt.xlabel("Model output (probability)"); plt.ylabel("Events")
plt.title("Signal vs Background — Test (UNWEIGHTED)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()

# 2) Weighted yields (what enters expected event counts)
plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype='step', linewidth=1.5, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype='step', linewidth=1.5, label="Background")
plt.yscale('log')  # important to see small yields
plt.xlabel("Model output (probability)"); plt.ylabel("Weighted events")
plt.title("Signal vs Background — Test (WEIGHTED, log y)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()

# 3) Shape-normalized (weighted densities integrate to 1 each)
plt.figure()
plt.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype='step', linewidth=1.5, label="Signal")
plt.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype='step', linewidth=1.5, label="Background")
plt.xlabel("Model output (probability)"); plt.ylabel("Density")
plt.title("Signal vs Background — Test (WEIGHTED, SHAPE‑NORMALIZED)")
plt.legend(); plt.grid(True, alpha=0.3); plt.tight_layout(); plt.show()


# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---------------------------------------------
# ---- CMS style helpers (matplotlib only) ----
from matplotlib.ticker import AutoMinorLocator

CMS_TEXT  = "Preliminary"          # or "Internal", "" for none
CMS_LUMI  = r"26.7 fb$^{-1}$"
CMS_SQRTS = r"13.6 TeV"

def set_cms_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
        "axes.labelsize": 14,
        "axes.titlesize": 16,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "axes.linewidth": 1.2,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "grid.alpha": 0.15,
        "figure.figsize": (6.4, 4.8),
    })

def cms_label(ax, text=CMS_TEXT, lumi=CMS_LUMI, sqrt_s=CMS_SQRTS):
    # Left: CMS [text]
    ax.text(0.02, 0.98, "CMS", transform=ax.transAxes,
            fontsize=18, fontweight="bold", va="top", ha="left")
    if text:
        ax.text(0.12, 0.98, text, transform=ax.transAxes,
                fontsize=14, style="italic", va="top", ha="left")
    # Right: lumi and sqrt(s)
    ax.text(0.98, 0.98, rf"{lumi}  ($\sqrt{{s}}$ = {sqrt_s})", transform=ax.transAxes,
            fontsize=12, va="top", ha="right")

def _finish_axes(ax, xlabel, ylabel, title=None, logy=False, square=False, legend_loc="best"):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if logy:
        ax.set_yscale("log")
    if square:
        ax.set_aspect("equal", adjustable="box")
    ax.grid(True)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.legend(frameon=False, loc=legend_loc)
    cms_label(ax)
set_cms_style()

bins = np.linspace(0.0, 1.0, 51)
w_sig = w_te_pre[sig_mask] if 'w_te_pre' in globals() else None
w_bkg = w_te_pre[bkg_mask] if 'w_te_pre' in globals() else None

# 1) UNWEIGHTED (shape only)
fig, ax = plt.subplots()
ax.hist(test_probs[sig_mask], bins=bins, histtype="step", linewidth=1.6, label="Signal")
ax.hist(test_probs[bkg_mask], bins=bins, histtype="step", linewidth=1.6, label="Background")
_finish_axes(ax,
             xlabel="DNN output",
             ylabel="Events",
             title="Signal vs Background — Test (Unweighted)")
fig.tight_layout()
plt.show()
# fig.savefig("dnn_sep_unweighted_cms.pdf")

# 2) WEIGHTED yields (log‑y)
fig, ax = plt.subplots()
ax.hist(test_probs[sig_mask], bins=bins, weights=w_sig, histtype="step", linewidth=1.6, label="Signal")
ax.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, histtype="step", linewidth=1.6, label="Background")
_finish_axes(ax,
             xlabel="DNN output",
             ylabel="Weighted events",
             title="Signal vs Background — Test (Weighted)",
             logy=True)
fig.tight_layout()
plt.show()
# fig.savefig("dnn_sep_weighted_logy_cms.pdf")

# 3) WEIGHTED & SHAPE‑NORMALIZED (densities integrate to 1)
fig, ax = plt.subplots()
ax.hist(test_probs[sig_mask], bins=bins, weights=w_sig, density=True, histtype="step", linewidth=1.6, label="Signal")
ax.hist(test_probs[bkg_mask], bins=bins, weights=w_bkg, density=True, histtype="step", linewidth=1.6, label="Background")
_finish_axes(ax,
             xlabel="DNN output",
             ylabel="Density",
             title="Signal vs Background — Test (Weighted, normalized)")
fig.tight_layout()
plt.show()
# fig.savefig("dnn_sep_weighted_density_cms.pdf")
fpr, tpr, _ = roc_curve(y_test_np, test_probs)
roc_auc = auc(fpr, tpr)
print(f"Test AUC: {roc_auc:.6f}")

set_cms_style()
fig, ax = plt.subplots()
ax.plot(fpr, tpr, linewidth=2.0, label=rf"AUC = {roc_auc:.4f}")
ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1.0)
_finish_axes(ax,
             xlabel="False positive rate",
             ylabel="True positive rate",
             title="ROC — Test set",
             square=True,
             legend_loc="lower right")
fig.tight_layout()
plt.show()
# fig.savefig("roc_test_cms.pdf")


##########

print(" Starting to perform test")
print("Train/Test sizes:", len(y_tr), len(y_va), len(y_te))
print("Class balance test:", np.unique(y_te, return_counts=True))
for feat in ["mass", "y_value"]:
    print(feat, "train mean:", X_tr[:, available_features.index(feat)].mean(),
                "test mean:", X_te[:, available_features.index(feat)].mean())


cols = [available_features.index('mass'), available_features.index('y_value')]
print("AUC mass,y only:", roc_auc_score(y_te, 0.5*X_te[:,cols[0]] + 0.5*X_te[:,cols[1]]))



import hashlib
def hash_row(arr): return hashlib.md5(arr.tobytes()).hexdigest()
tr_hash = set(map(hash_row, X_tr.astype(np.float32)))
te_hash = set(map(hash_row, X_te.astype(np.float32)))
print("overlap?", len(tr_hash & te_hash))



from sklearn.metrics import roc_auc_score
aucs = []
for i, f in enumerate(available_features):
    a = roc_auc_score(y_te, X_te[:, i])
    aucs.append((f, a))
for f,a in sorted(aucs, key=lambda x: -abs(x[1]-0.5)):
    print(f"{f:25s} AUC={a:.4f}")




# ==== MASS–SCORE CORRELATION DIAGNOSTICS ====
from scipy.stats import pearsonr, spearmanr
import numpy as np
import matplotlib.pyplot as plt

# 1) Recover "mass" in the test set (unscaled, human-readable)
i_mass = available_features.index("mass")

# If you want *unscaled* mass and you still have the scaler:
# Rebuild an array with test rows and inverse-transform only the mass column.
# (Safer than rescaling by hand in case of with-mean/with-std config.)
X_te_full_inv = scaler.inverse_transform(X_te)
mass_te = X_te_full_inv[:, i_mass]

# 2) Correlations of mass vs model score (S / B separately)
s_mass = mass_te[sig_mask]
b_mass = mass_te[bkg_mask]
s_score = test_probs[sig_mask]
b_score = test_probs[bkg_mask]

def corr_str(x, y):
    # Guard against constant arrays
    if np.allclose(np.std(x), 0) or np.allclose(np.std(y), 0):
        return "pearson: nan, spearman: nan"
    pr = pearsonr(x, y)[0]
    sr = spearmanr(x, y)[0]
    return f"pearson: {pr:+.4f}, spearman: {sr:+.4f}"

print("\n[MASS–SCORE correlations]")
print("Signal :", corr_str(s_mass, s_score))
print("Bkg    :", corr_str(b_mass, b_score))

# 3) Per-mass AUC (S/B separation *within* each exact mass value)
# If mass is continuous (not exact integers), bin first (see 4b below).
unique_masses = np.unique(mass_te.astype(int))  # masses are integers in your setup
mass_auc = []
for m in unique_masses:
    m_mask = (mass_te.astype(int) == m)
    if m_mask.sum() < 50:
        continue
    y_m = y_test_np[m_mask]
    p_m = test_probs[m_mask]
    # need both classes present
    if len(np.unique(y_m)) < 2:
        continue
    mass_auc.append((m, roc_auc_score(y_m, p_m)))
print("\nPer-mass AUC:")
for m, a in mass_auc:
    print(f"  m={m:4d}  AUC={a:.4f}")

# 4a) Mean score vs mass (points at true masses)
def binned_mean_std(x, y, bins):
    idx = np.digitize(x, bins) - 1
    centers = 0.5*(bins[1:] + bins[:-1])
    mu = np.full(len(centers), np.nan, dtype=float)
    sd = np.full(len(centers), np.nan, dtype=float)
    for i in range(len(centers)):
        sel = idx == i
        if sel.any():
            mu[i] = y[sel].mean()
            sd[i] = y[sel].std()
    return centers, mu, sd

bins_m = np.arange(min(unique_masses)-50, max(unique_masses)+51, 50)  # 50 GeV bins
cS, muS, sdS = binned_mean_std(s_mass, s_score, bins_m)
cB, muB, sdB = binned_mean_std(b_mass, b_score, bins_m)

plt.figure()
plt.errorbar(cS, muS, yerr=sdS, fmt="o-", label="Signal", capsize=2)
plt.errorbar(cB, muB, yerr=sdB, fmt="s-", label="Background", capsize=2)
plt.xlabel("mass [GeV]")
plt.ylabel("Mean DNN score")
plt.title("Mean DNN score vs mass (±1σ)")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()

# 4b) If you want *weighted* mean score vs mass (using test weights)
have_w = ("w_te_pre" in globals()) and (w_te_pre is not None) and np.isfinite(w_te_pre).all()
if have_w:
    ws = w_te_pre[sig_mask]
    wb = w_te_pre[bkg_mask]
    def w_binned_mean(x, y, w, bins):
        idx = np.digitize(x, bins) - 1
        centers = 0.5*(bins[1:] + bins[:-1])
        mu = np.full(len(centers), np.nan, dtype=float)
        # weighted std (sqrt of weighted variance)
        sd = np.full(len(centers), np.nan, dtype=float)
        for i in range(len(centers)):
            sel = idx == i
            if sel.any():
                ww = w[sel]
                yy = y[sel]
                ww = ww / (np.sum(ww) + 1e-12)
                m = np.sum(ww * yy)
                v = np.sum(ww * (yy - m)**2)
                mu[i] = m
                sd[i] = np.sqrt(v)
        return centers, mu, sd
    cSw, muSw, sdSw = w_binned_mean(s_mass, s_score, ws, bins_m)
    cBw, muBw, sdBw = w_binned_mean(b_mass, b_score, wb, bins_m)

    plt.figure()
    plt.errorbar(cSw, muSw, yerr=sdSw, fmt="o-", label="Signal (wgt)", capsize=2)
    plt.errorbar(cBw, muBw, yerr=sdBw, fmt="s-", label="Background (wgt)", capsize=2)
    plt.xlabel("mass [GeV]")
    plt.ylabel("Weighted mean DNN score")
    plt.title("Weighted mean DNN score vs mass (±1σ_w)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

# 5) 2D hexbin (mass vs score) to see structure (S and B)
gridsize = 40
fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True)
hb1 = axs[0].hexbin(s_mass, s_score, gridsize=gridsize, bins='log')
axs[0].set_title("Signal")
axs[0].set_xlabel("mass [GeV]")
axs[0].set_ylabel("DNN score")
fig.colorbar(hb1, ax=axs[0], label="log10(count)")

hb2 = axs[1].hexbin(b_mass, b_score, gridsize=gridsize, bins='log')
axs[1].set_title("Background")
axs[1].set_xlabel("mass [GeV]")
fig.colorbar(hb2, ax=axs[1], label="log10(count)")

plt.suptitle("Mass vs DNN score (hexbin)")
plt.tight_layout()
plt.show()
# ==== END MASS–SCORE CORRELATION ====




# Variable correlation

# ============================
# Variable correlation checks
# ============================
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl


# --- Helpers ---
def weighted_corr_matrix(X, w):
    """Return weighted Pearson correlation matrix for columns in X."""
    X = np.asarray(X, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64).reshape(-1, 1)
    w = w / (w.sum() + 1e-12)

    mu = (w * X).sum(axis=0, keepdims=True)           # weighted mean
    Xc = X - mu
    # finite-sample corrected weighted covariance
    eff_n = 1.0 / np.sum(w**2)                        # Kish effective sample size
    cov = (w * Xc).T @ Xc * (eff_n / (eff_n - 1.0) if eff_n > 1 else 1.0)

    sd = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
    corr = cov / (sd[:, None] * sd[None, :])
    return corr

def spearman_corr_matrix(X):
    """Unweighted Spearman correlation matrix (rank-based)."""
    X = np.asarray(X)
    # rank per column (average rank for ties)
    ranks = np.vstack([pd.Series(col).rank(method="average").values for col in X.T]).T
    return np.corrcoef(ranks, rowvar=False)

# def plot_corr_heatmap(corr, labels, title="Correlation matrix"):
#     fig, ax = plt.subplots(figsize=(max(6, 0.4*len(labels)), max(5, 0.35*len(labels))))
#     im = ax.imshow(corr, vmin=-1, vmax=1)
#     ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
#     ax.set_xticklabels(labels, rotation=90)
#     ax.set_yticklabels(labels)
#     ax.set_title(title)
#     ax.grid(False)
#     cbar = plt.colorbar(im, ax=ax)
#     cbar.set_label("Correlation")
#     fig.tight_layout()
#     plt.show()
def plot_corr_heatmap(corr, labels, title="Correlation matrix", fname=None):
    fig, ax = plt.subplots(figsize=(max(6, 0.4*len(labels)), max(5, 0.35*len(labels))))
    
    # Custom CMS-style diverging colormap (blue ↔ white ↔ red)
    cmap = mpl.cm.get_cmap("RdBu_r")  # already blue/red centered
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap=cmap)
    
    ax.set_xticks(range(len(labels))); ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=10, color="#003366")
    ax.set_yticklabels(labels, fontsize=10, color="#003366")
    ax.set_title(title, fontsize=14, color="#003366", weight="bold")
    
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Correlation", color="#003366", fontsize=12)
    cbar.ax.tick_params(labelsize=10, colors="#003366")
    
    # Grid lines faint grey
    ax.grid(False)
    fig.patch.set_facecolor("#f7fbff")  # light blue background
    fig.tight_layout()
    
    if fname:
        fig.savefig(fname, dpi=200, bbox_inches="tight")
    plt.show()

# --- Work on TEST set (raw/unscaled values) ---
# recover raw (unscaled) features on test for interpretability
X_te_raw = scaler.inverse_transform(X_te)
df_te = pd.DataFrame(X_te_raw, columns=available_features)

# Pearson (unweighted)
pearson = df_te.corr(method="pearson").values

# Spearman (unweighted, rank-based)
spearman = spearman_corr_matrix(df_te.values)

# Weighted Pearson using test weights (if available)
if ('w_te_pre' in globals()) and (w_te_pre is not None) and np.isfinite(w_te_pre).all():
    wpearson = weighted_corr_matrix(df_te.values, w_te_pre)
else:
    wpearson = None

# --- Plot heatmaps ---
plot_corr_heatmap(pearson, available_features, "Pearson correlation (test, unweighted)")
plot_corr_heatmap(spearman, available_features, "Spearman correlation (test, unweighted)")
if wpearson is not None:
    plot_corr_heatmap(wpearson, available_features, "Pearson correlation (test, weighted)")

# --- Correlation of each feature with LABEL (point-biserial = Pearson w/ binary) ---
# (Using test set for consistency with your other diagnostics)
feat_vs_label = []
for i, f in enumerate(available_features):
    x = df_te[f].values
    # standard Pearson with binary y equals point-biserial
    r = np.corrcoef(x, y_te)[0,1]
    feat_vs_label.append((f, r))
print("\nFeature ↔ label correlation (Pearson / point-biserial) [test]:")
for f, r in sorted(feat_vs_label, key=lambda t: -abs(t[1])):
    print(f"{f:25s} r={r:+.4f}")

# --- Correlation of each feature with MODEL SCORE (on test) ---
feat_vs_score = []
for i, f in enumerate(available_features):
    x = df_te[f].values
    r_p = np.corrcoef(x, test_probs)[0,1]                 # Pearson
    # Spearman (rank) per feature vs score
    x_rank = pd.Series(x).rank(method="average").values
    s_rank = pd.Series(test_probs).rank(method="average").values
    r_s = np.corrcoef(x_rank, s_rank)[0,1]
    feat_vs_score.append((f, r_p, r_s))

print("\nFeature ↔ model-score correlation (test):")
for f, rp, rs in sorted(feat_vs_score, key=lambda t: -max(abs(t[1]), abs(t[2]))):
    print(f"{f:25s} Pearson={rp:+.4f}  Spearman={rs:+.4f}")

# --- Optional: Weighted feature ↔ score correlation (Pearson) ---
if ('w_te_pre' in globals()) and (w_te_pre is not None) and np.isfinite(w_te_pre).all():
    def wcorr_1d(x, y, w):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        w = np.asarray(w, dtype=np.float64)
        w = w / (w.sum() + 1e-12)
        mx = (w * x).sum(); my = (w * y).sum()
        xc = x - mx; yc = y - my
        cov = (w * xc * yc).sum()
        sx = np.sqrt(np.clip((w * xc * xc).sum(), 1e-12, None))
        sy = np.sqrt(np.clip((w * yc * yc).sum(), 1e-12, None))
        return cov / (sx * sy)

    feat_vs_score_w = []
    for f in available_features:
        feat_vs_score_w.append((f, wcorr_1d(df_te[f].values, test_probs, w_te_pre)))
    print("\nFeature ↔ model-score correlation (test, weighted Pearson):")
    for f, rw in sorted(feat_vs_score_w, key=lambda t: -abs(t[1])):
        print(f"{f:25s} r_w={rw:+.4f}")

# --- Multicollinearity quick check (Variance Inflation Factor, unweighted) ---
try:
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    import statsmodels.api as sm
    X_for_vif = pd.DataFrame(
        # standardize columns to similar scale for numerical stability
        (df_te.values - df_te.values.mean(axis=0)) / (df_te.values.std(axis=0) + 1e-12),
        columns=available_features
    )
    vif_vals = [(col, variance_inflation_factor(X_for_vif.values, i)) for i, col in enumerate(X_for_vif.columns)]
    print("\nVariance Inflation Factor (VIF) — higher means more multicollinearity:")
    for col, vif in sorted(vif_vals, key=lambda t: -t[1]):
        print(f"{col:25s} VIF={vif:8.3f}")
except Exception as e:
    print("\n[VIF] Skipped (statsmodels not available):", e)


print("==================================================================")
print("Finished Scripts")
print("==================================================================")