import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc


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
from sklearn.metrics import roc_auc_score, accuracy_score
import uproot
import matplotlib.pyplot as plt

# -------------------------------
# 1. Load Signal Data
# -------------------------------
mass_points = [300, 400, 500, 550, 600, 650, 700, 800, 900, 1000]
y_values = [60, 70, 80, 90, 95, 100, 125, 150, 200]

signal_data = []
for mass in mass_points:
    for y in y_values:
        file_path = f"../../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"
        if os.path.exists(file_path):
            try:
                df = pd.read_parquet(file_path)
                df["mass"] = mass
                df["y_value"] = y
                df["label"] = 1
                if "weight_preselection" not in df:
                    df["weight_preselection"] = 1.0
                signal_data.append(df)
            except Exception as e:
                print(f"Warning: Could not read {file_path}. Error: {e}")

signal_df = pd.concat(signal_data, ignore_index=True) if signal_data else pd.DataFrame()
print("[INFO] Signal shape:", signal_df.shape)

# -------------------------------
# 2. Load Background Data
# -------------------------------
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
            df = tree.arrays(library="pd")
            df["label"] = 0
            if "weight_preselection" not in df:
                df["weight_preselection"] = 1.0
            background_data.append(df)
    except Exception as e:
        print(f"Warning: Could not read {file_path}. Error: {e}")

df_background = pd.concat(background_data, ignore_index=True) if background_data else pd.DataFrame()
print("[INFO] Background shape:", df_background.shape)

# -------------------------------
# 3. Match mass/y_value to background
# -------------------------------
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

df_background = df_background.sample(frac=0.2, random_state=42)


df_combined = pd.read_parquet("processed_combined.parquet")  # Or regenerate the features
features = [
    'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
    'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi',
    'sublead_bjet_eta', 'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB',
    'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
    'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
    'lead_pho_mvaID', 'sublead_pho_mvaID', 'mass', 'y_value'
]

X = df_combined[features].fillna(df_combined[features].mean()).values
y = df_combined["label"].values

# ---- 2. Preprocess
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

X_test_tensor = torch.tensor(X_test, dtype=torch.float32)

# ---- 3. Define Model
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

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = ParameterizedDNN(X_test.shape[1]).to(device)
model.load_state_dict(torch.load("best_pdnn.pt"))
model.eval()

# ---- 4. Inference
X_test_tensor = X_test_tensor.to(device)

with torch.no_grad():
    outputs = model(X_test_tensor).view(-1)
    probs = torch.sigmoid(outputs).cpu().numpy()

# ---- 5. Plot
y_test_np = y_test if isinstance(y_test, np.ndarray) else y_test.numpy()

# Output distribution
plt.hist(probs[y_test_np == 1], bins=50, alpha=0.5, label="Signal")
plt.hist(probs[y_test_np == 0], bins=50, alpha=0.5, label="Background")
plt.xlabel("Model Output")
plt.ylabel("Frequency")
plt.title("Output Distribution on Test Set")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# ROC Curve
fpr, tpr, _ = roc_curve(y_test_np, probs)
roc_auc = auc(fpr, tpr)

plt.figure()
plt.plot(fpr, tpr, label=f"AUC = {roc_auc:.4f}")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()