import os
import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
from torch.nn import BCEWithLogitsLoss



# Taking mass X and corresponding Y mass points
mass_points = [300, 400, 500, 550, 600, 650, 700, 900]  # Example mass points
y_values = [100, 125, 150, 200, 300, 400, 500, 600]  # Example Y values

# Initialize list to store data and a dictionary for missing files
signal_data = []
missing_files = {}

# Load signal data from Parquet files
for mass in mass_points:
    for y in y_values:
        file_path = f"../../../output_parquet/final_production_Syst/merged/NMSSM_X{mass}_Y{y}/nominal/NOTAG_merged.parquet"

        if os.path.exists(file_path):  # Check if file exists
            try:
                df = pd.read_parquet(file_path)  # Load the Parquet file
                df["mass"] = mass
                df["y_value"] = y  # Store Y value if needed
                df["label"] = 1  # Assuming signal label
                signal_data.append(df)
            except Exception as e:
                print(f"Warning: Could not read {file_path}. Error: {e}")
        else:
            print(f"Warning: File {file_path} does not exist.")
            # Track missing files
            if mass not in missing_files:
                missing_files[mass] = []
            missing_files[mass].append(y)

# Combine all signal data into a single DataFrame
signal_df = pd.concat(signal_data, ignore_index=True) if signal_data else pd.DataFrame()

#  print the missing files
if missing_files:
    print("Missing files for the following mass points and Y values:")
    for mass, ys in missing_files.items():
        print(f"Mass point {mass} is missing Y values: {ys}")

print(f"singal shape is",signal_df.shape)

# Reading background files
# Load background data from ROOT files
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
            df["mass"] = np.random.choice(mass_points, len(df))  # Random mass assignment
            df["label"] = 0
            background_data.append(df)
    except Exception as e:
        print(f"Warning: Could not read {file_path}. Error: {e}")

df_background = pd.concat(background_data, ignore_index=True) if background_data else pd.DataFrame()

print("total backgrounds", df_background)

# Define features and labels
features = [
    'bbgg_eta', 'bbgg_phi', 'lead_pho_phi', 'sublead_pho_eta',
    'sublead_pho_phi', 'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi',
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi', 'sublead_bjet_eta',
    'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB', 'CosThetaStar_gg',
    'CosThetaStar_jj', 'CosThetaStar_CS', 'DeltaR_jg_min', 'pholead_PtOverM',
    'phosublead_PtOverM', 'lead_pho_mvaID', 'sublead_pho_mvaID'
]

# Reduce background dataset size by random sampling
background_fraction = 0.2  #  20% of the background
df_background = df_background.sample(frac=background_fraction, random_state=42)

# Combine signal and background
df_combined = pd.concat([signal_df, df_background], ignore_index=True)
print("Combined shape with signal and background", df_combined)

# Ensure df_combined is not empty
if df_combined.empty:
    raise ValueError("Error: Combined DataFrame is empty. Check input files.")

# Convert feature data to DataFrame to prevent AttributeError
df_features = df_combined[features]

# Fill missing values with column mean
df_features = df_features.fillna(df_features.mean())

# Extract features (X) and labels (y)
X = df_features.values
y = df_combined["label"].values

print(f"total features", df_features.shape)

# Undersampling the Majority Class

from sklearn.utils import resample

df_majority = df_combined[df_combined["label"] == 0]
df_minority = df_combined[df_combined["label"] == 1]

df_majority_downsampled = resample(df_majority,
                                   replace=False,
                                   n_samples=len(df_minority),
                                   random_state=42)

df_balanced = pd.concat([df_majority_downsampled, df_minority])


# Standardize features
scaler = StandardScaler()
X = scaler.fit_transform(X)

# Convert to PyTorch tensors
X_tensor = torch.tensor(X, dtype=torch.float32)
y_tensor = torch.tensor(y, dtype=torch.float32)

# Check for GPU
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"Using device: {device}")

# Move data to GPU
# X_tensor = X_tensor.to(device)
# y_tensor = y_tensor.to(device)

# Create DataLoader
dataset = TensorDataset(X_tensor, y_tensor)
dataloader = DataLoader(dataset, batch_size=64, shuffle=True)

# Checking class imabalance
class_counts = np.bincount(y)
print(f"Class distribution: {dict(enumerate(class_counts))}")


import torch
import torch.nn as nn
from torch.optim import Adam

class ParameterizedDNN(nn.Module):
    def __init__(self, input_dim):
        super(ParameterizedDNN, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 256),  # Increase neurons
            nn.ReLU(),
            nn.Dropout(0.3),  # Reduce dropout

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(128, 64),  # Increase size from 4 → 16
            nn.ReLU(),
            nn.Dropout(0.2),  # Reduce dropout further

            nn.Linear(64, 1)  # Output layer (No activation function)
        )

    def forward(self, x):
        return self.model(x)  # No sigmoid here!



# Initialize model
input_dim = X.shape[1]
model = ParameterizedDNN(input_dim)
# criterion = nn.BCEWithLogitsLoss()  # Expecting raw logits
# criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([weight]))
optimizer = Adam(model.parameters(), lr=0.0001, weight_decay=1e-5)  # Reduce learning rate
# Compute class weights
pos_weight = torch.tensor([class_counts[0] / class_counts[1]], dtype=torch.float32)

# Update loss function
criterion = BCEWithLogitsLoss(pos_weight=pos_weight)


import torch
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
import matplotlib.pyplot as plt

# Check if GPU is available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

num_epochs = 100
train_losses = []
train_accuracies = []
train_aucs = []
fpr_all, tpr_all, thresholds_all = [], [], []

for epoch in range(num_epochs):
    epoch_loss = 0
    y_true = []
    y_pred = []

    model.train()  # Set to training mode
    for batch in dataloader:
        X_batch, y_batch = batch
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)  # Move data to GPU

        optimizer.zero_grad()
        outputs = model(X_batch).squeeze()  # Get raw logits

        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()

        # Store predictions for accuracy & AUC calculation
        y_true.extend(y_batch.cpu().numpy())  # True labels
        y_pred.extend(torch.sigmoid(outputs).detach().cpu().numpy())  # Apply sigmoid AFTER training

    # Compute Metrics
    avg_loss = epoch_loss / len(dataloader)
    y_pred_binary = [1 if p > 0.5 else 0 for p in y_pred]  # Convert to 0/1 labels
    accuracy = accuracy_score(y_true, y_pred_binary)
    auc = roc_auc_score(y_true, y_pred)  # Use probabilities, not logits

    # Store metrics
    train_losses.append(avg_loss)
    train_accuracies.append(accuracy)
    train_aucs.append(auc)

    # Compute ROC curve for current epoch (for plotting)
    fpr, tpr, thresholds = roc_curve(y_true, y_pred)
    fpr_all.append(fpr)
    tpr_all.append(tpr)
    thresholds_all.append(thresholds)

    print(f"Epoch {epoch+1}/{num_epochs} - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}, AUC: {auc:.4f}")




# Plot Loss
plt.figure(figsize=(12, 4))
plt.subplot(1, 3, 1)
plt.plot(range(1, num_epochs+1), train_losses, marker='o', linestyle='-', color='blue')
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("Loss vs. Epochs")


plt.tight_layout()
plt.savefig("loss_vs_epochs.png")
plt.savefig("loss_vs_epochs.pdf")


# Plot Accuracy
plt.subplot(1, 3, 2)
plt.plot(range(1, num_epochs+1), train_accuracies, marker='o', linestyle='-', color='green')
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.title("Accuracy vs. Epochs")

plt.tight_layout()
plt.savefig("accuracy_vs_epochs.png")
plt.savefig("accuracy_vs_epochs.pdf")


# Plot AUC


# Plot the final ROC curve
# Select the ROC curve from the last epoch
fpr_last = fpr_all[-1]
tpr_last = tpr_all[-1]

plt.figure(figsize=(10, 6))
plt.plot(fpr_last, tpr_last, color='darkorange', lw=2, label=f'ROC curve (AUC = {train_aucs[-1]:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')  # Random classifier line
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title(f'Final ROC Curve (AUC = {train_aucs[-1]:.2f})')
plt.legend(loc="lower right")
plt.savefig(AUC.png)
plt.savefig(AUC.pdf)


