# Required imports
import os
import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# File paths
 data_combinations = {
    "lowX_lowY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y70/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y70/preselection"),
        ]
    },
    "lowX_midY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y90/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y90/preselection"),
        ]
    },
    "lowX_highY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y100/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y100/preselection"),
        ]
    },

    "midX_midY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X500_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X500_Y90/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X550_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X550_Y90/preselection"),
        ]
    },
    "midX_lowY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X500_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X500_Y70/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X550_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X550_Y70/preselection"),
        ]
    },
    "midX_highY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X300_Y100/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X400_Y100/preselection"),
        ]
    },
    "highX_lowY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X600_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X600_Y70/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X650_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X650_Y70/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X700_Y60/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X700_Y70/preselection"),
        ]
    },
    "highX_midY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X600_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X600_Y90/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X650_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X650_Y90/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X700_Y80/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X700_Y90/preselection"),
        ]
    },
    "highX_highY": {
        "signal_files": [
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X600_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X600_Y100/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X650_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X650_Y100/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X700_Y95/preselection"),
            ("../../outputfiles/hhbbgg_analyzerNMSSM-trees.root", "/NMSSM_X700_Y100/preselection"),
        ]
    },
}

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
signal_df_3 = dfs.get("/NMSSM_X400_Y60/preselection", pd.DataFrame())
signal_df_4 = dfs.get("/NMSSM_X400_Y70/preselection", pd.DataFrame())

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
signal_df = pd.concat([signal_df_1, signal_df_2, signal_df_3, signal_df_4], ignore_index=True)
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

# Required imports
import os
import pandas as pd
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Define a simple neural network model
class SimpleDNN(nn.Module):
    def __init__(self, input_dim):
        super(SimpleDNN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # For binary classification
        )

    def forward(self, x):
        return self.network(x)

# Define configurations for each combination of X and Y values
data_combinations = {
    # Add the existing data_combinations here...
}

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

def load_data(signal_files, background_files):
    """
    Load and prepare the data for training.
    """
    dfs = {}
    # Load signal files
    for file, key in signal_files:
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

    # Extract signal and background DataFrames
    signal_df = pd.concat([dfs[key] for key in dfs if 'NMSSM' in key], ignore_index=True)
    background_df = pd.concat([dfs[key] for key in dfs if 'GGJet' in key or 'GJetPt' in key], ignore_index=True)

    # Combine signal and background DataFrames
    signal_df['label'] = 1
    background_df['label'] = 0
    combined_df = pd.concat([signal_df, background_df], ignore_index=True)

    return combined_df, signal_df, background_df

# Load the data
combined_df, signal_df, background_df = load_data(
    data_combinations['lowX_lowY']['signal_files'], background_files
)

# Check if 'weight_preselection' exists in all DataFrames
if 'weight_preselection' not in signal_df.columns or 'weight_preselection' not in background_df.columns:
    print("Error: 'weight_preselection' column missing in one or more DataFrames.")
    exit()

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

def prepare_data(df):
    """
    Prepare data: impute missing values, scale, and split into train/test sets.
    """
    X = df[features]
    y = df['label']
    weights = df['weight_preselection']

    # Split into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Extract the weights for train and test datasets
    X_train_weights = df.loc[X_train.index, 'weight_preselection']
    X_test_weights = df.loc[X_test.index, 'weight_preselection']

    # Impute and scale the features
    imputer = SimpleImputer(strategy='mean')
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)

    # Convert data to torch tensors
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

    return train_loader, test_loader

# Prepare data
train_loader, test_loader = prepare_data(combined_df)

# Initialize and train the model
input_dim = len(features)
model = SimpleDNN(input_dim)

# Train the model and retrieve loss and accuracy metrics
train_losses, test_losses, train_accuracies, test_accuracies = train_model(
    model, train_loader, test_loader
)

# Plot training and testing accuracy and loss curves
plt.figure(figsize=(14, 6))

# Accuracy plot
plt.subplot(1, 2, 1)
plt.plot(train_accuracies, label='Train Accuracy')
plt.plot(test_accuracies, label='Test Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('Model Accuracy')
plt.legend()

# Loss plot
plt.subplot(1, 2, 2)
plt.plot(train_losses, label='Train Loss')
plt.plot(test_losses, label='Test Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Model Loss')
plt.legend()

plt.tight_layout()
plt.savefig('accuracy_loss_curves.png')
print("Accuracy and loss curves saved as 'accuracy_loss_curves.png'.")

from sklearn.metrics import roc_curve, roc_auc_score

# Function to plot ROC curve
def plot_roc_curve(y_true, y_preds, weights, title, filename):
    fpr, tpr, _ = roc_curve(y_true, y_preds, sample_weight=weights)
    auc_score = roc_auc_score(y_true, y_preds, sample_weight=weights)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='blue', lw=2, label=f'AUC = {auc_score:.3f}')
    plt.plot([0, 1], [0, 1], color='gray', linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(title)
    plt.legend(loc='lower right')
    plt.grid()
    plt.savefig(filename)
    plt.close()
    print(f"ROC curve saved as '{filename}'.")

# Predictions and true values for ROC curve plotting
model.eval()
train_true = []
train_preds = []
train_weights = []
test_true = []
test_preds = []
test_weights = []

# Collect predictions and labels for training data
with torch.no_grad():
    for X_batch, y_batch, weights in train_loader:
        outputs = model(X_batch).squeeze()
        predictions = outputs.numpy()
        train_preds.extend(predictions)
        train_true.extend(y_batch.numpy())
        train_weights.extend(weights.numpy())

# Collect predictions and labels for test data
with torch.no_grad():
    for X_batch, y_batch, weights in test_loader:
        outputs = model(X_batch).squeeze()
        predictions = outputs.numpy()
        test_preds.extend(predictions)
        test_true.extend(y_batch.numpy())
        test_weights.extend(weights.numpy())

# Convert lists to numpy arrays
train_true = np.array(train_true)
train_preds = np.array(train_preds)
train_weights = np.array(train_weights)
test_true = np.array(test_true)
test_preds = np.array(test_preds)
test_weights = np.array(test_weights)

# Plot ROC curves for training and testing datasets
plot_roc_curve(train_true, train_preds, train_weights, title='ROC Curve - Training Data', filename='roc_curve_train.png')
plot_roc_curve(test_true, test_preds, test_weights, title='ROC Curve - Test Data', filename='roc_curve_test.png')



import numpy as np
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

# Function to get predictions from the model
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

# Define the function to plot ROC curves
def plot_roc_curve(true_labels, predictions, weights, title, filename):
    fpr, tpr, _ = roc_curve(true_labels, predictions, sample_weight=weights)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(10, 8))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(title)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(filename)
    print(f"ROC Curve saved as '{filename}'.")

# Get predictions for training and test data
train_preds, train_true = get_predictions(train_loader, model)
test_preds, test_true = get_predictions(test_loader, model)

# Convert weights tensors to NumPy arrays
X_train_weights_np = X_train_weights_tensor.numpy()
X_test_weights_np = X_test_weights_tensor.numpy()

# Define bins for histograms
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

# Add background colors and vertical line
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

# Plot ROC curves for training and testing datasets
plot_roc_curve(train_true, train_preds, X_train_weights_np, title='ROC Curve - Training Data', filename='roc_curve_train.png')
plot_roc_curve(test_true, test_preds, X_test_weights_np, title='ROC Curve - Test Data', filename='roc_curve_test.png')

