#!/usr/bin/env python3
"""
update_all_my_jsons_create_missing.py

Show diffs for every mass in mass_map. Create missing My_Json_<mass>.json files
or overwrite existing ones when run with --apply. Use --yes to auto-apply.

Usage:
  # dry-run (show diffs only, no writes)
  python update_all_my_jsons_create_missing.py

  # show diffs and then create/overwrite files (asks per-file)
  python update_all_my_jsons_create_missing.py --apply

  # apply to all without prompts
  python update_all_my_jsons_create_missing.py --apply --yes
"""

from collections import OrderedDict
import json
import os
import shutil
import time
import argparse
import difflib
import sys

# --- full mass -> Y lists (use your original data; 300 uses 60..170 sequence) ---
mass_map = OrderedDict([
    (300, [90, 95, 100, 125, 150, 170]),
    (320, [90, 95, 100, 125, 150, 170]),
    (350, [90, 95, 100, 125, 150, 170, 200]),
    (400, [90, 95, 100, 125, 150, 170, 200]),
    (450, [90, 95, 100, 125, 150, 170, 200, 250, 300]),
    (500, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350]),
    (550, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400]),
    (600, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450]),
    (650, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500]),
    (700, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550]),
    (750, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600]),
    (800, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650]),
    (850, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700]),
    (900, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700]),
    (950, [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800]),
    (1000,[90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800]),
])

# normalize Ys to ascending unique lists (safety)
for m in list(mass_map.keys()):
    mass_map[m] = sorted(set(mass_map[m]))

# templates (corrected ASCII quote)
systematics_template = [
    "Pileup",
    "ScaleEB2G_IJazZ",
    "ScaleEE2G_IJazZ",
    "Smearing2G_IJazZ",
    "ElectronVetoSF",
    "PreselSF",
    "TriggerSF",
    "PNet_bTagShapeSF"
]

corrections_template = [
    "jerc_jet_pnetNu_syst",
    "Smearing2G_IJazZ",
    "Pileup",
    "FNUF",
    "Material",
    "ElectronVetoSF",
    "PreselSF",
    "TriggerSF",
    "PNet_bTagShapeSF"
]

workflow = "HHbbgg"
metaconditions = "Era2022_v1"
taggers = []
analysis = "mainAnalysis"

def build_ordered_payload(mass):
    Ys = mass_map[mass]
    samplejson_name = f"sample_v1_test_{mass}.json"
    year_od = OrderedDict()
    systematics_od = OrderedDict()
    corrections_od = OrderedDict()
    for y in Ys:
        key = f"NMSSM_X{mass}_Y{y}"
        year_od[key] = ["2023postBPix"]
        systematics_od[key] = list(systematics_template)
        corrections_od[key] = list(corrections_template)
    payload = OrderedDict([
        ("samplejson", samplejson_name),
        ("workflow", workflow),
        ("metaconditions", metaconditions),
        ("year", year_od),
        ("taggers", taggers),
        ("systematics", systematics_od),
        ("corrections", corrections_od),
        ("analysis", analysis),
    ])
    return payload

def new_text_for_payload(payload):
    # preserve key ordering when dumping OrderedDict
    return json.dumps(payload, indent=4) + "\n"

def read_existing_text(path):
    if not os.path.exists(path):
        return ""  # empty for diff against a new file
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    if not txt.endswith("\n"):
        txt += "\n"
    return txt

def print_unified_diff(old_text, new_text, fname):
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines,
                                     fromfile=f"{fname} (current)",
                                     tofile=f"{fname} (new)",
                                     lineterm=""))
    if not diff:
        print(f"  [no changes] {fname}")
    else:
        print("="*80)
        print(f"Diff for {fname}:")
        print("-"*80)
        for line in diff:
            sys.stdout.write(line + ("\n" if not line.endswith("\n") else ""))
        print("-"*80)

def backup_file(path):
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak_name = f"{path}.bak.{ts}"
    shutil.copy2(path, bak_name)
    return bak_name

def confirm_prompt(fname, auto_yes=False):
    if auto_yes:
        return True
    while True:
        resp = input(f"Create/overwrite {fname}? [y]es / [n]o / [a]ll / [q]uit: ").strip().lower()
        if resp in ("y","yes"):
            return True
        if resp in ("n","no"):
            return False
        if resp in ("a","all"):
            return "ALL"
        if resp in ("q","quit"):
            return "QUIT"
        print("Please answer y / n / a / q.")

def main():
    parser = argparse.ArgumentParser(description="Show diffs for all masses and create missing My_Json files if requested.")
    parser.add_argument("--apply", action="store_true", help="Write files (create/overwrite) after showing diffs.")
    parser.add_argument("--yes", action="store_true", help="When --apply is set, apply to all without prompting.")
    args = parser.parse_args()

    cwd = os.getcwd()
    print(f"Running in: {cwd}")
    apply_changes = args.apply
    auto_yes = args.yes and apply_changes
    apply_all = False

    for mass in mass_map.keys():
        fname = f"My_Json_{mass}.json"
        payload = build_ordered_payload(mass)
        new_text = new_text_for_payload(payload)
        old_text = read_existing_text(fname)

        print(f"\nProcessing {fname} ...")
        print_unified_diff(old_text, new_text, fname)

        if not apply_changes:
            continue

        if apply_all or auto_yes:
            do_write = True
        else:
            resp = confirm_prompt(fname, auto_yes=auto_yes)
            if resp == "ALL":
                apply_all = True
                do_write = True
            elif resp == "QUIT":
                print("Quitting without further changes.")
                return
            else:
                do_write = bool(resp)

        if do_write:
            try:
                if os.path.exists(fname):
                    bak = backup_file(fname)
                else:
                    bak = None
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(new_text)
                if bak:
                    print(f"  -> wrote {fname} (backup: {bak})")
                else:
                    print(f"  -> created {fname}")
            except Exception as e:
                print(f"  ! error writing {fname}: {e}")
        else:
            print(f"  -> skipped {fname}")

    print("\nDone.")

if __name__ == "__main__":
    main()
