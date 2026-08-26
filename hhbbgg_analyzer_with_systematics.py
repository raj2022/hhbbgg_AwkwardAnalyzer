# !/usr/bin/env python3
# -*- coding: utf-8 -*-
print(">>> SCRIPT STARTED <<<")

import os
import re
import argparse
from pathlib import Path

import numpy as np
import uproot
import pandas as pd
import awkward as ak
import pyarrow.parquet as pq
from pyarrow import Table
import pyarrow
import yaml

from config.utils import lVector
from normalisation import getXsec, getLumi
from config.config import RunConfig


#time
import time
start = time.time()  # Start time here

# ---------------- PyROOT ONLY for histograms (separate file) ----------------
import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.TH1.AddDirectory(False)

# ---------------- Helpers ----------------
def _ensure_1d(a):
    a = np.asarray(a)
    return a.ravel()

def make_th1_pyroot(values, weights, name, title, binning):
    v  = _ensure_1d(values)
    w  = None if weights is None else _ensure_1d(weights)

    if w is not None:
        mask = np.isfinite(v) & np.isfinite(w)
        v = v[mask]; w = w[mask]
    else:
        mask = np.isfinite(v)
        v = v[mask]

    v2 = v.copy()

    def _is_angular_name(s):
        s = (s or "").lower()
        return ("phi" in s) or ("deltaphi" in s) or s.endswith("_phi")

    def _maybe_angle_edges(arr):
        if arr.size < 2 or not np.isfinite(arr).all():
            return False
        rng = float(np.nanmax(arr) - np.nanmin(arr))
        return (rng <= 2*np.pi + 1e-6) and (np.nanmin(arr) >= -2*np.pi-1e-6) and (np.nanmax(arr) <= 2*np.pi+1e-6)

    def _unwrap_edges_and_values(edges, vals):
        e = edges.astype("f8").copy()
        for i in range(1, e.size):
            if e[i] <= e[i-1] - 1e-15:
                shift = 2*np.pi * np.ceil((e[i-1] - e[i] + 1e-15)/(2*np.pi))
                e[i:] = e[i:] + shift
        e0 = e[0]; two_pi = 2*np.pi
        vals_out = vals.copy()
        fm = np.isfinite(vals_out)
        vals_out[ fm ] = (vals_out[ fm ] - e0) % two_pi + e0
        return e, vals_out

    if isinstance(binning, np.ndarray) or (
        isinstance(binning, (list, tuple)) and not (
            len(binning) == 3 and all(np.isscalar(x) for x in binning)
        )
    ):
        edges_np = np.asarray(binning, dtype="f8").ravel()
        edges_np = edges_np[np.isfinite(edges_np)]
        if edges_np.size < 2:
            raise ValueError(f"[{name}] Variable bin edges must have length >= 2, got: {edges_np}")

        if not np.all(np.diff(edges_np) > 0):
            if _is_angular_name(name) or _maybe_angle_edges(edges_np):
                edges_np, v2 = _unwrap_edges_and_values(edges_np, v2)
            else:
                e_sorted_unique = np.unique(edges_np)
                if e_sorted_unique.size < 2 or not np.all(np.diff(e_sorted_unique) > 0):
                    raise ValueError(f"[{name}] Invalid variable bin edges (not strictly increasing).")
                print(f"[WARN] {name}: edges not strictly increasing; using sorted unique edges.")
                edges_np = e_sorted_unique

        nb = len(edges_np) - 1
        h = ROOT.TH1D(name, title, int(nb), edges_np)
    else:
        nb, lo, hi = binning
        nb = int(nb); lo = float(lo); hi = float(hi)
        if not np.isfinite([lo, hi]).all() or hi <= lo or nb <= 0:
            raise ValueError(f"[{name}] Invalid (nb, lo, hi): {binning}")
        h = ROOT.TH1D(name, title, nb, lo, hi)
        edges_np = np.linspace(lo, hi, nb + 1, dtype="f8")

    if v2.dtype == np.bool_:
        v2 = v2.astype("f8")
    if w is not None and w.dtype == np.bool_:
        w = w.astype("f8")

    counts, _ = np.histogram(v2, bins=edges_np, weights=w)
    if w is None:
        sumw2 = counts.astype("f8")
    else:
        sumw2, _ = np.histogram(v2, bins=edges_np, weights=w * w)

    h.Sumw2()
    for i in range(1, h.GetNbinsX() + 1):
        c  = float(counts[i - 1])
        e2 = float(sumw2[i - 1])
        h.SetBinContent(i, c)
        h.SetBinError(i, float(np.sqrt(e2) if e2 >= 0 else 0.0))

    h.SetDirectory(0)
    return h


def detect_year_era_from_name(path: str):
    name = path.lower()

    year = None
    era = None

    # --- explicit year in path ---
    if "2022" in name:
        year = "2022"
    elif "2023" in name:
        year = "2023"
    elif "2024" in name:
        year = "2024"
    elif "2025" in name:
        year = "2025"

    # --- era implies year ---
    if "preee" in name:
        era = "PreEE"
        year = "2022"
    elif "postee" in name:
        era = "PostEE"
        year = "2022"
    elif "prebpix" in name:
        era = "preBPix"
        year = "2023"
    elif "postbpix" in name:
        era = "postBPix"
        year = "2023"

    # --- 2024/2025 have no sub-eras ---
    if year in ("2024", "2025") and era is None:
        era = "All"

    return year, era


# Numeric era code, one entry per BTAG_MEDIUM_WP key in regions.py --
# kept here since (year, era) is correctly detected per file here;
# regions.py only ever sees the resolved integer via cms_events.era_code.
ERA_CODES = {
    ("2022", "PreEE"): 0,
    ("2022", "PostEE"): 1,
    ("2023", "preBPix"): 2,
    ("2023", "postBPix"): 3,
    ("2024", "All"): 4,
    ("2025", "All"): 5,
}


def era_code_from_year_era(year, era):
    """Map (year, era) to the integer era code used by cms_events.era_code
    and regions.py's BTAG_MEDIUM_WP/UPART_YEARS. Raises on an unmapped
    combination rather than silently defaulting."""
    key = (str(year), str(era))
    if key not in ERA_CODES:
        raise ValueError(
            f"era_code_from_year_era: no era code mapped for (year={year!r}, "
            f"era={era!r}). Known combinations: {sorted(ERA_CODES.keys())}."
        )
    return ERA_CODES[key]


# Maps (year, era) to the era-suffix string actually used in year-specific
# UNCORRELATED b-tag SF weight branch names -- confirmed directly against
# real production schema (a full branch list from an actual 2022postEE
# file): the real columns are weight_btagSFbc_2022postEEUp/Down, NOT
# weight_btagSFbc_2022Up/Down as this file's own lookup previously
# assumed. This was a genuine, live bug (confirmed via the
# "[WARN] ... missing year-specific uncorrelated b-tag SF column(s)"
# print firing on every single 2022/2023 file, since the constructed
# column name never matched anything real) -- not just a naming
# preference. 2024/2025 have no sub-era in the branch name at all (the
# year alone is the correct suffix there), matching what this file's
# code already assumed correctly for those two years specifically.
#
# This mapping ALSO directly resolves the separate correlated/
# uncorrelated design question: bTagSF_bc_correlated/bTagSF_light_correlated
# (in WEIGHT_SYSTEMATICS above) already use a single FIXED nuisance name
# regardless of year/era, so combineCards.py naturally treats them as one
# shared, correlated systematic across every era -- exactly as intended.
# The uncorrelated pair, by using THIS per-era suffix in its own nuisance
# name (bTagSF_bc_<era_suffix>), gets a genuinely distinct name per
# sub-era -- so Combine treats 2022preEE's and 2022postEE's uncorrelated
# components as two independent nuisances, never silently merged under
# one shared name. No further, separate "implement correlated vs
# uncorrelated" work is needed beyond this naming fix -- the STRUCTURE
# was already correct; only the uncorrelated branch's constructed name
# was wrong.
WEIGHT_COLUMN_ERA_SUFFIX = {
    ("2022", "PreEE"): "2022preEE",
    ("2022", "PostEE"): "2022postEE",
    ("2023", "preBPix"): "2023preBPix",
    ("2023", "postBPix"): "2023postBPix",
}


def weight_column_era_suffix(year, era):
    year = str(year)
    if year in ("2024", "2025"):
        return year
    key = (year, str(era))
    if key not in WEIGHT_COLUMN_ERA_SUFFIX:
        raise ValueError(
            f"weight_column_era_suffix: no mapping for (year={year!r}, era={era!r}). "
            f"Known combinations: {sorted(WEIGHT_COLUMN_ERA_SUFFIX.keys())} plus "
            f"'2024'/'2025' (year-only, no sub-era)."
        )
    return WEIGHT_COLUMN_ERA_SUFFIX[key]


# ---------------- Nested-folder / systematic-variation handling ----------------
# Same convention as inference_PDnn.py's classify_systematic(), duplicated here
# (rather than imported) so this script has no hard dependency on the pDNN
# working directory. Keep the two in sync if the naming convention changes.
SYSTEMATIC_VARIATION_RE = re.compile(r"(_up|_down)$", re.IGNORECASE)


def classify_systematic(file_path: Path):
    """Identify which systematic-variation folder (if any) a file belongs to.

    Returns "nominal" if a parent directory is literally named "nominal",
    the matched folder name (e.g. "jec_syst_Total_up") if a parent
    directory matches the "_up"/"_down" naming convention, or None if
    neither is found anywhere in the path -- i.e. a flat file with no
    systematic-folder structure at all (the old layout used for
    background/data samples), which is always kept.
    """
    parts = [file_path.parent.name] + [p.name for p in file_path.parents]
    for part in parts:
        if part.lower() == "nominal":
            return "nominal"
    for part in parts:
        if SYSTEMATIC_VARIATION_RE.search(part):
            return part
    return None


def collect_parquet_files(root: Path, all_systematics: bool = False):
    """Recursively find parquet files under `root`, restricted to 'nominal'
    (plus any flat file with no systematic-folder structure at all) unless
    `all_systematics` is set.

    This mirrors inference_PDnn.py's default behavior exactly, since only
    'nominal' files are guaranteed to actually carry a pDNN_score column
    -- reading a systematic-variation file that was never scored would
    otherwise raise immediately in process_parquet_file().
    """
    all_files = sorted(root.rglob("*.parquet"))
    if all_systematics:
        return all_files

    kept, skipped = [], set()
    for fp in all_files:
        syst = classify_systematic(fp)
        if syst is None or syst == "nominal":
            kept.append(fp)
        else:
            skipped.add(syst)
    if skipped:
        print(f"[INFO] {root}: restricting to 'nominal' (pass --all-systematics to also "
              f"process {len(all_files) - len(kept)} file(s) under systematic-variation "
              f"folders): {sorted(skipped)}")
    return kept


def ensure_dir_in_tfile(tfile, path):
    curr = tfile
    if not path:
        return curr
    for part in path.split('/'):
        d = curr.GetDirectory(part)
        curr = d if d else curr.mkdir(part)
    return curr

def normalize_sample_name(name: str) -> str:
    base = os.path.basename(name)
    base = re.sub(r"\.(parquet|root)$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"(_part\d+|_chunk\d+|_\d+of\d+)$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"[_-]?(2022|2023)(PreEE|PostEE|All|preBPix|postBPix)?", "", base, flags=re.IGNORECASE)
    return base

# Filenames that carry no sample identity of their own -- the newer
# HiggsDNA-style production names EVERY leaf file identically (e.g.
# "NOTAG_merged.parquet") regardless of mass point or process, so the
# basename alone cannot distinguish samples the way the older flat-file
# convention (e.g. "2022_preEE_GGJets_low_Rescaled.parquet") could.
GENERIC_BASENAME_RE = re.compile(r"^(notag[_-]?merged|merged)$", re.IGNORECASE)


def resolve_sample_name(inputfile: str) -> str:
    """Resolve the sample identity for a file, robust to both naming
    conventions in use across productions.

    - Old flat convention (unique, descriptive basename): use the
      basename as before (normalize_sample_name), unchanged behavior.
    - New nested convention (generic basename like "NOTAG_merged"):
      fall back to the nearest ANCESTOR directory that is not itself a
      systematic-variation folder ("nominal", "*_up", "*_down") -- e.g.
      ".../NMSSM_X700_Y500/nominal/NOTAG_merged.parquet" resolves to
      "NMSSM_X700_Y500", not "NOTAG_merged" for every mass point at once.

    Without this fallback, every file sharing the generic basename would
    resolve to the identical sample_name_norm, silently colliding
    unrelated samples onto the same output tree/histogram path.
    """
    p = Path(inputfile)
    base = os.path.basename(inputfile)
    sample_name_raw = base.replace(".parquet", "").replace(".root", "")

    if not GENERIC_BASENAME_RE.match(sample_name_raw):
        return normalize_sample_name(sample_name_raw)

    candidate = p.parent
    if candidate.name.lower() == "nominal" or SYSTEMATIC_VARIATION_RE.search(candidate.name):
        candidate = candidate.parent
    return normalize_sample_name(candidate.name)


def ak_to_numpy_dict(arr: ak.Array) -> dict:
    out = {}
    for key in arr.fields:
        filled = ak.fill_none(arr[key], -9999)
        np_arr = ak.to_numpy(filled)
        if np.issubdtype(np_arr.dtype, np.integer):
            np_arr = np.nan_to_num(np_arr.astype("int64"), nan=-9999, posinf=999999999, neginf=-999999999)
        else:
            np_arr = np.nan_to_num(np_arr, nan=-9999, posinf=999999999, neginf=-999999999)
        out[key] = np_arr
    return out

def concat_field_dicts(dict_list):
    out = {}
    if not dict_list:
        return out
    keys = dict_list[0].keys()
    for k in keys:
        arrs = [np.asarray(d[k]) for d in dict_list if k in d]
        if len(arrs) == 0:
            out[k] = np.array([], dtype=np.float32)
        elif len(arrs) == 1:
            out[k] = arrs[0]
        else:
            out[k] = np.concatenate(arrs, axis=0)
    return out

## dtypes before writing to avoid out of range in 32-bit
def sanitize_for_uproot(d: dict) -> dict:
    """
    Make arrays uproot-safe:
      * ints -> int64
      * uints -> int64 (may clip negatives if any appear after cast, but we don't expect them)
      * floats -> float64
      * bool -> int8
      * forbid object dtypes
    Also ensure finite values (replace NaN/Inf).
    """
    out = {}
    for k, v in d.items():
        a = np.asarray(v)
        if a.dtype == np.bool_:
            a = a.astype(np.int8, copy=False)
        elif a.dtype.kind == "u":  # unsigned ints
            a = a.astype(np.int64, copy=False)
        elif a.dtype.kind == "i":  # signed ints
            a = a.astype(np.int64, copy=False)
        elif a.dtype.kind == "f":  # floats
            a = a.astype(np.float64, copy=False)
        elif a.dtype.kind == "O":
            raise TypeError(f"Branch '{k}' has object dtype; not supported in ROOT trees.")
        # replace non-finites with sentinels
        if a.dtype.kind in ("i", "u"):
            a = np.nan_to_num(a, nan=-9999, posinf=999999999, neginf=-999999999)
        else:
            a = np.nan_to_num(a, nan=-9999.0, posinf=9.999e306, neginf=-9.999e306)
        out[k] = a
    return out


# ---------------- Global accumulators ----------------
HIST_CACHE = {}   # (sample, systematic, region, varname) -> TH1D
TREE_CACHE = {}   # "sample/systematic/region" -> WritableTree handle, created once, extended
                   # repeatedly. Without this, write_tree_chunked()'s wdir.mktree() call (once
                   # per batch, once per region, once per file) creates a brand-new ROOT/uproot
                   # cycle every single time instead of appending to one tree -- silently
                   # discarding every cycle except the last one on any default read.

# ---------------- Weight-based systematics ----------------
# Column pairs read from the ntuple, one entry per systematic source. Each
# is a (up_column, down_column) tuple. These are all already present in the
# raw ntuple -- no new inference/analyzer files needed, unlike the
# folder-based (JEC/JER/Smearing/Scale) systematics.
#
# NOTE: only the columns present in a given file's schema are actually used
# (checked per-file, like ttH_killer_score) so this degrades gracefully on
# older productions that don't carry the full set.
WEIGHT_SYSTEMATICS = {
    "Pileup":          ("weight_PileupUp", "weight_PileupDown"),
    "TriggerSF":       ("weight_TriggerSFUp", "weight_TriggerSFDown"),
    "PreselSF":        ("weight_PreselSFUp", "weight_PreselSFDown"),
    "ElectronVetoSF":  ("weight_ElectronVetoSFUp", "weight_ElectronVetoSFDown"),
    "bTagSF_hf":        ("weight_bTagSF_sys_hfUp", "weight_bTagSF_sys_hfDown"),
    "bTagSF_lf":        ("weight_bTagSF_sys_lfUp", "weight_bTagSF_sys_lfDown"),
    "bTagSF_cferr1":    ("weight_bTagSF_sys_cferr1Up", "weight_bTagSF_sys_cferr1Down"),
    "bTagSF_cferr2":    ("weight_bTagSF_sys_cferr2Up", "weight_bTagSF_sys_cferr2Down"),
    "bTagSF_hfstats1":  ("weight_bTagSF_sys_hfstats1Up", "weight_bTagSF_sys_hfstats1Down"),
    "bTagSF_hfstats2":  ("weight_bTagSF_sys_hfstats2Up", "weight_bTagSF_sys_hfstats2Down"),
    "bTagSF_lfstats1":  ("weight_bTagSF_sys_lfstats1Up", "weight_bTagSF_sys_lfstats1Down"),
    "bTagSF_lfstats2":  ("weight_bTagSF_sys_lfstats2Up", "weight_bTagSF_sys_lfstats2Down"),
    "bTagSF_jes":       ("weight_bTagSF_sys_jesUp", "weight_bTagSF_sys_jesDown"),
    "bTagSF_bc_correlated":    ("weight_btagSFbc_correlatedUp", "weight_btagSFbc_correlatedDown"),
    "bTagSF_light_correlated": ("weight_btagSFlight_correlatedUp", "weight_btagSFlight_correlatedDown"),
}


def weight_systematic_value(weight_variant: np.ndarray, xsec: float, lumi: float) -> np.ndarray:
    """Compute a systematic-varied event weight by DIRECT SUBSTITUTION of
    the systematic weight column into the exact same normalization formula
    used for the nominal weight (weight_<syst> * xsec * lumi), mirroring
    `base_w = weight * xsec * lumi` in process_parquet_file with
    weight_<syst>Up/Down standing in for `weight`.

    weight_central is not used anywhere in this computation or elsewhere
    in this script -- confirmed to have no role in this pipeline's weight
    normalization.
    """
    w = np.where(np.isfinite(weight_variant), weight_variant, 0.0)
    out = w * float(xsec) * float(lumi)
    return np.where(np.isfinite(out), out, 0.0)


# ---------------- Utils ----------------
def is_signal_from_name(name: str) -> bool:
    s = name
    return any(x in s for x in [
        "GluGluToHH", "VBFHH", "Radion", "Graviton", "XToHH", "HHTo", "HHTobbgg",
        "NMSSM",  # this analysis's actual resonant signal (X->YH); previously unmatched
    ])
    
def is_dd_template(path: str) -> bool:
    """Return True for DD fake-γ templates (rescaled parquet files).

    Uses a regex (ddqc+dgjets?) for the QCD+GJet template instead of a
    fixed substring list, since the naming varies across productions --
    e.g. "DDQCDGJET_Rescaled" (2022, single C) vs "DDQCCDGJets" (2024,
    double C, no _Rescaled suffix). A plain substring check on the older
    spelling silently misses the newer one, which would fall through to
    regular MC xsec/lumi normalization instead of being treated as a DD
    template with its own per-event weight column.
    """
    b = os.path.basename(path).lower()
    if re.search(r"ddqc+dgjets?", b):
        return True
    return any(k in b for k in ("ggjets_low_rescaled", "ggjets_high_rescaled"))

# Which column to use for DD event weights if not 'weight'
DD_WEIGHT_COLUMNS = ("weight", "evt_weight", "w", "fake_weight")

def _get_dd_weight_col(all_columns) -> str:
    """Find the name of the event-weight column in DD files."""
    cols = set(map(str, all_columns))
    for c in DD_WEIGHT_COLUMNS:
        if c in cols:
            return c
    raise KeyError(
        "No DD weight column found in DD template. "
        f"Tried: {', '.join(DD_WEIGHT_COLUMNS)}; available: {sorted(cols)}"
    )

# ---------------- Core processing ----------------
def process_parquet_file(inputfile, cli_year, cli_era, xsec_lumi_cache=None, tree_upfile=None,
                          skip_trees=False, skip_histograms=False):
    """
    Process a single parquet file and accumulate:
      - histograms per (sample, region, variable)
      - regional trees per (sample, region)
      - full processed_events per sample
    """
    print(f"[INFO] Processing Parquet file: {inputfile}")
    required_columns = [
        "run",
        "lumi",
        "event",
        "Res_lead_bjet_pt",
        "Res_lead_bjet_eta",
        "Res_lead_bjet_phi",
        "Res_lead_bjet_mass",
        "Res_sublead_bjet_pt",
        "Res_sublead_bjet_eta",
        "Res_sublead_bjet_phi",
        "Res_sublead_bjet_mass",
        "lead_pt",
        "lead_eta",
        "lead_phi",
        "lead_mvaID_WP90",
        "lead_mvaID_WP80",
        "sublead_pt",
        "sublead_eta",
        "sublead_phi",
        "sublead_mvaID_WP90",
        "sublead_mvaID_WP80",
        "weight",
        "Res_lead_bjet_btagPNetB",
        "Res_sublead_bjet_btagPNetB",
        "Res_lead_bjet_PNetRegPtRawRes",     # Adding particle net regressed varaible
        "Res_sublead_bjet_PNetRegPtRawRes",   # Adding particle net regressed varaible
        # NOTE: Res_lead_bjet_btagUParTAK4B / Res_sublead_bjet_btagUParTAK4B
        # (the UParT b-tag discriminant, 2024/2025 only) are DELIBERATELY
        # NOT listed here unconditionally -- confirmed as a real, live
        # crash: these columns genuinely do not exist in 2022/2023 parquet
        # schemas, and requesting/consuming them unconditionally raised
        # awkward.errors.FieldNotFoundError the first time this ran against
        # real 2022 data. Checked per-file below instead, via schema_names,
        # the same pattern already used for ttH_killer_score just below.
        "lead_isScEtaEB",
        "sublead_isScEtaEB",
        "lead_isScEtaEE",
        "sublead_isScEtaEE",
        "Res_HHbbggCandidate_pt",
        "Res_HHbbggCandidate_eta",
        "Res_HHbbggCandidate_phi",
        "Res_HHbbggCandidate_mass",
        "Res_CosThetaStar_CS",
        "Res_CosThetaStar_gg",
        "Res_CosThetaStar_jj",
        "Res_DeltaR_jg_min",
        "Res_pholead_PtOverM",
        "Res_phosublead_PtOverM",
        "Res_FirstJet_PtOverM",
        "Res_SecondJet_PtOverM",
        "lead_mvaID",
        "sublead_mvaID",
        "Res_DeltaR_j1g1",
        "Res_DeltaR_j2g1",
        "Res_DeltaR_j1g2",
        "Res_DeltaR_j2g2",
        "Res_M_X",
        "Res_DeltaPhi_j1MET",
        "Res_DeltaPhi_j2MET",
        "Res_chi_t0",
        "Res_chi_t1",
        "lepton1_mvaID",
        "lepton1_pt",
        "lepton1_pfIsoId",
        "n_jets",
        # Number of jets ration (BTV)
        "Njets2p5",
        # Jets for the HT(BTV)
        "jet10_pt",
        "jet1_pt",
        "jet2_pt",
        "jet3_pt",
        "jet4_pt",
        "jet5_pt",
        "jet6_pt",
        "jet7_pt",
        "jet8_pt",
        "jet9_pt",
        #pDNN Score
        "pDNN_score",
        # number of leptons
        "n_leptons"
    ]

    parquet_file = pq.ParquetFile(inputfile)

    # Folder-based (object-level) systematic label for this file, e.g.
    # "jec_syst_Total_up", or "nominal" for both the nominal folder and any
    # flat file with no systematic-folder structure at all. Moved up from
    # later in this function specifically so it's available here, to gate
    # the weight-systematic missing-column warnings below (see those sites
    # for why: those columns/variants are only ever used for nominal-folder
    # files in the first place, per systematic_passes further down, so
    # warning about their absence on every non-nominal file was noisy and
    # misleading, not indicative of an actual problem).
    folder_systematic = classify_systematic(Path(inputfile)) or "nominal"

    # ttH_killer_score is read from inference_ttH_killer.py's output, which
    # runs after pDNN scoring but may not have touched every file yet during
    # the transition -- checked per-file rather than assumed, so a file
    # without it doesn't crash the whole run.
    has_tth_score = "ttH_killer_score" in parquet_file.schema.names
    if has_tth_score:
        required_columns.append("ttH_killer_score")
    else:
        print(f"[WARN] {inputfile}: no ttH_killer_score column found "
              f"(has inference_ttH_killer.py been run on this file yet?); "
              f"filling with NaN.")

    # UParT b-tag discriminant: confirmed 2024/2025-only in real production
    # schemas -- 2022/2023 files genuinely do not have these columns at
    # all (a real, live crash confirmed this: FieldNotFoundError when
    # accessed unconditionally against 2022 data). Checked per-file,
    # exactly like ttH_killer_score above, rather than assumed from year.
    # Both lead+sublead required together -- if only one were present,
    # that would itself indicate a genuine schema problem worth seeing
    # rather than silently proceeding with a mismatched pair.
    _upart_cols = ("Res_lead_bjet_btagUParTAK4B", "Res_sublead_bjet_btagUParTAK4B")
    has_upart = all(c in parquet_file.schema.names for c in _upart_cols)
    if has_upart:
        required_columns.extend(_upart_cols)
    elif any(c in parquet_file.schema.names for c in _upart_cols):
        print(f"[WARN] {inputfile}: only ONE of {_upart_cols} is present -- "
              f"treating UParT as unavailable for this file (filling both "
              f"with NaN) rather than proceeding with a mismatched pair.")
    else:
        print(f"[INFO] {inputfile}: no UParT b-tag columns found (expected for "
              f"pre-2024 production) -- filling lead/sublead_bjet_PNetUParTAK4B "
              f"with NaN.")

    # Weight-systematic columns: only request the ones actually present in
    # this file's schema (older productions may not carry the full set).
    schema_names = set(parquet_file.schema.names)
    available_weight_systs = {}
    for syst_name, (up_col, down_col) in WEIGHT_SYSTEMATICS.items():
        cols_present = [c for c in (up_col, down_col) if c in schema_names]
        for c in cols_present:
            if c not in required_columns:
                required_columns.append(c)
        if cols_present:
            available_weight_systs[syst_name] = (
                up_col if up_col in schema_names else None,
                down_col if down_col in schema_names else None,
            )
    missing_weight_systs = set(WEIGHT_SYSTEMATICS) - set(available_weight_systs)
    if missing_weight_systs and folder_systematic == "nominal":
        print(f"[WARN] {inputfile}: missing weight-systematic column(s) for "
              f"{sorted(missing_weight_systs)}; those variants will be skipped for this file.")
    # (No warning for non-nominal folders: weight-systematic variants are
    # only ever USED for nominal-folder files -- see systematic_passes
    # further down -- so their absence in e.g. a ScaleEB_Zee_down file is
    # expected and not itself informative about whether the underlying
    # upstream data actually has these columns.)

    sample_name_norm = resolve_sample_name(inputfile)

    # Classify using the RESOLVED sample identity, not the raw leaf
    # basename -- under the new nested convention every leaf file is
    # named identically ("NOTAG_merged.parquet"), so classifying from
    # `base` would never recognize NMSSM signal or DD templates at all,
    # independent of any pattern-matching fix to is_signal_from_name /
    # is_dd_template themselves.
    isdata = "Data" in sample_name_norm
    sigflag = is_signal_from_name(sample_name_norm)
    isdd   = is_dd_template(sample_name_norm)


    
    det_year, det_era = detect_year_era_from_name(inputfile)
    use_year = det_year or str(cli_year)
    use_era  = det_era  or str(cli_era) 

    _era_suffix = weight_column_era_suffix(use_year, use_era)
    for _flavor in ("bc", "light"):
        _syst_name = f"bTagSF_{_flavor}_{_era_suffix}"
        _up_col = f"weight_btagSF{_flavor}_{_era_suffix}Up"
        _down_col = f"weight_btagSF{_flavor}_{_era_suffix}Down"
        _cols_present = [c for c in (_up_col, _down_col) if c in schema_names]
        for _c in _cols_present:
            if _c not in required_columns:
                required_columns.append(_c)
        if _cols_present:
            available_weight_systs[_syst_name] = (
                _up_col if _up_col in schema_names else None,
                _down_col if _down_col in schema_names else None,
            )
        else:
            if folder_systematic == "nominal":
                print(f"[WARN] {inputfile}: missing year-specific uncorrelated b-tag SF "
                      f"column(s) for {_syst_name} (looked for {_up_col}/{_down_col}); "
                      f"that variant will be skipped for this file.")
            # (No warning for non-nominal folders -- same reasoning as the
            # general weight-systematics warning above: these variants are
            # only ever used for nominal-folder files.)

    if xsec_lumi_cache is None:
        xsec_lumi_cache = {}
    if inputfile not in xsec_lumi_cache:
        if isdata or isdd:
            # No σ×L scaling for data or DD templates
            xsec_lumi_cache[inputfile] = (1.0, 1.0)
        else:
            # Use the RESOLVED sample identity, not the raw file path --
            # getXsec() matches by substring against os.path.basename() of
            # whatever it's given, and every file in the newer HiggsDNA-
            # style production shares the identical generic leaf filename
            # "NOTAG_merged.parquet". Passing inputfile directly meant
            # getXsec() was matching against "notagmerged" for nearly
            # every sample -- silently falling through to its 1.0 pb
            # default for the vast majority of signal and background
            # samples alike, with no error or warning. sample_name_norm
            # is already correctly resolved above (via resolve_sample_name)
            # to the real per-sample identity (e.g. "GGJets_MGG-80",
            # "GluGluHtoGG") and is what must be used here instead.
            xsec_lumi_cache[inputfile] = (float(getXsec(sample_name_norm)),
                                          float(getLumi(use_year, use_era)) * 1000.0,      # lumi in pb^-1
                                          )      
    xsec_, lumi_ = xsec_lumi_cache[inputfile]
    print(f"[NORM] sample={os.path.basename(inputfile)} xsec={xsec_} pb, "
      f"lumi={lumi_/1000.0:.3f} fb^-1 ({use_year} {use_era}) "
      f"[flags: data={isdata} dd = {isdd}]") 


    # region utils & plotting config
    from regions import (
        get_mask_preselection,
        get_mask_selection,
        get_mask_srbbgg,
        get_mask_srbbgg_EBEB,
        get_mask_srbbgg_mixed,
        get_mask_srbbgg_EEEE,
        get_mask_srbbggMET,
        get_mask_crantibbgg, 
        get_mask_crbbantigg, 
        get_mask_crantibbantigg,
        get_mask_sideband,
        get_mask_idmva_presel, 
        get_mask_idmva_sideband,
    )
    from variables import vardict, regions, variables_common
    from binning import binning

    for batch in parquet_file.iter_batches(batch_size=10000, columns=required_columns):
        df = batch.to_pandas()
        print(f"[INFO] Batch rows: {len(df)}")
        tree_ = ak.from_arrow(pyarrow.Table.from_pandas(df))

        cms_events = ak.zip(
            {
                "run": tree_["run"], "lumi": tree_["lumi"],
                "event": tree_["event"],
                "lead_bjet_pt": tree_["Res_lead_bjet_pt"], 
                "lead_bjet_eta": tree_["Res_lead_bjet_eta"],
                "lead_bjet_phi": tree_["Res_lead_bjet_phi"], 
                "lead_bjet_mass": tree_["Res_lead_bjet_mass"],
                "sublead_bjet_pt": tree_["Res_sublead_bjet_pt"],
                "sublead_bjet_eta": tree_["Res_sublead_bjet_eta"],
                "sublead_bjet_phi": tree_["Res_sublead_bjet_phi"],
                "sublead_bjet_mass": tree_["Res_sublead_bjet_mass"],
                "lead_pho_pt": tree_["lead_pt"], 
                "lead_pho_eta": tree_["lead_eta"], 
                "lead_pho_phi": tree_["lead_phi"],
                "lead_pho_mvaID_WP90": tree_["lead_mvaID_WP90"], 
                "lead_pho_mvaID_WP80": tree_["lead_mvaID_WP80"],
                "sublead_pho_pt": tree_["sublead_pt"], 
                "sublead_pho_eta": tree_["sublead_eta"], 
                "sublead_pho_phi": tree_["sublead_phi"],
                "sublead_pho_mvaID_WP90": tree_["sublead_mvaID_WP90"],
                "sublead_pho_mvaID_WP80": tree_["sublead_mvaID_WP80"],
                "weight": tree_["weight"],
                "lead_bjet_PNetB": tree_["Res_lead_bjet_btagPNetB"], 
                "sublead_bjet_PNetB": tree_["Res_sublead_bjet_btagPNetB"],
                "lead_bjet_PNetRegPtRawRes": tree_["Res_lead_bjet_PNetRegPtRawRes"],    # Adding particle net regressed varaible 
                "sublead_bjet_PNetRegPtRawRes":tree_["Res_sublead_bjet_PNetRegPtRawRes"], # Adding particle net regressed varaible
                "lead_bjet_PNetUParTAK4B": (
                    tree_["Res_lead_bjet_btagUParTAK4B"] if has_upart
                    else ak.Array(np.full(len(tree_), np.nan, dtype="float32"))
                ),    # Adding particle net  varaible for 2024 and 2025
                "sublead_bjet_PNetUParTAK4B": (
                    tree_["Res_sublead_bjet_btagUParTAK4B"] if has_upart
                    else ak.Array(np.full(len(tree_), np.nan, dtype="float32"))
                ), # Adding particle net  varaible for 2024 and 2025
                "lead_isScEtaEB": tree_["lead_isScEtaEB"],
                "sublead_isScEtaEB": tree_["sublead_isScEtaEB"],
                "lead_isScEtaEE": tree_["lead_isScEtaEE"],
                "sublead_isScEtaEE": tree_["sublead_isScEtaEE"],
                "CosThetaStar_CS": tree_["Res_CosThetaStar_CS"],
                "CosThetaStar_gg": tree_["Res_CosThetaStar_gg"], 
                "CosThetaStar_jj": tree_["Res_CosThetaStar_jj"],
                "DeltaR_jg_min": tree_["Res_DeltaR_jg_min"],
                "pholead_PtOverM": tree_["Res_pholead_PtOverM"],
                "phosublead_PtOverM": tree_["Res_phosublead_PtOverM"],
                "FirstJet_PtOverM": tree_["Res_FirstJet_PtOverM"], 
                "SecondJet_PtOverM": tree_["Res_SecondJet_PtOverM"],
                "lead_pho_mvaID": tree_["lead_mvaID"],
                "sublead_pho_mvaID": tree_["sublead_mvaID"],
                "DeltaR_j1g1": tree_["Res_DeltaR_j1g1"],
                "DeltaR_j2g1": tree_["Res_DeltaR_j2g1"],
                "DeltaR_j1g2": tree_["Res_DeltaR_j1g2"],
                "DeltaR_j2g2": tree_["Res_DeltaR_j2g2"],
                "bbgg_mass": tree_["Res_HHbbggCandidate_mass"],
                "bbgg_pt": tree_["Res_HHbbggCandidate_pt"],
                "bbgg_eta": tree_["Res_HHbbggCandidate_eta"],
                "bbgg_phi": tree_["Res_HHbbggCandidate_phi"],
                "MX": tree_["Res_M_X"],
                "DeltaPhi_j1MET": tree_["Res_DeltaPhi_j1MET"],
                "DeltaPhi_j2MET": tree_["Res_DeltaPhi_j2MET"],
                "Res_chi_t0": tree_["Res_chi_t0"],
                "Res_chi_t1": tree_["Res_chi_t1"],
                "lepton1_mvaID": tree_["lepton1_mvaID"],
                "lepton1_pt": tree_["lepton1_pt"], 
                "lepton1_pfIsoId": tree_["lepton1_pfIsoId"],
                "n_jets": tree_["n_jets"],
                "Njets2p5": tree_["Njets2p5"],
                "jet10_pt": tree_["jet10_pt"],
                "jet1_pt": tree_["jet1_pt"],
                "jet2_pt": tree_["jet2_pt"],
                "jet3_pt": tree_["jet3_pt"],
                "jet4_pt": tree_["jet4_pt"],
                "jet5_pt": tree_["jet5_pt"],
                "jet6_pt": tree_["jet6_pt"],
                "jet7_pt": tree_["jet7_pt"],
                "jet8_pt": tree_["jet8_pt"],
                "jet9_pt": tree_["jet9_pt"],
                "pDNN_score":tree_["pDNN_score"],
                "n_leptons": tree_["n_leptons"],
                "ttH_killer_score": (
                    tree_["ttH_killer_score"] if has_tth_score
                    else ak.Array(np.full(len(tree_), np.nan, dtype="float32"))
                ),
            },
            depth_limit=1,
        )

        n_entries = len(tree_)
        cms_events["signal"] = ak.Array(np.full(n_entries, 1 if sigflag else 0, dtype=np.int8))
        cms_events["isdata"] = ak.Array(np.full(n_entries, 1 if isdata else 0, dtype=np.int8))
        cms_events["isdd"]   = ak.Array(np.full(n_entries, 1 if isdd   else 0, dtype=np.int8))
        this_era_code = era_code_from_year_era(use_year, use_era)
        cms_events["era_code"] = ak.Array(np.full(n_entries, this_era_code, dtype=np.int8))

        # Weight-systematic variant columns, for whichever ones this file's
        # schema actually has (per available_weight_systs, computed above).
        for syst_name, (up_col, down_col) in available_weight_systs.items():
            for col in (up_col, down_col):
                if col is not None:
                    cms_events[col] = tree_[col]

        out_events = ak.zip({"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]}, depth_limit=1)

        dibjet_ = lVector(
            cms_events["lead_bjet_pt"], cms_events["lead_bjet_eta"], cms_events["lead_bjet_phi"],
            cms_events["sublead_bjet_pt"], cms_events["sublead_bjet_eta"], cms_events["sublead_bjet_phi"],
            cms_events["lead_bjet_mass"], cms_events["sublead_bjet_mass"],
        )
        diphoton_ = lVector(
            cms_events["lead_pho_pt"], cms_events["lead_pho_eta"], cms_events["lead_pho_phi"],
            cms_events["sublead_pho_pt"], cms_events["sublead_pho_eta"], cms_events["sublead_pho_phi"],
        )
        cms_events["dibjet_mass"] = dibjet_.mass
        cms_events["dibjet_pt"]   = dibjet_.pt
        cms_events["diphoton_mass"] = diphoton_.mass
        cms_events["diphoton_pt"]   = diphoton_.pt
        cms_events["dibjet_eta"] = dibjet_.eta
        cms_events["dibjet_phi"] = dibjet_.phi
        cms_events["diphoton_eta"] = diphoton_.eta
        cms_events["diphoton_phi"] = diphoton_.phi

        cms_events["lead_pt_over_diphoton_mass"]    = cms_events["lead_pho_pt"]     / cms_events["diphoton_mass"]
        cms_events["sublead_pt_over_diphoton_mass"] = cms_events["sublead_pho_pt"]  / cms_events["diphoton_mass"]
        cms_events["lead_pt_over_dibjet_mass"]      = cms_events["lead_bjet_pt"]    / cms_events["dibjet_mass"]
        cms_events["sublead_pt_over_dibjet_mass"]   = cms_events["sublead_bjet_pt"] / cms_events["dibjet_mass"]
        cms_events["diphoton_bbgg_mass"] = cms_events["diphoton_pt"] / cms_events["bbgg_mass"]
        cms_events["dibjet_bbgg_mass"]   = cms_events["dibjet_pt"]   / cms_events["bbgg_mass"]

        cms_events["max_gamma_MVA_ID"] = ak.where(
            cms_events["lead_pho_mvaID"] > cms_events["sublead_pho_mvaID"],
            cms_events["lead_pho_mvaID"], cms_events["sublead_pho_mvaID"]
        )
        
        # Number of jets ration (BTV)
        cms_events["Njets2p5"] = cms_events["Njets2p5"]
        # Jets for the HT(BTV)
        jets_pts = ak.concatenate([
            cms_events["jet1_pt"].to_numpy().reshape(-1,1),
            cms_events["jet2_pt"].to_numpy().reshape(-1,1),
            cms_events["jet3_pt"].to_numpy().reshape(-1,1),
            cms_events["jet4_pt"].to_numpy().reshape(-1,1),
            cms_events["jet5_pt"].to_numpy().reshape(-1,1),
            cms_events["jet6_pt"].to_numpy().reshape(-1,1),
            cms_events["jet7_pt"].to_numpy().reshape(-1,1),
            cms_events["jet8_pt"].to_numpy().reshape(-1,1),
            cms_events["jet9_pt"].to_numpy().reshape(-1,1),
            cms_events["jet10_pt"].to_numpy().reshape(-1,1),
        ], axis=1)
        cms_events["HT"] = ak.Array(np.sum(jets_pts, axis=1))
        

        from regions import (
            get_mask_preselection, get_mask_selection,
            get_mask_srbbgg, get_mask_srbbgg_EBEB, 
            get_mask_srbbgg_mixed, get_mask_srbbgg_EEEE,
            get_mask_srbbggMET,
            get_mask_crantibbgg, get_mask_crbbantigg, get_mask_crantibbantigg,
            get_mask_sideband, get_mask_idmva_presel, get_mask_idmva_sideband,
        )
        from variables import vardict, regions, variables_common
        from binning import binning

        cms_events["preselection"]   = get_mask_preselection(cms_events)
        cms_events["selection"]      = get_mask_selection(cms_events)
        cms_events["srbbgg"]         = get_mask_srbbgg(cms_events)
        cms_events["srbbgg_EBEB"]    = get_mask_srbbgg_EBEB(cms_events)
        cms_events["srbbgg_mixed"]   = get_mask_srbbgg_mixed(cms_events)
        cms_events["srbbgg_EEEE"]    = get_mask_srbbgg_EEEE(cms_events)
        cms_events["srbbggMET"]      = get_mask_srbbggMET(cms_events)
        cms_events["crbbantigg"]     = get_mask_crbbantigg(cms_events)
        cms_events["crantibbgg"]     = get_mask_crantibbgg(cms_events)
        cms_events["crantibbantigg"] = get_mask_crantibbantigg(cms_events)
        cms_events["sideband"]       = get_mask_sideband(cms_events)
        cms_events["idmva_presel"]   = get_mask_idmva_presel(cms_events)
        cms_events["idmva_sideband"] = get_mask_idmva_sideband(cms_events)

        keys_to_copy = [
            "lead_pho_pt","lead_pho_eta","lead_pho_phi",
            "sublead_pho_pt","sublead_pho_eta","sublead_pho_phi",
            "lead_bjet_pt","lead_bjet_eta","lead_bjet_phi",
            "sublead_bjet_pt","sublead_bjet_eta","sublead_bjet_phi",
            "dibjet_mass","diphoton_mass","bbgg_mass","dibjet_pt","diphoton_pt","bbgg_pt","bbgg_eta","bbgg_phi",
            "DeltaPhi_j1MET","DeltaPhi_j2MET","Res_chi_t0","Res_chi_t1",
            "lepton1_mvaID","lepton1_pt","lepton1_pfIsoId","n_jets",
            "dibjet_eta","dibjet_phi","diphoton_eta","diphoton_phi",
            "lead_bjet_PNetB","sublead_bjet_PNetB", "lead_bjet_PNetRegPtRawRes","sublead_bjet_PNetRegPtRawRes", 
            "lead_bjet_PNetUParTAK4B","sublead_bjet_PNetUParTAK4B", 
            "pholead_PtOverM","phosublead_PtOverM","FirstJet_PtOverM","SecondJet_PtOverM",
            "CosThetaStar_CS","CosThetaStar_jj","CosThetaStar_gg","DeltaR_jg_min",
            "lead_pt_over_diphoton_mass","sublead_pt_over_diphoton_mass",
            "lead_pt_over_dibjet_mass","sublead_pt_over_dibjet_mass",
            "diphoton_bbgg_mass","dibjet_bbgg_mass",
            "lead_pho_mvaID_WP90","lead_pho_mvaID_WP80","sublead_pho_mvaID_WP90","sublead_pho_mvaID_WP80",
            "lead_pho_mvaID","sublead_pho_mvaID","max_gamma_MVA_ID",
            "preselection","selection","srbbgg","srbbgg_EBEB","srbbgg_mixed","srbbgg_EEEE","srbbggMET","crbbantigg","crantibbgg","crantibbantigg","sideband",
            "idmva_sideband","idmva_presel",
            "DeltaR_j1g1","DeltaR_j2g1","DeltaR_j1g2","DeltaR_j2g2",
            "signal","isdata", "isdd","era_code","HT","Njets2p5",
            "pDNN_score",
            "n_leptons",
            "ttH_killer_score",
        ]
        out_events = ak.zip({k: cms_events[k] for k in keys_to_copy} | {"run": tree_["run"], "lumi": tree_["lumi"], "event": tree_["event"]}, depth_limit=1)

        # ---------------- Build event weights (nominal / baseline) ----------------
        if isdata:
            # Unit weight for real data
            base_w = np.ones(len(tree_), dtype="f8")

        elif isdd:
            # DD template: read per-event weight directly
            try:
                dd_wname = _get_dd_weight_col(tree_.fields)
                dd_w = ak.to_numpy(tree_[dd_wname])
            except Exception:
                dd_wname = _get_dd_weight_col(df.columns)
                dd_w = df[dd_wname].to_numpy()
            base_w = np.where(np.isfinite(dd_w), dd_w, 0.0)

        else:
            # MC: sigma x L normalization
            base_w = ak.to_numpy(cms_events["weight"]) * float(xsec_) * float(lumi_)
            base_w = np.where(np.isfinite(base_w), base_w, 0.0)

        # ---------------- Determine systematic passes ----------------
        # Each pass is (systematic_label, weight_array), sharing the SAME
        # event selection/kinematics -- weight variations don't change which
        # events pass which region, only which weight fills the histogram.
        #
        # A folder-based (object-level) systematic file gets exactly ONE
        # pass, at that folder's own label, using the nominal weight --
        # object-level and weight-level systematics are evaluated
        # independently (each source varied with all others held at
        # nominal), not combined into the same pass.
        #
        # A nominal-folder file gets a "nominal" pass PLUS one pass per
        # available weight-systematic Up/Down (MC only -- not data, not DD
        # templates, which have no scale-factor systematics defined here).
        systematic_passes = [(folder_systematic, base_w)]
        if folder_systematic == "nominal" and not isdata and not isdd:
            for syst_name, (up_col, down_col) in available_weight_systs.items():
                if up_col is not None:
                    w_up = weight_systematic_value(ak.to_numpy(cms_events[up_col]), xsec_, lumi_)
                    systematic_passes.append((f"{syst_name}Up", w_up))
                if down_col is not None:
                    w_down = weight_systematic_value(ak.to_numpy(cms_events[down_col]), xsec_, lumi_)
                    systematic_passes.append((f"{syst_name}Down", w_down))

        for systematic_label, syst_w in systematic_passes:
            out_events_syst = out_events
            for r in ["preselection","selection","srbbgg","srbbgg_EBEB", "srbbgg_EEEE", "srbbgg_mixed", "srbbggMET",
                    "crbbantigg","crantibbgg","crantibbantigg",
                    "sideband","idmva_sideband","idmva_presel"]:
                out_events_syst = ak.with_field(out_events_syst, syst_w, "weight_"+r)

            for ireg in regions:
                thisregion = out_events_syst[out_events_syst[ireg] == True]
                thisregion_ = thisregion[~(ak.is_none(thisregion))]
                weight_ = "weight_" + ireg

                if not skip_histograms:
                    for ivar in variables_common[ireg]:
                        hist_name_ = f"{vardict[ivar]}"
                        vals = ak.to_numpy(thisregion_[ivar])
                        wts  = ak.to_numpy(thisregion_[weight_])
                        if wts is not None:
                            wts = np.where(np.isfinite(wts), wts, 0.0)
                        h = make_th1_pyroot(vals, wts, hist_name_, hist_name_, binning[ireg][ivar])

                        key = (sample_name_norm, systematic_label, ireg, hist_name_)
                        if key not in HIST_CACHE:
                            acc = h.Clone(f"{hist_name_}__acc")
                            acc.Reset()
                            acc.SetDirectory(0)
                            HIST_CACHE[key] = acc
                        HIST_CACHE[key].Add(h)
                        del h

                # Full event trees are written only for the baseline pass of
                # this file (nominal, or this file's own folder-systematic
                # label) -- NOT duplicated per weight-systematic variant.
                # Weight-systematic variants share identical kinematics with
                # nominal; only the weight differs, and the per-variant
                # weight column itself is already available directly from
                # the raw ntuple, so a full duplicate event tree per variant
                # isn't needed just to preserve that information. Revisit if
                # downstream (datacard/fit) tooling turns out to need
                # per-weight-systematic trees rather than just histograms.
                if not skip_trees and systematic_label == folder_systematic:
                    tree_data_ = ak_to_numpy_dict(thisregion_)
                    merged = sanitize_for_uproot(tree_data_)
                    write_tree_chunked(
                        tree_upfile,
                        f"{sample_name_norm}/{systematic_label}/{ireg}",
                        merged,
                        step=50_000,
                        tree_cache=TREE_CACHE,
                    )

def ensure_dir(upfile, path):
    """Create nested directories explicitly for Uproot writing."""
    curr = upfile
    if not path:
        return curr
    parts = [p for p in path.split("/") if p]
    for p in parts:
        # mkdir returns the subdirectory; if it exists, __getitem__ returns it
        curr = curr.mkdir(p) if p not in curr.keys() else curr[p]
    return curr

def write_tree_chunked(upfile, full_path, merged, step=200_000, tree_cache=None):
    """
    Create directories explicitly, create a tree with a *simple name* (no slashes),
    and stream data in chunks. `merged` must be sanitized.

    `tree_cache` (a dict keyed by `full_path`) is REQUIRED for correctness
    across repeated calls to the same path -- e.g. once per parquet batch,
    across every file for the same sample/region. Without it, wdir.mktree()
    below creates a brand-new ROOT/uproot cycle on every call instead of
    extending one tree, and every cycle except the last is silently
    unreachable on a normal (no-cycle-specified) read. Pass the same dict
    across the whole run (see TREE_CACHE).
    """
    if not merged:
        return

    # Split "sample/region" into directory + short tree name
    parts = [p for p in full_path.split("/") if p]
    treename = parts[-1]
    dirpath  = "/".join(parts[:-1])

    # Enforce 1D, consistent lengths, and map to explicit string types
    first_key = next(iter(merged))
    n = len(merged[first_key])
    for k, v in merged.items():
        a = np.asarray(v)
        if a.ndim != 1:
            raise ValueError(f"Branch '{k}' is not 1D (shape={a.shape}).")
        if len(a) != n:
            raise ValueError(f"Branch length mismatch: '{k}' has {len(a)} vs {n}.")

    if tree_cache is not None and full_path in tree_cache:
        tree = tree_cache[full_path]
    else:
        # Use explicit ROOT-friendly type strings (avoid dtype inference pitfalls)
        def _branch_type(a):
            a = np.asarray(a)
            if a.dtype == np.bool_:
                return "int8"
            if a.dtype.kind in ("i", "u"):
                return "int64"
            if a.dtype.kind == "f":
                return "float64"
            raise TypeError(f"Unsupported dtype for branch: {a.dtype}")

        types = {k: _branch_type(v) for k, v in merged.items()}

        # Ensure the directory exists, then create the tree ONCE.
        wdir = ensure_dir(upfile, dirpath)
        tree = wdir.mktree(treename, types)
        if tree_cache is not None:
            tree_cache[full_path] = tree

    # Stream the data
    step = min(step, n if n else step)
    for start in range(0, n, step):
        stop  = min(start + step, n)
        piece = {k: v[start:stop] for k, v in merged.items()}
        tree.extend(piece)



# ---------------- Entry point ----------------
def main():
    ap = argparse.ArgumentParser(
        description="hhbbgg analyzer (parquet) with true multi-year + multi-era support"
    )

    ap.add_argument(
        "-i", "--inFile", action="append", required=True,
        help="Parquet file or directory. Can be given multiple times. "
             "Directories are searched recursively (handles both the flat "
             "background/data layout and the nested "
             "<mass_point>/<systematic>/*.parquet signal layout)."
    )

    ap.add_argument(
        "--config-years", type=str, required=True,
        help="Comma-separated list of years, e.g. 2022,2023,2024"
    )

    ap.add_argument(
        "--era", default="All",
        help="Fallback era if not detectable from filename (PreEE, PostEE, preBPix, postBPix, All)"
    )

    ap.add_argument(
        "--tag", default=None,
        help="Output tag name"
    )

    ap.add_argument(
        "--all-systematics", action="store_true",
        help="Also process files under systematic-variation subfolders (e.g. "
             "jec_syst_Total_up, Smearing_down). Default: process only "
             "'nominal' (plus any flat file with no systematic-folder "
             "structure at all). Systematic-variation files that were never "
             "scored by inference_PDnn.py will not have a pDNN_score column "
             "and would otherwise crash this script."
    )
    ap.add_argument(
        "--skip-trees", action="store_true",
        help="Skip writing per-event tree output entirely -- only fill and write "
             "histograms. Useful for a second pass over the same input once trees "
             "are already complete, to (re)generate histograms without redoing the "
             "much larger tree-writing I/O. Mutually meaningful with "
             "--skip-histograms (running with both set does nothing)."
    )
    ap.add_argument(
        "--skip-histograms", action="store_true",
        help="Skip filling and writing histogram output entirely -- only write "
             "trees. Useful when running trees-only now and histograms in a "
             "separate, later pass (see --skip-trees) to avoid the histogram "
             "output's fixed-filename RECREATE mode overwriting a shared file "
             "unnecessarily during a trees-only run."
    )

    args = ap.parse_args()

    if args.skip_trees and args.skip_histograms:
        raise SystemExit("--skip-trees and --skip-histograms cannot both be set -- "
                          "that would process every input file and write no output at all.")

    # -----------------------------------------
    # Parse years
    # -----------------------------------------
    config_years = [y.strip() for y in args.config_years.split(",")]
    print(f"[INFO] Configured years: {config_years}")

    # -----------------------------------------
    # Collect parquet files (recursively, filtered to nominal by default)
    # -----------------------------------------
    inputfiles = []
    for ip in args.inFile:
        p = Path(ip).resolve()
        if p.is_file() and p.suffix == ".parquet":
            inputfiles.append(str(p))
        elif p.is_dir():
            found = collect_parquet_files(p, all_systematics=args.all_systematics)
            inputfiles.extend(str(x) for x in found)

    if not inputfiles:
        raise RuntimeError("No parquet files found")

    print(f"[INFO] Found {len(inputfiles)} parquet files")

    # -----------------------------------------
    # Xsec / lumi cache per file
    # -----------------------------------------
    xsec_lumi_cache = {}

    # -----------------------------------------
    # Output paths (created ONCE)
    # -----------------------------------------
    out_tag = args.tag or "_".join(config_years)
    out_dir = Path("outputfiles") / "merged" / out_tag
    out_dir.mkdir(parents=True, exist_ok=True)

    hist_file_path = out_dir / f"hhbbgg_analyzer-v2-histograms__{time.strftime('%Y%m%d_%H%M%S')}.root"

    # -----------------------------------------
    # Group input files by (resolved sample identity, systematic), and
    # process one (sample, systematic) tree output file at a time.
    #
    # FIXED (round 1): a single tree_upfile was opened ONCE for the
    # entire run and every parquet file streamed into it -- confirmed as
    # the cause of a live crash mid-run:
    #   struct.error: 'i' format requires -2147483648 <= number <= 2147483647
    # (2^31-1, the 32-bit signed-int ceiling uproot's classic-ROOT write
    # cascade uses for file offsets, overflowing once a single output
    # file crosses ~2GB). Round-1 fix: one tree file per SAMPLE instead.
    #
    # FIXED (round 2, this pass): per-sample splitting alone was NOT
    # sufficient granularity, confirmed by a second live crash --
    # GGJets_MGG-80(_Rescaled).root (3.2GB each) and GluGluHtoGG.root
    # (2.8GB) all completed successfully DESPITE being well over 2GB,
    # which reveals the real mechanism: the crash isn't a hard file-size
    # ceiling, it specifically happens when a NEW directory needs
    # creating (mkdir(), for a not-yet-seen sample/systematic/region
    # combination) AFTER the file has already grown past the internal
    # offset limit -- further writes to an ALREADY-existing directory
    # are just tree.extend() calls, which don't hit this code path even
    # well past 2GB. A large background MC sample with many systematic
    # variations can exceed the threshold within its OWN file, once a
    # later systematic's fresh directories are needed.
    #
    # Since each input parquet file already corresponds to exactly ONE
    # systematic (folder structure: <mass_point>/<systematic>/*.parquet),
    # and full event trees are only ever written for a file's own
    # baseline pass (never duplicated per weight-systematic variant --
    # see the "systematic_label == folder_systematic" check in
    # process_parquet_file), grouping by (sample, systematic) instead of
    # sample alone maps naturally onto the existing per-file systematic
    # boundaries and gives much finer, safer granularity.
    #
    # TREE_CACHE is cleared between groups, since its entries are live
    # handles into whichever file is currently open -- carrying stale
    # entries across a close/reopen would make write_tree_chunked() try
    # to extend a tree object belonging to an already-closed file.
    # -----------------------------------------
    from collections import OrderedDict
    files_by_group = OrderedDict()
    for infile in inputfiles:
        s = resolve_sample_name(infile)
        syst = classify_systematic(Path(infile)) or "flat"
        files_by_group.setdefault((s, syst), []).append(infile)

    print(f"[INFO] Grouped into {len(files_by_group)} (sample, systematic) group(s) "
          f"for per-group tree output files")

    def _safe_filename_part(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", s)

    if not args.skip_trees:
        for (sample_name, syst_name), group_files in files_by_group.items():
            safe_sample = _safe_filename_part(sample_name)
            safe_syst = _safe_filename_part(syst_name)
            tree_file_path = out_dir / f"hhbbgg_analyzer-v2-trees__{safe_sample}__{safe_syst}.root"

            # Resumability: skip a (sample, systematic) group whose output
            # already exists AND is genuinely readable -- lets a re-run of
            # the exact same command pick up only what's missing after a
            # crash, without reprocessing hours of already-good output.
            # Existence alone is NOT enough to trust: the group that was
            # mid-write when a crash happened will have a partial, likely
            # UNREADABLE file on disk (uproot.recreate() never got to
            # finalize it) -- skipping that on existence alone would
            # silently leave a corrupted/incomplete file in place forever.
            # Confirmed necessary directly: this is exactly the situation
            # after the most recent crash, not a hypothetical.
            if tree_file_path.exists():
                try:
                    with uproot.open(tree_file_path) as _check:
                        _ = _check.keys()
                    print(f"[SKIP] '{sample_name}' / '{syst_name}': output already exists and "
                          f"is readable, skipping ({tree_file_path})")
                    continue
                except Exception as e:
                    print(f"[WARN] '{sample_name}' / '{syst_name}': existing output file is "
                          f"present but NOT readable ({type(e).__name__}: {e}) -- likely a "
                          f"partial file from an interrupted run. Reprocessing from scratch.")

            print(f"[INFO] Opening tree output file for sample '{sample_name}', systematic "
                  f"'{syst_name}' ({len(group_files)} file(s)): {tree_file_path}")
            tree_upfile = uproot.recreate(tree_file_path)
            TREE_CACHE.clear()

            for infile in group_files:
                det_year, det_era = detect_year_era_from_name(infile)

                year = det_year if det_year in config_years else None
                if year is None:
                    raise RuntimeError(
                        f"File {infile} has year={det_year}, not in --config-years {config_years}"
                    )

                era = det_era or args.era

                print(f"[INFO] Processing {os.path.basename(infile)} → {year} {era}")

                process_parquet_file(
                    infile,
                    cli_year=year,
                    cli_era=era,
                    xsec_lumi_cache=xsec_lumi_cache,
                    tree_upfile=tree_upfile,
                    skip_trees=False,
                    skip_histograms=args.skip_histograms,
                )

            tree_upfile.close()
            print(f"[OK] Closed tree output file for sample '{sample_name}', systematic "
                  f"'{syst_name}': {tree_file_path}")
    else:
        # --skip-trees: no per-(sample, systematic) tree file machinery
        # needed at all -- just iterate every input file directly, filling
        # HIST_CACHE only. This is the "second pass, histograms only" mode
        # for a run where trees are already complete.
        print(f"[INFO] --skip-trees set: processing {len(inputfiles)} file(s) for "
              f"histograms only, no tree output will be written.")
        for infile in inputfiles:
            det_year, det_era = detect_year_era_from_name(infile)

            year = det_year if det_year in config_years else None
            if year is None:
                raise RuntimeError(
                    f"File {infile} has year={det_year}, not in --config-years {config_years}"
                )

            era = det_era or args.era

            print(f"[INFO] Processing {os.path.basename(infile)} → {year} {era}")

            process_parquet_file(
                infile,
                cli_year=year,
                cli_era=era,
                xsec_lumi_cache=xsec_lumi_cache,
                tree_upfile=None,
                skip_trees=True,
                skip_histograms=False,
            )

    # -----------------------------------------
    # Write histograms (cached in memory)
    # -----------------------------------------
    if args.skip_histograms:
        print("[INFO] --skip-histograms set: no histogram output written this run.")
    else:
        print("[INFO] Writing histograms...")
        hist_tfile = ROOT.TFile(str(hist_file_path), "RECREATE")
        for (sample, systematic, region, var), h in HIST_CACHE.items():
            ensure_dir_in_tfile(hist_tfile, f"{sample}/{systematic}/{region}").cd()
            h_clone = h.Clone(var)
            h_clone.Write()
        hist_tfile.Close()

    print("======================================")
    print(f"[OK] Histograms → {hist_file_path}")
    print(f"[OK] Trees       → {out_dir} (one file per sample+systematic: "
          f"hhbbgg_analyzer-v7-trees__<sample>__<systematic>.root)")
    print(f"[NOTE] Histogram output now uses a unique per-run filename (was previously a "
          f"single fixed name that a targeted re-run would silently overwrite, destroying "
          f"any prior run's accumulated histograms). Merge all "
          f"hhbbgg_analyzer-v7-histograms__*.root files with hadd once every sample has "
          f"been processed, the same way as the per-sample tree files.")
    print("======================================")
    
    
if __name__ == "__main__":
    main()




end = time.time()
print(f"Execution time: {end - start:.4f} seconds")