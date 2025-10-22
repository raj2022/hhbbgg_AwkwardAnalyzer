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
    ("../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GGJets/preselection"),
    ("../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt20To40/preselection"),
    ("../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt40/preselection"),
]

# Model input features (mass, y_value appended later)
FEATURES_CORE = [
    'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
    'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi',
    'sublead_bjet_eta', 'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB',
    'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
    'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
    'lead_pho_mvaID', 'sublead_pho_mvaID'
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
        file_path = f"../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"
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



# -------------------------------------------------
# 1. CvM Loss Function
# -------------------------------------------------
def cvm_loss(output, mass):
    """Cramer-von Mises loss: penalizes correlation between output and mass."""
    n = len(output)
    sorted_mass_idx = torch.argsort(mass)
    sorted_output = output[sorted_mass_idx]
    ranks = torch.arange(1, n + 1, dtype=torch.float32, device=output.device) / n
    output_cdf = torch.cumsum(sorted_output, dim=0) / (torch.sum(sorted_output) + 1e-6)
    return torch.mean((output_cdf - ranks) ** 2)

# -------------------------------------------------
# 2. Add Mass to Dataset
# -------------------------------------------------
class DecorrelatedDataset(Dataset):
    def __init__(self, X, y, w, mass):
        self.X = X
        self.y = y
        self.w = w
        self.mass = mass

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        x = torch.tensor(self.X[idx], dtype=torch.float32)
        y = torch.tensor(self.y[idx], dtype=torch.float32)
        w = torch.tensor(self.w[idx], dtype=torch.float32)
        m = torch.tensor(self.mass[idx], dtype=torch.float32)
        return x, y, w, m

mass_tr = X_tr[:, FEATURES_FINAL.index("mass")]
train_dataset = DecorrelatedDataset(X_tr, y_tr, w_tr_pre, mass_tr)
train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True, pin_memory=(device.type == "cuda"), num_workers=2)

# -------------------------------------------------
# 3. Training Loop with CvM Loss
# -------------------------------------------------
lambda_cvm = 0.1  # Adjust this value to tune decorrelation strength
history = {"train_loss": [], "val_auc": [], "val_acc": []}
best_auc = -np.inf
best_epoch = 0
max_epochs = 50

for epoch in range(max_epochs):
    model.train()
    epoch_loss = 0.0

    for xb, yb, wb, mb in train_loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        wb = wb.to(device, non_blocking=True)
        mb = mb.to(device, non_blocking=True)

        wb = wb / (wb.mean() + 1e-8)
        wb = torch.clamp(wb, max=10.0)

        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            logits = model(xb).view(-1)
            probs = torch.sigmoid(logits)
            loss_cls = (criterion(logits, yb) * wb).mean()
            loss_cvm = cvm_loss(probs[yb < 0.5], mb[yb < 0.5])  # decorrelate background only
            loss = loss_cls + lambda_cvm * loss_cvm

        scaler_amp.scale(loss).backward()
        scaler_amp.step(optimizer)
        scaler_amp.update()

        epoch_loss += float(loss.item())

    model.eval()
    with torch.no_grad():
        val_logits = model(X_va_tensor).view(-1)
        val_probs  = torch.sigmoid(val_logits).cpu().numpy()
    val_auc = roc_auc_score(y_va, val_probs)
    val_acc = accuracy_score(y_va, (val_probs > 0.5).astype(int))

    history["train_loss"].append(epoch_loss)
    history["val_auc"].append(val_auc)
    history["val_acc"].append(val_acc)

    print(f"Epoch {epoch+1:02d} | Loss: {epoch_loss:.4f} | Val AUC: {val_auc:.4f} | Acc: {val_acc:.4f}")

    if val_auc > best_auc + 1e-4:
        best_auc = val_auc
        best_epoch = epoch
        torch.save(model.state_dict(), "best_pdnn_decorrelated.pt")
        print(f"[INFO] New best model saved at epoch {epoch+1}")
    elif epoch - best_epoch >= patience:
        print(f"[INFO] Early stopping at epoch {epoch+1}")
        break

def plot_mass_vs_score(test_probs, mass_te, y_te, label="", cmap="viridis"):
    plt.figure(figsize=(6.4, 5))
    plt.hist2d(mass_te[y_te == 0], test_probs[y_te == 0], bins=(50, 50), cmap=cmap)
    plt.xlabel("Mass (background only)")
    plt.ylabel("DNN score")
    plt.title(f"Mass Sculpting — {label}")
    plt.colorbar(label="Counts")
    plt.tight_layout()
    plt.show()



# Evaluate vanilla (no CvM)
model.load_state_dict(torch.load("best_pdnn.pt", map_location=device))
model.eval()
with torch.no_grad():
    test_probs_vanilla = torch.sigmoid(model(X_te_tensor).view(-1)).cpu().numpy()

# Evaluate decorrelated
model.load_state_dict(torch.load("best_pdnn_decorrelated.pt", map_location=device))
model.eval()
with torch.no_grad():
    test_probs_cvm = torch.sigmoid(model(X_te_tensor).view(-1)).cpu().numpy()

# Get mass for plotting
mass_te = X_te[:, FEATURES_FINAL.index("mass")]



plot_mass_vs_score(test_probs_vanilla, mass_te, y_te, label="Before CvM (Vanilla PDNN)", cmap="Blues")
plot_mass_vs_score(test_probs_cvm, mass_te, y_te, label="After CvM (Decorrelated PDNN)", cmap="Greens")



def compute_cvm_np(probs, mass):
    from scipy.stats import rankdata
    sorted_idx = np.argsort(mass)
    ranks = np.arange(1, len(probs)+1) / len(probs)
    output_cdf = np.cumsum(probs[sorted_idx]) / np.sum(probs)
    return np.mean((output_cdf - ranks)**2)

cvm_before = compute_cvm_np(test_probs_vanilla[y_te == 0], mass_te[y_te == 0])
cvm_after  = compute_cvm_np(test_probs_cvm[y_te == 0], mass_te[y_te == 0])

print(f"CvM (vanilla):     {cvm_before:.4e}")
print(f"CvM (decorrelated): {cvm_after:.4e}")
