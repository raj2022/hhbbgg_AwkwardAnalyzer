import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, roc_curve, auc
import matplotlib.pyplot as plt
import seaborn as sns

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Define file path and tree names
file_path = '../outputfiles/hhbbgg_analyzer-histograms.root'
sig_treename = 'GluGluToHH'
bkg_treename_1 = 'GGJets'
bkg_treename_2 = 'GJetPt20To40'
bkg_treename_3 = 'GJetPt40'

# Define histogram keys
keys = [
    'srbbgg-diphoton_mass',
    'srbbgg-dibjet_mass',
    'srbbgg-lead_pho_pt',
    'srbbgg-sublead_pho_pt',
    'srbbgg-bbgg_eta',
    'srbbgg-bbgg_phi',
    'srbbgg-lead_pho_eta',
    'srbbgg-lead_pho_phi',
    'srbbgg-sublead_pho_eta',
    'srbbgg-sublead_pho_phi',
    'srbbgg-diphoton_eta',
    'srbbgg-diphoton_phi',
    'srbbgg-dibjet_eta',
    'srbbgg-dibjet_phi',
    'srbbgg-lead_bjet_pt',
    'srbbgg-sublead_bjet_pt',
    'srbbgg-lead_bjet_eta',
    'srbbgg-lead_bjet_phi',
    'srbbgg-sublead_bjet_eta',
    'srbbgg-sublead_bjet_phi',
    'srbbgg-sublead_bjet_PNetB',
    'srbbgg-lead_bjet_PNetB',
    'srbbgg-CosThetaStar_gg',
    'srbbgg-CosThetaStar_jj',
    'srbbgg-CosThetaStar_CS',
    'srbbgg-DeltaR_jg_min',
    'srbbgg-pholead_PtOverM',
    'srbbgg-phosublead_PtOverM',
    'srbbgg-FirstJet_PtOverM',
    'srbbgg-SecondJet_PtOverM',
    'srbbgg-lead_pt_over_diphoton_mass',
    'srbbgg-sublead_pt_over_diphoton_mass',
    'srbbgg-lead_pt_over_dibjet_mass',
    'srbbgg-sublead_pt_over_dibjet_mass',
    'srbbgg-diphoton_bbgg_mass',
    'srbbgg-dibjet_bbgg_mass',
]

# Open ROOT file
file = uproot.open(file_path)

# Function to read histograms from a tree
def read_histograms(treename):
    tree_dfs = {}
    for branch in keys:
        full_key = f"{treename}/{branch}"
        if full_key in file:
            hist = file[full_key]
            values, _ = hist.to_numpy() 
            df = pd.DataFrame(values, columns=[branch])
            tree_dfs[branch] = df
        else:
            print(f"{full_key} not found in the file.")
    return tree_dfs

# Read histograms for signal and backgrounds
dfs = {}
dfs['signal'] = read_histograms(sig_treename)
dfs[bkg_treename_1] = read_histograms(bkg_treename_1)
dfs[bkg_treename_2] = read_histograms(bkg_treename_2)
dfs[bkg_treename_3] = read_histograms(bkg_treename_3)

# Combine dataframes
signal_df = pd.concat(dfs['signal'].values(), axis=1)
background_df_1 = pd.concat(dfs[bkg_treename_1].values(), axis=1)
background_df_2 = pd.concat(dfs[bkg_treename_2].values(), axis=1)
background_df_3 = pd.concat(dfs[bkg_treename_3].values(), axis=1)
background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)

print(signal_df.shape)

# Add labels
signal_df['label'] = 1
background_df['label'] = 0

# Combine signal and background dataframes
combined_df = pd.concat([signal_df, background_df], ignore_index=True)

# Features to use in the model
features = keys  # Use all keys as features

# Define X and y
X = combined_df[features]
y = combined_df['label']

# Handle missing values using SimpleImputer before scaling
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

# Standardizing the data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

# Convert to PyTorch tensors
X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
y_tensor = torch.tensor(y.values, dtype=torch.float32).reshape(-1, 1)

# Splitting the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_tensor, y_tensor, test_size=0.2, random_state=42)

# Define the DNN model
class DNN(nn.Module):
    def __init__(self, input_dim):
        super(DNN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.dropout1 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(128, 64)
        self.dropout2 = nn.Dropout(0.5)
        self.fc3 = nn.Linear(64, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout1(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout2(x)
        x = self.fc3(x)
        x = self.sigmoid(x)
        return x

# Instantiate the model
model = DNN(input_dim=X_train.shape[1])

# Define loss function and optimizer
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Training the model
epochs = 200
batch_size = 16
train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)

model.train()
for epoch in range(epochs):
    running_loss = 0.0
    for inputs, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()
    print(f"Epoch [{epoch+1}/{epochs}], Loss: {running_loss / len(train_loader)}")

# Evaluate the model
model.eval()
with torch.no_grad():
    y_pred = model(X_test).numpy()
    y_pred_class = np.round(y_pred).astype(int)
    accuracy = accuracy_score(y_test.numpy(), y_pred_class)
    roc_auc = roc_auc_score(y_test.numpy(), y_pred)

# Print evaluation metrics
print(f"Accuracy: {accuracy}")
print(classification_report(y_test.numpy(), y_pred_class))

# Compute ROC curve
fpr, tpr, _ = roc_curve(y_test.numpy(), y_pred)
roc_auc = auc(fpr, tpr)

# Plot ROC curve
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label='ROC curve (area = %0.2f)' % roc_auc)
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc="lower right")
plt.grid(True)
plt.show()

