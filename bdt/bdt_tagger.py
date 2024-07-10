import numpy as np
import uproot
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import roc_curve, auc  # Add this line


# File and tree names
file_path = '../outputfiles/hhbbgg_analyzer-histograms.root'
sig_treename = 'GluGluToHH'
bkg_treename_1 = 'GGJets'
bkg_treename_2 = 'GJetPt20To40'
bkg_treename_3 = 'GJetPt40'

# Keys
keys = [
    'srbbgg-dibjet_mass',
    'srbbgg-diphoton_mass',
    'srbbgg-bbgg_mass',
    'srbbgg-dibjet_pt',
    'srbbgg-diphoton_pt',
    'srbbgg-bbgg_pt',
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

X = combined_df[features]
y = combined_df['label']

# Handle missing values using SimpleImputer before scaling
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

# Standardizing the data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

# Splitting the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Train the classifier
model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.1, max_depth=4)
model.fit(X_train, y_train)

# Predict probabilities
y_train_scores = model.predict_proba(X_train)[:, 1]
y_test_scores = model.predict_proba(X_test)[:, 1]

# Plotting
bins = np.linspace(0, 1, 50)

plt.figure(figsize=(8, 6))

# Train signal
train_sig_hist, _ = np.histogram(y_train_scores[y_train == 1], bins=bins, density=True)
train_bkg_hist, _ = np.histogram(y_train_scores[y_train == 0], bins=bins, density=True)

# Test signal
test_sig_hist, _ = np.histogram(y_test_scores[y_test == 1], bins=bins, density=True)
test_bkg_hist, _ = np.histogram(y_test_scores[y_test == 0], bins=bins, density=True)

bin_centers = 0.5 * (bins[1:] + bins[:-1])

# Plot histograms with error bars
plt.errorbar(bin_centers, train_sig_hist, yerr=np.sqrt(train_sig_hist), fmt='o', label='S (Train)', color='blue')
plt.errorbar(bin_centers, test_sig_hist, yerr=np.sqrt(test_sig_hist), fmt='^', label='S (Test)', color='blue', alpha=0.7)
plt.errorbar(bin_centers, train_bkg_hist, yerr=np.sqrt(train_bkg_hist), fmt='o', label='R (Train)', color='red')
plt.errorbar(bin_centers, test_bkg_hist, yerr=np.sqrt(test_bkg_hist), fmt='^', label='R (Test)', color='red', alpha=0.7)

plt.fill_between(bin_centers, train_sig_hist, step='mid', alpha=0.2, color='blue', lw=0)
plt.fill_between(bin_centers, train_bkg_hist, step='mid', alpha=0.2, color='red', lw=0)

plt.xlabel('Classifier output')
plt.ylabel('Normalized Yields')
plt.title('Classification with scikit-learn')
plt.legend(loc='upper center', frameon=False)
plt.ylim(0, 0.5)
plt.show()

# Plotting functions
def plot_roc_curve(y_true, y_scores, title='ROC Curve'):
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(title)
    plt.legend(loc='lower right')
    plt.show()

def plot_feature_importances(model, feature_names):
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    plt.figure(figsize=(12, 6))
    plt.title('Feature Importances')
    plt.bar(range(len(importances)), importances[indices], align='center')
    plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=90)
    plt.tight_layout()
    plt.show()

plot_roc_curve(y_test, y_test_scores)
plot_feature_importances(model, features)

