import os
import uproot
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, roc_curve, auc
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

import matplotlib.pyplot as plt
import seaborn as sns

# File path and tree names
file_path = '../outputfiles/hhbbgg_analyzer-histograms.root'
sig_treename = 'GluGluToHH'
bkg_treename_1 = 'GGJets'
bkg_treename_2 = 'GJetPt20To40'
bkg_treename_3 = 'GJetPt40'

# Features
keys = [
    'srbbgg-dibjet_mass',
    'srbbgg-diphoton_mass',
    'srbbgg-bbgg_mass',
    'srbbgg-dibjet_pt',
    'srbbgg-diphoton_pt',
    'srbbgg-bbgg_pt',
    'srbbgg-lead_pho_pt',
    'srbbgg-sublead_pho_pt',
]

# Load data function
def load_data(file_path, tree_name):
    with uproot.open(file_path) as file:
        tree = file[tree_name]
        df = tree.arrays(library='pd')
    return df

# Load signal and background data
df_sig = load_data(file_path, sig_treename)
df_bkg_1 = load_data(file_path, bkg_treename_1)
df_bkg_2 = load_data(file_path, bkg_treename_2)
df_bkg_3 = load_data(file_path, bkg_treename_3)

# Combine background data
df_bkg = pd.concat([df_bkg_1, df_bkg_2, df_bkg_3])

# Add labels
df_sig['label'] = 1
df_bkg['label'] = 0

# Combine signal and background data
df = pd.concat([df_sig, df_bkg])

# Separate features and labels
X = df[keys]
y = df['label']

# Normalize the features to the range 0 to 1
scaler = MinMaxScaler()
X = scaler.fit_transform(X)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Build a pipeline with imputer and classifier
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('model', GradientBoostingClassifier())
])

# Define the parameter grid for GridSearchCV
param_grid = {
    'model__n_estimators': [100, 200],
    'model__learning_rate': [0.01, 0.1, 0.2],
    'model__max_depth': [3, 4, 5]
}

# Perform grid search
grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='roc_auc')
grid_search.fit(X_train, y_train)

# Get the best parameters and the accuracy
best_params = grid_search.best_params_
best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)
y_proba = best_model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_proba)
report = classification_report(y_test, y_pred)

print(f"Best parameters: {best_params}")
print(f"Accuracy: {accuracy}")
print(f"ROC AUC: {roc_auc}")
print(report)

# Ensure bdtplots directory exists
os.makedirs("bdtplots", exist_ok=True)

# Plot the ROC curve
fpr, tpr, _ = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)

plt.figure()
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic')
plt.legend(loc="lower right")
plt.savefig("bdtplots/roc_curve.png")

# Plot feature importance
importance = best_model.named_steps['model'].feature_importances_
plt.figure()
plt.bar(range(len(importance)), importance)
plt.xlabel('Feature')
plt.ylabel('Importance')
plt.title('Feature Importance')
plt.savefig("bdtplots/feature_importance.png")

# Plot distributions
for feature in keys:
    plt.figure()
    sns.histplot(df_sig[feature], color="blue", label="Signal", kde=True, stat="density")
    sns.histplot(df_bkg[feature], color="red", label="Background", kde=True, stat="density")
    plt.title(f"Distribution of {feature}")
    plt.xlabel(f"{feature}")
    plt.ylabel("Density")
    plt.legend()
    plt.savefig(f"bdtplots/Distribution of {feature}.png")

