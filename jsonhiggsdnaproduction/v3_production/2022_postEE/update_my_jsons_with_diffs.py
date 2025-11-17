#!/usr/bin/env python3
"""
update_my_jsons_with_diffs.py

Print unified diffs between existing My_Json_<mass>.json files and the new
payloads built from the mass->Y lists. Optionally overwrite files after
confirming, creating backups.

Usage:
  # dry-run: print diffs only
  python update_my_jsons_with_diffs.py

  # show diffs and prompt before overwriting, create backups when writing
  python update_my_jsons_with_diffs.py --apply

  # apply without interactive prompts (use with care)
  python update_my_jsons_with_diffs.py --apply --yes
"""

import json
import os
import shutil
import time
import argparse
import difflib
import sys

# --- mass -> Y lists (as provided by you) ---
mass_map = {
    300: [90, 95, 100, 125, 150, 170],
    320: [90, 95, 100, 125, 150, 170],
    350: [90, 95, 100, 125, 150, 170, 200],
    400: [90, 95, 100, 125, 150, 170, 200],
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
    1000:[90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}

# --- template pieces (same for all mass/Y combos) ---
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

def build_payload(mass):
    samplejson_name = f"sample_v1_test_{mass}.json"
    year = {}
    systematics = {}
    corrections = {}

    Ys = mass_map[mass]
    for y in Ys:
        key = f"NMSSM_X{mass}_Y{y}"
        year[key] = ["2022postEE"]
        systematics[key] = list(systematics_template)
        corrections[key] = list(corrections_template)

    payload = {
        "samplejson": samplejson_name,
        "workflow": workflow,
        "metaconditions": metaconditions,
        "year": year,
        "taggers": taggers,
        "systematics": systematics,
        "corrections": corrections,
        "analysis": analysis
    }
    return payload

def normalize_json_text_from_file(path):
    """
    Try to read and normalize JSON text from path. If parse fails, return raw text.
    Normalized form uses sorted keys and indent=4 for stable diffs.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        obj = json.loads(raw)
        normalized = json.dumps(obj, indent=4, sort_keys=True) + "\n"
        return normalized, True
    except Exception:
        # fallback to raw text (preserve exactly for diff)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw2 = f.read()
        # ensure trailing newline for unified diff compatibility
        if not raw2.endswith("\n"):
            raw2 = raw2 + "\n"
        return raw2, False

def new_text_for_payload(payload):
    # produce normalized JSON text with sorted keys and newline at end
    return json.dumps(payload, indent=4, sort_keys=True) + "\n"

def backup_file(path):
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak_name = f"{path}.bak.{ts}"
    shutil.copy2(path, bak_name)
    return bak_name

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
        # print lines (they already include newlines)
        for line in diff:
            sys.stdout.write(line + ("\n" if not line.endswith("\n") else ""))
        print("-"*80)

def confirm_prompt(fname, auto_yes=False):
    if auto_yes:
        return True
    while True:
        resp = input(f"Overwrite {fname}? [y]es / [n]o / [a]ll / [q]uit: ").strip().lower()
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
    parser = argparse.ArgumentParser(description="Show diffs and optionally update My_Json_*.json files.")
    parser.add_argument("--apply", action="store_true", help="If set, actually write files after confirmation.")
    parser.add_argument("--yes", action="store_true", help="When --apply is set, apply changes without prompting.")
    args = parser.parse_args()

    cwd = os.getcwd()
    print(f"Running in: {cwd}")
    apply_changes = args.apply
    auto_yes = args.yes and apply_changes
    apply_all = False

    for mass in sorted(mass_map.keys()):
        fname = f"My_Json_{mass}.json"
        if not os.path.exists(fname):
            print(f"Skipping (not found): {fname}")
            continue

        print(f"\nProcessing {fname} ...")
        # old text (normalized if possible)
        old_text, old_is_json = normalize_json_text_from_file(fname)

        # new payload and text (normalized)
        payload = build_payload(mass)
        new_text = new_text_for_payload(payload)

        # print diff
        print_unified_diff(old_text, new_text, fname)

        if not apply_changes:
            continue  # dry-run; do not write

        # if apply changes: ask for confirmation (unless auto-yes or apply_all)
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
                bak = backup_file(fname)
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(new_text)
                print(f"  -> wrote {fname} (backup: {bak})")
            except Exception as e:
                print(f"  ! error writing {fname}: {e}")
        else:
            print(f"  -> skipped {fname}")

    print("\nDone.")

if __name__ == "__main__":
    main()
