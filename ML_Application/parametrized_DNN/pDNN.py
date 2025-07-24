import os
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from torch.optim import Adam
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample
from sklearn.metrics import roc_auc_score, accuracy_score
import uproot
import matplotlib.pyplot as plt

# ======================
# 0. Configuration
# ======================
used_columns = [
    'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
    'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi',
    'sublead_bjet_eta', 'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB',
    'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
    'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
    'lead_pho_mvaID', 'sublead_pho_mvaID'
]
par_params = ['mass', 'y_value', 'label', 'weight_preselection']
features = used_columns + ['mass', 'y_value']
columns_to_keep = list(set(used_columns + par_params))

# ======================
# 1. Load Signal Data
# ======================
start = time.time()
mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
y_values = [60, 70, 80, 90, 95, 100, 125, 150, 200]

signal_data = []
for mass in mass_points:
    for y in y_values:
        file_path = f"../../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path, columns=columns_to_keep)
                df["mass"] = mass
                df["y_value"] = y
                df["label"] = 1
                if "weight_preselection" not in df:
                    df["weight_preselection"] = 1.0
                signal_data.append(df)
            except Exception as e:
                print(f"Warning: {file_path} failed: {e}")

signal_df = pd.concat(signal_data, ignore_index=True) if signal_data else pd.DataFrame()
print(f"[INFO] Loaded signal: {signal_df.shape} in {time.time() - start:.2f}s")

# ======================
# 2. Load Background Data
# ======================
start = time.time()
background_files = [
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GGJets/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt20To40/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt40/preselection"),
]

background_data = []
for file_path, tree_name in background_files:
    try:
        with uproot.open(file_path) as file:
            tree = file[tree_name]
            df = tree.arrays(columns=columns_to_keep, library="pd", entry_stop=100_000)
            df["label"] = 0
            if "weight_preselection" not in df:
                df["weight_preselection"] = 1.0
            background_data.append(df)
    except Exception as e:
        print(f"Warning: Could not read {tree_name}: {e}")

df_background = pd.concat(background_data, ignore_index=True) if background_data else pd.DataFrame()
print(f"[INFO] Loaded background: {df_background.shape} in {time.time() - start:.2f}s")

# ======================
# 3. Balance and Combine
# ======================
start = time.time()
# Assign sampled (mass, y_value) to background
signal_mass_y = signal_df[["mass", "y_value"]]
value_counts = signal_mass_y.value_counts(normalize=True).reset_index()
value_counts.columns = ["mass", "y_value", "weight"]

sampled_mass_y = value_counts.sample(
    n=len(df_background),
    replace=True,
    weights="weight",
    random_state=42
).reset_index(drop=True)

df_background["mass"] = sampled_mass_y["mass"]
df_background["y_value"] = sampled_mass_y["y_value"]

# Upsample signal to match background
signal_upsampled = resample(signal_df, replace=True, n_samples=len(df_background), random_state=42)
df_combined = pd.concat([signal_upsampled, df_background], ignore_index=True)

df_features = df_combined[features].fillna(df_combined[features].mean())
X = df_features.values
y = df_combined["label"].values
w_pre = df_combined["weight_preselection"].values
print(f"[INFO] Combined shape: {df_combined.shape} in {time.time() - start:.2f}s")

# ======================
# 4. Train/Test Split + Weights
# ======================
X_train, X_test, y_train, y_test, w_pre_train, w_pre_test = train_test_split(
    X, y, w_pre, test_size=0.2, stratify=y, random_state=42
)

def compute_total_weights(y, w_pre):
    w_class = np.zeros_like(w_pre, dtype=np.float32)
    n_signal = np.sum(y == 1)
    n_background = np.sum(y == 0)
    w_class[y == 1] = 0.5 / n_signal
    w_class[y == 0] = 0.5 / n_background
    w_total = w_class * w_pre
    w_total *= len(w_total)
    return w_total

w_train = compute_total_weights(y_train, w_pre_train)
w_test = compute_total_weights(y_test, w_pre_test)

# ======================
# 5. Standardize + Tensor Conversion
# ======================
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train, dtype=torch.float32)
w_train_tensor = torch.tensor(w_train, dtype=torch.float32)
X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
y_test_tensor = torch.tensor(y_test, dtype=torch.float32)

assert not torch.isnan(X_train_tensor).any()
assert not torch.isinf(X_train_tensor).any()

# ======================
# 6. Model Setup
# ======================
train_dataset = TensorDataset(X_train_tensor, y_train_tensor, w_train_tensor)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Training on device: {device}")

class ParameterizedDNN(nn.Module):
    def __init__(self, input_dim):
        super(ParameterizedDNN, self).__init__()
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

model = ParameterizedDNN(X_train.shape[1]).to(device)
optimizer = Adam(model.parameters(), lr=0.001)
criterion = nn.BCEWithLogitsLoss(reduction='none')

# ======================
# 7. Training Loop
# ======================
for epoch in range(10):
    model.train()
    epoch_loss, y_pred_train, y_true_train = 0, [], []

    for xb, yb, wb in train_loader:
        xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
        optimizer.zero_grad()
        outputs = model(xb).view(-1)
        loss = criterion(outputs, yb)
        weighted_loss = (loss * wb).mean()
        weighted_loss.backward()
        optimizer.step()

        probs = torch.sigmoid(outputs).detach().cpu().numpy()
        y_pred_train.extend(probs)
        y_true_train.extend(yb.cpu().numpy())
        epoch_loss += weighted_loss.item()

    auc = roc_auc_score(y_true_train, y_pred_train)
    acc = accuracy_score(y_true_train, [1 if p > 0.5 else 0 for p in y_pred_train])
    print(f"Epoch {epoch+1:02d} | Loss: {epoch_loss:.4f} | AUC: {auc:.4f} | Acc: {acc:.4f}", flush=True)

# ======================
# 8. Evaluation
# ======================
model.eval()
with torch.no_grad():
    test_probs = torch.sigmoid(model(X_test_tensor.to(device)).view(-1)).cpu().numpy()

plt.hist(test_probs[y_test == 1], bins=50, alpha=0.5, label="Signal")
plt.hist(test_probs[y_test == 0], bins=50, alpha=0.5, label="Background")
plt.xlabel("Model Output")
plt.ylabel("Frequency")
plt.title("Output Distribution on Test Set")
plt.legend()
plt.grid(True)
plt.show()
