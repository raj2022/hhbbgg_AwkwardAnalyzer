import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
CAMPAIGNS = {
    "2022preEE":    "Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2",
    "2022postEE":   "Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2",
    "2023preBPix":  "Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v2",
    "2023postBPix": "Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2",
}
parser.add_argument(
    "--era", choices=CAMPAIGNS.keys(), default="2022postEE",
    help="Which era's campaign to submit against. Default matches existing behavior "
         "(2022postEE) -- running with no flags is unchanged from before.",
)
parser.add_argument(
    "--check", action="store_true",
    help="Skip submission entirely. Just check actual EOS output for every "
         "sample recorded as submitted, and print a status report.",
)
parser.add_argument(
    "--dry-run", action="store_true",
    help="Skip submission entirely. Just DAS-check every sample currently "
         "listed in NMSSM_Samples (including ones already submitted) and "
         "report which resolve, with zero side effects -- no directories "
         "created, no produce_one_mc.py calls, no state file writes. Safe "
         "to run in a second terminal while a real submission is in progress.",
)
args = parser.parse_args()

outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/" + os.environ['USER'] + "/HiggsDNA_v7_dask/"
extra_dir = ""

STATE_FILE = "nmssm_submission_state.json"

# Full (mX, mY) grid intended for this analysis, respecting the phase-space
# constraint mY < mX - mH. Uncomment/fill in mX blocks as each is confirmed
# in DAS -- don't submit an mX block you haven't pre-flight-checked.
NMSSM_Samples = {
    240: [50, 60, 70, 80, 90, 95, 100],
    280: [50, 60, 70, 80, 90, 95, 100, 125, 150],
    300: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],   # verified in DAS: 10/10 OK
    320: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],
    350: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200],
    400: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250],
    400: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250],
    450: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300],
    500: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    550: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
    600: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    650: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    700: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    750: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    800: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
    850: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    900: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    950: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    # # # 1000: verified against real resolved xrootd files -- these are the ACTUAL
    # # # mY points that exist (no 50/60/70/80 for this mX, unlike the others above)
    1000: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}

campaign = CAMPAIGNS[args.era]

samples = []
for mX, mY_list in NMSSM_Samples.items():
    for mY in mY_list:
        samples.append({
            "keyword": f"NMSSM_X{mX}_Y{mY}",
            "cmsdas": f"/NMSSM_XtoYHto2B2G_MX-{mX}_MY-{mY}_TuneCP5_13p6TeV_madgraph-pythia8/{campaign}/NANOAODSIM",
            "year": args.era,
            "nano": "12",
            "state_key": f"{args.era}:NMSSM_X{mX}_Y{mY}",  # avoids cross-era collision in state file
        })

def parent_dir_for(sample):
    year_folder = sample['year'][:4]   # "2022"
    era_folder = sample['year'][4:]    # "postEE"
    return outbase_dir + "/" + year_folder + "/sim/" + era_folder + "/" + extra_dir

def has_output(sample):
    """
    Recursive check -- real output sits two levels deep, one subfolder per
    systematic variation (<sample>/<variation>/<uuid>_..._Events...parquet, cycle-numbered like Events;2).
    countCondorOutputs.py's single-level glob misses this structure and
    reports a false zero; rglob here checks the actual nested layout.
    """
    sample_dir = Path(parent_dir_for(sample)) / sample["keyword"]
    if not sample_dir.exists():
        return 0
    return len(list(sample_dir.rglob("*.parquet")))

# --- Load prior run state, if any ---
state = {"submitted": [], "failed": []}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)

def migrate_legacy_state_keys(key_list):
    """
    Old state files (before --era support) stored bare keywords, e.g.
    "NMSSM_X850_Y50" -- implicitly 2022postEE, the only era ever run before
    this. Normalize those to the new "era:keyword" format so every lookup
    from here on can assume state_key format consistently.
    """
    return [k if ":" in k else f"2022postEE:{k}" for k in key_list]

state["submitted"] = migrate_legacy_state_keys(state["submitted"])
state["failed"] = migrate_legacy_state_keys(state["failed"])

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ============================================================
# --dry-run mode: DAS check only, zero side effects. Safe to run
# concurrently with a real submission in another terminal.
# ============================================================
if args.dry_run:
    print(f"[DRY RUN] Checking all {len(samples)} sample(s) currently in NMSSM_Samples "
          f"against DAS for --era {args.era}. No submission, no directories, no state changes.\n")
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
        print(f"{len(missing)} did NOT resolve -- check the CAMPAIGN tag for these "
              f"specifically before uncommenting/submitting this mX block:")
        for s in missing:
            print(f"  - {s['keyword']}: {s['cmsdas']}")
    else:
        print("All samples currently in the grid resolve. Safe to submit for real "
              "(rerun without --dry-run).")
    print("=" * 60)
    sys.exit(0)

# ============================================================
# --check mode: no submission, just report actual output status
# ============================================================
if args.check:
    if state["submitted"] or state["failed"]:
        # Normal case: robust script has been used, state file tracks exactly
        # what was submitted through it. Entries are "era:keyword" (legacy
        # bare-keyword entries already migrated to this format on load).
        to_report = state["submitted"]
        source_note = f"tracked in {STATE_FILE}"
    else:
        # No state file at all -- fall back to checking every sample
        # currently defined in NMSSM_Samples, for the era selected via
        # --era, against real EOS output. Can't distinguish "never
        # submitted" from "submitted, still running" from "submitted,
        # failed" in this mode -- only has-output vs. no-output.
        to_report = [s["state_key"] for s in samples]
        source_note = f"no {STATE_FILE} found -- checking all {len(samples)} sample(s) currently in NMSSM_Samples for --era {args.era} instead"
        print(f"[NOTE] {source_note}.\n")

    by_state_key = {s["state_key"]: s for s in samples}
    no_output, has_files = [], []

    print(f"Checking output for {len(to_report)} sample(s) ({source_note})...\n")
    for state_key in to_report:
        sample = by_state_key.get(state_key)
        if sample is None:
            print(f"  [?]        {state_key} -- not in current NMSSM_Samples grid for this era, can't locate")
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
        print(f"\n{len(no_output)} sample(s) with no output on disk yet "
              f"(still running, failed, or never submitted -- can't tell which from output alone):")
        print("Check condor_q and checkCondorErrors.py for these specifically:")
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

ensure_valid_proxy()

print(f"Total samples in grid: {len(samples)}")
if state["submitted"] or state["failed"]:
    print(f"Resuming: {len(state['submitted'])} already submitted, "
          f"{len(state['failed'])} previously failed (will retry failed ones).")
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

# --- Submission -- skip anything already submitted; one failure doesn't
#     stop the rest of the grid; every outcome recorded to STATE_FILE as
#     it happens, so a kill at any point loses nothing already done. ---
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

    command = f"python submission/tools_HHbbgg/produce_one_mc.py --keyword {sample['keyword']} --cmsdas {sample['cmsdas']} --parent-dir {parent_dir} --year {sample['year']} --nano {sample['nano']}   --memory 30GB "
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

    save_state()   # persist after every sample, not just at the end

# --- Summary ---
print("\n" + "=" * 60)
print(f"Done. {len(state['submitted'])} submitted total, {len(state['failed'])} failed.")
if state["failed"]:
    print("Failed samples (rerun this script to retry just these):")
    for k in state["failed"]:
        print(f"  - {k}")
print("=" * 60)