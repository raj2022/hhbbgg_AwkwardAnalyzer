#!/usr/bin/env python3
"""
NMSSM signal MC production -- 2024/2025.

⚠️⚠️⚠️  READ BEFORE USING  ⚠️⚠️⚠️
`higgs_dna/systematics/jet_systematics_json.py` (line ~166) explicitly warns:

    "Current 2024 and 2025 JER are preliminary, 2023PostBPix is used!
     These ntuples should not be used for a final physics result!"

Production through this script will run and produce output, but that output
carries this caveat. Confirm this is acceptable for your purpose (pipeline
validation is fine; a final result is not) before relying on it.
⚠️⚠️⚠️  ------------------------  ⚠️⚠️⚠️

Kept as a SEPARATE file from produce_xtoyh_signal_mc_2024_robust.py (2022/2023)
because several real, DAS-confirmed differences don't fit that script's
assumptions cleanly:

  - Dataset naming is DIFFERENT: hyphenated `NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-<mX>-MY-<mY>`,
    not the underscored `NMSSM_XtoYHto2B2G_MX-<mX>_MY-<mY>` used for 2022/2023.
    Confirmed directly via dasgoclient, e.g.:
      /NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-1000-MY-125_TuneCP5_13p6TeV_madgraph-pythia8/
          RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM
  - `--year` is NOT era-qualified for these two years -- just "2024"/"2025",
    confirmed from produce_one_mc.py's own --year argparse choices list
    (no "2024preXYZ"/"2024postXYZ" the way 2022/2023 have preEE/postEE).
  - NanoAOD version is v15, not v12 (--nano 15).
  - 2024 and 2025 share the SAME physical dataset/campaign -- confirmed no
    separate 2025 MC production exists; both years are the same events,
    split by event ID via --split-mc ("even for 2024, odd for 2025").

Everything else (resume/dedup via state file, --check, --dry-run, per-sample
try/except, proxy handling) is deliberately identical in mechanics to the
2022/2023 script -- same state file (nmssm_submission_state.json), same
state_key format ("year:keyword"), so --check works the same way across
both scripts without needing to merge them.
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()

# Confirmed via dasgoclient for MX-1000_MY-125; NOT yet confirmed this exact
# string resolves for every (mX, mY) point below -- that's what --dry-run is for.
CAMPAIGNS = {
    "2024": "RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2",
    # Confirmed (2026-08-23): no separate 2025 MC production exists -- 2025
    # reuses the SAME 2024 dataset, split by event ID (--split-mc: even for
    # 2024, odd for 2025). Same campaign string as "2024" is correct here,
    # not a placeholder/guess.
    "2025": "RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2",
}

parser.add_argument(
    "--year", choices=CAMPAIGNS.keys(), default="2024",
    help="2024 or 2025. NOT era-qualified like the 2022/2023 script's --era.",
)
parser.add_argument(
    "--check", action="store_true",
    help="Skip submission entirely. Just check actual EOS output for every "
         "sample recorded as submitted, and print a status report.",
)
parser.add_argument(
    "--dry-run", action="store_true",
    help="Skip submission entirely. Just DAS-check every sample currently "
         "listed in NMSSM_Samples against DAS, zero side effects. Run this "
         "BEFORE ever submitting for real -- the campaign string above is "
         "confirmed for only one (mX, mY) point so far.",
)
args = parser.parse_args()

outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/" + os.environ['USER'] + "/HiggsDNA_v7_dask/"
extra_dir = ""

STATE_FILE = "nmssm_submission_state.json"   # SAME file as the 2022/2023 script

# Full (mX, mY) grid intended for this analysis, matching the same phase-space
# envelope (mY < mX - mH) already established and DAS-confirmed for 2022/2023.
# Listed here as CANDIDATES only -- NOT yet confirmed for 2024/2025 beyond the
# two blocks below. Uncomment/validate each mX block via --dry-run before
# submitting it for real, exactly the same discipline as the 2022/2023 script.
# Full (mX, mY) grid intended for this analysis, respecting the phase-space
# constraint mY < mX - mH. Uncomment/fill in mX blocks as each is confirmed
# in DAS -- don't submit an mX block you haven't pre-flight-checked.
NMSSM_Samples = {
    # 240: [50],
    # 240: [50, 60, 70, 80, 90, 95, 100],
    # 280: [50, 60, 70, 80, 90, 95, 100, 125, 150],
    # 300: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],   # verified in DAS: 10/10 OK
    320: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],
    350: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200],
    # 400: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250],
    # 400: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250],
    # 450: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300],
    # 500: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    # 550: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
    # 600: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    # 650: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    # 700: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    # 750: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    # 800: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
    # 850: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    # 900: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    # 950: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    # 1000: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}
campaign = CAMPAIGNS[args.year]

samples = []
for mX, mY_list in NMSSM_Samples.items():
    for mY in mY_list:
        samples.append({
            "keyword": f"NMSSM_X{mX}_Y{mY}",
            "cmsdas": f"/NMSSM-XtoYH-Yto2B-Hto2G_Par-MX-{mX}-MY-{mY}_TuneCP5_13p6TeV_madgraph-pythia8/{campaign}/NANOAODSIM",
            "year": args.year,       # plain "2024"/"2025", not era-qualified
            "nano": "15",            # confirmed NanoAODv15, not v12
            "state_key": f"{args.year}:NMSSM_X{mX}_Y{mY}",
        })

def parent_dir_for(sample):
    # No era subfolder for 2024/2025 -- year alone, no preEE/postEE-style split
    return outbase_dir + "/" + sample["year"] + "/sim/" + extra_dir

def has_output(sample):
    sample_dir = Path(parent_dir_for(sample)) / sample["keyword"]
    if not sample_dir.exists():
        return 0
    return len(list(sample_dir.rglob("*Events_0*")))

# --- Load prior run state -- SHARED with the 2022/2023 script's state file ---
state = {"submitted": [], "failed": []}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ============================================================
# --dry-run mode
# ============================================================
if args.dry_run:
    print(f"[DRY RUN] Checking all {len(samples)} sample(s) currently in NMSSM_Samples "
          f"against DAS for --year {args.year}. No submission, no directories, no state changes.\n")
    missing, ok = [], []
    for sample in samples:
        result = subprocess.run(
            f"dasgoclient -query=\"dataset={sample['cmsdas']}\"",
            shell=True, capture_output=True, text=True,
        )
        if not result.stdout.strip():
            missing.append(sample)
            print(f"  [MISSING] {sample['keyword']}: {sample['cmsdas']}")
        else:
            ok.append(sample["keyword"])
            print(f"  [OK]      {sample['keyword']}")

    print("\n" + "=" * 60)
    print(f"[DRY RUN] {len(ok)}/{len(samples)} resolve in DAS.")
    if missing:
        print(f"{len(missing)} did NOT resolve -- check the naming convention/campaign "
              f"tag for these specifically before uncommenting/submitting:")
        for s in missing:
            print(f"  - {s['keyword']}: {s['cmsdas']}")
    else:
        print("All samples currently in the grid resolve. Safe to submit for real "
              "(rerun without --dry-run). Remember: JER caveat still applies (see top of file).")
    print("=" * 60)
    sys.exit(0)

# ============================================================
# --check mode
# ============================================================
if args.check:
    if state["submitted"] or state["failed"]:
        to_report = state["submitted"]
        source_note = f"tracked in {STATE_FILE}"
    else:
        to_report = [s["state_key"] for s in samples]
        source_note = f"no {STATE_FILE} found -- checking all {len(samples)} sample(s) currently in NMSSM_Samples for --year {args.year} instead"
        print(f"[NOTE] {source_note}.\n")

    by_state_key = {s["state_key"]: s for s in samples}
    no_output, has_files = [], []

    print(f"Checking output for {len(to_report)} sample(s) ({source_note})...\n")
    for state_key in to_report:
        sample = by_state_key.get(state_key)
        if sample is None:
            print(f"  [?]        {state_key} -- not in current NMSSM_Samples grid for this year, can't locate")
            continue
        n = has_output(sample)
        if n > 0:
            print(f"  [OK]       {state_key}: {n} chunk file(s) found")
            has_files.append(state_key)
        else:
            print(f"  [NO OUTPUT] {state_key}: 0 files -- still running, or job failed")
            no_output.append(state_key)

    print("\n" + "=" * 60)
    print(f"{len(has_files)} sample(s) have output, {len(no_output)} do not (yet, or failed).")
    if state["failed"]:
        print(f"\n{len(state['failed'])} sample(s) failed at submission (never reached Condor):")
        for k in state["failed"]:
            print(f"  - {k}")
    if no_output:
        print(f"\n{len(no_output)} sample(s) with no output on disk yet:")
        for k in no_output:
            print(f"  - {k}")
    print("=" * 60)
    sys.exit(0)

# ============================================================
# Submission mode (default)
# ============================================================
def ensure_valid_proxy():
    result = subprocess.run("voms-proxy-info --exists", shell=True)
    if result.returncode != 0:
        print("No valid proxy found -- initializing (requires interactive passphrase)...")
        subprocess.run("voms-proxy-init --rfc --voms cms -valid 192:00", shell=True, check=True)
    else:
        print("Valid proxy already exists -- skipping voms-proxy-init.")

print("=" * 60)
print("⚠️  2024/2025 JER is PRELIMINARY -- output from this run should NOT be")
print("    used for a final physics result. See top of this file / ")
print("    jet_systematics_json.py line ~166 for the exact upstream warning.")
print("=" * 60 + "\n")

ensure_valid_proxy()

print(f"Total samples in grid: {len(samples)}")
year_submitted = [k for k in state["submitted"] if k.startswith(args.year)]
year_failed = [k for k in state["failed"] if k.startswith(args.year)]
if year_submitted or year_failed:
    print(f"Resuming for {args.year}: {len(year_submitted)} already submitted, "
          f"{len(year_failed)} previously failed (will retry failed ones).")

to_check = [s for s in samples if s["state_key"] not in state["submitted"]]
print(f"\nChecking dataset existence in DAS for {len(to_check)} remaining sample(s)...")
missing = []
for sample in to_check:
    result = subprocess.run(
        f"dasgoclient -query=\"dataset={sample['cmsdas']}\"",
        shell=True, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        missing.append(sample["keyword"])
        print(f"  [MISSING] {sample['keyword']}: {sample['cmsdas']}")
    else:
        print(f"  [OK]      {sample['keyword']}")

if missing:
    print(f"\n{len(missing)} of {len(to_check)} datasets did not resolve in DAS:")
    for k in missing:
        print(f"  - {k}")
    print("\nNot submitting any jobs -- fix these before rerunning.")
    raise SystemExit(1)

print("\nAll datasets confirmed in DAS. Proceeding with submission.\n")

for sample in samples:
    keyword = sample["keyword"]
    state_key = sample["state_key"]

    if state_key in state["submitted"]:
        print(f"[SKIP] {state_key} -- already submitted in a prior run.")
        continue

    parent_dir = parent_dir_for(sample)

    print(f"Creating directory: {parent_dir}")
    os.makedirs(parent_dir, exist_ok=True)
    os.chmod(parent_dir, 0o777)

    command = (
        f"python submission/tools_HHbbgg/produce_one_mc.py "
        f"--keyword {sample['keyword']} --cmsdas {sample['cmsdas']} "
        f"--parent-dir {parent_dir} --year {sample['year']} --nano {sample['nano']} "
        f"--memory 30GB "
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing: {command}")

    try:
        subprocess.run(command, shell=True, check=True)
        state["submitted"].append(state_key)
        if state_key in state["failed"]:
            state["failed"].remove(state_key)
        print(f"[OK]   {state_key} submitted.")
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {state_key} failed to submit: {e}")
        if state_key not in state["failed"]:
            state["failed"].append(state_key)

    save_state()

print("\n" + "=" * 60)
year_submitted = [k for k in state["submitted"] if k.startswith(args.year)]
year_failed = [k for k in state["failed"] if k.startswith(args.year)]
print(f"Done. {len(year_submitted)} submitted for {args.year}, {len(year_failed)} failed.")
if year_failed:
    print("Failed samples (rerun this script to retry just these):")
    for k in year_failed:
        print(f"  - {k}")
print("=" * 60)