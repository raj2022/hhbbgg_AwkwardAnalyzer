#!/usr/bin/env python3
# =============================================================================
# check_res_branch_turnon.py
#
# Direct turn-on check: for a fixed mX, scan every available mY point and
# report whether the resonant-tagger branches (Res_*) exist in that file's
# schema, and if so, how many rows are non-null / pass basic quality cuts.
# A resonant reconstruction efficiency that drops to zero (or the Res_
# branch disappearing entirely) at low mY is direct, unambiguous evidence
# of the turn-on -- no shape plot required to see it.
#
# Usage:
#   python3 check_res_branch_turnon.py --mx 600
# =============================================================================

import os
import argparse
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

SIG_TPL = (
    "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"
    "NMSSM_X{m}_Y{y}/nominal/NOTAG_merged.parquet"
)

# Full Y grid observed on disk (from check_signal_grid.py output)
Y_GRID = [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800]

SENTINEL_THRESHOLD = -900.0


def check_point(mx, my):
    path = SIG_TPL.format(m=mx, y=my)
    if not os.path.exists(path):
        return {"mY": my, "status": "NO FILE"}

    try:
        schema_names = pq.read_schema(path).names
    except Exception as e:
        return {"mY": my, "status": f"SCHEMA READ FAIL: {e}"}

    has_res = any(c.startswith("Res_") for c in schema_names)
    has_nonres = any(c.startswith("nonRes_") for c in schema_names)

    result = {"mY": my, "status": "OK", "has_Res_branches": has_res, "has_nonRes_branches": has_nonres}

    # If Res_M_X (or nonRes_M_X as fallback) exists, read it and report
    # total rows vs. rows passing the sentinel cut (i.e. actually reconstructed).
    mass_col = None
    for candidate in ("Res_M_X", "nonRes_M_X", "nonResReg_M_X"):
        if candidate in schema_names:
            mass_col = candidate
            break

    if mass_col is not None:
        try:
            df = pd.read_parquet(path, columns=[mass_col, "weight"] if "weight" in schema_names else [mass_col])
            n_total = len(df)
            vals = df[mass_col].to_numpy(dtype=float)
            n_valid = int(np.sum(vals > SENTINEL_THRESHOLD))
            result["mass_col_used"] = mass_col
            result["n_total_rows"] = n_total
            result["n_valid_reco"] = n_valid
            result["frac_valid_reco"] = n_valid / n_total if n_total > 0 else float("nan")
        except Exception as e:
            result["read_error"] = str(e)
    else:
        result["mass_col_used"] = None

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mx", type=int, required=True, help="Fixed mX to scan across all available mY")
    args = ap.parse_args()

    print(f"[INFO] Scanning mX={args.mx} across mY grid: {Y_GRID}\n")
    rows = []
    for my in Y_GRID:
        r = check_point(args.mx, my)
        rows.append(r)
        print(f"  mY={my:4d}  {r}")

    print("\n=== Summary table ===")
    print(f"{'mY':>5} {'file':>8} {'Res_br':>7} {'nonRes_br':>10} {'mass_col':>14} {'n_total':>9} {'n_valid':>9} {'frac_valid':>11}")
    for r in rows:
        my = r["mY"]
        status = r.get("status", "?")
        if status != "OK":
            print(f"{my:>5} {status:>8}")
            continue
        has_res = r.get("has_Res_branches")
        has_nonres = r.get("has_nonRes_branches")
        mass_col = r.get("mass_col_used", "-")
        n_total = r.get("n_total_rows", "-")
        n_valid = r.get("n_valid_reco", "-")
        frac = r.get("frac_valid_reco", float("nan"))
        frac_str = f"{frac:.3f}" if isinstance(frac, float) and not np.isnan(frac) else "-"
        print(f"{my:>5} {'OK':>8} {str(has_res):>7} {str(has_nonres):>10} {str(mass_col):>14} {str(n_total):>9} {str(n_valid):>9} {frac_str:>11}")


if __name__ == "__main__":
    main()