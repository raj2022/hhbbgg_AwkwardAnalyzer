#!/usr/bin/env python3
"""
check_feature_correlations.py

Computes the full pairwise Pearson correlation matrix across
FEATURES_CORE (non-engineered), on real signal MC, and flags any pair
above a configurable threshold. Originally built to proactively check
whether the 10 features restored by the RAW_COLUMNS_OF_INTEREST fix
introduced any new, high-correlation pairs; 3 of those 10
(Res_M_X, Res_dijet_mass, Res_dijet_mass_DNNreg) were subsequently
removed from FEATURES_CORE entirely as a mass-sculpting-risk
mitigation (see feature_definitions_v2.py) and are excluded here too --
the remaining 7 (Njets2p5, Res_DeltaPhi_j1MET, Res_DeltaPhi_j2MET,
lead_mvaID, lead_r9, sigma_m_over_m, sublead_r9) are still checked.
This remains a proactive, visual cross-check of statistical redundancy
-- a separate question from mass-sculpting risk -- not a replacement
for the training pipeline's own automatic 0.95-threshold pruning step.

Combines several mass points into one sample by default (recommended:
a pDNN is parametrized across the grid, so a correlation structure
representative of only one mass point could miss mass-point-specific
effects).

Usage:
    python check_feature_correlations.py \
        --mass-points 600,300 600,90 1000,800 \
        --out-heatmap feature_correlations.png \
        --out-csv feature_correlations.csv
"""

import argparse
import itertools

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import seaborn as sns

FEATURES_CORE = [
    "lead_eta", "lead_phi", "sublead_eta", "sublead_phi",
    "Res_dijet_eta", "Res_dijet_phi",
    "Res_HHbbggCandidate_eta", "Res_HHbbggCandidate_phi", "Res_HHbbggCandidate_pt",
    "Res_DeltaR_jg_min",
    "Res_CosThetaStar_gg", "Res_CosThetaStar_jj", "Res_CosThetaStar_CS",
    "lead_mvaID",
    "n_leptons", "n_jets", "puppiMET_pt", "puppiMET_phi", "Njets2p5",
    "Res_DeltaPhi_j1MET", "Res_DeltaPhi_j2MET",
    "Res_chi_t0", "Res_chi_t1",
    "Res_dijet_pt",
    "Res_pholead_PtOverM", "Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM", "Res_SecondJet_PtOverM",
    "sigma_m_over_m",
    "lead_r9", "sublead_r9",
    "Res_lead_bjet_btagPNetB", "Res_sublead_bjet_btagPNetB",
]  # engineered features (ptjj_over_mHH, ptHH_over_mHH) excluded --
   # these depend on a downstream computation not replicated here.
   # Res_dijet_mass, Res_dijet_mass_DNNreg, and Res_M_X are likewise
   # excluded here -- removed from the training pipeline's own
   # FEATURES_CORE as a deliberate mass-sculpting-risk mitigation (see
   # feature_definitions_v2.py), not present to check correlations for.

NEWLY_RESTORED = {
    "Njets2p5", "Res_DeltaPhi_j1MET", "Res_DeltaPhi_j2MET",
    "lead_mvaID", "lead_r9", "sigma_m_over_m", "sublead_r9",
}  # the 7 of the original 10 gap-fill features that remain in
   # FEATURES_CORE after the 3 sculpting-risk removals above.

SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/"
    "2022/sim/postEE/merged/NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)


def load_combined(mass_points, sig_tpl):
    frames = []
    for m, y in mass_points:
        path = sig_tpl.format(m=m, y=y)
        try:
            available = set(pq.ParquetFile(path).schema_arrow.names)
        except Exception as e:
            print(f"[WARN] Could not open {path}: {e} -- skipped.")
            continue
        cols_here = [c for c in FEATURES_CORE if c in available]
        missing_here = [c for c in FEATURES_CORE if c not in available]
        if missing_here:
            print(f"[WARN] X{m}_Y{y}: {len(missing_here)} FEATURES_CORE column(s) "
                  f"not found in this file, excluded for this point: {missing_here}")
        df = pd.read_parquet(path, columns=cols_here)
        df["_mass_point"] = f"X{m}_Y{y}"
        frames.append(df)
        print(f"[INFO] X{m}_Y{y}: loaded {len(df)} events, {len(cols_here)} column(s).")

    if not frames:
        raise RuntimeError("No mass points could be loaded -- nothing to check.")

    combined = pd.concat(frames, ignore_index=True, sort=False)
    print(f"\n[INFO] Combined sample: {len(combined)} total events across {len(frames)} mass point(s).")
    return combined


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mass-points", nargs="+", required=True,
                     help="One or more 'mX,mY' pairs, e.g. --mass-points 600,300 600,90 1000,800")
    ap.add_argument("--sig-tpl", default=SIG_TPL,
                     help="Path template with {m} and {y} placeholders.")
    ap.add_argument("--threshold", type=float, default=0.95,
                     help="Flag threshold, matching the training pipeline's own "
                          "correlation-pruning cutoff (default 0.95).")
    ap.add_argument("--watch-threshold", type=float, default=0.80,
                     help="Lower, informational threshold for pairs worth watching "
                          "even if not automatically pruned (default 0.80).")
    ap.add_argument("--out-heatmap", default="feature_correlations.png")
    ap.add_argument("--out-csv", default=None)
    args = ap.parse_args()

    mass_points = []
    for mp in args.mass_points:
        m, y = mp.split(",")
        mass_points.append((m.strip(), y.strip()))

    df = load_combined(mass_points, args.sig_tpl)

    present_features = [c for c in FEATURES_CORE if c in df.columns]
    corr = df[present_features].corr(method="pearson")

    # --- Flag high-correlation pairs ---
    pairs = []
    for f1, f2 in itertools.combinations(present_features, 2):
        r = corr.loc[f1, f2]
        if pd.isna(r):
            continue
        if abs(r) >= args.watch_threshold:
            involves_new = (f1 in NEWLY_RESTORED) or (f2 in NEWLY_RESTORED)
            pairs.append((f1, f2, r, involves_new))

    pairs.sort(key=lambda x: -abs(x[2]))

    print(f"\n=== Pairs with |r| >= {args.threshold} (would trigger the pipeline's own pruning) ===")
    hard_flags = [p for p in pairs if abs(p[2]) >= args.threshold]
    if hard_flags:
        for f1, f2, r, is_new in hard_flags:
            tag = "  <-- involves a newly-restored feature" if is_new else ""
            print(f"  {f1} <-> {f2}: r={r:+.4f}{tag}")
    else:
        print("  (none)")

    print(f"\n=== Pairs with {args.watch_threshold} <= |r| < {args.threshold} (below auto-prune, worth watching) ===")
    soft_flags = [p for p in pairs if abs(p[2]) < args.threshold]
    if soft_flags:
        for f1, f2, r, is_new in soft_flags:
            tag = "  <-- involves a newly-restored feature" if is_new else ""
            print(f"  {f1} <-> {f2}: r={r:+.4f}{tag}")
    else:
        print("  (none)")

    n_involving_new = sum(1 for _, _, _, is_new in pairs if is_new)
    print(f"\n[SUMMARY] {len(pairs)} pair(s) at or above the watch threshold; "
          f"{n_involving_new} involve at least one of the 10 newly-restored features.")

    if args.out_csv:
        corr.to_csv(args.out_csv)
        print(f"[Saved] full correlation matrix -> {args.out_csv}")

    # --- Heatmap ---
    fig, ax = plt.subplots(figsize=(14, 12))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, cmap="coolwarm", vmin=-1, vmax=1, center=0,
                square=True, linewidths=0.3, cbar_kws={"shrink": 0.7},
                annot=False, ax=ax)
    ax.set_title("Feature correlation matrix (Pearson), FEATURES_CORE (non-engineered)", fontsize=13)
    plt.xticks(rotation=90, fontsize=7)
    plt.yticks(rotation=0, fontsize=7)
    fig.tight_layout()
    fig.savefig(args.out_heatmap, dpi=200, bbox_inches="tight")
    print(f"[Saved] {args.out_heatmap}")


if __name__ == "__main__":
    main()