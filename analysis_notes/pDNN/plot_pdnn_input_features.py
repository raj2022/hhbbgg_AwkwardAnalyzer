#!/usr/bin/env python3
"""
Produce pDNN input-feature distribution plots: signal (mX=300/600/1000,
all at mY=125) overlaid as lines against stacked/filled background
(GGJets_MGG-80 = "gg+jets", DDQCDGJets_Rescaled = "g+jets"), for every
variable in FEATURES_CORE (pDNN_v2.py's real, current training feature
list).

Changes from the previous version:
  - ptHH_over_mHH / ptjj_over_mHH are not raw parquet columns -- they are
    engineered by pDNN_v2.py's add_engineered_features() from
    Res_dijet_pt / Res_HHbbggCandidate_pt divided by
    Res_HHbbggCandidate_mass. Reconstructed here with the identical
    protected-division logic (0 mass -> NaN, not a raw ZeroDivisionError
    or inf), rather than silently reported as "not found".
  - One PNG per variable (individual figures), not multi-panel pages.
  - Real signal sample names (NMSSM_X{mx}_Y{my}) as legend labels/
    filenames, not lowX/midX/highX.
  - Smarter binning: low-cardinality variables (e.g. n_jets, n_leptons,
    Njets2p5) get integer bins spanning their actual observed range,
    instead of being forced through the same 40-bin continuous
    percentile scheme used for genuinely continuous variables (which
    was cutting them down oddly).

Run inside an environment with pandas/pyarrow (e.g. `micromamba activate
higgs-dna`, or `hhbbgg-awk` if pyarrow is available there):
    python3 plot_pdnn_input_features.py

Outputs: pdnn_input_plots/<feature_name>.png (one file per variable)
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
    "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)

BACKGROUND_BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE"
BACKGROUND_FILES = {
    r"$\gamma\gamma$+jets": os.path.join(BACKGROUND_BASE_DIR, "GGJets_MGG-80", "NOTAG_merged.parquet"),
    r"$\gamma$+jets": os.path.join(BACKGROUND_BASE_DIR, "DDQCCDGJets", "DDQCDGJets_Rescaled.parquet"),
}

WEIGHT_COL = "weight_central"

SIGNAL_POINTS = [
    (300, 125, "#e41a1c"),
    (600, 125, "#377eb8"),
    (1000, 125, "#4daf4a"),
]

# Real FEATURES_CORE list from pDNN_v2.py.
FEATURES_CORE = [
    "lead_eta", "lead_phi", "sublead_eta", "sublead_phi",
    "Res_dijet_eta", "Res_dijet_phi",
    "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi", "Res_HHbbggCandidate_pt",
    "Res_dijet_mass_DNNreg",
    "Res_DeltaR_jg_min",
    "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
    "lead_mvaID",
    "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi", "Njets2p5",
    "Res_DeltaPhi_j1MET", "Res_DeltaPhi_j2MET",
    "Res_chi_t0", "Res_chi_t1",
    "Res_dijet_pt", "Res_dijet_mass",
    "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
    "sigma_m_over_m",
    "Res_M_X",
    "lead_r9", "sublead_r9",
    "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
    "ptjj_over_mHH", "ptHH_over_mHH",  # engineered, reconstructed below
]

# Engineered features and the raw columns needed to reconstruct them,
# matching pDNN_v2.py's add_engineered_features() exactly.
ENGINEERED_FEATURES = {"ptjj_over_mHH", "ptHH_over_mHH"}
EXTRA_RAW_FOR_ENGINEERING = {"Res_HHbbggCandidate_mass"}  # not otherwise in FEATURES_CORE

OUT_DIR = "pdnn_input_plots"

# General sentinel-value filter: HiggsDNA/pDNN-stage variables use an
# unphysical default (visibly ~-999/-1000) when a reconstruction quantity
# fails. None of the FEATURES_CORE variables (masses, pT ratios, eta/phi,
# DeltaR, chi2, b-tag scores, multiplicities) can legitimately take a
# value anywhere near this, so a single threshold safely applies across
# all of them rather than needing a per-variable rule.
SENTINEL_THRESHOLD = -900.0


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Reconstructs ptjj_over_mHH / ptHH_over_mHH exactly as
    pDNN_v2.py's add_engineered_features() does: protected division by
    Res_HHbbggCandidate_mass (0 treated as NaN, not inf/crash)."""
    m_hh = df.get("Res_HHbbggCandidate_mass", pd.Series(index=df.index, dtype="float64"))
    m_hh = m_hh.replace(0, np.nan)

    df["ptjj_over_mHH"] = df["Res_dijet_pt"] / m_hh if "Res_dijet_pt" in df.columns else np.nan
    df["ptHH_over_mHH"] = (
        df["Res_HHbbggCandidate_pt"] / m_hh if "Res_HHbbggCandidate_pt" in df.columns else np.nan
    )
    for c in ["ptjj_over_mHH", "ptHH_over_mHH"]:
        df[c] = df[c].replace([np.inf, -np.inf], np.nan)
    return df


def _read_parquet_slim(path, wanted_cols):
    """Read only the columns that actually exist in this file (matching
    pDNN_v2.py's own _read_parquet_slim pattern) -- requesting a column
    that doesn't exist raises in pandas/pyarrow rather than being
    silently skipped, so existence has to be checked first."""
    schema = pq.read_schema(path)
    available = set(schema.names)
    subset = [c for c in wanted_cols if c in available]
    missing = sorted(set(wanted_cols) - available)
    if missing:
        print(f"    [INFO] {os.path.basename(path)}: {len(missing)} requested column(s) "
              f"not present, skipped: {missing[:8]}{'...' if len(missing) > 8 else ''}")
    df = pd.read_parquet(path, columns=subset)
    return add_engineered_features(df)


def load_signal_dfs():
    dfs = {}
    request_cols = list((set(FEATURES_CORE) - ENGINEERED_FEATURES) | EXTRA_RAW_FOR_ENGINEERING | {WEIGHT_COL})
    for mx, my, color in SIGNAL_POINTS:
        label = f"NMSSM_X{mx}_Y{my}"
        path = SIG_TPL.format(m=mx, y=my)
        if not os.path.exists(path):
            print(f"[WARN] Missing signal file for {label}: {path}")
            continue
        try:
            df = _read_parquet_slim(path, request_cols)
        except Exception as e:
            print(f"[WARN] Failed reading {path}: {e}")
            continue
        dfs[label] = (df, mx, my, color)
        print(f"Loaded {label}: {len(df)} rows")
    return dfs


def load_background_dfs():
    dfs = {}
    request_cols = list((set(FEATURES_CORE) - ENGINEERED_FEATURES) | EXTRA_RAW_FOR_ENGINEERING | {WEIGHT_COL})
    for label, path in BACKGROUND_FILES.items():
        if not os.path.exists(path):
            print(f"[WARN] Missing background file {label}: {path}")
            continue
        try:
            df = _read_parquet_slim(path, request_cols)
        except Exception as e:
            print(f"[WARN] Failed reading {path}: {e}")
            continue
        dfs[label] = df
        print(f"Loaded background {label}: {len(df)} rows")
    return dfs


def weighted_percentile(values, weights, percentiles):
    sorter = np.argsort(values)
    v_sorted = values[sorter]
    w_sorted = weights[sorter]
    cum_w = np.cumsum(w_sorted) - 0.5 * w_sorted
    cum_w /= np.sum(w_sorted)
    return np.interp(np.asarray(percentiles) / 100.0, cum_w, v_sorted)


def choose_bins(pooled_v, pooled_w, n_continuous_bins=40):
    """Smarter binning: low-cardinality (discrete-looking) variables get
    integer bins spanning their real observed range; genuinely continuous
    variables get weighted-percentile-based bins (0.5-99.5, wider than
    the previous 1-99 to avoid over-clipping legitimate tails)."""
    finite = pooled_v[np.isfinite(pooled_v)]
    n_unique = len(np.unique(finite))

    if n_unique <= 15:
        lo, hi = np.floor(finite.min()), np.ceil(finite.max())
        n_steps = int(hi - lo) + 2
        return np.linspace(lo - 0.5, hi + 0.5, n_steps + 1)

    lo, hi = weighted_percentile(pooled_v, pooled_w, [0.5, 99.5])
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    return np.linspace(lo, hi, n_continuous_bins)


def valid_mask(v, w):
    """Finite AND above the sentinel threshold -- combines the two
    validity checks used everywhere a variable/weight pair is read."""
    return np.isfinite(v) & np.isfinite(w) & (v > SENTINEL_THRESHOLD)


def plot_single_variable(var, signal_dfs, background_dfs, out_dir):
    all_vals, all_w = [], []
    for label, (df, mx, my, color) in signal_dfs.items():
        if var not in df.columns:
            continue
        v = df[var].to_numpy(dtype=float)
        w = df[WEIGHT_COL].to_numpy(dtype=float)
        valid = valid_mask(v, w)
        all_vals.append(v[valid]); all_w.append(w[valid])
    for label, df in background_dfs.items():
        if var not in df.columns:
            continue
        v = df[var].to_numpy(dtype=float)
        w = df[WEIGHT_COL].to_numpy(dtype=float)
        valid = valid_mask(v, w)
        all_vals.append(v[valid]); all_w.append(w[valid])

    if not all_vals:
        print(f"  [SKIP] '{var}' not found in any sample.")
        return

    pooled_v = np.concatenate(all_vals)
    pooled_w = np.concatenate(all_w)
    bins = choose_bins(pooled_v, pooled_w)

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    bkg_colors = {r"$\gamma\gamma$+jets": "#b3cde3", r"$\gamma$+jets": "#d9d9d9"}
    bottom = np.zeros(len(bins) - 1)
    for label, df in background_dfs.items():
        if var not in df.columns:
            continue
        v = df[var].to_numpy(dtype=float)
        w = df[WEIGHT_COL].to_numpy(dtype=float)
        valid = valid_mask(v, w)
        counts, edges = np.histogram(v[valid], bins=bins, weights=w[valid])
        total_w = w[valid].sum()
        if total_w > 0:
            counts = counts / total_w
        ax.bar(edges[:-1], counts, width=np.diff(edges), bottom=bottom,
               align="edge", color=bkg_colors.get(label, "#cccccc"),
               edgecolor="none", label=label, alpha=0.8)
        bottom += counts

    for label, (df, mx, my, color) in signal_dfs.items():
        if var not in df.columns:
            continue
        v = df[var].to_numpy(dtype=float)
        w = df[WEIGHT_COL].to_numpy(dtype=float)
        valid = valid_mask(v, w)
        counts, edges = np.histogram(v[valid], bins=bins, weights=w[valid])
        total_w = w[valid].sum()
        if total_w > 0:
            counts = counts / total_w
        ax.step(edges[:-1], counts, where="post", color=color, linewidth=1.8, label=label)

    ax.set_xlabel(var, fontsize=12)
    ax.set_ylabel("Normalized Events", fontsize=12)
    ax.legend(fontsize=9, frameon=False)
    ax.tick_params(labelsize=10)
    fig.tight_layout()

    out_path = os.path.join(out_dir, f"{var}.png")
    fig.savefig(out_path, dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {out_path}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    signal_dfs = load_signal_dfs()
    background_dfs = load_background_dfs()

    if not signal_dfs or not background_dfs:
        print("[ERROR] Could not load signal or background data; aborting.")
        return

    print(f"\nPlotting {len(FEATURES_CORE)} variables individually into {OUT_DIR}/\n")
    for var in FEATURES_CORE:
        plot_single_variable(var, signal_dfs, background_dfs, OUT_DIR)


if __name__ == "__main__":
    main()