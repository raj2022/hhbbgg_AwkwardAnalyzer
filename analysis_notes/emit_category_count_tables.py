#!/usr/bin/env python3
"""
Emit one LaTeX longtable per year (2022, 2023, 2024), listing the AMS2
category count for every mass point, sorted by mX then mY. Uses `longtable`
since each table has ~196-197 rows and won't fit on one page as a plain
`table` environment.

Run directly (stdlib json only):
    python3 emit_category_count_tables.py > category_count_tables.tex
"""

import json
import re

YEAR_FILES = {
    "2022": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2022/event_categories.json",
    "2023": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2023/event_categories.json",
    "2024": "/eos/home-s/sraj/Work_/CUA_20--/Analysis/hhbbgg_AwkwardAnalyzer/slides_fitting/CMSSW_14_1_0_pre4/src/outputs/categories_2024/event_categories.json",
}

MASS_POINT_RE = re.compile(r"^mX(\d+)_mY(\d+)$")


def load_boundaries(path):
    with open(path) as f:
        data = json.load(f)
    return data["boundaries"]


def parse_mass_point(key):
    m = MASS_POINT_RE.match(key)
    if not m:
        raise ValueError(f"Unrecognized mass point key format: {key}")
    return int(m.group(1)), int(m.group(2))


def emit_longtable(year, counts):
    """counts: dict mass_point_key -> n_categories"""
    rows = []
    for mp, n_cat in counts.items():
        mx, my = parse_mass_point(mp)
        rows.append((mx, my, n_cat))
    rows.sort(key=lambda r: (r[0], r[1]))

    print(r"\begin{longtable}{c c c}")
    print(r"\caption{AMS2 category count by mass point, %s (%d points).}" % (year, len(rows)))
    print(r"\label{tab:category_count_%s} \\" % year)
    print(r"\hline")
    print(r"$m_X$ [GeV] & $m_Y$ [GeV] & N categories \\")
    print(r"\hline")
    print(r"\endfirsthead")
    print(r"\multicolumn{3}{c}{\tablename\ \thetable{} -- continued} \\")
    print(r"\hline")
    print(r"$m_X$ [GeV] & $m_Y$ [GeV] & N categories \\")
    print(r"\hline")
    print(r"\endhead")
    print(r"\hline")
    print(r"\endfoot")
    print(r"\hline")
    print(r"\endlastfoot")
    for mx, my, n_cat in rows:
        print(f"{mx} & {my} & {n_cat} \\\\")
    print(r"\end{longtable}")
    print()


def main():
    print(r"%% Requires \usepackage{longtable} in the preamble.")
    print()
    for year, path in YEAR_FILES.items():
        boundaries = load_boundaries(path)
        counts = {mp: len(b) for mp, b in boundaries.items()}
        emit_longtable(year, counts)


if __name__ == "__main__":
    main()