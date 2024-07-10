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

keys = [
    'preselection-dibjet_mass',
    'preselection-diphoton_mass',
    'preselection-bbgg_mass',
    'preselection-dibjet_pt',
    'preselection-diphoton_pt',
    'preselection-bbgg_pt',
    'preselection-lead_pho_pt',
    'preselection-sublead_pho_pt',
    'preselection-bbgg_eta',
    'preselection-bbgg_phi',
    'preselection-lead_pho_eta',
    'preselection-lead_pho_phi',
    'preselection-sublead_pho_eta',
    'preselection-sublead_pho_phi',
    'preselection-diphoton_eta',
    'preselection-diphoton_phi',
    'preselection-dibjet_eta',
    'preselection-dibjet_phi',
    'preselection-lead_bjet_pt',
    'preselection-sublead_bjet_pt',
    'preselection-lead_bjet_eta',
    'preselection-lead_bjet_phi',
    'preselection-sublead_bjet_eta',
    'preselection-sublead_bjet_phi',
    'preselection-sublead_bjet_PNetB',
    'preselection-lead_bjet_PNetB',
    'preselection-CosThetaStar_gg',
    'preselection-CosThetaStar_jj',
    'preselection-CosThetaStar_CS',
    'preselection-DeltaR_jg_min',
    'preselection-pholead_PtOverM',
    'preselection-phosublead_PtOverM',
    'preselection-FirstJet_PtOverM',
    'preselection-SecondJet_PtOverM',
    'preselection-lead_pt_over_diphoton_mass',
    'preselection-sublead_pt_over_diphoton_mass',
    'preselection-lead_pt_over_dibjet_mass',
    'preselection-sublead_pt_over_dibjet_mass',
    'preselection-diphoton_bbgg_mass',
    'preselection-dibjet_bbgg_mass',
]

file = uproot.open(file_path)

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

dfs = {}
dfs['signal'] = read_histograms(sig_treename)
dfs[bkg_treename_1] = read_histograms(bkg_treename_1)
dfs[bkg_treename_2] = read_histograms(bkg_treename_2)
dfs[bkg_treename_3] = read_histograms(bkg_treename_3)

signal_df = pd.concat(dfs['signal'].values(), axis=1)
background_df_1 = pd.concat(dfs[bkg_treename_1].values(), axis=1)
background_df_2 = pd.concat(dfs[bkg_treename_2].values(), axis=1)
background_df_3 = pd.concat(dfs[bkg_treename_3].values(), axis=1)

background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)

signal_df['label'] = 1
background_df['label'] = 0

combined_df = pd.concat([signal_df, background_df], ignore_index=True)

features = [
    'preselection-diphoton_mass',
    'preselection-dibjet_mass',
    'preselection-lead_pho_pt',
    'preselection-sublead_pho_pt',
    'preselection-bbgg_eta',
    'preselection-bbgg_phi',
    'preselection-lead_pho_eta',
    'preselection-lead_pho_phi',
    'preselection-sublead_pho_eta',
    'preselection-sublead_pho_phi',
    'preselection-diphoton_eta',
    'preselection-diphoton_phi',
    'preselection-dibjet_eta',
    'preselection-dibjet_phi',
    'preselection-lead_bjet_pt',
    'preselection-sublead_bjet_pt',
    'preselection-lead_bjet_eta',
    'preselection-lead_bjet_phi',
    'preselection-sublead_bjet_eta',
    'preselection-sublead_bjet_phi',
    'preselection-sublead_bjet_PNetB',
    'preselection-lead_bjet_PNetB',
    'preselection-CosThetaStar_gg',
    'preselection-CosThetaStar_jj',
    'preselection-CosThetaStar_CS',
    'preselection-DeltaR_jg_min',
    'preselection-pholead_PtOverM',
    'preselection-phosublead_PtOverM',
    'preselection-FirstJet_PtOverM',
    'preselection-SecondJet_PtOverM',
    'preselection-lead_pt_over_diphoton_mass',
    'preselection-sublead_pt_over_diphoton_mass',
    'preselection-lead_pt_over_dibjet_mass',
    'preselection-sublead_pt_over_dibjet_mass',
    'preselection-diphoton_bbgg_mass',
    'preselection-dibjet_bbgg_mass',
]

X = combined_df[features]
y = combined_df['label']

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

train_data = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train.values, dtype=torch.long))
test_data = TensorDataset(torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test.values, dtype=torch.long))

train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
test_loader = DataLoader(test_data, batch_size=32, shuffle=False)

class DNN(nn.Module):
    def __init__(self):
        super(DNN, self).__init__()
        self.fc1 = nn.Linear(len(features), 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 64)
        self.fc4 = nn.Linear(64, 32)
        self.fc5 = nn.Linear(32, 1)
        self.dropout = nn.Dropout(0.5)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.relu(self.fc3(x))
        x = self.dropout(x)
        x = self.sigmoid(self.fc4(x))
        x = self.dropout(x)
        x = self.sigmoid(self.fc5(x))
        return x

model = DNN()
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

num_epochs = 500

for epoch in range(num_epochs):
    model.train()
    for X_batch, y_batch in train_loader:
        optimizer.zero_grad()
        outputs = model(X_batch).squeeze()
        loss = criterion(outputs, y_batch.float())
        loss.backward()
        optimizer.step()

    print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.4f}')

model.eval()
with torch.no_grad():
    y_train_pred = model(torch.tensor(X_train, dtype=torch.float32)).squeeze().numpy()
    y_test_pred = model(torch.tensor(X_test, dtype=torch.float32)).squeeze().numpy()

y_train_pred_class = (y_train_pred > 0.5).astype(int)
y_test_pred_class = (y_test_pred > 0.5).astype(int)

# Classifier output plot
plt.figure(figsize=(10, 8))
plt.hist(y_train_pred[y_train == 1], bins=20, color='blue', alpha=0.5, label='S (Train)', density=True)
plt.hist(y_train_pred[y_train == 0], bins=20, color='red', alpha=0.5, label='R (Train)', density=True)
plt.scatter(y_test_pred[y_test == 1], np.full(y_test[y_test == 1].shape, -0.1), color='blue', label='S (Test)', alpha=0.6)
plt.scatter(y_test_pred[y_test == 0], np.full(y_test[y_test == 0].shape, -0.1), color='red', label='R (Test)', alpha=0.6)
plt.xlabel('Classifier output')
plt.ylabel('Normalized Yields')
plt.title('Classification with scikit-learn')
plt.savefig("bdtplots/dnn/classifier.png")
plt.savefig("bdtplots/dnn/classifier.pdf")
plt.legend()
plt.grid(True)
plt.show()

# ROC curve
fpr, tpr, thresholds = roc_curve(y_test, y_test_pred)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label='ROC curve (area = {:.2f})'.format(roc_auc))
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.0])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc='lower right')
plt.grid(True)
plt.savefig("bdtplots/dnn/ROC_curve.png")
plt.savefig("bdtplots/dnn/ROC_curve.png")
plt.show()

print("Accuracy on test set:", accuracy_score(y_test, y_test_pred_class))
print("ROC AUC on test set:", roc_auc_score(y_test, y_test_pred))
print(classification_report(y_test, y_test_pred_class))
