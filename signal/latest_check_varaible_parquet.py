# import pyarrow.parquet as pq
# import os

# # Full path to parquet file
# parquet_file = "/eos/user/b/bartek/hhbbgg/systematics_v3/2022_postEE/merged/NMSSM_X900_Y95/nominal/NOTAG_merged.parquet"

# # Output file in the SAME directory as parquet
# output_txt = os.path.join(os.path.dirname(parquet_file), "parquet_variables.txt")

# # Read only schema (no full loading)
# schema = pq.read_schema(parquet_file)

# # Write column names
# with open(output_txt, "w") as f:
#     for name in schema.names:
#         f.write(name + "\n")

# print(f"Saved {len(schema.names)} variables to {output_txt}")
# # ----------------------------
#!/usr/bin/env python
"""
inspect_variables.py

Audits every column available in your signal and background parquet
samples against what pDNN_v2.py actually uses, so you can see at a glance
whether anything potentially useful is being left on the table.

Reads only parquet *schemas* (via pyarrow), not the actual data, so it's
fast even on large files -- no full dataframe load required.

Splits columns into three tiers:
  1. TRAINED     -- in FEATURES_CORE, actually fed into the network
  2. READ-ONLY   -- in RAW_COLUMNS_OF_INTEREST but not FEATURES_CORE
                    (read from disk, used only to build engineered
                    features like ptjj_over_mHH / DeltaR_gg, never
                    trained on directly)
  3. UNUSED      -- present in your parquet files but not referenced
                    anywhere in pDNN_v2.py

Also flags the reverse case: anything pDNN_v2.py expects (FEATURES_CORE /
RAW_COLUMNS_OF_INTEREST) that isn't actually present in any sample --
those silently no-op today (handled gracefully, but worth knowing about).

Run this from anywhere -- it locates pDNN_v2.py automatically (its own
directory, the known training-script location, or your current working
directory, in that order):

    python inspect_variables.py

Output:
  - A console report grouped by physics-object category
  - variable_audit.csv -- full column-by-column table for spreadsheet review
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import pyarrow.parquet as pq

# Import the config + feature lists directly from the training script, so
# this audit always reflects whatever pDNN_v2.py currently uses -- no
# duplicated/hardcoded lists to drift out of sync.
#
# pDNN_v2.py doesn't have to live next to this script or in the current
# working directory -- both this script's own folder and the known
# training-script location are searched, in that order.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PDNN_DIR = "/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/ML_Application/parametrized_DNN/working/pDNN_Without_Correlation"

for _candidate in (_THIS_DIR, _PDNN_DIR, os.getcwd()):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

try:
    from pDNN_v2 import CFG, FEATURES_CORE, RAW_COLUMNS_OF_INTEREST  # noqa: E402
except ModuleNotFoundError as e:
    print(f"[ERROR] Could not import pDNN_v2.py: {e}")
    print(f"        Searched: {_THIS_DIR}, {_PDNN_DIR}, {os.getcwd()}")
    print("        Either run this script from the same directory as pDNN_v2.py,")
    print("        or edit _PDNN_DIR at the top of this file to point at it.")
    sys.exit(1)


def schema_columns(path: str) -> Set[str]:
    """Read a parquet file's column names without loading any data."""
    try:
        return set(pq.ParquetFile(path).schema.names)
    except Exception as e:
        print(f"[WARN] Could not read schema for {path}: {e}")
        return set()


def collect_all_columns(cfg) -> Tuple[Set[str], Set[str], Dict[str, Set[str]]]:
    """Scan every configured signal and background file's schema.

    Returns (signal_columns_union, background_columns_union, per_file_columns).
    """
    signal_cols: Set[str] = set()
    background_cols: Set[str] = set()
    per_file: Dict[str, Set[str]] = {}
    n_signal_found = n_signal_missing = 0

    for mass in cfg.MASS_POINTS:
        for y in cfg.Y_VALUES:
            fp = cfg.SIG_TPL.format(m=mass, y=y)
            if not os.path.exists(fp):
                n_signal_missing += 1
                continue
            cols = schema_columns(fp)
            if cols:
                signal_cols |= cols
                per_file[fp] = cols
                n_signal_found += 1

    n_bkg_found = n_bkg_missing = 0
    for fp in cfg.BACKGROUND_FILES:
        if not os.path.exists(fp):
            print(f"[WARN] Missing background file: {fp}")
            n_bkg_missing += 1
            continue
        cols = schema_columns(fp)
        if cols:
            background_cols |= cols
            per_file[fp] = cols
            n_bkg_found += 1

    print(f"Signal files found:     {n_signal_found}  (missing/skipped: {n_signal_missing})")
    print(f"Background files found: {n_bkg_found}  (missing/skipped: {n_bkg_missing})\n")
    return signal_cols, background_cols, per_file


def categorize(col: str) -> str:
    """Rough physics-object bucket, purely to make a long column list scannable."""
    prefixes = [
        ("lead_", "photon (lead)"), ("sublead_", "photon (sublead)"),
        ("fatjet", "fat jet"), ("jet", "jet"),
        ("lepton", "lepton"),
        ("Res_DNNpair", "resolved (DNN-paired)"),
        ("Res_", "resolved"),
        ("nonResReg_", "non-resonant (regressed)"), ("nonRes_", "non-resonant"),
        ("VBF_", "VBF"),
        ("puppiMET", "MET"),
        ("weight", "weight / systematics"),
    ]
    for prefix, label in prefixes:
        if col.startswith(prefix):
            return label
    return "other / event-level"


def main() -> None:
    cfg = CFG
    trained = set(FEATURES_CORE)
    read_only = set(RAW_COLUMNS_OF_INTEREST) - trained
    always_present = {cfg.WEIGHT_COL, "mass", "y_value", "label"}
    used = trained | read_only | always_present

    print("Scanning signal and background parquet schemas ...\n")
    signal_cols, background_cols, per_file = collect_all_columns(cfg)
    all_cols = signal_cols | background_cols

    if not all_cols:
        print("No columns found -- check that the paths in Config are reachable "
              "from this machine (run on lxplus / wherever /eos is mounted).")
        return

    print(f"Total unique columns across all samples: {len(all_cols)}")
    print(f"  Signal only:     {len(signal_cols - background_cols)}")
    print(f"  Background only: {len(background_cols - signal_cols)}")
    print(f"  In both:         {len(signal_cols & background_cols)}\n")

    trained_present = sorted(trained & all_cols)
    trained_missing = sorted(trained - all_cols)
    read_only_present = sorted(read_only & all_cols)
    unused = sorted(all_cols - used)

    print(f"=== TIER 1: TRAINED features actually fed to the network ({len(trained_present)}/{len(trained)}) ===")
    if trained_missing:
        print(f"  [!] {len(trained_missing)} expected training feature(s) NOT found in any sample "
              f"(silently absent from the model today): {trained_missing}")
    print()

    print(f"=== TIER 2: READ-ONLY columns (used to build engineered features, not trained on) "
          f"({len(read_only_present)}) ===")
    for c in read_only_present:
        in_sig = "S" if c in signal_cols else " "
        in_bkg = "B" if c in background_cols else " "
        print(f"    [{in_sig}{in_bkg}] {c}")
    print()

    print(f"=== TIER 3: UNUSED -- present in your data, never referenced in pDNN_v2.py ({len(unused)}) ===\n")
    buckets: Dict[str, List[str]] = defaultdict(list)
    for c in unused:
        buckets[categorize(c)].append(c)
    for label in sorted(buckets):
        cols = sorted(buckets[label])
        print(f"-- {label} ({len(cols)}) --")
        for c in cols:
            in_sig = "S" if c in signal_cols else " "
            in_bkg = "B" if c in background_cols else " "
            print(f"    [{in_sig}{in_bkg}] {c}")
        print()

    print("(S = present in at least one signal sample, B = present in at least one background sample)\n")

    # Full CSV for spreadsheet review / discussion with collaborators.
    out_path = "variable_audit.csv"
    with open(out_path, "w") as f:
        f.write("column,in_signal,in_background,tier,category\n")
        for c in sorted(all_cols):
            if c in trained:
                tier = "trained"
            elif c in read_only:
                tier = "read_only_engineered"
            elif c in always_present:
                tier = "meta"
            else:
                tier = "unused"
            f.write(f"{c},{c in signal_cols},{c in background_cols},{tier},{categorize(c)}\n")
    print(f"Full audit written to {out_path} -- open in a spreadsheet to review Tier 3 with collaborators.")
    print("\nNote: this script only tells you what EXISTS and is UNUSED. It does not judge whether")
    print("an unused variable is actually useful, discriminating, or safe from mgg correlation --")
    print("that still requires the same correlation/leakage checks the training script already runs.")


if __name__ == "__main__":
    main()