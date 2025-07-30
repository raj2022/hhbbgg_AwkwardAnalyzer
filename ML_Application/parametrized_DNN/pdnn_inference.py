# import os
# import numpy as np
# import pandas as pd
# import uproot
# import matplotlib.pyplot as plt

# import torch
# import torch.nn as nn
# from torch.utils.data import Dataset, DataLoader
# from torch.optim import Adam

# from sklearn.model_selection import train_test_split
# from sklearn.preprocessing import StandardScaler
# from sklearn.utils import resample
# from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve, auc

# # -----------------------------
# # Config
# # -----------------------------
# SEED = 42
# np.random.seed(SEED)

# # If you want to keep background smaller for memory, use < 1.0 (e.g., 0.3).
# # Set to 1.0 for no pre-reduction.
# BACKGROUND_FRAC = 0.3

# mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
# y_values   = [60, 70, 80, 90, 95, 100, 125, 150, 200]

# background_files = [
#     ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GGJets/preselection"),
#     ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt20To40/preselection"),
#     ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt40/preselection"),
# ]

# # Model input features (mass, y_value appended later)
# FEATURES_CORE = [
#     'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
#     'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
#     'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi',
#     'sublead_bjet_eta', 'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB',
#     'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
#     'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
#     'lead_pho_mvaID', 'sublead_pho_mvaID'
# ]
# FEATURES_FINAL = FEATURES_CORE + ['mass', 'y_value']
# WEIGHT_COL = 'weight_preselection'

# # -----------------------------
# # Helpers
# # -----------------------------
# def downcast_float_cols(df: pd.DataFrame) -> pd.DataFrame:
#     """Downcast float64 to float32 to reduce memory footprint."""
#     for c in df.select_dtypes(include=['float64']).columns:
#         df[c] = df[c].astype('float32')
#     return df

# def ensure_weight(df: pd.DataFrame, weight_col=WEIGHT_COL) -> pd.DataFrame:
#     if weight_col not in df.columns:
#         df[weight_col] = 1.0
#     return df

# # -----------------------------
# # 1) Load SIGNAL (Parquet), per mass/y_value
# # -----------------------------
# signal_data = []
# for mass in mass_points:
#     for y in y_values:
#         file_path = f"../../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"
#         if os.path.exists(file_path):
#             try:
#                 # Read only needed columns if available for memory safety
#                 try:
#                     df_sig = pd.read_parquet(file_path, columns=[c for c in (FEATURES_CORE + [WEIGHT_COL]) if c in pd.read_parquet(file_path, columns=None).columns])
#                 except Exception:
#                     # Fallback: read full file if schema probing fails
#                     df_sig = pd.read_parquet(file_path)

#                 # Keep only features we need (if present)
#                 keep_cols = [c for c in FEATURES_CORE if c in df_sig.columns]
#                 extras = [WEIGHT_COL] if WEIGHT_COL in df_sig.columns else []
#                 df_sig = df_sig[keep_cols + extras].copy()

#                 # Add mass/y/label
#                 df_sig['mass'] = mass
#                 df_sig['y_value'] = y
#                 df_sig['label'] = 1

#                 # Ensure weight
#                 df_sig = ensure_weight(df_sig)

#                 # Downcast to float32
#                 df_sig = downcast_float_cols(df_sig)

#                 signal_data.append(df_sig)
#             except Exception as e:
#                 print(f"Warning: Could not read {file_path}. Error: {e}")

# signal_df = pd.concat(signal_data, ignore_index=True) if signal_data else pd.DataFrame()

# # -----------------------------
# # 2) Load BACKGROUND (ROOT/UpROOT)
# # -----------------------------
# background_data = []
# for file_path, tree_name in background_files:
#     if not os.path.exists(file_path):
#         print(f"Warning: Missing file {file_path}")
#         continue
#     try:
#         with uproot.open(file_path) as f:
#             if tree_name not in f:
#                 print(f"Warning: Tree {tree_name} not found in {file_path}")
#                 continue
#             tree = f[tree_name]

#             # Ask for only columns we might use
#             # Build a filter list from FEATURES_CORE + weight column (some may not exist in ROOT)
#             requested = list(set(FEATURES_CORE + [WEIGHT_COL]))
#             # uproot uses filter_name with wildcards usually; here try exact matches:
#             df_bkg = tree.arrays(filter_name=requested, library="pd")

#             # Ensure weight, label
#             df_bkg = ensure_weight(df_bkg)
#             df_bkg['label'] = 0

#             # Keep only requested feature columns we actually got
#             keep_cols = [c for c in FEATURES_CORE if c in df_bkg.columns]
#             df_bkg = df_bkg[keep_cols + [WEIGHT_COL, 'label']].copy()

#             # Downcast
#             df_bkg = downcast_float_cols(df_bkg)

#             background_data.append(df_bkg)
#     except Exception as e:
#         print(f"Warning: Could not read {file_path} ({tree_name}). Error: {e}")

# df_background = pd.concat(background_data, ignore_index=True) if background_data else pd.DataFrame()

# # Optionally pre-reduce background for memory
# if BACKGROUND_FRAC < 1.0 and not df_background.empty:
#     df_background = df_background.sample(frac=BACKGROUND_FRAC, random_state=SEED).reset_index(drop=True)

# # -----------------------------
# # 3) Match (mass, y_value) for BACKGROUND to SIGNAL distribution
# # -----------------------------
# if signal_df.empty or df_background.empty:
#     raise RuntimeError(f"Empty data: signal_df empty? {signal_df.empty}, df_background empty? {df_background.empty}")

# sig_mass_y = signal_df[['mass', 'y_value']].copy()
# value_counts = sig_mass_y.value_counts(normalize=True).reset_index()
# value_counts.columns = ['mass', 'y_value', 'weight']  # weight here is the sampling prob

# # Sample (mass,y) for each background row, following the signal distribution
# sampled_mass_y = value_counts.sample(
#     n=len(df_background),
#     replace=True,
#     weights='weight',
#     random_state=SEED
# ).reset_index(drop=True)

# df_background['mass'] = sampled_mass_y['mass'].values
# df_background['y_value'] = sampled_mass_y['y_value'].values

# # -----------------------------
# # 4) Balance by DOWNSAMPLING the majority class
# # -----------------------------
# n_sig = len(signal_df)
# n_bkg = len(df_background)

# if n_sig == 0 or n_bkg == 0:
#     raise RuntimeError(f"Empty class detected: n_sig={n_sig}, n_bkg={n_bkg}")

# if n_sig > n_bkg:
#     # Downsample signal to match background
#     signal_bal = resample(signal_df, replace=False, n_samples=n_bkg, random_state=SEED)
#     background_bal = df_background
#     print(f"[Balance] Downsampling signal: {n_sig} → {n_bkg}")
# elif n_bkg > n_sig:
#     # Downsample background to match signal
#     background_bal = resample(df_background, replace=False, n_samples=n_sig, random_state=SEED)
#     signal_bal = signal_df
#     print(f"[Balance] Downsampling background: {n_bkg} → {n_sig}")
# else:
#     signal_bal = signal_df
#     background_bal = df_background
#     print(f"[Balance] Already balanced: n_sig = n_bkg = {n_sig}")

# df_combined = pd.concat([signal_bal, background_bal], ignore_index=True)

# # -----------------------------
# # 5) Prepare arrays, split, scale
# # -----------------------------
# # Keep only features we truly have
# available_features = [c for c in FEATURES_FINAL if c in df_combined.columns]
# missing = sorted(set(FEATURES_FINAL) - set(available_features))
# if missing:
#     print(f"Note: Missing features (will be ignored): {missing}")

# # Impute NaNs with per-column mean, then build X
# df_features = df_combined[available_features].copy()
# df_features = df_features.fillna(df_features.mean(numeric_only=True))

# # Downcast feature matrix again (after impute)
# df_features = downcast_float_cols(df_features)

# X = df_features.values
# y = df_combined['label'].astype(np.int8).values
# w_pre = df_combined[WEIGHT_COL].astype('float32').values

# # Train/test split (stratified)
# X_train, X_test, y_train, y_test, w_pre_train, w_pre_test = train_test_split(
#     X, y, w_pre, test_size=0.2, random_state=SEED, stratify=y
# )

# # Scale features (fit on train only)
# scaler = StandardScaler()
# X_train = scaler.fit_transform(X_train)
# X_test  = scaler.transform(X_test)

# # -----------------------------
# # 6) Diagnostics
# # -----------------------------
# print("\n=== Diagnostics ===")
# print("Signal shape (raw):    ", signal_df.shape)
# print("Background shape (raw):", df_background.shape)
# print("Combined (balanced):   ", df_combined.shape)
# print("Class distribution:\n", df_combined['label'].value_counts())

# print("\nFeature matrix:")
# print("X_train:", X_train.shape, " X_test:", X_test.shape)
# print("y_train:", y_train.shape, " y_test:", y_test.shape)
# print("w_pre_train:", w_pre_train.shape, " w_pre_test:", w_pre_test.shape)


# # -------------------------------
# # Dataset & DataLoader
# # -------------------------------
# class LazyDataset(Dataset):
#     def __init__(self, X, y, w):
#         self.X = X
#         self.y = y
#         self.w = w

#     def __len__(self):
#         return len(self.X)

#     def __getitem__(self, idx):
#         x = torch.tensor(self.X[idx], dtype=torch.float32)
#         y = torch.tensor(self.y[idx], dtype=torch.float32)
#         w = torch.tensor(self.w[idx], dtype=torch.float32)
#         return x, y, w

# # FIX: use w_pre_train (not w_train)
# train_dataset = LazyDataset(X_train, y_train, w_pre_train)

# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"[INFO] Using device: {device}")

# train_loader = DataLoader(
#     train_dataset,
#     batch_size=256,
#     shuffle=True,
#     pin_memory=(device.type == "cuda"),
#     num_workers=2 if os.name != "nt" else 0  # safer on Windows
# )

# # Keep test set in memory for fast evaluation
# X_test_tensor = torch.tensor(X_test, dtype=torch.float32).to(device)
# y_test_tensor = torch.tensor(y_test, dtype=torch.float32).to(device)
# # FIX: use w_pre_test (not w_test); not used later but keep for completeness
# w_test_tensor = torch.tensor(w_pre_test, dtype=torch.float32).to(device)

# # -------------------------------
# # PDNN
# # -------------------------------
# class ParameterizedDNN(nn.Module):
#     def __init__(self, input_dim):
#         super().__init__()
#         self.model = nn.Sequential(
#             nn.Linear(input_dim, 16),
#             nn.ReLU(),
#             nn.BatchNorm1d(16),
#             nn.Dropout(0.3),
#             nn.Linear(16, 8),
#             nn.ReLU(),
#             nn.BatchNorm1d(8),
#             nn.Dropout(0.3),
#             nn.Linear(8, 1)
#         )

#     def forward(self, x):
#         return self.model(x)

# # -------------------------------
# # Train (AMP + early stopping)
# # -------------------------------
# use_amp = torch.cuda.is_available()
# scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

# model = ParameterizedDNN(X_train.shape[1]).to(device)
# if hasattr(torch, "compile"):  # PyTorch 2.x
#     try:
#         model = torch.compile(model)
#     except Exception:
#         pass  # safe fallback

# criterion = nn.BCEWithLogitsLoss(reduction='none')
# optimizer = Adam(model.parameters(), lr=0.001)

# losses, aucs, accs = [], [], []
# best_auc = 0.0
# best_epoch = 0
# patience = 3
# max_epochs = 10
# early_stop = False

# for epoch in range(max_epochs):
#     if early_stop:
#         print(f"[INFO] Early stopping triggered at epoch {epoch}")
#         break

#     model.train()
#     epoch_loss = 0.0
#     y_pred_train, y_true_train = [], []

#     for xb, yb, wb in train_loader:
#         xb = xb.to(device, non_blocking=True)
#         yb = yb.to(device, non_blocking=True)
#         wb = wb.to(device, non_blocking=True)

#         optimizer.zero_grad()
#         with torch.amp.autocast(device_type='cuda', enabled=use_amp):
#             outputs = model(xb).view(-1)
#             loss = criterion(outputs, yb)
#             weighted_loss = (loss * wb).mean()

#         scaler.scale(weighted_loss).backward()
#         scaler.step(optimizer)
#         scaler.update()

#         y_pred_train.append(torch.sigmoid(outputs).detach())
#         y_true_train.append(yb)
#         epoch_loss += float(weighted_loss.item())

#     y_pred_train = torch.cat(y_pred_train).cpu().numpy()
#     y_true_train = torch.cat(y_true_train).cpu().numpy()

#     auc_score = roc_auc_score(y_true_train, y_pred_train)
#     acc_score = accuracy_score(y_true_train, (y_pred_train > 0.5).astype(int))

#     losses.append(epoch_loss)
#     aucs.append(auc_score)
#     accs.append(acc_score)

#     print(f"Epoch {epoch+1:02d} | Loss: {epoch_loss:.4f} | AUC: {auc_score:.4f} | Acc: {acc_score:.4f}", flush=True)

#     if auc_score > best_auc:
#         best_auc = auc_score
#         best_epoch = epoch
#         torch.save(model.state_dict(), "best_pdnn.pt")
#         print(f"[INFO] New best AUC: {best_auc:.4f} — model saved")
#     elif epoch - best_epoch >= patience:
#         early_stop = True

# # -------------------------------
# # Evaluation
# # -------------------------------
# model.load_state_dict(torch.load("best_pdnn.pt", map_location=device))
# model.eval()

# with torch.no_grad():
#     test_outputs = model(X_test_tensor).view(-1)
#     test_probs = torch.sigmoid(test_outputs).cpu().numpy()

# # FIX: y_test is already a NumPy array
# y_test_np = y_test

# # Histogram output distribution
# plt.figure()
# plt.hist(test_probs[y_test_np == 1], bins=50, alpha=0.5, label="Signal")
# plt.hist(test_probs[y_test_np == 0], bins=50, alpha=0.5, label="Background")
# plt.xlabel("Model Output")
# plt.ylabel("Frequency")
# plt.title("Output Distribution on Test Set")
# plt.legend()
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# # FIX: use y_test_np (not y_test.numpy())
# fpr, tpr, _ = roc_curve(y_test_np, test_probs)
# roc_auc = auc(fpr, tpr)

# plt.figure()
# plt.plot(fpr, tpr, label=f"ROC Curve (AUC = {roc_auc:.4f})")
# plt.plot([0, 1], [0, 1], 'k--', lw=1)
# plt.xlabel("False Positive Rate")
# plt.ylabel("True Positive Rate")
# plt.title("ROC Curve (Test Set)")
# plt.legend()
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# # Plot Loss
# plt.figure()
# plt.plot(losses, marker='o')
# plt.title("Training Loss")
# plt.xlabel("Epoch")
# plt.ylabel("Loss")
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# # Plot Accuracy
# plt.figure()
# plt.plot(accs, marker='o')
# plt.title("Training Accuracy")
# plt.xlabel("Epoch")
# plt.ylabel("Accuracy")
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# # Plot AUC
# plt.figure()
# plt.plot(aucs, marker='o')
# plt.title("Training AUC")
# plt.xlabel("Epoch")
# plt.ylabel("AUC")
# plt.grid(True)
# plt.tight_layout()
# plt.show()



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
class ParameterizedDNN(nn.Module):
    def __init__(self, input_dim):
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
            nn.Linear(8, 1)
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
patience = 5
max_epochs = 30

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



