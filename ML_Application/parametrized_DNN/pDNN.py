import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from torch.optim import Adam
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, accuracy_score

# mass and Y points
mass_points = [300, 400]
y_values = [60, 70, 80, 90, 95, 100, 125, 150, 200]

# Features used in training
features = [
    'bbgg_eta', 'bbgg_phi',
    'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
    'diphoton_eta', 'diphoton_phi',
    'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt',
    'lead_bjet_eta', 'lead_bjet_phi',
    'sublead_bjet_eta', 'sublead_bjet_phi',
    'sublead_bjet_PNetB', 'lead_bjet_PNetB',
    'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
    'DeltaR_jg_min',
    'pholead_PtOverM', 'phosublead_PtOverM',
    'lead_pho_mvaID', 'sublead_pho_mvaID',
    'mass', 'y_value'
]

# Load signal data
signal_data = []
for mass in mass_points:
    for y in y_values:
        file_path = f"../../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path)
                missing = [col for col in features if col not in df.columns]
                if missing:
                    print(f"Skipping {file_path}, missing columns: {missing}")
                    continue
                df = df[[col for col in features if col not in ['mass', 'y_value']]]
                df['mass'] = mass
                df['y_value'] = y
                df['label'] = 1
                signal_data.append(df)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        else:
            print(f"Missing signal file: {file_path}")

signal_df = pd.concat(signal_data, ignore_index=True) if signal_data else pd.DataFrame()
print("Loaded signal:", signal_df.shape)

if signal_df.empty:
    raise RuntimeError("Signal dataset is empty. Check your input files.")

# Load background data
background_files = [
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GGJets/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt20To40/preselection"),
    ("../../outputfiles/hhbbgg_analyzer-v2-trees.root", "/GJetPt40/preselection"),
]

background_data = []
for path, tree in background_files:
    try:
        with uproot.open(path) as file:
            df = file[tree].arrays(library="pd")
            df = df[[col for col in features if col not in ['mass', 'y_value']]]
            df["label"] = 0
            background_data.append(df)
    except Exception as e:
        print(f"Error reading background {path}:{tree} — {e}")

df_background = pd.concat(background_data, ignore_index=True) if background_data else pd.DataFrame()
print("Loaded background:", df_background.shape)

if df_background.empty:
    raise RuntimeError("Background dataset is empty. Check your input files.")

# Assign signal-distributed mass and y_value to background
value_counts = signal_df[["mass", "y_value"]].value_counts(normalize=True).reset_index()
value_counts.columns = ["mass", "y_value", "weight"]
sampled = value_counts.sample(n=len(df_background), replace=True, weights="weight", random_state=42)
df_background["mass"] = sampled["mass"].values
df_background["y_value"] = sampled["y_value"].values

# Downsample background, upsample signal
df_background = df_background.sample(frac=0.6, random_state=42)
signal_upsampled = resample(signal_df, replace=True, n_samples=len(df_background), random_state=42)

# Combine
df_combined = pd.concat([signal_upsampled, df_background], ignore_index=True)
df_combined = df_combined.fillna(df_combined.mean())

X = df_combined[features].values
y = df_combined["label"].values

X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2, random_state=42)

# Normalize
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Class weight helper
def compute_class_normalized_weights(y):
    n_signal = np.sum(y == 1)
    n_background = np.sum(y == 0)
    weights = np.zeros_like(y, dtype=np.float32)
    weights[y == 1] = 0.5 / n_signal
    weights[y == 0] = 0.5 / n_background
    return weights * len(y)

# Tensors
w_train = compute_class_normalized_weights(y_train)
X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train, dtype=torch.float32)
w_train_tensor = torch.tensor(w_train, dtype=torch.float32)

X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
y_test_tensor = torch.tensor(y_test, dtype=torch.float32)

# Model
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

# Training
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = ParameterizedDNN(X_train.shape[1]).to(device)
optimizer = Adam(model.parameters(), lr=0.001)
criterion = nn.BCEWithLogitsLoss(reduction='none')

train_dataset = TensorDataset(X_train_tensor, y_train_tensor, w_train_tensor)
train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)

# Loop
for epoch in range(10):
    model.train()
    y_pred_train, y_true_train, loss_epoch = [], [], 0
    for xb, yb, wb in train_loader:
        xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
        optimizer.zero_grad()
        logits = model(xb).squeeze()
        loss = (criterion(logits, yb) * wb).mean()
        loss.backward()
        optimizer.step()
        y_pred_train.extend(torch.sigmoid(logits).cpu().numpy())
        y_true_train.extend(yb.cpu().numpy())
        loss_epoch += loss.item()
    auc = roc_auc_score(y_true_train, y_pred_train)
    acc = accuracy_score(y_true_train, [p > 0.5 for p in y_pred_train])
    print(f"Epoch {epoch+1} | Loss: {loss_epoch:.4f} | AUC: {auc:.4f} | Acc: {acc:.4f}")

# Eval plot
model.eval()
with torch.no_grad():
    probs = torch.sigmoid(model(X_test_tensor.to(device)).squeeze()).cpu().numpy()

plt.hist(probs[y_test == 1], bins=50, alpha=0.5, label='Signal')
plt.hist(probs[y_test == 0], bins=50, alpha=0.5, label='Background')
plt.xlabel("Model Output")
plt.ylabel("Count")
plt.title("Output Distribution")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig("output_distribution.png")
plt.show()
