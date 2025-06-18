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

# Define configurations for each combination of X and Y values
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



def prepare_data(df):
    """
    Prepare data: impute missing values, scale, and split into train/test sets.
    """
    # Define features and labels
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


def train_model(train_loader, input_dim):
    """
    Train the model.
    """
    # Define the neural network model
    model = SimpleDNN(input_dim)

    # Define loss and optimizer
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    # Training loop
    num_epochs = 20
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        for inputs, labels, weights in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs).squeeze()
            loss = criterion(outputs, labels.float())
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {running_loss / len(train_loader):.4f}")

    return model




# Define training function
def train_model(model, train_loader, test_loader, num_epochs=50, learning_rate=0.001):
    # Define loss function and optimizer
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    train_losses, test_losses, train_accuracies, test_accuracies = [], [], [], []
    
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, labels, weights in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs).squeeze()
            loss = criterion(outputs, labels.float())
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            predicted = (outputs > 0.5).int()
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

        train_losses.append(running_loss / total)
        train_accuracies.append(correct / total)

        # Evaluate on the test set
        model.eval()
        test_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, labels, weights in test_loader:
                outputs = model(inputs).squeeze()
                loss = criterion(outputs, labels.float())
                test_loss += loss.item() * inputs.size(0)
                predicted = (outputs > 0.5).int()
                correct += (predicted == labels).sum().item()
                total += labels.size(0)

        test_losses.append(test_loss / total)
        test_accuracies.append(correct / total)
        
        print(f"Epoch [{epoch+1}/{num_epochs}], Train Loss: {train_losses[-1]:.4f}, Test Loss: {test_losses[-1]:.4f}, Train Acc: {train_accuracies[-1]:.4f}, Test Acc: {test_accuracies[-1]:.4f}")
    
    return train_losses, test_losses, train_accuracies, test_accuracies

# Train the model
train_losses, test_losses, train_accuracies, test_accuracies = train_model(model, train_loader, test_loader)


## Accuracy and loss
# Plot training and testing accuracy
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
    print(f"ROC curve saved as '{filename}'.")

# Plot ROC curve for training and testing data
plot_roc_curve(train_true, train_preds, X_train_weights_np, 'ROC Curve (Train Data)', 'roc_curve_train.png')
plot_roc_curve(test_true, test_preds, X_test_weights_np, 'ROC Curve (Test Data)', 'roc_curve_test.png')


