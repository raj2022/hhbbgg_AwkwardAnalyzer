# PDNN trnsformed score on the saved outputs. 

# 1. check the saved model from the traning
# 2. On the saved model, check the samples.
# 3.  On the transformed score, include it as variables in each sample
# 4. process it as Data/MC comaprison

#!/usr/bin/env python3
# PDNN transformed score on saved outputs + Data/MC comparison
# ------------------------------------------------------------
# What this script does:
# 1) Verifies saved artifacts (model, scaler, features).
# 2) Loads samples (ROOT or Parquet), applies pDNN, and writes out files that include `pdnn_score`.
# 3) Makes a Data/MC comparison plot of `pdnn_score` (stacked MC vs. data points).
#
# Examples:
#   A) Score MC (ROOT) + make Data/MC plot with only MC (no data):
#      python pdnn_transform_and_datamc.py \
#         --mc-root ../../outputfiles/hhbbgg_analyzer-v2-trees.root:GGJets/preselection:GGJets \
#         --mc-root ../../outputfiles/hhbbgg_analyzer-v2-trees.root:GJetPt40/preselection:GJet40 \
#         --mass 600 --y_value 100 \
#         --keep-cols run lumi event weight_preselection \
#         --out-dir ./pdnn_out \
#         --plot-out ./pdnn_out/datamc_pdnn_score.png
#
#   B) Mix Parquet & ROOT, include a data sample (ROOT), and write outputs as Parquet:
#      python pdnn_transform_and_datamc.py \
#         --data-root /path/to/data.root:DataTree:Data2018 \
#         --mc-parquet /path/to/mc1.parquet:MC1 \
#         --mc-root    /path/to/mc2.root:preselection:MC2 \
#         --mass 600 --y_value 100 \
#         --out-format parquet \
#         --keep-cols run lumi event weight_preselection \
#         --out-dir ./pdnn_out \
#         --plot-out ./pdnn_out/datamc_pdnn_score.png
#
# Notes:
# - If your inputs already have 'mass' and 'y_value' columns, you can skip --mass/--y_value.
# - If they don't, pass --mass and --y_value to set them for all rows of the file(s).
# - We write one scored file per input (with same base name + suffix), AND produce a Data/MC plot.

import os
import json
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import joblib

# Optional dependency for ROOT
try:
    import uproot
    import awkward as ak
except Exception:
    uproot = None
    ak = None


# -------------------------------
# Model (must match your training)
# -------------------------------
class ParameterizedDNN(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 12),
            nn.ReLU(),
            nn.BatchNorm1d(12),
            nn.Dropout(0.3),
            nn.Linear(12, 8),
            nn.ReLU(),
            nn.BatchNorm1d(8),
            nn.Dropout(0.3),
            nn.Linear(8, 1),
        )
    def forward(self, x):
        return self.model(x)


# -------------------------------
# Utilities
# -------------------------------
def parse_sample_arg(arg_str, is_root: bool):
    """
    For ROOT:  "<path.root>:<treename>:<tag>"
    For Parquet:"<path.parquet>:<tag>"
    Returns dict with {path, treename (or None), tag}
    """
    parts = arg_str.split(":")
    if is_root:
        if len(parts) != 3:
            raise ValueError(f"Use format PATH:BRANCH:TAG for --*_root, got: {arg_str}")
        return {"path": parts[0], "treename": parts[1], "tag": parts[2]}
    else:
        if len(parts) != 2:
            raise ValueError(f"Use format PATH:TAG for --*_parquet, got: {arg_str}")
        return {"path": parts[0], "treename": None, "tag": parts[1]}


def ensure_available(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing input: {path}")


def ensure_cols(df, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required features: {missing}")
    return df


def add_mass_y(df, mass, y_value):
    if mass is not None:
        df["mass"] = mass
    if y_value is not None:
        df["y_value"] = y_value
    if "mass" not in df.columns or "y_value" not in df.columns:
        raise RuntimeError("mass/y_value not found. Provide --mass and --y_value or have them in the file.")
    return df


def impute_with_means(df, means_dict):
    for c, m in means_dict.items():
        if c in df.columns:
            df[c] = df[c].astype("float32")
            df[c] = df[c].fillna(m)
    return df


def batch_predict(df, feature_order, scaler, weights_path, device=None, batch_size=65536):
    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model = ParameterizedDNN(len(feature_order)).to(device)
    state = torch.load(weights_path, map_location=device)
    model.load_state_dict(state)
    model.eval()

    X = df[feature_order].astype("float32").values
    X = scaler.transform(X).astype("float32")

    probs = np.empty(X.shape[0], dtype=np.float32)
    with torch.no_grad():
        for i in range(0, X.shape[0], batch_size):
            xb = torch.from_numpy(X[i:i+batch_size]).to(device)
            logits = model(xb).view(-1)
            probs[i:i+batch_size] = torch.sigmoid(logits).float().cpu().numpy()
    return probs


def read_root_df(path, treename, needed_cols=None, keep_all=False):
    """
    If keep_all=True we read the whole tree to be able to re-write it with pdnn_score.
    Otherwise we only read the columns we need (faster).
    """
    if uproot is None:
        raise RuntimeError("uproot is not installed. `pip install uproot awkward` to use ROOT IO.")
    with uproot.open(path) as f:
        if treename not in f:
            raise RuntimeError(f"Tree '{treename}' not in {path}")
        t = f[treename]
        if keep_all:
            arr = t.arrays(library="ak")
            df = ak.to_pandas(arr)
        else:
            cols = list(set(needed_cols)) if needed_cols else None
            arr = t.arrays(filter_name=cols, library="pd")
            df = arr
    # uproot/awkward may produce multi-index if jagged—assume flat ntuples here
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([c for c in tup if c]) for tup in df.columns.to_list()]
    return df


def write_root_with_score(in_path, treename, out_path, original_tree_df, score_col="pdnn_score"):
    """
    Write a NEW ROOT file containing the same tree (columns from original df) + pdnn_score.
    """
    if uproot is None:
        raise RuntimeError("uproot is not installed. Cannot write ROOT.")
    # Make dict of column -> numpy array
    arrays = {c: np.asarray(original_tree_df[c]) for c in original_tree_df.columns}
    if score_col not in arrays:
        arrays[score_col] = np.asarray(original_tree_df[score_col])
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with uproot.recreate(out_path) as fout:
        fout[treename] = arrays


def write_parquet_with_score(out_path, df, score_col="pdnn_score"):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    df.to_parquet(out_path, index=False)


def make_datamc_plot(data_hist, mc_hists, edges, out_png,
                     title="Data/MC comparison: pDNN score",
                     xlabel="pDNN score", ylabel="Events", logy=False):
    """
    data_hist: (values, errors) or None
    mc_hists: list of dicts {name, values, color(optional)}
    edges: bin edges (np.ndarray)
    """
    centers = 0.5*(edges[:-1] + edges[1:])
    width   = np.diff(edges)

    plt.figure(figsize=(7.0,5.0))
    # MC stack
    bottom = np.zeros_like(centers, dtype=float)
    for h in mc_hists:
        vals = h["values"]
        label = h.get("name","MC")
        plt.bar(centers, vals, width=width, bottom=bottom, edgecolor="black", linewidth=0.5, label=label)
        bottom += vals

    # Data points with errors
    if data_hist is not None:
        y, yerr = data_hist
        plt.errorbar(centers, y, yerr=yerr, fmt="o", label="Data")

    if logy:
        plt.yscale("log")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    print(f"[PLOT] Saved Data/MC plot -> {out_png}")
    plt.close()


# -------------------------------
# Main
# -------------------------------
def main():
    ap = argparse.ArgumentParser(description="Apply saved pDNN to samples, write score, and make Data/MC plot.")
    # Artifacts
    ap.add_argument("--weights",  default="best_pdnn.pt", help="Path to saved model state_dict")
    ap.add_argument("--scaler",   default="pdnn_scaler.pkl", help="Path to saved StandardScaler (joblib)")
    ap.add_argument("--features", default="pdnn_features.json", help="Path to feature metadata (json)")
    ap.add_argument("--device",   default=None, help="'cuda' or 'cpu' (default auto)")
    # Inputs: ROOT or Parquet (multiple allowed)
    ap.add_argument("--data-root",   action="append", default=[], help="ROOT sample as path:treename:tag")
    ap.add_argument("--data-parquet",action="append", default=[], help="Parquet sample as path:tag")
    ap.add_argument("--mc-root",     action="append", default=[], help="ROOT sample as path:treename:tag")
    ap.add_argument("--mc-parquet",  action="append", default=[], help="Parquet sample as path:tag")
    # Physics/meta
    ap.add_argument("--mass", type=float, default=None, help="Force mass for all rows (optional)")
    ap.add_argument("--y_value", type=float, default=None, help="Force y_value for all rows (optional)")
    ap.add_argument("--keep-cols", nargs="*", default=["weight_preselection"], help="Extra columns to keep/copy to outputs")
    # Output
    ap.add_argument("--out-dir", default="./pdnn_scored", help="Directory to write per-sample outputs")
    ap.add_argument("--out-format", choices=["parquet","root"], default="parquet", help="Output format")
    ap.add_argument("--plot-out", default=None, help="Path to save Data/MC plot (png). If omitted, no plot.")
    ap.add_argument("--bins", type=int, default=40, help="Histogram bins for Data/MC plot")
    ap.add_argument("--range", nargs=2, type=float, default=[0.0,1.0], help="Score range for plot")
    ap.add_argument("--norm-to-data", action="store_true", help="Scale total MC to Data before plotting")
    ap.add_argument("--logy", action="store_true", help="Log-y on plot")
    ap.add_argument("--keep-all-root-cols", action="store_true", help="When scoring ROOT, read/write every column")
    args = ap.parse_args()

    # ----- Load artifacts
    ensure_available(args.weights)
    ensure_available(args.scaler)
    ensure_available(args.features)

    scaler = joblib.load(args.scaler)
    with open(args.features, "r") as f:
        meta = json.load(f)
    feature_order = meta["feature_order"]
    col_means = meta.get("col_means", {})

    # ----- Collect sample specs
    data_specs = [parse_sample_arg(s, is_root=True)  for s in args.data_root]    \
               + [parse_sample_arg(s, is_root=False) for s in args.data_parquet]
    mc_specs   = [parse_sample_arg(s, is_root=True)  for s in args.mc_root]      \
               + [parse_sample_arg(s, is_root=False) for s in args.mc_parquet]

    if not data_specs and not mc_specs:
        raise RuntimeError("No inputs provided. Use --data-*/--mc-*.")

    os.makedirs(args.out_dir, exist_ok=True)
    all_edges = np.linspace(args.range[0], args.range[1], args.bins+1)

    # For plotting
    data_hist_counts = None
    data_hist_errs   = None
    mc_stack = []  # list of dicts {name, values}

    # ----- Helper to process any single sample
    def process_one(spec, is_data: bool):
        path = spec["path"]
        treename = spec["treename"]
        tag = spec["tag"]
        ensure_available(path)

        print(f"[LOAD] {'DATA' if is_data else 'MC'}: {path}  tag={tag}  tree={treename}")
        # Read
        keep_cols = list(set(feature_order + ["mass","y_value"] + args.keep_cols))
        if path.lower().endswith(".root"):
            df_full = read_root_df(path, treename, needed_cols=keep_cols, keep_all=args.keep_all_root_cols)
        else:
            df_full = pd.read_parquet(path)
            # If we aren't keeping all cols in Parquet, reduce to keep_cols to save IO
            missing_for_parquet = [c for c in keep_cols if c not in df_full.columns]
            # It's fine if some keep_cols are missing (e.g., identifiers), we just won't include them
            ok_cols = [c for c in keep_cols if c in df_full.columns]
            if ok_cols:
                df_full = df_full[ok_cols].copy()

        # Add/verify mass & y
        df_full = add_mass_y(df_full, args.mass, args.y_value)

        # Ensure features exist & impute
        ensure_cols(df_full, feature_order)
        df_full = impute_with_means(df_full, col_means)

        # Predict
        scores = batch_predict(df_full, feature_order, scaler, args.weights, device=args.device)
        df_full["pdnn_score"] = scores.astype("float32")

        # Output one file per sample
        base = os.path.basename(path)
        base_noext = os.path.splitext(base)[0]
        out_name = f"{base_noext}__{tag}__pdnn.{ 'parquet' if args.out_format=='parquet' else 'root' }"
        out_path = os.path.join(args.out_dir, out_name)

        if args.out_format == "parquet":
            write_parquet_with_score(out_path, df_full)
        else:
            if not path.lower().endswith(".root"):
                # convert DF to ROOT with only what we have
                write_root_with_score(path, treename or "tree", out_path, df_full)
            else:
                write_root_with_score(path, treename, out_path, df_full)

        print(f"[WRITE] -> {out_path}  (rows={len(df_full):,})")

        # Return histogram ingredients for plotting
        weights = df_full["weight_preselection"] if "weight_preselection" in df_full.columns else None
        vals, _ = np.histogram(df_full["pdnn_score"].values, bins=all_edges, weights=weights)

        if is_data:
            # Poisson errors for data (use sqrt(N) in the binned sum; if weights, use sqrt(sum w^2))
            if weights is None:
                errs = np.sqrt(vals)
            else:
                w2, _ = np.histogram(df_full["pdnn_score"].values, bins=all_edges, weights=(weights.values**2))
                errs = np.sqrt(w2)
            return vals, errs
        else:
            return {"name": tag, "values": vals}

    # ----- Process data & MC
    if data_specs:
        # If multiple data inputs, we sum them together
        d_sum = np.zeros(args.bins, dtype=float)
        e2_sum = np.zeros(args.bins, dtype=float)
        for spec in data_specs:
            vals, errs = process_one(spec, is_data=True)
            d_sum += vals
            e2_sum += errs**2
        data_hist_counts = d_sum
        data_hist_errs   = np.sqrt(e2_sum)

    if mc_specs:
        for spec in mc_specs:
            mc_stack.append(process_one(spec, is_data=False))

    # ----- Make Data/MC plot if requested
    if args.plot_out is not None:
        # Optionally scale MC to Data area
        if data_hist_counts is not None and mc_stack:
            mc_tot = np.sum([m["values"] for m in mc_stack], axis=0)
            data_sum = data_hist_counts.sum()
            mc_sum = mc_tot.sum()
            if args.norm_to_data and mc_sum > 0:
                scale = data_sum / mc_sum if mc_sum > 0 else 1.0
                for m in mc_stack:
                    m["values"] = m["values"] * scale
                print(f"[NORM] Scaled total MC to Data by factor {scale:.3f}")

            make_datamc_plot(
                data_hist=(data_hist_counts, data_hist_errs),
                mc_hists=mc_stack,
                edges=all_edges,
                out_png=args.plot_out,
                logy=args.logy
            )
        else:
            # Can still plot MC-only
            make_datamc_plot(
                data_hist=None,
                mc_hists=mc_stack,
                edges=all_edges,
                out_png=args.plot_out,
                logy=args.logy
            )


if __name__ == "__main__":
    main()



