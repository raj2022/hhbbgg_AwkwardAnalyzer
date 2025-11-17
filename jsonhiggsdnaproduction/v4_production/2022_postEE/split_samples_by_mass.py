#!/usr/bin/env python3
"""
split_samples_by_mass.py

Reads samples_2022_postEE.json and writes one JSON file per mass:
  split_by_mass/samples_X300.json, samples_X320.json, ...

Usage:
  python split_samples_by_mass.py
"""

import json
import os
import re
from collections import defaultdict, OrderedDict

INPUT = "../samples_2022_postEE.json"
OUTDIR = ""
KEY_RE = re.compile(r"NMSSM_X(?P<m>\d+)_Y(?P<y>\d+)")

def main():
    if not os.path.exists(INPUT):
        print(f"Error: {INPUT} not found in {os.getcwd()}")
        return

    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)  # dict of keys -> list of files

    # group by mass preserving insertion order of keys inside each mass
    grouped = defaultdict(OrderedDict)
    for k, v in data.items():
        m = KEY_RE.match(k)
        if not m:
            # keep unexpected keys under a special file
            grouped["__other__"][k] = v
            continue
        mass = m.group("m")
        grouped[mass][k] = v

    # os.makedirs(OUTDIR, exist_ok=True)

    for mass, entries in grouped.items():
        # choose filename for 'other' entries
        if mass == "__other__":
            outname = os.path.join("samples_other_keys.json")
        else:
            outname = os.path.join(f"sample_v1_test_{mass}.json")
        with open(outname, "w", encoding="utf-8") as outf:
            # pretty print with indent=4 for readability
            json.dump(entries, outf, indent=4)
        print(f"Wrote {outname} ({len(entries)} keys)")

    print("Done.")

if __name__ == "__main__":
    main()
