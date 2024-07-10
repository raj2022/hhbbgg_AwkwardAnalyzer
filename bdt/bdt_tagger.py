import uproot
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

import seaborn as sns
import numpy as np


file_path = '../outputfiles/hhbbgg_analyzer-histograms.root'

sig_treename = 'GluGluToHH'
bkg_treename_1 = 'GGJets'
bkg_treename_2 = 'GJetPt20To40'
bkg_treename_3 = 'GJetPt40'

# keys
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

# Define parameter grid for GridSearchCV
param_grid = {
    'model__n_estimators': [100, 1000],
    'model__learning_rate': [0.001, 0.01, 0.1, 1.0],
    'model__max_depth': [3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40]
}

# Create a pipeline
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', StandardScaler()),
    ('model', GradientBoostingClassifier())
])

# Perform grid search with the pipeline
grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='roc_auc')
grid_search.fit(X_train, y_train)

# Best parameters and model evaluation
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred)

# Get predicted probabilities for positive class
y_scores = best_model.predict_proba(X_test)[:, 1]

# Compute ROC curve and ROC area for each class
fpr, tpr, _ = roc_curve(y_test, y_scores)
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

print(f"Best parameters: {grid_search.best_params_}")
print(f"Accuracy: {accuracy}")
print(f"ROC AUC: {roc_auc}")
print(classification_report(y_test, y_pred))

# Save the plot to a file
plt.savefig('bdtplots/roc_curve.png')
plt.savefig('bdtplots/roc_curve.pdf')

# Show plot
#plt.show()

#-------------------------------

# Plot feature importances
importances = best_model.named_steps['model'].feature_importances_
indices = np.argsort(importances)[::-1]

# Plot the feature importances
plt.figure(figsize=(12, 8))
plt.title("Feature importances")
plt.bar(range(X.shape[1]), importances[indices], color="r", align="center")
plt.xticks(range(X.shape[1]), [features[i] for i in indices], rotation=90)
plt.xlim([-1, X.shape[1]])
plt.show()

# Plot the distributions for the most important features
for feature in [features[i] for i in indices[:5]]:
    plt.figure(figsize=(8, 6))
    sns.kdeplot(signal_df[feature], color='blue', label='Signal', fill=True)
    sns.kdeplot(background_df[feature], color='red', label='Background', fill=True)
    plt.title(f'Distribution of {feature}')
    plt.xlabel(feature)
    plt.ylabel('Density')
    plt.legend()
    plt.savefig("bdtplots/Distribution of {feature}.png")
    plt.savefig("bdtplots/Distribution of {feature}.pdf")
#    plt.show()

#---------------------------

# Feature to plot
feature = 'srbbgg-diphoton_mass'

# Plotting
plt.figure(figsize=(8, 6))

# Plot signal and background distributions
sns.histplot(signal_df[feature], kde=True, stat="density", linewidth=0, label='Signal', color='blue', alpha=0.6)
sns.histplot(background_df[feature], kde=True, stat="density", linewidth=0, label='Background', color='red', alpha=0.6)

# Add labels and title
plt.xlabel(feature)
plt.ylabel('Density')
plt.title(f'Distribution of {feature}')
plt.legend()
plt.grid(True)

# Save the plot to a file
plt.savefig('bdtplots/distribution_plot.png')
plt.savefig('bdtplots/distribution_plot.pdf')


