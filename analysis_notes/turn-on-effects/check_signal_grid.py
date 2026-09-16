#!/usr/bin/env python3
# =============================================================================
# check_signal_grid.py
#
# Scans the signal parquet base directory and reports every (mX, mY) point
# that actually exists on disk, regardless of what any hardcoded grid list
# (e.g. pDNN_v2.py's MASS_POINTS/Y_VALUES) assumes.
#
# Usage:
#   python3 check_signal_grid.py
# =============================================================================

import os
import re
import glob

BASE_DIR = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/HiggsDNA_v7_dask_merged/2022/sim/postEE/merged/"

# Matches directories like NMSSM_X300_Y90, NMSSM_X1000_Y800, etc.
PATTERN = re.compile(r"^NMSSM_X(\d+)_Y(\d+)$")

# The specific ranges you want to check
X_CHECK_MIN, X_CHECK_MAX = 300, 950
Y_CHECK_MIN = 50  # per your message: Y reportedly starts as low as 50


def scan_grid(base_dir):
    found = []
    if not os.path.isdir(base_dir):
        print(f"[ERROR] Directory does not exist or is not mounted: {base_dir}")
        return found

    for entry in sorted(os.listdir(base_dir)):
        m = PATTERN.match(entry)
        if not m:
            continue
        mx, my = int(m.group(1)), int(m.group(2))
        # confirm the actual parquet file is present, not just the directory
        parquet_path = os.path.join(base_dir, entry, "nominal", "NOTAG_merged.parquet")
        has_file = os.path.isfile(parquet_path)
        found.append((mx, my, has_file, parquet_path))
    return found


def main():
    all_points = scan_grid(BASE_DIR)
    if not all_points:
        print("[WARN] No NMSSM_X###_Y### directories found -- check BASE_DIR / EOS mount.")
        return

    print(f"[INFO] Found {len(all_points)} NMSSM_X###_Y### directories total under:\n  {BASE_DIR}\n")

    # Full grid, sorted
    print("=== Full (mX, mY) grid found on disk ===")
    by_x = {}
    for mx, my, has_file, path in sorted(all_points):
        by_x.setdefault(mx, []).append((my, has_file))

    for mx in sorted(by_x):
        ys = by_x[mx]
        y_str = ", ".join(f"{y}{'':s}" if ok else f"{y}(NO FILE)" for y, ok in sorted(ys))
        print(f"  X{mx}: {y_str}")

    # Focused check: X in [300,950], Y >= 50
    print(f"\n=== Filtered: X in [{X_CHECK_MIN},{X_CHECK_MAX}], Y >= {Y_CHECK_MIN} ===")
    filtered = [(mx, my, ok) for mx, my, ok, _ in all_points
                if X_CHECK_MIN <= mx <= X_CHECK_MAX and my >= Y_CHECK_MIN]
    if not filtered:
        print("  (none found in this range)")
    else:
        by_x_f = {}
        for mx, my, ok in filtered:
            by_x_f.setdefault(mx, []).append((my, ok))
        for mx in sorted(by_x_f):
            ys = by_x_f[mx]
            y_str = ", ".join(f"{y}" if ok else f"{y}(NO FILE)" for y, ok in sorted(ys))
            print(f"  X{mx}: {y_str}")

    # Explicitly flag any Y < 90 found anywhere (relevant to the turn-on discussion)
    low_y = sorted(set((mx, my) for mx, my, ok, _ in all_points if my < 90))
    print(f"\n=== Points with mY < 90 GeV (relevant to Fig.2/Sec.7.2 discussion) ===")
    if low_y:
        for mx, my in low_y:
            print(f"  X{mx}_Y{my}")
    else:
        print("  (none found -- lowest mY on disk is >= 90 GeV)")


if __name__ == "__main__":
    main()