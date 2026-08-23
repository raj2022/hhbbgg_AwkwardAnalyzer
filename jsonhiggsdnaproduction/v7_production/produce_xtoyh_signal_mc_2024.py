import os
import subprocess

# Initialize VOMS proxy
print("Initializing VOMS proxy...")
subprocess.run("voms-proxy-init --rfc --voms cms -valid 192:00", shell=True, check=True)
#outbase_dir = "/eos/user/" + os.environ['USER'][:1] + "/" + os.environ['USER'] + "/HiggsDNA_v7PrelimProd/"
#outbase_dir = "/eos/user/" + os.environ['USER'][:1] + "/" + os.environ['USER'] + "/HiggsDNA_v7_NMSSM/"
#/eos/cms/store/group/phys_b2g/HHbbgg/bsahu/higgsdna_v7_dask/2022preEE/
outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/" + os.environ['USER'] + "/HiggsDNA_v7_dask/"
extra_dir = ""

# Full (mX, mY) grid intended for this analysis, respecting the phase-space
# constraint mY < mX - mH. Uncomment/fill in mX blocks as each is confirmed
# in DAS -- don't submit an mX block you haven't pre-flight-checked.
NMSSM_Samples = {
    #240: [50, 60, 70, 80, 90, 95, 100],
    # 240: [90, 95, 100],
    #280: [50, 60, 70, 80, 90, 95, 100, 125, 150],
    300: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],   # verified in DAS: 10/10 OK
    # 320: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170],
    # 350: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200],
    # 400: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250],
    #450: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300],
    #500: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    #550: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
    #600: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    #650: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    #700: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    #750: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    #800: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
    #850: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    #900: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    #950: [50, 60, 70, 80, 90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    # 1000: verified against real resolved xrootd files -- these are the ACTUAL
    # mY points that exist (no 50/60/70/80 for this mX, unlike the others above)
    1000: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}
    
CAMPAIGN = "Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2"

samples = []
for mX, mY_list in NMSSM_Samples.items():
    for mY in mY_list:
        samples.append({
            "keyword": f"NMSSM_X{mX}_Y{mY}",
            "cmsdas": f"/NMSSM_XtoYHto2B2G_MX-{mX}_MY-{mY}_TuneCP5_13p6TeV_madgraph-pythia8/{CAMPAIGN}/NANOAODSIM",
            "year": "2022postEE",   # era-qualified -- produce_one_mc.py rejects bare "2022"
            "nano": "12",
        })

print(f"Total samples in grid: {len(samples)}")

# --- Pre-flight check: confirm every dataset actually exists in DAS before
#     submitting anything. Catches a wrong campaign tag for an unverified
#     mX block before it wastes a Condor submission cycle.
print("\nChecking dataset existence in DAS...")
missing = []
for sample in samples:
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
    print(f"\n{len(missing)} of {len(samples)} datasets did not resolve in DAS:")
    for k in missing:
        print(f"  - {k}")
    print("\nFix the campaign tag / naming for these before proceeding.")
    print("Not submitting any jobs -- rerun after fixing.")
    raise SystemExit(1)

print("\nAll datasets confirmed in DAS. Proceeding with submission.\n")

# --- Submission -- same sequential per-sample pattern as produce_all_data.py ---
for sample in samples:
    year_folder = sample['year'][:4]   # "2022"
    era_folder = sample['year'][4:]    # "postEE"
    parent_dir = outbase_dir + "/" + year_folder + "/sim/" + era_folder + "/" + extra_dir

    print(f"Creating directory: {parent_dir}")
    os.makedirs(parent_dir, exist_ok=True)
    os.chmod(parent_dir, 0o777)
    command = f"python submission/tools_HHbbgg/produce_one_mc.py --keyword {sample['keyword']} --cmsdas {sample['cmsdas']} --parent-dir {parent_dir} --year {sample['year']} --nano {sample['nano']}   --memory 30GB "
    print(f"Executing: {command}")
    subprocess.run(command, shell=True, check=True)

print("All jobs have been executed successfully.")