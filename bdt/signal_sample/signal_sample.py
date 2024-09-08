
import os
import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_curve, auc, accuracy_score
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam


# File paths
signal_files_lowX_lowY = [
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y60/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y70/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y80/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y90/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y95/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y100/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y60/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y70/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y80/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y90/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y95/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y100/preselection"),
]
background_files = [
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/GGJets/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/GJetPt20To40/preselection"),
    ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/GJetPt40/preselection"),
]

keys = [
    'bbgg_mass', 'dibjet_pt', 'diphoton_pt', 'bbgg_pt', 'bbgg_eta', 'bbgg_phi',
    'lead_pho_eta', 'lead_pho_phi', 'sublead_pho_eta', 'sublead_pho_phi', 'diphoton_eta', 
    'diphoton_phi', 'dibjet_eta', 'dibjet_phi', 'lead_bjet_pt', 'sublead_bjet_pt', 
    'lead_bjet_eta', 'lead_bjet_phi', 'sublead_bjet_eta', 'sublead_bjet_phi', 
    'sublead_bjet_PNetB', 'lead_bjet_PNetB', 'CosThetaStar_gg', 'CosThetaStar_jj', 
    'CosThetaStar_CS', 'DeltaR_jg_min', 'pholead_PtOverM', 'phosublead_PtOverM', 
    'FirstJet_PtOverM', 'SecondJet_PtOverM', 'diphoton_bbgg_mass', 'dibjet_bbgg_mass', 
    'weight_preselection',
]

# Load DataFrames
dfs = {}

# Load signal files
for file, key in signal_files_lowX_lowY:
    try:
        with uproot.open(file) as f:
            dfs[key] = f[key].arrays(keys, library="pd")
    except Exception as e:
        print(f"Error loading {file} with key {key}: {e}")

# Load background files
for file, key in background_files:
    try:
        with uproot.open(file) as f:
            dfs[key] = f[key].arrays(keys, library="pd")
    except Exception as e:
        print(f"Error loading {file} with key {key}: {e}")

# Extracting DataFrames
signal_df_1 = dfs.get("/NMSSM_X300_Y60/preselection", pd.DataFrame())
signal_df_2 = dfs.get("/NMSSM_X300_Y70/preselection", pd.DataFrame())
signal_df_3 = dfs.get("/NMSSM_X300_Y80/preselection", pd.DataFrame())
signal_df_4 = dfs.get("/NMSSM_X300_Y90/preselection", pd.DataFrame())
signal_df_5 = dfs.get("/NMSSM_X300_Y95/preselection", pd.DataFrame())
signal_df_6 = dfs.get("/NMSSM_X300_Y100/preselection", pd.DataFrame())
signal_df_7 = dfs.get("/NMSSM_X400_Y60/preselection", pd.DataFrame())
signal_df_8 = dfs.get("/NMSSM_X400_Y70/preselection", pd.DataFrame())
signal_df_9 = dfs.get("/NMSSM_X400_Y80/preselection", pd.DataFrame())
signal_df_10 = dfs.get("/NMSSM_X400_Y90/preselection", pd.DataFrame())
signal_df_11 = dfs.get("/NMSSM_X400_Y95/preselection", pd.DataFrame())
signal_df_12 = dfs.get("/NMSSM_X400_Y100/preselection", pd.DataFrame())

background_df_1 = dfs.get("/GGJets/preselection", pd.DataFrame())
background_df_2 = dfs.get("/GJetPt20To40/preselection", pd.DataFrame())
background_df_3 = dfs.get("/GJetPt40/preselection", pd.DataFrame())

# Print signal samples info
print(f'----------------------------------------------')
print('======== Printing Signal Samples ======')
print('Signal df NMSSM_X300_Y60:', signal_df_1.shape)
print('Signal df NMSSM_X300_Y70:', signal_df_2.shape)
print('Signal df NMSSM_X400_Y60:', signal_df_3.shape)
print('Signal df NMSSM_X400_Y70:', signal_df_4.shape)

# Print background samples info
print(f'----------------------------------------------')
print('======== Printing Background Samples ======')
print('Background df GGJets:', background_df_1.shape)
print('Background df GJetPt20To40:', background_df_2.shape)
print('Background df GJetPt40:', background_df_3.shape)

# Combine background DataFrames
background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)
print('Total Background Shape:', background_df.shape)

# Combine signal DataFrames
signal_df = pd.concat([signal_df_1, signal_df_2, signal_df_3, signal_df_4,
#    signal_df_5, signal_df_6, signal_df_7, signal_df_8, signal_df_9, signal_df_10, signal_df_11, signal_df_12
    ], ignore_index=True)
print('===============================================')
print('Total Background Shape:', background_df.shape)
print('Total Signal Shape:', signal_df.shape)

# Check if 'weight_preselection' exists in all DataFrames
if 'weight_preselection' not in signal_df.columns or 'weight_preselection' not in background_df.columns:
    print("Error: 'weight_preselection' column missing in one or more DataFrames.")
    exit()

# Assign labels
signal_df['label'] = 1
background_df['label'] = 0

# Combine signal and background data
combined_df = pd.concat([signal_df, background_df], ignore_index=True)
print('Combined DataFrame:', combined_df.shape)

# Define features and labels
features = [
    'bbgg_eta', 'bbgg_phi', 'bbgg_mass', 'lead_pho_eta', 'lead_pho_phi', 'sublead_pho_eta', 
    'sublead_pho_phi', 'diphoton_eta', 'diphoton_phi', 'dibjet_eta', 'dibjet_phi', 
    'lead_bjet_pt', 'sublead_bjet_pt', 'lead_bjet_eta', 'lead_bjet_phi', 'sublead_bjet_eta', 
    'sublead_bjet_phi', 'sublead_bjet_PNetB', 'lead_bjet_PNetB', 'CosThetaStar_gg', 
    'CosThetaStar_jj', 'CosThetaStar_CS', 'DeltaR_jg_min', 'pholead_PtOverM', 
    'phosublead_PtOverM', 'FirstJet_PtOverM', 'SecondJet_PtOverM', 'diphoton_bbgg_mass', 
    'dibjet_bbgg_mass'
]

X = combined_df[features]
y = combined_df['label']
weights = combined_df['weight_preselection']

# Impute missing values and scale the data
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

# Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(combined_df[features], combined_df['label'], test_size=0.2, random_state=42, stratify=combined_df['label'])

# Extract the weights for train and test datasets
# Extract the weights for train and test datasets
X_train_weights = combined_df.loc[X_train.index, 'weight_preselection']
X_test_weights = combined_df.loc[X_test.index, 'weight_preselection']

# Impute and scale the features
imputer = SimpleImputer(strategy='mean')
X_train_imputed = imputer.fit_transform(X_train)
X_test_imputed = imputer.transform(X_test)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_imputed)
X_test_scaled = scaler.transform(X_test_imputed)



# Convert data to torch tensors
X_train_tensor = torch.tensor(X_train.values, dtype=torch.float32)
X_test_tensor = torch.tensor(X_test.values, dtype=torch.float32)

y_train_tensor = torch.tensor(y_train.values, dtype=torch.long)
y_test_tensor = torch.tensor(y_test.values, dtype=torch.long)
X_train_weights_tensor = torch.tensor(X_train_weights.values, dtype=torch.float32)
X_test_weights_tensor = torch.tensor(X_test_weights.values, dtype=torch.float32)

# Create TensorDataset and DataLoader
train_data = TensorDataset(X_train_tensor, y_train_tensor, X_train_weights_tensor)
test_data = TensorDataset(X_test_tensor, y_test_tensor, X_test_weights_tensor)

train_loader = DataLoader(train_data, batch_size=32, shuffle=True)
test_loader = DataLoader(test_data, batch_size=32, shuffle=False)

# Define the neural network model
#class SimpleDNN(nn.Module):
#    def __init__(self, input_dim):
#        super(SimpleDNN, self).__init__()
#        self.fc1 = nn.Linear(input_dim, 128)
##        self.bn1 = nn.BatchNorm1d(128)
#        self.fc2 = nn.Linear(128, 64)
##        self.bn2 = nn.BatchNorm1d(64)
#        self.fc3 = nn.Linear(64, 32)
##        self.bn3 = nn.BatchNorm1d(32)
#        self.fc4 = nn.Linear(32, 16)
##        self.dropout = nn.Dropout(0.3)
#        self.output = nn.Linear(16, 1)
#        self.relu = nn.ReLU()
#        self.sigmoid = nn.Sigmoid()
#
#    def forward(self, x):
#        x = self.relu(self.bn1(self.fc1(x)))
##        x = self.dropout(x)
#        x = self.relu(self.bn2(self.fc2(x)))
##        x = self.dropout(x)
#        x = self.relu(self.bn3(self.fc3(x)))
#        x = self.relu(self.fc4(x))
#        x = self.sigmoid(self.output(x))
#        return x
class SimpleDNN(nn.Module):
    def __init__(self, input_dim):
        super(SimpleDNN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 32)
        self.fc4 = nn.Linear(32, 16)
        self.dropout = nn.Dropout(0.3)
        self.output = nn.Linear(16, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.relu(self.fc3(x))
        x = self.relu(self.fc4(x))
        x = self.sigmoid(self.output(x))
        return x

# Initialize the model
input_dim = X_train.shape[1]
model = SimpleDNN(input_dim)

# Load the saved model weights, or handle the case if the file is missing
model_path = 'preselection_simple_dnn_model.pth'

if os.path.exists(model_path):
    try:
        model.load_state_dict(torch.load(model_path))
        model.eval()
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
else:
    print(f"Model file '{model_path}' not found. Please ensure the model is trained and saved at this path.")
    # Optional: Add code here to train the model if needed
    # Example:
    # Train the model here...
    # Save the trained model:
    # torch.save(model.state_dict(), model_path)


# Function to get predictions
def get_predictions(loader, model):
    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for inputs, labels, _ in loader:
            outputs = model(inputs)
            outputs = outputs.squeeze()
            all_preds.extend(outputs.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    return np.array(all_preds), np.array(all_labels)

# Get predictions for training and test data
train_preds, train_true = get_predictions(train_loader, model)
test_preds, test_true = get_predictions(test_loader, model)

# Convert weights tensors to NumPy arrays
X_train_weights_np = X_train_weights_tensor.numpy()
X_test_weights_np = X_test_weights_tensor.numpy()

# Define bins
bins = np.linspace(0, 1, 31)

# Plot histograms for training data
plt.figure(figsize=(10, 8))
plt.hist(train_preds[train_true == 1], bins=bins, color='blue', alpha=0.5, label='Signal (Train)', density=True, weights=X_train_weights_np[train_true == 1])
plt.hist(train_preds[train_true == 0], bins=bins, color='red', alpha=0.5, label='Background (Train)', density=True, weights=X_train_weights_np[train_true == 0])

# Calculate histograms for test data
test_hist_s, _ = np.histogram(test_preds[test_true == 1], bins=bins, density=True, weights=X_test_weights_np[test_true == 1])
test_hist_b, _ = np.histogram(test_preds[test_true == 0], bins=bins, density=True, weights=X_test_weights_np[test_true == 0])

# Plot scatter points for test data
plt.scatter((bins[:-1] + bins[1:]) / 2, test_hist_s, color='blue', alpha=0.7, label='Signal (Test)', marker='o', s=30, edgecolor='k')
plt.scatter((bins[:-1] + bins[1:]) / 2, test_hist_b, color='red', alpha=0.7, label='Background (Test)', marker='o', s=30, edgecolor='k')

# Add background colors
plt.axvspan(0, 0.5, color='red', alpha=0.1)
plt.axvspan(0.5, 1, color='blue', alpha=0.1)

plt.axvline(0.5, color='k', linestyle='--')
plt.xlabel('Classifier output')
plt.ylabel('Normalized Yields')
plt.xlim(0, 1)
plt.legend()
plt.title('Classifier Output with PyTorch')
plt.tight_layout()
# Save the plot instead of showing it interactively
plt.savefig('classifier_output.png')
print("Plot saved as 'classifier_output.png'.")
#plt.show()






# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# File paths and data loading omitted for brevity; assume it's the same as your code above.

# Define the neural network model
class SimpleDNN(nn.Module):
    def __init__(self, input_dim):
        super(SimpleDNN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.bn1 = nn.BatchNorm1d(128)
        self.fc2 = nn.Linear(128, 64)
        self.bn2 = nn.BatchNorm1d(64)
        self.fc3 = nn.Linear(64, 32)
        self.bn3 = nn.BatchNorm1d(32)
        self.fc4 = nn.Linear(32, 16)
        self.dropout = nn.Dropout(0.3)
        self.output = nn.Linear(16, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.bn1(self.fc1(x)))
        x = self.dropout(x)
        x = self.relu(self.bn2(self.fc2(x)))
        x = self.dropout(x)
        x = self.relu(self.bn3(self.fc3(x)))
        x = self.relu(self.fc4(x))
        x = self.sigmoid(self.output(x))
        return x

# Initialize the model
input_dim = X_train.shape[1]
model = SimpleDNN(input_dim).to(device)

# Training settings
criterion = nn.BCELoss(reduction='none')
optimizer = Adam(model.parameters(), lr=0.001)
num_epochs =50  # Set this to the desired number of epochs

# Function to calculate weighted loss
def weighted_loss(outputs, targets, weights):
    loss = criterion(outputs, targets)
    return torch.mean(loss * weights)

# Training loop with accuracy and loss tracking
train_losses, test_losses, train_accuracies, test_accuracies = [], [], [], []

for epoch in range(num_epochs):
    model.train()
    train_loss, correct, total = 0.0, 0, 0
    for inputs, labels, weights in train_loader:
        inputs, labels, weights = inputs.to(device), labels.to(device).float(), weights.to(device)
        optimizer.zero_grad()
        outputs = model(inputs).squeeze()
        loss = weighted_loss(outputs, labels, weights)
        loss.backward()
        optimizer.step()
        train_loss += loss.item() * inputs.size(0)
        predicted = (outputs > 0.5).float()
        correct += (predicted == labels).sum().item()
        total += labels.size(0)

    train_losses.append(train_loss / total)
    train_accuracies.append(correct / total)

    # Validation step
    model.eval()
    test_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for inputs, labels, weights in test_loader:
            inputs, labels, weights = inputs.to(device), labels.to(device).float(), weights.to(device)
            outputs = model(inputs).squeeze()
            loss = weighted_loss(outputs, labels, weights)
            test_loss += loss.item() * inputs.size(0)
            predicted = (outputs > 0.5).float()
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

    test_losses.append(test_loss / total)
    test_accuracies.append(correct / total)
    print(f"Epoch {epoch + 1}/{num_epochs} - Train Loss: {train_losses[-1]:.4f}, Test Loss: {test_losses[-1]:.4f}, Train Acc: {train_accuracies[-1]:.4f}, Test Acc: {test_accuracies[-1]:.4f}")

# Plot training and validation loss
plt.figure(figsize=(10, 5))
plt.plot(range(1, num_epochs + 1), train_losses, label='Train Loss')
plt.plot(range(1, num_epochs + 1), test_losses, label='Test Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.title('Loss vs. Epochs')
plt.legend()
plt.tight_layout()
plt.savefig('loss_vs_epochs.png')
print("Loss vs. Epochs plot saved as 'loss_vs_epochs.png'.")

# Plot training and validation accuracy
plt.figure(figsize=(10, 5))
plt.plot(range(1, num_epochs + 1), train_accuracies, label='Train Accuracy')
plt.plot(range(1, num_epochs + 1), test_accuracies, label='Test Accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.title('Accuracy vs. Epochs')
plt.legend()
plt.tight_layout()
plt.savefig('accuracy_vs_epochs.png')
print("Accuracy vs. Epochs plot saved as 'accuracy_vs_epochs.png'.")

# Function to get predictions
def get_predictions(loader, model):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for inputs, labels, _ in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs).squeeze()
            all_preds.extend(outputs.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    return np.array(all_preds), np.array(all_labels)

# Get predictions for training and test data
train_preds, train_true = get_predictions(train_loader, model)
test_preds, test_true = get_predictions(test_loader, model)

# Plot ROC curve
fpr, tpr, _ = roc_curve(test_true, test_preds)
roc_auc = auc(fpr, tpr)
plt.figure(figsize=(10, 8))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC Curve (area = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic')
plt.legend(loc='lower right')
plt.tight_layout()
plt.savefig('roc_curve.png')
print("ROC curve plot saved as 'roc_curve.png'.")



# Get predictions for training and test data
train_preds, train_true = get_predictions(train_loader, model)
test_preds, test_true = get_predictions(test_loader, model)

# Convert weights tensors to NumPy arrays
X_train_weights_np = X_train_weights_tensor.numpy()
X_test_weights_np = X_test_weights_tensor.numpy()

# Define bins
bins = np.linspace(0, 1, 31)

# Plot histograms for training data
plt.figure(figsize=(10, 8))
plt.hist(train_preds[train_true == 1], bins=bins, color='blue', alpha=0.5, label='Signal (Train)', density=True, weights=X_train_weights_np[train_true == 1])
plt.hist(train_preds[train_true == 0], bins=bins, color='red', alpha=0.5, label='Background (Train)', density=True, weights=X_train_weights_np[train_true == 0])

# Calculate histograms for test data
test_hist_s, _ = np.histogram(test_preds[test_true == 1], bins=bins, density=True, weights=X_test_weights_np[test_true == 1])
test_hist_b, _ = np.histogram(test_preds[test_true == 0], bins=bins, density=True, weights=X_test_weights_np[test_true == 0])

# Plot scatter points for test data
plt.scatter((bins[:-1] + bins[1:]) / 2, test_hist_s, color='blue', alpha=0.7, label='Signal (Test)', marker='o', s=30, edgecolor='k')
plt.scatter((bins[:-1] + bins[1:]) / 2, test_hist_b, color='red', alpha=0.7, label='Background (Test)', marker='o', s=30, edgecolor='k')

# Add background colors
plt.axvspan(0, 0.5, color='red', alpha=0.1)
plt.axvspan(0.5, 1, color='blue', alpha=0.1)

plt.axvline(0.5, color='k', linestyle='--')
plt.xlabel('Classifier output')
plt.ylabel('Normalized Yields')
plt.xlim(0, 1)
plt.legend()
plt.title('Classifier Output with PyTorch')
plt.tight_layout()
# Save the plot instead of showing it interactively
plt.savefig('classifier_output.png')
print("Plot saved as 'classifier_output.png'.")
#plt.show()



