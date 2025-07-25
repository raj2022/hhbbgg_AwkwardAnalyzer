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

# -------------------------------
# 4. Combine & Feature Processing
# -------------------------------
signal_upsampled = resample(signal_df, replace=True, n_samples=len(df_background), random_state=42)
df_combined = pd.concat([signal_upsampled, df_background], ignore_index=True)

features = [
    'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi',
    'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi',
    'sublead_bjet_eta', 'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB',
    'CosThetaStar_gg', 'CosThetaStar_jj', 'CosThetaStar_CS',
    'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM',
    'lead_pho_mvaID', 'sublead_pho_mvaID', 'mass', 'y_value'
]

df_features = df_combined[features].fillna(df_combined[features].mean())
print("total shape", df_features)

X = df_features.values
y = df_combined["label"].values
w_pre = df_combined["weight_preselection"].values

# -------------------------------
# 5. Train/Test Split
# -------------------------------
X_train, X_test, y_train, y_test, w_pre_train, w_pre_test = train_test_split(
    X, y, w_pre, test_size=0.2, random_state=42, stratify=y
)

# -------------------------------
# 6. Compute Total Weights
# -------------------------------
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

# -------------------------------
# 7. Standardize
# -------------------------------
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# -------------------------------
# 8. Convert to Tensors
# -------------------------------
X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train, dtype=torch.float32)
w_train_tensor = torch.tensor(w_train, dtype=torch.float32)

X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
y_test_tensor = torch.tensor(y_test, dtype=torch.float32)

# Sanity check: NaNs/Infs
assert not torch.isnan(X_train_tensor).any(), "NaNs in X_train"
assert not torch.isinf(X_train_tensor).any(), "Infs in X_train"

# -------------------------------
# 9. Device and Loader
# -------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {device}")

# Move tensors to GPU
X_train_tensor = X_train_tensor.to(device)
y_train_tensor = y_train_tensor.to(device)
w_train_tensor = w_train_tensor.to(device)
X_test_tensor = X_test_tensor.to(device)
y_test_tensor = y_test_tensor.to(device)


# -------------------------------
# 10. Define PDNN
# -------------------------------
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

# -------------------------------
# 11. Optimized Train Loop (GPU + AMP + Batch + Compile)
# -------------------------------
use_amp = torch.cuda.is_available()
scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

model = ParameterizedDNN(X_train.shape[1]).to(device)

# Optional: compile model for speed (PyTorch ≥ 2.0)
if hasattr(torch, "compile"):
    model = torch.compile(model)

criterion = nn.BCEWithLogitsLoss(reduction='none')
optimizer = Adam(model.parameters(), lr=0.001)

train_dataset = TensorDataset(X_train_tensor, y_train_tensor, w_train_tensor)
train_loader = DataLoader(
    train_dataset, 
    batch_size=1024, 
    shuffle=True, 
    pin_memory=(device.type == "cuda")
)

# from sklearn.metrics import roc_curve, auc
# #--------------------------------
# losses, aucs, accs = [], [], []

# for epoch in range(10):
#     model.train()
#     epoch_loss = 0
#     y_pred_train, y_true_train = [], []

#     for xb, yb, wb in train_loader:
#         # Use non_blocking transfers for speed with pinned memory
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

#         epoch_loss += weighted_loss.item()

#     y_pred_train = torch.cat(y_pred_train).cpu().numpy()
#     y_true_train = torch.cat(y_true_train).cpu().numpy()
    

    
#     auc = roc_auc_score(y_true_train, y_pred_train)
#     acc = accuracy_score(y_true_train, (y_pred_train > 0.5).astype(int))
    
#     losses.append(epoch_loss)
#     aucs.append(auc)
#     accs.append(acc)
#     print(f"Epoch {epoch+1:02d} | Loss: {epoch_loss:.4f} | AUC: {auc:.4f} | Acc: {acc:.4f}", flush=True)
    
# # Save model
# torch.save(model.state_dict(), "trained_pdnn.pt")
# print("[INFO] Model saved to 'trained_pdnn.pt'")


# # -------------------------------
# # 12. Evaluation (GPU)
# # -------------------------------
# model.eval()
# with torch.no_grad():
#     test_outputs = model(X_test_tensor).view(-1)
#     test_probs = torch.sigmoid(test_outputs).cpu().numpy()

# plt.hist(test_probs[y_test == 1], bins=50, alpha=0.5, label="Signal")
# plt.hist(test_probs[y_test == 0], bins=50, alpha=0.5, label="Background")
# plt.xlabel("Model Output")
# plt.ylabel("Frequency")
# plt.title("Output Distribution on Test Set")
# plt.legend()
# plt.grid(True)
# plt.show()


# # === Plot Metrics ===
# plt.figure()
# plt.plot(losses, marker='o')
# plt.title("Training Loss")
# plt.xlabel("Epoch")
# plt.ylabel("Loss")
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# plt.figure()
# plt.plot(accs, marker='o')
# plt.title("Training Accuracy")
# plt.xlabel("Epoch")
# plt.ylabel("Accuracy")
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# plt.figure()
# plt.plot(aucs, marker='o')
# plt.title("Training AUC")
# plt.xlabel("Epoch")
# plt.ylabel("AUC")
# plt.grid(True)
# plt.tight_layout()
# plt.show()




# # === ROC Curve on Test Set ===
# from sklearn.metrics import roc_curve, auc

# fpr, tpr, _ = roc_curve(y_test.cpu().numpy(), test_probs)
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

from sklearn.metrics import roc_auc_score, accuracy_score, roc_curve, auc
import matplotlib.pyplot as plt

# -------------------------------
# Training with Early Stopping
# -------------------------------
losses, aucs, accs = [], [], []

best_auc = 0
best_epoch = 0
patience = 3
early_stop = False
max_epochs = 50  # you can raise this, early stopping will prevent overfitting

for epoch in range(max_epochs):
    if early_stop:
        print(f"[INFO] Early stopping triggered at epoch {epoch}")
        break

    model.train()
    epoch_loss = 0
    y_pred_train, y_true_train = [], []

    for xb, yb, wb in train_loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        wb = wb.to(device, non_blocking=True)

        optimizer.zero_grad()
        with torch.amp.autocast(device_type='cuda', enabled=use_amp):
            outputs = model(xb).view(-1)
            loss = criterion(outputs, yb)
            weighted_loss = (loss * wb).mean()

        scaler.scale(weighted_loss).backward()
        scaler.step(optimizer)
        scaler.update()

        y_pred_train.append(torch.sigmoid(outputs).detach())
        y_true_train.append(yb)
        epoch_loss += weighted_loss.item()

    # Evaluate training epoch
    y_pred_train = torch.cat(y_pred_train).cpu().numpy()
    y_true_train = torch.cat(y_true_train).cpu().numpy()

    auc_score = roc_auc_score(y_true_train, y_pred_train)
    acc_score = accuracy_score(y_true_train, (y_pred_train > 0.5).astype(int))

    losses.append(epoch_loss)
    aucs.append(auc_score)
    accs.append(acc_score)

    print(f"Epoch {epoch+1:02d} | Loss: {epoch_loss:.4f} | AUC: {auc_score:.4f} | Acc: {acc_score:.4f}", flush=True)

    # Early stopping check
    if auc_score > best_auc:
        best_auc = auc_score
        best_epoch = epoch
        torch.save(model.state_dict(), "best_pdnn.pt")
        print(f"[INFO] New best AUC: {best_auc:.4f} — model saved")
    elif epoch - best_epoch >= patience:
        early_stop = True


# -------------------------------
# Evaluation
# -------------------------------
model.load_state_dict(torch.load("best_pdnn.pt"))
model.eval()

with torch.no_grad():
    test_outputs = model(X_test_tensor).view(-1)
    test_probs = torch.sigmoid(test_outputs).cpu().numpy()

# Convert y_test to NumPy array if needed
y_test_np = y_test.numpy() if isinstance(y_test, torch.Tensor) else y_test

# Histogram output distribution
plt.hist(test_probs[y_test_np == 1], bins=50, alpha=0.5, label="Signal")
plt.hist(test_probs[y_test_np == 0], bins=50, alpha=0.5, label="Background")
plt.xlabel("Model Output")
plt.ylabel("Frequency")
plt.title("Output Distribution on Test Set")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()


# ROC Curve on test set
fpr, tpr, _ = roc_curve(y_test.numpy(), test_probs)
roc_auc = auc(fpr, tpr)

plt.figure()
plt.plot(fpr, tpr, label=f"ROC Curve (AUC = {roc_auc:.4f})")
plt.plot([0, 1], [0, 1], 'k--', lw=1)
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve (Test Set)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# Plot Loss
plt.figure()
plt.plot(losses, marker='o')
plt.title("Training Loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True)
plt.tight_layout()
plt.show()

# Plot Accuracy
plt.figure()
plt.plot(accs, marker='o')
plt.title("Training Accuracy")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.grid(True)
plt.tight_layout()
plt.show()

# Plot AUC
plt.figure()
plt.plot(aucs, marker='o')
plt.title("Training AUC")
plt.xlabel("Epoch")
plt.ylabel("AUC")
plt.grid(True)
plt.tight_layout()
plt.show()




