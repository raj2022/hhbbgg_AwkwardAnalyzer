#Take four varibles using trees and histogram and plot it. Similarly do it for th theoutpit of singal nad background
#event weight not provided properly
#Take dibjet mass plot it normalized from trees and histogram.
# 



import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, roc_curve, auc
import matplotlib.pyplot as plt
import seaborn as sns
from torchsummary import summary
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Define file path and tree names
files = [
    ("../outputfiles/hhbbgg_analyzer-trees.root", "/GluGluToHH/preselection"),
    ("../outputfiles/hhbbgg_analyzer-trees.root", "/GGJets/preselection"),
    ("../outputfiles/hhbbgg_analyzer-trees.root", "/GJetPt20To40/preselection"),
    ("../outputfiles/hhbbgg_analyzer-trees.root", "/GJetPt40/preselection")
]
keys = [
    'dibjet_mass',
    'diphoton_mass',
    'bbgg_mass',
    'dibjet_pt',
    'diphoton_pt',
    'bbgg_pt',
    'lead_pho_pt',
    'sublead_pho_pt',
    'bbgg_eta',
    'bbgg_phi',
    'lead_pho_eta',
    'lead_pho_phi',
    'sublead_pho_eta',
    'sublead_pho_phi',
    'diphoton_eta',
    'diphoton_phi',
    'dibjet_eta',
    'dibjet_phi',
    'lead_bjet_pt',
    'sublead_bjet_pt',
    'lead_bjet_eta',
    'lead_bjet_phi',
    'sublead_bjet_eta',
    'sublead_bjet_phi',
    'sublead_bjet_PNetB',
    'lead_bjet_PNetB',
    'CosThetaStar_gg',
    'CosThetaStar_jj',
    'CosThetaStar_CS',
    'DeltaR_jg_min',
    'pholead_PtOverM',
    'phosublead_PtOverM',
    'FirstJet_PtOverM',
    'SecondJet_PtOverM',
    'lead_pt_over_diphoton_mass',
    'sublead_pt_over_diphoton_mass',
    'lead_pt_over_dibjet_mass',
    'sublead_pt_over_dibjet_mass',
    'diphoton_bbgg_mass',
    'dibjet_bbgg_mass',
    'weight_preselection',
]

# Initialize an empty dictionary to store dataframes
dfs = {}

# Loop through each file and load the corresponding dataframe
for file, key in files:
    with uproot.open(file) as f:
        dfs[key] = f[key].arrays(keys, library="pd")

# Access your dataframes by key
signal_df = dfs["/GluGluToHH/preselection"]
background_df_1 = dfs["/GGJets/preselection"]
background_df_2 = dfs["/GJetPt20To40/preselection"]
background_df_3 = dfs["/GJetPt40/preselection"]

weight = 'weight_preselection'

print(signal_df.shape)
print(background_df_1.shape)
print(background_df_2.shape)
print(background_df_3.shape)

background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)

signal_df['label'] = 1
background_df['label'] = 0

combined_df = pd.concat([signal_df, background_df], ignore_index=True)

features = [
    'diphoton_mass',
    'dibjet_mass',
    'lead_pho_pt',
    'sublead_pho_pt',
    'bbgg_eta',
    'bbgg_phi',
    'lead_pho_eta',
    'lead_pho_phi',
    'sublead_pho_eta',
    'sublead_pho_phi',
    'diphoton_eta',
    'diphoton_phi',
    'dibjet_eta',
    'dibjet_phi',
    'lead_bjet_pt',
    'sublead_bjet_pt',
    'lead_bjet_eta',
    'lead_bjet_phi',
    'sublead_bjet_eta',
    'sublead_bjet_phi',
    'sublead_bjet_PNetB',
    'lead_bjet_PNetB',
    'CosThetaStar_gg',
    'CosThetaStar_jj',
    'CosThetaStar_CS',
    'DeltaR_jg_min',
    'pholead_PtOverM',
    'phosublead_PtOverM',
    'FirstJet_PtOverM',
    'SecondJet_PtOverM',
    'lead_pt_over_diphoton_mass',
    'sublead_pt_over_diphoton_mass',
    'lead_pt_over_dibjet_mass',
    'sublead_pt_over_dibjet_mass',
    'diphoton_bbgg_mass',
    'dibjet_bbgg_mass',
]

X = combined_df[features]
y = combined_df['label']
weight = combined_df['weight_preselection']

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

X_train, X_test, y_train, y_test = train_test_split(combined_df[features], combined_df['label'], test_size=0.2, random_state=42, stratify=combined_df['label'])

# Extract the weights for train and test datasets
X_train_weights = combined_df.loc[X_train.index, 'weight_preselection']  # Weight provided as the DNN weight 
X_test_weights = combined_df.loc[X_test.index, 'weight_preselection']

# Impute and scale the features
imputer = SimpleImputer(strategy='mean')
X_train_imputed = imputer.fit_transform(X_train)
X_test_imputed = imputer.transform(X_test)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_imputed)
X_test_scaled = scaler.transform(X_test_imputed)

# Convert to torch tensors
X_train_tensor = torch.tensor(X_train_scaled, dtype=torch.float32)
X_test_tensor = torch.tensor(X_test_scaled, dtype=torch.float32)
y_train_tensor = torch.tensor(y_train.values, dtype=torch.long)
y_test_tensor = torch.tensor(y_test.values, dtype=torch.long)
X_train_weights_tensor = torch.tensor(X_train_weights.values, dtype=torch.float32)
X_test_weights_tensor = torch.tensor(X_test_weights.values, dtype=torch.float32)

# Create TensorDataset and DataLoader
train_data = TensorDataset(X_train_tensor, y_train_tensor, X_train_weights_tensor)
test_data = TensorDataset(X_test_tensor, y_test_tensor, X_test_weights_tensor)

train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
test_loader = DataLoader(test_data, batch_size=32, shuffle=False)

class DNN(nn.Module):
    def __init__(self):
        super(DNN, self).__init__()
        self.fc1 = nn.Linear(len(features), 128)
        self.bn1 = nn.BatchNorm1d(128)
        self.fc2 = nn.Linear(128, 64)
        self.dropout = nn.Dropout(0.5)
        self.bn2 = nn.BatchNorm1d(64)
        self.fc3 = nn.Linear(64, 32)
        self.dropout = nn.Dropout(0.5)
        self.bn3 = nn.BatchNorm1d(32)
        self.fc4 = nn.Linear(32, 32)
        self.dropout = nn.Dropout(0.5)
        self.bn4 = nn.BatchNorm1d(32)
        self.fc5 = nn.Linear(32, 16)
        self.dropout = nn.Dropout(0.5)
        self.bn5 = nn.BatchNorm1d(16)
        self.fc6 = nn.Linear(16, 8)
        self.dropout = nn.Dropout(0.5)
        self.bn6 = nn.BatchNorm1d(8)
        self.fc7 = nn.Linear(8, 1)
        self.dropout = nn.Dropout(0.5)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.relu(self.fc3(x))
        x = self.dropout(x)
        x = torch.relu(self.fc4(x))
        x = self.dropout(x)
        x = torch.relu(self.fc5(x))
        x = self.dropout(x)
        x = torch.relu(self.fc6(x))
        x = self.dropout(x)
        x = self.sigmoid(self.fc7(x))
        return x

model = DNN()

# Save model summary to file
with open("bdtplots/dnn/model_summary.txt", "w") as f:
    summary(model, input_size=(1, X_train.shape[1]), file=f)

criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

num_epochs = 50
train_losses = []
train_accuracy = []

# Early stopping parameters
early_stopping_patience = 10
best_loss = float('inf')
epochs_no_improve = 0

# Training loop with early stopping
for epoch in range(num_epochs):
    model.train()
    epoch_loss = 0.0
    correct = 0.0
    total = 0.0
    for X_batch, y_batch, weights_batch in train_loader:
        optimizer.zero_grad()
        outputs = model(X_batch).squeeze()
        loss = criterion(outputs, y_batch.float())
        weighted_loss = loss * weights_batch
        weighted_loss.mean().backward()
        optimizer.step()
        
        # Training accuracy
        predicted = (outputs > 0.5).float()
        correct += (predicted == y_batch).sum().item()
        total += y_batch.size(0)

        epoch_loss += weighted_loss.mean().item()

    train_losses.append(epoch_loss / len(train_loader))
    train_accuracy.append(correct / total)

    print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {train_losses[-1]:.4f}, Accuracy: {train_accuracy[-1]*100:.2f}%')

    # Early stopping
    if train_losses[-1] < best_loss:
        best_loss = train_losses[-1]
        epochs_no_improve = 0
        torch.save(model.state_dict(), 'best_model.pt')  # Save the best model
    else:
        epochs_no_improve += 1

    if epochs_no_improve == early_stopping_patience:
        print("Early stopping")
        break

# Load the best model
model.load_state_dict(torch.load('best_model.pt'))

# Model prediction and evaluation
model.eval()
with torch.no_grad():
    y_train_pred = model(X_train_tensor).squeeze().numpy()
    y_test_pred = model(X_test_tensor).squeeze().numpy()

y_train_pred_class = (y_train_pred > 0.5).astype(int)
y_test_pred_class = (y_test_pred > 0.5).astype(int)

## Classifier output plot with grids
#plt.figure(figsize=(10, 8))
#plt.hist(y_train_pred[y_train == 1], bins=30, color='blue', alpha=0.5, label='S (Train)', density=True)
#plt.hist(y_train_pred[y_train == 0], bins=30, color='red', alpha=0.5, label='R (Train)', density=True)
#plt.scatter(y_test_pred[y_test == 1], np.full(y_test[y_test == 1].shape, -0.01), color='blue', label='S (Test)', marker='o', s=20)
#plt.scatter(y_test_pred[y_test == 0], np.full(y_test[y_test == 0].shape, -0.01), color='red', label='R (Test)', marker='o', s=20)
#plt.axvline(0.5, color='k', linestyle='--')
#plt.xlabel('Classifier Output')
#plt.ylabel('Density')
#plt.legend()
#plt.title('Classifier Output Plot')
#plt.grid(True)
#plt.savefig("bdtplots/dnn/classifier_output_plot.png")
#plt.savefig("bdtplots/dnn/classifier_output_plot.pdf")
#plt.close()

# Classifier output plot
plt.figure(figsize=(10, 8))
bins = np.linspace(0, 1, 20)
plt.hist(y_train_pred[y_train == 1], bins=bins, color='blue', alpha=0.5, label='S (Train)', density=True, histtype='stepfilled')
plt.hist(y_train_pred[y_train == 0], bins=bins, color='red', alpha=0.5, label='R (Train)', density=True, histtype='stepfilled')

# Scatter plot for test data
plt.scatter(y_test_pred[y_test == 1], np.full(y_test[y_test == 1].shape, -0.02), color='blue', label='S (Test)', marker='o', s=100, edgecolor='k')
plt.scatter(y_test_pred[y_test == 0], np.full(y_test[y_test == 0].shape, -0.02), color='red', label='R (Test)', marker='o', s=100, edgecolor='k')

plt.axvline(0.5, color='k', linestyle='--')
plt.xlabel('Classifier Output')
plt.ylabel('Density')
plt.legend()
plt.title('Classifier Output Plot')
plt.grid(True)
plt.savefig("bdtplots/dnn/classifier_output_plot.png")
plt.savefig("bdtplots/dnn/classifier_output_plot.pdf")
plt.show()



# Confusion Matrix
conf_matrix = pd.crosstab(y_test, y_test_pred_class, rownames=['Actual'], colnames=['Predicted'])
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix')
plt.savefig("bdtplots/dnn/confusion_matrix.png")
plt.savefig("bdtplots/dnn/confusion_matrix.pdf")
plt.close()

# ROC Curve
fpr, tpr, thresholds = roc_curve(y_test, y_test_pred)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(10, 8))
plt.plot(fpr, tpr, color='blue', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc="lower right")
plt.grid(True)
plt.savefig("bdtplots/dnn/roc_curve.png")
plt.savefig("bdtplots/dnn/roc_curve.pdf")
plt.close()

print("Accuracy on test set:", accuracy_score(y_test, y_test_pred_class))
print("ROC AUC on test set:", roc_auc_score(y_test, y_test_pred))
print(classification_report(y_test, y_test_pred_class))

# Plot training accuracy over epochs
plt.figure(figsize=(10, 6))
plt.plot(range(1, len(train_accuracy) + 1), train_accuracy, label='Training Accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.title('Training Accuracy Over Epochs')
plt.legend()
plt.grid(True)
plt.savefig("bdtplots/dnn/training_accuracy.png")
plt.close()

