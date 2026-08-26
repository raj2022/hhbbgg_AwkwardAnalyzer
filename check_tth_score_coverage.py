#!/usr/bin/env python3
"""
check_tth_score_coverage.py

Walks every "scored/" directory across 2022/2023/2024 sim+data and
checks whether each parquet file actually has a "ttH_killer_score"
column -- i.e. whether inference_ttH_killer.py has genuinely run on it,
rather than trusting that a file living under a scored/ folder means
it was scored.

Usage:
    python check_tth_score_coverage.py
"""

import pyarrow.parquet as pq
from pathlib import Path

SCORED_DIRS = [
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/preEE/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/sim/postEE/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2022/data/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/postBPix/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/sim/preBPix/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2023/data/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/sim/scored/",
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/output_parquet/Run3_2024/data/scored/",
]

TARGET_COLUMN = "ttH_killer_score"

MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds


def read_schema_with_retry(fp):
    """Read just the schema (cheap) with retries for transient EOS I/O errors."""
    import time
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return pq.ParquetFile(str(fp)).schema.names
        except OSError as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise last_exc


def main():
    grand_total = 0
    grand_missing = 0
    grand_unreadable = 0

    for scored_dir in SCORED_DIRS:
        root = Path(scored_dir)
        print(f"\n=== {scored_dir} ===")

        if not root.is_dir():
            print("  [MISSING DIRECTORY]")
            continue

        files = sorted(root.rglob("*.parquet"))
        if not files:
            print("  [NO PARQUET FILES FOUND]")
            continue

        n_total = len(files)
        missing = []
        unreadable = []

        for fp in files:
            try:
                cols = read_schema_with_retry(fp)
            except Exception as e:
                unreadable.append((fp, str(e)))
                continue
            if TARGET_COLUMN not in cols:
                missing.append(fp)

        n_missing = len(missing)
        n_unreadable = len(unreadable)
        n_ok = n_total - n_missing - n_unreadable

        print(f"  Total files:        {n_total}")
        print(f"  Has {TARGET_COLUMN}: {n_ok}")
        print(f"  MISSING column:     {n_missing}")
        print(f"  Unreadable:         {n_unreadable}")

        if missing:
            print(f"  --- Files missing '{TARGET_COLUMN}' ---")
            for fp in missing:
                print(f"    {fp}")

        if unreadable:
            print(f"  --- Files that could not be read ---")
            for fp, err in unreadable:
                print(f"    {fp}  ({err})")

        grand_total += n_total
        grand_missing += n_missing
        grand_unreadable += n_unreadable

    print("\n================ SUMMARY ================")
    print(f"Total files checked:  {grand_total}")
    print(f"Missing {TARGET_COLUMN}: {grand_missing}")
    print(f"Unreadable:           {grand_unreadable}")
    if grand_missing == 0 and grand_unreadable == 0:
        print(f"[OK] Every file has '{TARGET_COLUMN}'.")
    else:
        print(f"[ACTION NEEDED] Some files are missing '{TARGET_COLUMN}' or "
              f"could not be read -- see details above.")
    print("===========================================")


if __name__ == "__main__":
    main()