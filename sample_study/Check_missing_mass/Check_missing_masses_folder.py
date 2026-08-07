#!/usr/bin/env python3
"""
check_missing_masses.py

Scan a folder of NMSSM_X<mass>_Y<y> sample directories and report which
(mass, y) points from the expected signal grid are missing, and (as a
cross-check) which present folders are NOT in the expected grid at all.

Usage:
  python check_missing_masses.py -i /path/to/merged

Optional:
  --require-file NOTAG_merged.parquet   file that must exist inside
                                          <sample>/nominal/ for a point to
                                          count as "present" (default:
                                          just require the sample folder
                                          itself to exist; pass this to
                                          also verify the nominal parquet
                                          is actually there, not just an
                                          empty/partial directory)
  --systematic nominal                  subfolder to check the file in
                                          (default: "nominal")
"""

import argparse
import re
from pathlib import Path

# Expected signal grid, exactly as specified.
EXPECTED_GRID = {
    300: [90, 95, 100, 125, 150, 170],
    320: [90, 95, 100, 125, 150, 170],
    350: [90, 95, 100, 125, 150, 170, 200],
    400: [90, 95, 100, 125, 150, 170, 200, 250],
    450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
    500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
    600: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    650: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    700: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    750: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    800: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
    850: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    900: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    950: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    1000: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}

# Same convention used throughout the pipeline (inference_PDnn.py, etc.)
SAMPLE_DIR_RE = re.compile(r"^NMSSM_X(\d+)_Y(\d+)$", re.IGNORECASE)


def scan_present_points(root: Path) -> dict:
    """Return {(mass, y): Path} for every NMSSM_X###_Y### subfolder found."""
    present = {}
    for child in root.iterdir():
        if not child.is_dir():
            continue
        m = SAMPLE_DIR_RE.match(child.name)
        if m:
            present[(int(m.group(1)), int(m.group(2)))] = child
    return present


def check_file_present(sample_dir: Path, systematic: str, require_file: str) -> bool:
    """Check a specific file exists inside <sample_dir>/<systematic>/."""
    return (sample_dir / systematic / require_file).exists()


def main():
    ap = argparse.ArgumentParser(description="Report missing/extra NMSSM mass points vs. the expected grid.")
    ap.add_argument("-i", "--input", required=True, help="Folder containing NMSSM_X<mass>_Y<y> subfolders")
    ap.add_argument("--require-file", default=None,
                     help="If set, also require this file to exist inside <sample>/<systematic>/ "
                          "for the point to count as present (e.g. NOTAG_merged.parquet). "
                          "If not set, only the sample folder's existence is checked.")
    ap.add_argument("--systematic", default="nominal",
                     help="Subfolder to check --require-file in (default: nominal)")
    ap.add_argument("--min-y", type=int, default=90,
                     help="Only report EXTRA folders with Y >= this value (default: 90). "
                          "Lower-Y folders are known to exist out of scope and are silently "
                          "excluded from the report, just counted in a one-line summary. "
                          "Does not affect MISSING/INCOMPLETE, since the expected grid "
                          "already only contains Y >= 90.")
    args = ap.parse_args()

    root = Path(args.input).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Not a folder: {root}")

    present = scan_present_points(root)

    expected_points = {(mass, y) for mass, ys in EXPECTED_GRID.items() for y in ys}
    present_points = set(present.keys())

    missing = sorted(expected_points - present_points)
    extra_all = sorted(present_points - expected_points)
    extra = [(m, y) for m, y in extra_all if y >= args.min_y]
    extra_suppressed = len(extra_all) - len(extra)

    # Points whose folder exists but fail the optional file check.
    incomplete = []
    if args.require_file:
        for (mass, y) in sorted(expected_points & present_points):
            sample_dir = present[(mass, y)]
            if not check_file_present(sample_dir, args.systematic, args.require_file):
                incomplete.append((mass, y, sample_dir))

    n_expected = len(expected_points)
    n_present = len(expected_points & present_points)
    print(f"Scanned: {root}")
    print(f"Expected grid points: {n_expected}")
    print(f"Present (folder exists): {n_present}")
    if args.require_file:
        print(f"Present AND has {args.systematic}/{args.require_file}: "
              f"{n_present - len(incomplete)}")
    print()

    if missing:
        print(f"=== MISSING: {len(missing)} point(s) with no folder at all ===")
        by_mass = {}
        for mass, y in missing:
            by_mass.setdefault(mass, []).append(y)
        for mass in sorted(by_mass):
            ys = ", ".join(str(y) for y in sorted(by_mass[mass]))
            print(f"  X={mass:5d}: Y = {ys}")
        print()
    else:
        print("No missing points -- every expected (X, Y) has a folder present.\n")

    if args.require_file and incomplete:
        print(f"=== INCOMPLETE: {len(incomplete)} point(s) with a folder but no "
              f"{args.systematic}/{args.require_file} ===")
        by_mass = {}
        for mass, y, path in incomplete:
            by_mass.setdefault(mass, []).append(y)
        for mass in sorted(by_mass):
            ys = ", ".join(str(y) for y in sorted(by_mass[mass]))
            print(f"  X={mass:5d}: Y = {ys}")
        print()

    if extra:
        print(f"=== EXTRA: {len(extra)} folder(s) present but NOT in the expected grid "
              f"(Y >= {args.min_y}) ===")
        by_mass = {}
        for mass, y in extra:
            by_mass.setdefault(mass, []).append(y)
        for mass in sorted(by_mass):
            ys = ", ".join(str(y) for y in sorted(by_mass[mass]))
            print(f"  X={mass:5d}: Y = {ys}")
        print()
    if extra_suppressed:
        print(f"({extra_suppressed} additional out-of-scope folder(s) with Y < {args.min_y} "
              f"found but not listed; rerun with --min-y 0 to see them.)\n")

    if not missing and not extra and not incomplete:
        print("Everything matches the expected grid exactly.")


if __name__ == "__main__":
    main()