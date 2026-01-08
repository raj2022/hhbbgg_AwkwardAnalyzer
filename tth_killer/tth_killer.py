# ================================================================
# ttH KILLER DNN (Binary)
# CMS-style auxiliary classifier for resonant HH → bbγγ
# Shivam Raj
# ================================================================

import os, warnings, pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, roc_curve

warnings.filterwarnings("ignore")

# ------------------------------------------------
# Config
# ------------------------------------------------
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {DEVICE}")

BASE = "/afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE"

SAMPLES = {
    "ttHToGG.parquet": 1,
    "TTGG.parquet": 0,
    "VHToGG.parquet": 0,
    "VBFHToGG.parquet": 0,
    "GluGluHToGG.parquet": 0,
}

WEIGHT_COL = "weight_central"

FEATURES = [
    # photons
    "lead_eta","lead_phi","sublead_eta","sublead_phi",

    # jets / topology
    "Res_lead_bjet_eta","Res_sublead_bjet_eta",
    "Res_DeltaR_jg_min","Res_DeltaR_j1g1","Res_DeltaR_j2g2",

    # helicity
    "Res_CosThetaStar_gg","Res_CosThetaStar_jj",

    # event activity (ttH-critical)
    "n_jets","n_leptons","puppiMET_pt",

    # topness
    "Res_chi_t0","Res_chi_t1",

    # b-tag
    "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
]

# ------------------------------------------------
# Load data
# ------------------------------------------------
dfs = []
for fname, label in SAMPLES.items():
    fpath = os.path.join(BASE, fname)
    if not os.path.exists(fpath):
        print(f"[WARN] Missing {fname}")
        continue

    df = pd.read_parquet(fpath)

    # keep only features that exist
    cols = [c for c in FEATURES if c in df.columns]
    df = df[cols].copy()

    if WEIGHT_COL not in df.columns:
        df[WEIGHT_COL] = 1.0

    df["label"] = label
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)
print("\n[INFO] Class balance:")
print(df_all["label"].value_counts())

# ------------------------------------------------
# Arrays + split
# ------------------------------------------------
X = df_all[FEATURES].fillna(0).values.astype("float32")
y = df_all["label"].values.astype("int64")
w = df_all[WEIGHT_COL].values.astype("float32")

X_tr, X_va, y_tr, y_va, w_tr, w_va = train_test_split(
    X, y, w,
    test_size=0.25,
    stratify=y,
    random_state=SEED
)

scaler = StandardScaler()
X_tr = scaler.fit_transform(X_tr)
X_va = scaler.transform(X_va)

with open("scaler_tth.pkl", "wb") as f:
    pickle.dump(scaler, f)

# ------------------------------------------------
# Dataset
# ------------------------------------------------
class ArrayDataset(Dataset):
    def __init__(self, X, y, w):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)
        self.w = torch.tensor(w, dtype=torch.float32)

    def __len__(self): 
        return len(self.X)

    def __getitem__(self, i):
        return self.X[i], self.y[i], self.w[i]

train_loader = DataLoader(
    ArrayDataset(X_tr, y_tr, w_tr),
    batch_size=256,
    shuffle=True
)

# ------------------------------------------------
# Model
# ------------------------------------------------
class TTHKiller(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.net(x).view(-1)

model = TTHKiller(X_tr.shape[1]).to(DEVICE)
criterion = nn.BCEWithLogitsLoss(reduction="none")
optimizer = Adam(model.parameters(), lr=1e-3)

# ------------------------------------------------
# Training
# ------------------------------------------------
best_auc = -np.inf

for epoch in range(50):
    model.train()
    total_loss = 0.0
    n_seen = 0

    for xb, yb, wb in train_loader:
        xb, yb, wb = xb.to(DEVICE), yb.to(DEVICE), wb.to(DEVICE)

        optimizer.zero_grad()
        logits = model(xb)
        loss = (criterion(logits, yb) * wb).mean()
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * xb.size(0)
        n_seen += xb.size(0)

    train_loss = total_loss / max(n_seen, 1)

    model.eval()
    with torch.no_grad():
        p_va = torch.sigmoid(
            model(torch.tensor(X_va, device=DEVICE))
        ).cpu().numpy()

    auc = roc_auc_score(y_va, p_va, sample_weight=w_va)
    print(f"Epoch {epoch:03d} | TrainLoss={train_loss:.4f} | ValAUC={auc:.4f}")

    if auc > best_auc:
        best_auc = auc
        torch.save(model.state_dict(), "best_tth_killer.pt")

print(f"\n[INFO] Best validation AUC = {best_auc:.4f}")

# ------------------------------------------------
# Evaluation
# ------------------------------------------------
model.load_state_dict(torch.load("best_tth_killer.pt", map_location=DEVICE))
model.eval()

with torch.no_grad():
    tth_score = torch.sigmoid(
        model(torch.tensor(X_va, device=DEVICE))
    ).cpu().numpy()

mask_tth = (y_va == 1)
mask_bkg = (y_va == 0)

w_tth = w_va[mask_tth]
w_bkg = w_va[mask_bkg]

# ------------------------------------------------
# ROC
# ------------------------------------------------
fpr, tpr, _ = roc_curve(y_va, tth_score, sample_weight=w_va)

plt.figure(figsize=(6,5))
plt.plot(fpr, tpr, lw=2, label=f"AUC = {best_auc:.3f}")
plt.plot([0,1],[0,1],'k--')
plt.xlabel("Non-ttH efficiency")
plt.ylabel("ttH efficiency")
plt.title("ttH Killer ROC")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# ------------------------------------------------
# Score distributions
# ------------------------------------------------
bins = np.linspace(0,1,50)

# Weighted (log-y)
plt.figure(figsize=(7,5))
plt.hist(tth_score[mask_tth], bins=bins, weights=w_tth,
         histtype="step", lw=2, label="ttH")
plt.hist(tth_score[mask_bkg], bins=bins, weights=w_bkg,
         histtype="step", lw=2, label="Other resonant Higgs")
plt.yscale("log")
plt.xlabel("ttH killer score")
plt.ylabel("Weighted events")
plt.title("ttH Killer Output (Weighted)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

# Shape-normalized
plt.figure(figsize=(7,5))
plt.hist(tth_score[mask_tth], bins=bins, weights=w_tth, density=True,
         histtype="step", lw=2, label="ttH")
plt.hist(tth_score[mask_bkg], bins=bins, weights=w_bkg, density=True,
         histtype="step", lw=2, label="Other resonant Higgs")
plt.xlabel("ttH killer score")
plt.ylabel("Arbitrary units")
plt.title("ttH Killer Output (Shape Normalized)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("~/tth_killer_score_distribution.png", dpi=150)
plt.show()

# ------------------------------------------------
# Working points (Loose / Medium / Tight)
# ------------------------------------------------
cuts = np.linspace(0.0, 1.0, 2000)

def weighted_eff(scores, weights, cut):
    return np.sum(weights[scores < cut]) / np.sum(weights)

eff_tth = np.array([weighted_eff(tth_score[mask_tth], w_tth, c) for c in cuts])
eff_bkg = np.array([weighted_eff(tth_score[mask_bkg], w_bkg, c) for c in cuts])

def find_wp(target, cuts, effs):
    idx = np.argmin(np.abs(effs - target))
    return cuts[idx], effs[idx]

WP_TARGETS = {
    "Loose": 0.50,
    "Medium": 0.20,
    "Tight": 0.10,
}

wps = {}

print("\n[ttH killer working points]")
print("WP       cut    ε(ttH)  ε(other Higgs)")
print("--------------------------------------")

for name, target in WP_TARGETS.items():
    cut, eff = find_wp(target, cuts, eff_tth)
    bkg_eff = weighted_eff(tth_score[mask_bkg], w_bkg, cut)
    wps[name] = cut
    print(f"{name:6s}  {cut:5.3f}   {eff:5.3f}     {bkg_eff:5.3f}")

# ------------------------------------------------
# Efficiency vs cut
# ------------------------------------------------
plt.figure(figsize=(7,5))
plt.plot(cuts, eff_tth, label="ttH efficiency", lw=2)
plt.plot(cuts, eff_bkg, label="Other resonant Higgs efficiency", lw=2)
plt.xlabel("ttH killer cut (score < cut)")
plt.ylabel("Efficiency")
plt.title("Efficiency vs ttH Killer Cut")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
