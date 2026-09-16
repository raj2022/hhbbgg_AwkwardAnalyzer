#!/usr/bin/env python3
# =============================================================================
# find_res_columns.py
#
# Searches parquet schemas for columns starting with a BARE "Res_" prefix
# (explicitly excluding nonRes_ and nonResReg_, which contain "Res" as a
# substring but are a different branch family). Prints only the matches --
# short, targeted output instead of dumping the full ~600-column schema.
#
# Usage:
#   python3 find_res_columns.py --mx 300 --my 50 60 70 80 90 95 100 150
# =============================================================================

import os
import csv
import argparse
import pyarrow.parquet as pq

SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
    "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)


def bare_res_columns(names):
    """Columns starting with 'Res_' but NOT 'nonRes_' or 'nonResReg_'."""
    return sorted(c for c in names if c.startswith("Res_"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mx", type=int, required=True)
    ap.add_argument("--my", type=int, nargs="+", required=True)
    ap.add_argument("--csv-out", type=str, default=None,
                     help="Path to write results as CSV. Defaults to "
                          "res_columns_check_X<mx>.csv in the current directory.")
    args = ap.parse_args()

    csv_path = args.csv_out or f"res_columns_check_X{args.mx}.csv"

    print(f"[INFO] Checking for bare 'Res_' columns at mX={args.mx}, across mY={sorted(args.my)}\n")

    rows = []
    for my in sorted(args.my):
        path = SIG_TPL.format(m=args.mx, y=my)
        if not os.path.exists(path):
            print(f"Y{my}: [NO FILE] {path}")
            rows.append({"mX": args.mx, "mY": my, "status": "NO FILE",
                         "n_res_columns": "", "res_columns": "", "file_path": path})
            continue
        try:
            names = pq.read_schema(path).names
        except Exception as e:
            print(f"Y{my}: [SCHEMA READ FAIL] {e}")
            rows.append({"mX": args.mx, "mY": my, "status": f"SCHEMA READ FAIL: {e}",
                         "n_res_columns": "", "res_columns": "", "file_path": path})
            continue

        res_cols = bare_res_columns(names)
        if res_cols:
            print(f"Y{my}: {len(res_cols)} 'Res_' column(s) found:")
            for c in res_cols:
                print(f"    {c}")
            status = "HAS_RES_COLUMNS"
        else:
            print(f"Y{my}: NO bare 'Res_' columns found (only nonRes_/nonResReg_ present, if any)")
            status = "NO_RES_COLUMNS"
        print()

        rows.append({
            "mX": args.mx,
            "mY": my,
            "status": status,
            "n_res_columns": len(res_cols),
            "res_columns": ";".join(res_cols),
            "file_path": path,
        })

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mX", "mY", "status", "n_res_columns", "res_columns", "file_path"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[SAVED] {csv_path}")
    print("\n=== Summary ===")
    for r in rows:
        print(f"  mY={r['mY']:>4}  {r['status']:<20}  n_res_columns={r['n_res_columns']}")


if __name__ == "__main__":
    main()