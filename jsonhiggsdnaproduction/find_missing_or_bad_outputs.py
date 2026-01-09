import json
import os
import subprocess

json_file = "My_Json_300.json"
eos_out = "/eos/user/s/sraj/Work_/CUA_20--/Analysis/output_parquet/systematics_v3/2022_postEE/"
min_size_mb = 1.0

def eos_ls(path):
    return subprocess.check_output(["eos", "ls", path], text=True).split()

def eos_size(path):
    out = subprocess.check_output(["eos", "stat", path], text=True)
    for line in out.splitlines():
        if "Size" in line:
            return int(line.split()[-1])
    return 0

with open(json_file) as f:
    js = json.load(f)

# -------- FIND DATASETS ROBUSTLY --------
datasets = []

if "samples" in js:
    datasets = list(js["samples"].keys())
elif "datasets" in js:
    datasets = list(js["datasets"].keys())
else:
    # assume datasets are top-level keys
    datasets = [k for k, v in js.items() if isinstance(v, dict)]

print(f"Found {len(datasets)} datasets in JSON")

missing = []
bad = []

for ds in datasets:
    outdir = os.path.join(eos_out, ds)
    try:
        files = eos_ls(outdir)
    except subprocess.CalledProcessError:
        missing.append(ds)
        continue

    parquet_files = [f for f in files if f.endswith(".parquet")]
    if not parquet_files:
        missing.append(ds)
        continue

    for pf in parquet_files:
        size_mb = eos_size(os.path.join(outdir, pf)) / 1024 / 1024
        if size_mb < min_size_mb:
            bad.append(f"{ds}/{pf}")

print("\n==== MISSING DATASETS ====")
for m in missing:
    print(m)

print("\n==== BAD / EMPTY PARQUETS ====")
for b in bad:
    print(b)
