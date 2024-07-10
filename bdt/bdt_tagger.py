## Commments:
##.1 Check with preselection as we have less evetns for the preselection
## 2.


import uproot
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, roc_curve, auc
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

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

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

param_grid = {
    'model__n_estimators': [100, 300, 500],
    'model__learning_rate': [0.01, 0.1, 0.2],
    'model__max_depth': [3, 5, 7, 10],
    'model__min_child_weight': [1, 3, 5],
    'model__gamma': [0, 0.1, 0.2],
    'model__subsample': [0.8, 0.9, 1.0],
    'model__colsample_bytree': [0.8, 0.9, 1.0]
}

pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='mean')),
    ('scaler', MinMaxScaler()),
    ('model', XGBClassifier(use_label_encoder=False, eval_metric='logloss'))
])

grid_search = GridSearchCV(pipeline, param_grid, cv=3, scoring='roc_auc', n_jobs=-1, verbose=2)
grid_search.fit(X_train, y_train)

best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred)

y_scores = best_model.predict_proba(X_test)[:, 1]

fpr, tpr, _ = roc_curve(y_test, y_scores)
roc_auc = auc(fpr, tpr)

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

# Plot feature importances
importances = best_model.named_steps['model'].feature_importances_
indices = np.argsort(importances)[::-1]

plt.figure(figsize=(12, 8))
plt.title("Feature Importances")
plt.bar(range(X.shape[1]), importances[indices], align="center")
plt.xticks(range(X.shape[1]), [features[i] for i in indices], rotation=90)
plt.xlim([-1, X.shape[1]])
plt.tight_layout()

# Save the plot to a file
plt.savefig('bdtplots/feature_importances.png')
plt.savefig('bdtplots/feature_importances.pdf')

# Plot distribution of the top 5 important features for both signal and background
top_features = [features[i] for i in indices[:5]]

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

for i, feature in enumerate(top_features):
    sns.histplot(signal_df[feature], color="blue", label="Signal", kde=True, ax=axes[i], stat="density")
    sns.histplot(background_df[feature], color="red", label="Background", kde=True, ax=axes[i], stat="density")
    axes[i].set_title(f"Distribution of {feature}")
    axes[i].legend()

plt.tight_layout()

# Save the plots to files
plt.savefig('bdtplots/top_features_distributions.png')
plt.savefig('bdtplots/top_features_distributions.pdf')

# Plot decision scores for signal and background
signal_indices = combined_df[combined_df['label'] == 1].index
background_indices = combined_df[combined_df['label'] == 0].index

y_scores_signal = best_model.predict_proba(X_scaled[signal_indices])[:, 1]
y_scores_background = best_model.predict_proba(X_scaled[background_indices])[:, 1]

plt.figure(figsize=(12, 8))
sns.histplot(y_scores_signal, color="blue", label="Signal", kde=True, stat="density", bins=10)
sns.histplot(y_scores_background, color="red", label="Background", kde=True, stat="density", bins=10)
plt.xlabel("Decision Score")
plt.ylabel("Density")
plt.title("Decision Scores for Signal and Background")
plt.legend()
plt.grid(True)

# Save the plot to a file
plt.savefig('bdtplots/decision_scores.png')
plt.savefig('bdtplots/decision_scores.pdf')

print("Plots have been saved to the 'bdtplots' directory.")




print("------------------------------------")

best_model.fit(X_train, y_train)

# Plot feature importance
feature_importance = best_model.named_steps['model'].feature_importances_
feature_names = features

plt.figure(figsize=(10, 8))
sns.barplot(x=feature_importance, y=feature_names, palette='viridis')
plt.xlabel('Feature Importance Score')
plt.ylabel('Features')
plt.title('Feature Importance')
plt.grid(True)
plt.savefig("bdtplots/Feature_importance.png")
plt.savefig("bdtplots/Feature_importance.pdf")
