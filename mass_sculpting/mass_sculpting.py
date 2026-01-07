#!/usr/bin/env python3
# ============================================================
# Mass sculpting check for pDNN (background only)
# HH → bbγγ
# Shivam Raj
# ============================================================

import os
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn

# ============================================================
# Paths
# ============================================================

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

PDNN_DIR = os.path.abspath(
    os.path.join(THIS_DIR, "../ML_Application/parametrized_DNN")
)

OUTDIR = os.path.join(THIS_DIR, "plots")
os.makedirs(OUTDIR, exist_ok=True)

MODEL_PATH    = os.path.join(PDNN_DIR, "best_pdnn.pt")
SCALER_PATH   = os.path.join(PDNN_DIR, "scaler.pkl")
FEATURES_JSON = os.path.join(PDNN_DIR, "features_used.json")

print("[INFO] Using pDNN directory:")
print("       ", PDNN_DIR)

for p in [MODEL_PATH, SCALER_PATH, FEATURES_JSON]:
    assert os.path.exists(p), f"Missing file: {p}"

# ============================================================
# Config
# ============================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Background efficiencies to test
BKG_EFFS = [0.50, 0.20, 0.10, 0.05]

# Mass variables to check
MASS_VARS = {
    "Res_HHbbggCandidate_mass": dict(xmin=200, xmax=1200, nbins=50),
    # "Res_dijet_mass": dict(xmin=50, xmax=300, nbins=40),  # optional
}

# Background inputs (same as training)
BKG_FILES = [
    "../../output_root/v3_production/samples/postEE/GGJets.parquet",
    "../../output_root/v3_production/samples/postEE/GJetPt20To40.parquet",
    "../../output_root/v3_production/samples/postEE/GJetPt40.parquet",
]

# ============================================================
# Load features & scaler
# ============================================================

with open(FEATURES_JSON) as f:
    FEATURES = json.load(f)["features"]

with open(SCALER_PATH, "rb") as f:
    scaler = pickle.load(f)

print(f"[INFO] Number of features: {len(FEATURES)}")

# ============================================================
# Model definition (must match training)
# ============================================================

USE_BATCHNORM = False  # must match training

def maybe_bn(n):
    return nn.BatchNorm1d(n) if USE_BATCHNORM else nn.Identity()


class ParameterizedDNN(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 128), maybe_bn(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64), maybe_bn(64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 32), maybe_bn(32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.net(x)

model = ParameterizedDNN(len(FEATURES)).to(DEVICE)
state = torch.load(MODEL_PATH, map_location=DEVICE)
model.load_state_dict(state)
model.eval()

# ============================================================
# Load background
# ============================================================

print("[INFO] Loading background samples...")
dfs = []
for f in BKG_FILES:
    if not os.path.exists(f):
        raise RuntimeError(f"Missing background file: {f}")
    dfs.append(pd.read_parquet(f))

df = pd.concat(dfs, ignore_index=True)
print(f"[INFO] Background events: {len(df):,}")

# ============================================================
# Feature engineering
# ⚠️ MUST MATCH TRAINING
# ============================================================

def ensure_photon_mva_columns(df):
    pairs = [
        ("lead_mvaID_run3", "lead_mvaID_nano"),
        ("sublead_mvaID_run3", "sublead_mvaID_nano"),
    ]
    for want, alt in pairs:
        if want not in df.columns and alt in df.columns:
            df[want] = df[alt]
    return df

def add_engineered_features(df):
    mHH = df["Res_HHbbggCandidate_mass"].replace(0, np.nan)

    df["ptjj_over_mHH"] = df["Res_dijet_pt"] / mHH
    df["ptHH_over_mHH"] = df["Res_HHbbggCandidate_pt"] / mHH

    for c in ["ptjj_over_mHH", "ptHH_over_mHH"]:
        df[c] = df[c].fillna(0.0)

    for c in ["Res_CosThetaStar_gg",
              "Res_CosThetaStar_jj",
              "Res_CosThetaStar_CS"]:
        if c in df.columns:
            df[c] = df[c].abs()

    return df

df = ensure_photon_mva_columns(df)
df = add_engineered_features(df)

# ============================================================
# Build feature matrix & score
# ============================================================

missing = [f for f in FEATURES if f not in df.columns]
if missing:
    raise RuntimeError(f"Missing required features: {missing}")

X = df[FEATURES].copy()
X = X.fillna(X.mean(numeric_only=True))
X = scaler.transform(X)

with torch.no_grad():
    Xt = torch.tensor(X, dtype=torch.float32, device=DEVICE)
    scores = torch.sigmoid(model(Xt)).cpu().numpy()

df["pdnn_score"] = scores

# ============================================================
# Compute thresholds for target background efficiencies
# ============================================================

thresholds = {}
print("\n[INFO] pDNN working points:")
for eff in BKG_EFFS:
    thr = np.quantile(scores, 1.0 - eff)
    thresholds[eff] = thr
    print(f"  Bkg eff {eff:5.0%}  →  score > {thr:.4f}")

# ============================================================
# Plot mass sculpting
# ============================================================

for mass_var, cfg in MASS_VARS.items():

    bins = np.linspace(cfg["xmin"], cfg["xmax"], cfg["nbins"] + 1)

    plt.figure(figsize=(7.5, 5.5))

    # Inclusive
    plt.hist(
        df[mass_var],
        bins=bins,
        density=True,
        histtype="step",
        linewidth=2.6,
        label="Inclusive"
    )

    # After pDNN cuts
    for eff, thr in thresholds.items():
        sel = df["pdnn_score"] > thr
        plt.hist(
            df.loc[sel, mass_var],
            bins=bins,
            density=True,
            histtype="step",
            linewidth=1.8,
            label=f"pDNN eff = {eff:.0%}"
        )

    plt.xlabel(mass_var.replace("_", " "))
    plt.ylabel("Normalized events")
    plt.title("Background mass sculpting check")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    out_png = os.path.join(OUTDIR, f"sculpting_{mass_var}.png")
    out_pdf = out_png.replace(".png", ".pdf")
    plt.savefig(out_png, dpi=600)
    plt.savefig(out_pdf)
    plt.show()

    print(f"[Saved] {out_png}")
    print(f"[Saved] {out_pdf}")

print("\n[INFO] Mass sculpting check completed successfully.")
