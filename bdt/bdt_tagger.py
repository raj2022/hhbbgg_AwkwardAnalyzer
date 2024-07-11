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

print(signal_df.shape)
print(background_df_1.shape)
print(background_df_2.shape)
print(background_df_3.shape)

background_df = pd.concat([background_df_1, background_df_2, background_df_3], ignore_index=True)

signal_df['label'] = 1
background_df['label'] = 0

combined_df = pd.concat([signal_df, background_df], ignore_index=True)
print(combined_df.shape)

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

# Check dataset size
print(f"Total samples: {len(X)}")

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

# Check for a sufficient number of events for training and testing
if len(X) > 100:
    test_size = 0.2
else:
    test_size = 0.5  # Use a higher test size if the dataset is small

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=test_size, random_state=42)

print(f"X_train Shape:", X_train.shape)
print(f"X_test Shape:", X_test.shape)
print(f"y_train Shape:", y_train.shape)
print(f"y_test Shape:", y_test.shape)

print(f"Total samples for training: {len(X_train)}")
print(f"Total samples for testing: {len(X_test)}")


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

y_train_pred = best_model.predict(X_train)
y_test_pred = best_model.predict(X_test)

y_train_scores = best_model.predict_proba(X_train)[:, 1]
y_test_scores = best_model.predict_proba(X_test)[:, 1]

# Classifier output plot
plt.figure(figsize=(10, 8))
plt.hist(y_train_scores[y_train == 1], bins=20, color='blue', alpha=0.5, label='S (Train)', density=True)
plt.hist(y_train_scores[y_train == 0], bins=20, color='red', alpha=0.5, label='R (Train)', density=True)
plt.scatter(y_test_scores[y_test == 1], np.full(y_test[y_test == 1].shape, -0.01), color='blue', label='S (Test)')
plt.scatter(y_test_scores[y_test == 0], np.full(y_test[y_test == 0].shape, -0.01), color='red', label='R (Test)')
plt.xlabel('Classifier output')
plt.ylabel('Normalized Yields')
plt.title('Classification with scikit-learn')
plt.legend()
plt.grid(True)
plt.show()

# ROC curve
fpr, tpr, thresholds = roc_curve(y_test, y_test_scores)
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
plt.show()

print("Best parameters:", grid_search.best_params_)
print("Accuracy on test set:", accuracy_score(y_test, y_test_pred))
print("ROC AUC on test set:", roc_auc_score(y_test, y_test_scores))
print(classification_report(y_test, y_test_pred))

#---------------------------

y_scores = best_model.predict_proba(X_test)[:, 1]

fpr, tpr, _ = roc_curve(y_test, y_scores)


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



#--------------------
# Save the plot to a file
plt.savefig('bdtplots/bdt/roc_curve.png')
plt.savefig('bdtplots/bdt/roc_curve.pdf')

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
plt.savefig('bdtplots/bdt/feature_importances.png')
plt.savefig('bdtplots/bdt/feature_importances.pdf')

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
plt.savefig('bdtplots/bdt/top_features_distributions.png')
plt.savefig('bdtplots/bdt/top_features_distributions.pdf')

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
plt.savefig('bdtplots/bdt/decision_scores.png')
plt.savefig('bdtplots/bdt/decision_scores.pdf')

print("Plots have been saved to the 'bdtplots/bdt' directory.")




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
plt.savefig("bdtplots/bdt/Feature_importance.png")
plt.savefig("bdtplots/bdt/Feature_importance.pdf")
