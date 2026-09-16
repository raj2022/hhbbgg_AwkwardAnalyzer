#!/usr/bin/env python3
"""
Compute the observed range in the number of signal-region categories across
the mass grid, from the AMS2 categorization boundary JSON files, for the
Sec 11.5 TODO in AN-25-133:

    "quote the observed range in the number of categories across the grid
    (e.g. minimum and maximum categories found, and roughly how many mass
    points fall at each count) once the full-grid categorization is
    finalized."

Number of categories for a given mass point = len(boundaries[mass_point]),
since each entry in the boundaries list marks the lower edge of one
accepted AMS2-selected category.

Run directly (no special environment needed, just stdlib json):
    python3 compute_category_count_distribution.py
"""

import json
from collections import Counter

YEAR_FILES = {
    "2022": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022/event_categories.json",
    "2023": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023/event_categories.json",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024/event_categories.json",
}


def load_boundaries(path):
    with open(path) as f:
        data = json.load(f)
    return data["boundaries"]


def main():
    per_year_counts = {}  # year -> {mass_point: n_categories}
    for year, path in YEAR_FILES.items():
        boundaries = load_boundaries(path)
        per_year_counts[year] = {mp: len(b) for mp, b in boundaries.items()}

    # ---- Per-year summary ----
    for year, counts in per_year_counts.items():
        n_points = len(counts)
        values = list(counts.values())
        print("=" * 70)
        print(f"Year {year}: {n_points} mass points")
        print("=" * 70)
        print(f"  min categories = {min(values)}")
        print(f"  max categories = {max(values)}")
        hist = Counter(values)
        print("  distribution (n_categories -> n_mass_points):")
        for n_cat in sorted(hist):
            n_pts = hist[n_cat]
            pct = 100.0 * n_pts / n_points
            print(f"    {n_cat} categories: {n_pts} points ({pct:.1f}%)")
        # show which points hit the extremes
        min_pts = [mp for mp, n in counts.items() if n == min(values)]
        max_pts = [mp for mp, n in counts.items() if n == max(values)]
        print(f"  point(s) with min categories: {min_pts}")
        print(f"  point(s) with max categories: {max_pts}")
        print()

    # ---- Cross-year consistency check ----
    print("=" * 70)
    print("Cross-year consistency check (same mass point, different year)")
    print("=" * 70)
    all_mass_points = set()
    for counts in per_year_counts.values():
        all_mass_points.update(counts.keys())

    inconsistent = []
    for mp in sorted(all_mass_points):
        counts_by_year = {
            year: per_year_counts[year].get(mp) for year in YEAR_FILES
        }
        values_present = [v for v in counts_by_year.values() if v is not None]
        if len(set(values_present)) > 1:
            inconsistent.append((mp, counts_by_year))

    if inconsistent:
        print(f"{len(inconsistent)} mass points have a DIFFERENT category count between years:")
        for mp, cby in inconsistent:
            print(f"  {mp}: {cby}")
    else:
        print("All mass points present in multiple years have the SAME category")
        print("count across years (categorization is mass-point-driven, not")
        print("year-dependent, as expected).")

    # ---- Combined (all years, union of points) summary ----
    print()
    print("=" * 70)
    print("Combined summary (union of mass points across all years)")
    print("=" * 70)
    combined = {}
    for counts in per_year_counts.values():
        combined.update(counts)  # last year wins if inconsistent; flagged above
    values = list(combined.values())
    n_points = len(combined)
    print(f"Total distinct mass points: {n_points}")
    print(f"min categories = {min(values)}")
    print(f"max categories = {max(values)}")
    hist = Counter(values)
    print("distribution (n_categories -> n_mass_points):")
    for n_cat in sorted(hist):
        n_pts = hist[n_cat]
        pct = 100.0 * n_pts / n_points
        print(f"  {n_cat} categories: {n_pts} points ({pct:.1f}%)")


if __name__ == "__main__":
    main()