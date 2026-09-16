#!/usr/bin/env python3
"""
Build the Sec 11.7 "Sample Yields" table for the representative mass
hypothesis mX=600, mY=100 -- one table per year, since category
boundaries differ by year (see event_categories.json).

Mechanics match categorize_events.py exactly:
  - SR and CR are both carved out of the single 'srbbgg' tree via a cut
    on diphoton_mass (SR: |mgg-125|<2, CR: 4<=|mgg-125|<10), not read
    from separate trees.
  - alpha(pNN) is built from background MC yields in SR vs CR (Eq. 15).
  - Background yield per category = alpha(score) applied to real,
    unblinded CR DATA events, then binned into categories (Eq. 16).
  - Observed = raw (unweighted) CR data count per category.
  - Signal = weighted SR sum for the true (mX,mY) sample, per category.
  - Weight branch: weight_srbbgg (confirmed equivalent to
    weight_selection at this analyzer stage).

Run inside the `hhbbgg-awk` micromamba environment:
    micromamba activate hhbbgg-awk
    python3 build_sec11_7_yield_table.py
"""

import glob
import json
import os

import numpy as np
import uproot

YEAR_DIRS = {
    "2022": "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/outputfiles/DD_2022_combined_trees",
    "2023": "/afs/cern.ch/user/s/sraj/b2g_HHbbgg/sraj/Hhbbgg_AwkwardAnalyzer/outputfiles/DD_2023_combined_trees",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/DD_2024",
}

CATEGORY_JSON = {
    "2022": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022/event_categories.json",
    "2023": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023/event_categories.json",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024/event_categories.json",
}

FILE_PREFIX = "hhbbgg_analyzer-v2-trees__"
TREE_NAME = "srbbgg"
BR_WGT = "weight_srbbgg"
BR_SCORE = "pDNN_score"
BR_MGG = "diphoton_mass"

SR_LO, SR_HI = 123.0, 127.0        # |mgg-125| < 2
CR_LO, CR_HI = 4.0, 10.0           # 4 <= |mgg-125| < 10
ALPHA_BINS = 60

SIGNAL_SAMPLE = "NMSSM_X600_Y100"
MASS_TAG = "mX600_mY100"

BACKGROUND_SAMPLES = {
    "DDQCDGJets_Rescaled": None,
    "GGJets_MGG-80_Rescaled": None,
    "GluGluHtoGG": None,
    "VBFHtoGG": None,
    "VHtoGG": None, "WmHtoGG": None, "WpHtoGG": None, "ZHtoGG": None,
    "ttHtoGG": None,
    "bbHtoGG": None,
}


def find_sample_file(year_dir, sample_name):
    for suffix in ("nominal", "flat"):
        candidate = os.path.join(year_dir, f"{FILE_PREFIX}{sample_name}__{suffix}.root")
        if os.path.exists(candidate):
            return candidate
    return None


def find_data_files(year_dir):
    pattern = os.path.join(year_dir, f"{FILE_PREFIX}Data*__*.root")
    files = glob.glob(pattern)
    return [f for f in files if f.endswith("__nominal.root") or f.endswith("__flat.root")]


def get_srbbgg_tree(root_file_path):
    f = uproot.open(root_file_path)
    keys = f.keys()
    tree_keys = [k for k in keys if k.split(";")[0].endswith(f"/{TREE_NAME}")]
    if not tree_keys:
        return None
    return f[tree_keys[0]]


def read_mgg_score_weight(fpath, need_weight=True):
    tree = get_srbbgg_tree(fpath)
    if tree is None or tree.num_entries == 0:
        return None
    branches = tree.keys()
    required = {BR_MGG, BR_SCORE}
    if need_weight:
        required.add(BR_WGT)
    if not required.issubset(branches):
        return None
    out = {
        "mgg": tree[BR_MGG].array(library="np"),
        "score": tree[BR_SCORE].array(library="np"),
    }
    if need_weight:
        out["weight"] = tree[BR_WGT].array(library="np")
    return out


def make_alpha(score_sr_mc, w_sr_mc, score_cr_mc, w_cr_mc, nbins=ALPHA_BINS):
    lo = float(np.min([np.min(score_sr_mc), np.min(score_cr_mc)])) if len(score_sr_mc) and len(score_cr_mc) else 0.0
    hi = float(np.max([np.max(score_sr_mc), np.max(score_cr_mc)])) if len(score_sr_mc) and len(score_cr_mc) else 1.0
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        lo, hi = 0.0, 1.0
    edges = np.linspace(lo, hi, nbins + 1)
    h_sr, _ = np.histogram(score_sr_mc, bins=edges, weights=w_sr_mc)
    h_cr, _ = np.histogram(score_cr_mc, bins=edges, weights=w_cr_mc)
    eps = 1e-9
    alpha = (h_sr + eps) / (h_cr + eps)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, alpha, (lo, hi)


def eval_alpha(x, centers, alpha, lohi):
    lo, hi = lohi
    return np.interp(np.clip(x, lo, hi), centers, alpha)


def categorize_by_edges(scores, edges_sorted_desc_thresholds):
    """edges_sorted_desc_thresholds: ascending-sorted boundary list, as
    stored in event_categories.json. Returns an integer category index
    per event (0..N-1), or -1 if uncategorized (score below the lowest
    boundary). Category N-1 = highest score / highest purity."""
    edges = np.asarray(sorted(edges_sorted_desc_thresholds))
    cat = np.full(len(scores), -1, dtype=int)
    for i, thr in enumerate(edges):
        sel = scores >= thr
        cat[sel] = i
    return cat


def process_year(year, year_dir, json_path):
    with open(json_path) as f:
        cat_json = json.load(f)
    boundaries = cat_json["boundaries"]
    if MASS_TAG not in boundaries:
        print(f"[{year}] WARNING: mass tag '{MASS_TAG}' not found in {json_path}; skipping year.")
        return None
    edges = boundaries[MASS_TAG]
    n_categories = len(edges)
    print(f"[{year}] category edges for {MASS_TAG}: {edges} ({n_categories} categories)")

    # ---- background MC pool (SR + CR, for alpha) ----
    bsr_scores, bsr_w = [], []
    bcr_scores, bcr_w = [], []
    for sample_name in BACKGROUND_SAMPLES:
        fpath = find_sample_file(year_dir, sample_name)
        if fpath is None:
            continue
        data = read_mgg_score_weight(fpath)
        if data is None:
            continue
        mgg, score, w = data["mgg"], data["score"], data["weight"]
        in_sr = (mgg >= SR_LO) & (mgg <= SR_HI)
        absd = np.abs(mgg - 125.0)
        in_cr = (absd >= CR_LO) & (absd < CR_HI)
        if in_sr.any():
            bsr_scores.append(score[in_sr]); bsr_w.append(w[in_sr])
        if in_cr.any():
            bcr_scores.append(score[in_cr]); bcr_w.append(w[in_cr])

    if not bsr_scores or not bcr_scores:
        print(f"[{year}] WARNING: background MC pool empty in SR or CR; cannot build alpha(pNN).")
        return None

    Bsr_mc = np.concatenate(bsr_scores); Bsrw_mc = np.concatenate(bsr_w)
    Bcr_mc = np.concatenate(bcr_scores); Bcrw_mc = np.concatenate(bcr_w)
    centers, alpha, lohi = make_alpha(Bsr_mc, Bsrw_mc, Bcr_mc, Bcrw_mc)

    # ---- real, unblinded CR data ----
    cr_data_scores = []
    for fpath in find_data_files(year_dir):
        data = read_mgg_score_weight(fpath, need_weight=False)
        if data is None:
            continue
        mgg, score = data["mgg"], data["score"]
        absd = np.abs(mgg - 125.0)
        in_cr = (absd >= CR_LO) & (absd < CR_HI)
        if in_cr.any():
            cr_data_scores.append(score[in_cr])
    if not cr_data_scores:
        print(f"[{year}] WARNING: no CR data events found.")
        return None
    Dcr = np.concatenate(cr_data_scores)

    # background estimate per CR-data event, transferred via alpha(score)
    Bw_per_event = eval_alpha(Dcr, centers, alpha, lohi)

    # categorize CR-data events (both for background-estimate binning and
    # for the raw "observed" count)
    cr_cats = categorize_by_edges(Dcr, edges)

    bkg_yield = np.zeros(n_categories)
    observed_count = np.zeros(n_categories, dtype=int)
    for i in range(n_categories):
        sel = cr_cats == i
        bkg_yield[i] = Bw_per_event[sel].sum()
        observed_count[i] = sel.sum()

    # ---- signal: true (mX,mY) sample, SR-selected, weighted ----
    sig_fpath = find_sample_file(year_dir, SIGNAL_SAMPLE)
    signal_yield = np.zeros(n_categories)
    if sig_fpath is not None:
        data = read_mgg_score_weight(sig_fpath)
        if data is not None:
            mgg, score, w = data["mgg"], data["score"], data["weight"]
            in_sr = (mgg >= SR_LO) & (mgg <= SR_HI)
            sig_cats = categorize_by_edges(score[in_sr], edges)
            sig_w = w[in_sr]
            for i in range(n_categories):
                sel = sig_cats == i
                signal_yield[i] = sig_w[sel].sum()
    else:
        print(f"[{year}] WARNING: signal sample {SIGNAL_SAMPLE} not found.")

    return {
        "n_categories": n_categories,
        "edges": edges,
        "signal_yield": signal_yield,
        "bkg_yield": bkg_yield,
        "observed": observed_count,
    }


def emit_latex_table(year, result):
    n = result["n_categories"]
    print(f"\n%% ---- {year} yield table (mX=600, mY=100) ----")
    print(r"\begin{table}[htbp!]")
    print(r"\centering")
    print(r"\caption{Expected signal and background yields, and observed (CR) event "
          r"counts, per signal-region category, for $m_X=600$~GeV, $m_Y=100$~GeV, %s.}" % year)
    print(r"\begin{tabular}{c c c c}")
    print(r"\hline")
    print(r"Category & Signal yield & Background yield (transferred) & Observed (CR) \\")
    print(r"\hline")
    # present from highest-purity (largest index) to lowest, per the note's
    # stated convention ("ordering of categories follows decreasing pNN score")
    for i in reversed(range(n)):
        label = f"Cat. {n - i}"  # Cat. 1 = highest purity
        print(f"{label} & {result['signal_yield'][i]:.3g} & "
              f"{result['bkg_yield'][i]:.3g} & {result['observed'][i]} \\\\")
    print(r"\hline")
    print(r"\end{tabular}")
    print(r"\end{table}")


def main():
    for year, year_dir in YEAR_DIRS.items():
        result = process_year(year, year_dir, CATEGORY_JSON[year])
        if result is not None:
            emit_latex_table(year, result)


if __name__ == "__main__":
    main()