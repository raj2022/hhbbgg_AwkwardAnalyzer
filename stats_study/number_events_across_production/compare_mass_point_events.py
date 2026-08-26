#!/usr/bin/env python3
"""
compare_mass_point_events.py

Compares event counts (and basic stats) for given branches (default:
dibjet_mass, diphoton_mass) between two parallel productions, for a given
mass point (e.g. X600 -> matches NMSSM_X600_Y*).

Looks for parquet files under:
    <base_dir>/NMSSM_X<mass>_Y*/nominal/*.parquet

for each of the two base directories, and reports per-Y-value and total
event counts plus basic stats for each requested column.

Usage:
    python compare_mass_point_events.py --mass 600
    python compare_mass_point_events.py --mass 600 --columns dibjet_mass diphoton_mass
    python compare_mass_point_events.py --mass 600 \
        --dir-a /eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2024/merged/scored/ \
        --dir-b /eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/
"""

import argparse
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq


DEFAULT_DIR_A = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2024/merged/scored/"
DEFAULT_DIR_B = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/2024/merged/scored/"
DEFAULT_COLUMNS = ["dibjet_mass", "diphoton_mass", "bbgg_mass"]

MAX_RETRIES = 4
RETRY_DELAY = 5


# ---------------------------------------------------------------------------
# These "derived" columns are NOT stored directly in the raw scored parquet
# files (confirmed via schema inspection: the files only carry raw HiggsDNA
# branches like Res_lead_bjet_pt/eta/phi/mass, lead_pt/eta/phi, etc.) --
# they're computed downstream in hhbbgg_analyzer_with_systematics.py via
# lVector(...).mass. Rather than expecting the column to already exist,
# this script recognizes these three specific names and computes them
# on the fly from the same raw branches, using the same physics (photons
# treated as massless, matching lVector's diphoton call signature which
# omits a mass argument for photons).
#
# Any OTHER column name passed via --columns is read directly as-is, with
# no special handling -- only these three get the derived-quantity
# treatment.
# ---------------------------------------------------------------------------
DERIVED_COLUMN_INPUTS = {
    "dibjet_mass": [
        "Res_lead_bjet_pt", "Res_lead_bjet_eta", "Res_lead_bjet_phi", "Res_lead_bjet_mass",
        "Res_sublead_bjet_pt", "Res_sublead_bjet_eta", "Res_sublead_bjet_phi", "Res_sublead_bjet_mass",
    ],
    "diphoton_mass": [
        "lead_pt", "lead_eta", "lead_phi",
        "sublead_pt", "sublead_eta", "sublead_phi",
    ],
    "bbgg_mass": [
        "Res_HHbbggCandidate_mass",
    ],
}


def _invariant_mass_two_body(pt1, eta1, phi1, m1, pt2, eta2, phi2, m2):
    """Standard two-body invariant mass from (pt, eta, phi, mass) for each
    particle -- same physics as the lVector(...).mass calls in
    hhbbgg_analyzer_with_systematics.py."""
    px1 = pt1 * np.cos(phi1); py1 = pt1 * np.sin(phi1); pz1 = pt1 * np.sinh(eta1)
    px2 = pt2 * np.cos(phi2); py2 = pt2 * np.sin(phi2); pz2 = pt2 * np.sinh(eta2)
    e1 = np.sqrt(np.maximum(m1**2 + px1**2 + py1**2 + pz1**2, 0.0))
    e2 = np.sqrt(np.maximum(m2**2 + px2**2 + py2**2 + pz2**2, 0.0))
    e = e1 + e2
    px = px1 + px2
    py = py1 + py2
    pz = pz1 + pz2
    m2_out = e**2 - px**2 - py**2 - pz**2
    return np.sqrt(np.maximum(m2_out, 0.0))


def compute_derived_column(name, table):
    """Compute one of the DERIVED_COLUMN_INPUTS columns from raw branches
    already read into `table` (a pyarrow Table). Returns a numpy array."""
    if name == "dibjet_mass":
        pt1 = np.asarray(table.column("Res_lead_bjet_pt"))
        eta1 = np.asarray(table.column("Res_lead_bjet_eta"))
        phi1 = np.asarray(table.column("Res_lead_bjet_phi"))
        m1 = np.asarray(table.column("Res_lead_bjet_mass"))
        pt2 = np.asarray(table.column("Res_sublead_bjet_pt"))
        eta2 = np.asarray(table.column("Res_sublead_bjet_eta"))
        phi2 = np.asarray(table.column("Res_sublead_bjet_phi"))
        m2 = np.asarray(table.column("Res_sublead_bjet_mass"))
        return _invariant_mass_two_body(pt1, eta1, phi1, m1, pt2, eta2, phi2, m2)

    if name == "diphoton_mass":
        pt1 = np.asarray(table.column("lead_pt"))
        eta1 = np.asarray(table.column("lead_eta"))
        phi1 = np.asarray(table.column("lead_phi"))
        pt2 = np.asarray(table.column("sublead_pt"))
        eta2 = np.asarray(table.column("sublead_eta"))
        phi2 = np.asarray(table.column("sublead_phi"))
        zeros = np.zeros_like(pt1, dtype="f8")
        return _invariant_mass_two_body(pt1, eta1, phi1, zeros, pt2, eta2, phi2, zeros)

    if name == "bbgg_mass":
        return np.asarray(table.column("Res_HHbbggCandidate_mass"))

    raise ValueError(f"compute_derived_column: unknown derived column {name!r}")


def read_parquet_with_retry(path):
    """Open a ParquetFile with retries, to ride out transient EOS I/O
    errors (OSError, e.g. Errno 5 / Errno 71) rather than failing the
    whole comparison over one flaky read."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return pq.ParquetFile(str(path))
        except OSError as e:
            last_exc = e
            print(f"    [WARN] Failed to open {path} (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise last_exc


def find_mass_point_dirs(base_dir: Path, mass: str):
    """Find every NMSSM_X<mass>_Y* directory directly under base_dir."""
    if not base_dir.is_dir():
        return []
    pattern = f"NMSSM_X{mass}_Y*"
    return sorted(base_dir.glob(pattern))


def find_nominal_parquets(mass_point_dir: Path):
    """Find parquet file(s) under <mass_point_dir>/nominal/."""
    nominal_dir = mass_point_dir / "nominal"
    if not nominal_dir.is_dir():
        return []
    return sorted(nominal_dir.glob("*.parquet"))


def column_stats(pf: pq.ParquetFile, columns):
    """Read the columns needed for the requested output columns, computing
    derived quantities (dibjet_mass, diphoton_mass, bbgg_mass) from raw
    branches per DERIVED_COLUMN_INPUTS when applicable, and reading any
    other requested column directly. Handles missing raw inputs gracefully
    rather than crashing the whole comparison."""
    available = set(pf.schema.names)

    # Work out which raw columns actually need to be read from disk.
    raw_cols_needed = set()
    missing_cols = []
    for c in columns:
        if c in DERIVED_COLUMN_INPUTS:
            inputs = DERIVED_COLUMN_INPUTS[c]
            if all(i in available for i in inputs):
                raw_cols_needed.update(inputs)
            else:
                missing_cols.append(c)
        elif c in available:
            raw_cols_needed.add(c)
        else:
            missing_cols.append(c)

    stats = {c: None for c in missing_cols}

    if not raw_cols_needed:
        return stats, pf.metadata.num_rows

    table = pf.read(columns=sorted(raw_cols_needed))
    n_rows = table.num_rows

    for c in columns:
        if c in missing_cols:
            continue
        if c in DERIVED_COLUMN_INPUTS:
            arr = compute_derived_column(c, table)
        else:
            arr = np.asarray(table.column(c))

        finite = np.isfinite(arr)
        stats[c] = {
            "n_entries": int(arr.size),
            "n_finite": int(finite.sum()),
            "mean": float(np.mean(arr[finite])) if finite.any() else float("nan"),
            "min": float(np.min(arr[finite])) if finite.any() else float("nan"),
            "max": float(np.max(arr[finite])) if finite.any() else float("nan"),
        }

    return stats, n_rows


def summarize_side(label, base_dir, mass, columns):
    print(f"\n=== {label}: {base_dir} ===")
    mass_dirs = find_mass_point_dirs(Path(base_dir), mass)

    if not mass_dirs:
        print(f"  [NOT FOUND] No NMSSM_X{mass}_Y* directories under this base path.")
        return {}

    results = {}
    for mp_dir in mass_dirs:
        y_label = mp_dir.name  # e.g. "NMSSM_X600_Y300"
        parquet_files = find_nominal_parquets(mp_dir)

        if not parquet_files:
            print(f"  [{y_label}] [NO NOMINAL PARQUET FOUND] (looked in {mp_dir / 'nominal'})")
            continue

        total_rows = 0
        combined_stats = {c: {"n_entries": 0, "n_finite": 0, "sum": 0.0,
                               "min": np.inf, "max": -np.inf} for c in columns}
        any_missing = {c: False for c in columns}

        for fp in parquet_files:
            try:
                pf = read_parquet_with_retry(fp)
            except Exception as e:
                print(f"  [{y_label}] [UNREADABLE] {fp}: {e}")
                continue

            stats, n_rows = column_stats(pf, columns)
            total_rows += n_rows

            for c in columns:
                s = stats.get(c)
                if s is None:
                    any_missing[c] = True
                    continue
                combined_stats[c]["n_entries"] += s["n_entries"]
                combined_stats[c]["n_finite"] += s["n_finite"]
                if s["n_finite"] > 0:
                    combined_stats[c]["sum"] += s["mean"] * s["n_finite"]
                    combined_stats[c]["min"] = min(combined_stats[c]["min"], s["min"])
                    combined_stats[c]["max"] = max(combined_stats[c]["max"], s["max"])

        print(f"  [{y_label}] files={len(parquet_files)}  total_rows={total_rows}")
        for c in columns:
            if any_missing[c]:
                print(f"      {c}: [COLUMN MISSING in at least one file]")
                continue
            cs = combined_stats[c]
            mean = cs["sum"] / cs["n_finite"] if cs["n_finite"] > 0 else float("nan")
            print(f"      {c}: n_entries={cs['n_entries']} n_finite={cs['n_finite']} "
                  f"mean={mean:.4f} min={cs['min']:.4f} max={cs['max']:.4f}")

        results[y_label] = {
            "total_rows": total_rows,
            "columns": {
                c: (None if any_missing[c] else {
                    "n_entries": combined_stats[c]["n_entries"],
                    "n_finite": combined_stats[c]["n_finite"],
                })
                for c in columns
            },
        }

    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mass", required=True, help="X mass value, e.g. 600 (matches NMSSM_X600_Y*)")
    ap.add_argument("--columns", nargs="+", default=DEFAULT_COLUMNS,
                     help=f"Columns to compare (default: {DEFAULT_COLUMNS})")
    ap.add_argument("--dir-a", default=DEFAULT_DIR_A, help="First base directory")
    ap.add_argument("--dir-b", default=DEFAULT_DIR_B, help="Second base directory")
    args = ap.parse_args()

    print(f"Comparing mass point X{args.mass}, columns={args.columns}")

    results_a = summarize_side("Production A", args.dir_a, args.mass, args.columns)
    results_b = summarize_side("Production B", args.dir_b, args.mass, args.columns)

    print("\n================ COMPARISON ================")
    all_y_labels = sorted(set(results_a.keys()) | set(results_b.keys()))
    if not all_y_labels:
        print("No matching mass-point directories found in either production.")
        return

    for y_label in all_y_labels:
        ra = results_a.get(y_label)
        rb = results_b.get(y_label)
        print(f"\n{y_label}:")
        if ra is None:
            print("  [ONLY IN B] Not found in Production A")
            continue
        if rb is None:
            print("  [ONLY IN A] Not found in Production B")
            continue

        print(f"  total_rows: A={ra['total_rows']}  B={rb['total_rows']}  "
              f"diff={ra['total_rows'] - rb['total_rows']}")

        for c in args.columns:
            ca = ra["columns"].get(c)
            cb = rb["columns"].get(c)
            if ca is None or cb is None:
                print(f"  {c}: [MISSING in at least one production]")
                continue
            diff_entries = ca["n_entries"] - cb["n_entries"]
            diff_finite = ca["n_finite"] - cb["n_finite"]
            flag = "  <-- MISMATCH" if diff_entries != 0 or diff_finite != 0 else ""
            print(f"  {c}: A(n_entries={ca['n_entries']}, n_finite={ca['n_finite']})  "
                  f"B(n_entries={cb['n_entries']}, n_finite={cb['n_finite']})  "
                  f"diff_entries={diff_entries} diff_finite={diff_finite}{flag}")

    print("=============================================")


if __name__ == "__main__":
    main()