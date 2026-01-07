# #!/usr/bin/env python3
# import json, sys, os
# import uproot, awkward as ak
# import numpy as np

# ROOT = sys.argv[1] if len(sys.argv)>1 else "../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root"
# EDGES_JSON = sys.argv[2] if len(sys.argv)>2 else "outputs/categories_alpha/event_categories.json"
# TREE_NAME = "selection"
# BR_SCORE  = "pDNN_score"
# BR_ISDATA = "isdata"
# DEFAULT_MJJ = "dibjet_mass"

# print("File:", ROOT)
# with open(EDGES_JSON) as f:
#     edges = sorted(json.load(f)["boundaries"]["combined"])
# print("Loaded edges (combined):", edges)

# def collect_dirs(fin):
#     return [k.split(";")[0] for k in fin.keys()
#             if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

# def group_of(name: str):
#     n = name.lower()
#     if "tth" in n: return "ttH"
#     if "ggh" in n or "vbfh" in n or "vbf" in n: return "ggH+VBFH"
#     if "wh" in n or "zh" in n or "vh" in n: return "VH"
#     return None

# with uproot.open(ROOT) as fin:
#     dirs = collect_dirs(fin)
#     print("\nTop-level directories ({}):".format(len(dirs)))
#     for d in dirs:
#         print("  ", d)
#     print()

#     # Summary counters
#     summary = {}
#     for d in dirs:
#         grp = group_of(d) or "OTHER"
#         tdir = fin[d]
#         sel_key = None
#         for k in tdir.keys():
#             if k.split(";")[0] == TREE_NAME:
#                 sel_key = k
#                 break
#         if sel_key is None:
#             print(f"[skip] {d}: no tree named '{TREE_NAME}'")
#             continue

#         tree = tdir[sel_key]
#         branches = list(tree.keys())
#         print(f"\nDirectory: {d}  -> group: {grp}")
#         print("  Tree key:", sel_key)
#         print("  Branches (sample):", branches[:30])
#         # check presence of the branches we expect
#         has_mjj = DEFAULT_MJJ in branches
#         has_score = BR_SCORE in branches
#         has_isdata = BR_ISDATA in branches
#         print(f"  Has branches? mjj('{DEFAULT_MJJ}')={has_mjj}, score('{BR_SCORE}')={has_score}, isdata('{BR_ISDATA}')={has_isdata}")
#         if not (has_mjj and has_score):
#             print("  -> missing required branches, skipping further checks for this dir.")
#             continue

#         # read small sample to get ranges and counts (fast)
#         arr = tree.arrays([DEFAULT_MJJ, BR_SCORE, BR_ISDATA], entry_stop=200000, library="ak")
#         mjj = ak.to_numpy(arr[DEFAULT_MJJ])
#         score = ak.to_numpy(arr[BR_SCORE])
#         isdata = ak.to_numpy(arr[BR_ISDATA]) if BR_ISDATA in arr.fields else None

#         print("  Sample size read:", len(mjj))
#         if len(mjj)==0:
#             print("  -> tree empty")
#             continue

#         print(f"   mjj: min={mjj.min():.3f}, max={mjj.max():.3f}")
#         print(f"   score: min={score.min():.3f}, max={score.max():.3f}")
#         if isdata is not None:
#             print(f"   isdata unique values: {np.unique(isdata)[:10]} (showing up to 10)")

#         # count MC entries (isdata == 0) and entries in mjj window / any score window
#         mc_mask = (isdata == 0) if isdata is not None else np.ones_like(mjj, dtype=bool)
#         nmcc = mc_mask.sum()
#         in_mjj_range = (mjj >= 90) & (mjj <= 200)
#         n_in_mjj_mc = np.sum(mc_mask & in_mjj_range)
#         print(f"   MC entries in sample: {int(nmcc)}; MC with 90<=mjj<=200: {int(n_in_mjj_mc)}")

#         # check score boundaries vs edges
#         lo_all = -1e9
#         hi_all = 1e9
#         cat_any_mask = np.zeros_like(score, dtype=bool)
#         edges_full = [-np.inf] + edges + [np.inf]
#         for i in range(len(edges_full)-1):
#             lo, hi = edges_full[i], edges_full[i+1]
#             cat_any_mask |= (score >= lo) & (score < hi)
#         print("   fraction of entries inside any category window (score):", float(cat_any_mask.sum())/len(score))

#         summary.setdefault(grp,0)
#         summary[grp] += len(mjj)

#     print("\nSummary (total entries per group in checked sample):")
#     for k,v in summary.items():
#         print("  ", k, v)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple ROOT reader: plots dibjet_mass for ggH+VBFH, ttH, VH groups.
 - No command-line arguments
 - No isdata filtering
 - Reads all entries and plots per-group + overlay histograms
"""
import os
import numpy as np
import uproot
import awkward as ak
import matplotlib.pyplot as plt

ROOT_FILE = "../../../outputfiles/merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root"
TREE_NAME = "selection"
MJJ_BRANCH = "dibjet_mass"

# --- Helpers ---
def collect_dirs(fin):
    return [k.split(";")[0] for k in fin.keys()
            if isinstance(fin[k], uproot.reading.ReadOnlyDirectory)]

def get_tree_key(tdir, base):
    for tkey in tdir.keys():
        if tkey.split(";")[0] == base:
            return tkey
    return None

def group_of(name: str):
    n = name.lower()
    if "tth" in n: return "ttH"
    if "ggh" in n or "vbfh" in n or "vbf" in n: return "ggH+VBFH"
    if "wh" in n or "zh" in n or "vh" in n: return "VH"
    return None

# --- Collect and plot ---
groups = {"ttH": [], "ggH+VBFH": [], "VH": []}
counts = {k: 0 for k in groups}

with uproot.open(ROOT_FILE) as fin:
    for d in collect_dirs(fin):
        grp = group_of(d)
        if grp is None:
            continue
        tdir = fin[d]
        sel = get_tree_key(tdir, TREE_NAME)
        if sel is None:
            continue
        tree = tdir[sel]

        if MJJ_BRANCH not in tree.keys():
            print(f"[skip] {d}: no branch {MJJ_BRANCH}")
            continue

        arr = tree.arrays([MJJ_BRANCH], library="ak")
        mjj = ak.to_numpy(arr[MJJ_BRANCH])

        # remove invalid entries
        mjj = mjj[np.isfinite(mjj)]
        mjj = mjj[mjj > -9000]

        if mjj.size == 0:
            continue

        groups[grp].append(mjj)
        counts[grp] += mjj.size

# concatenate arrays
for g in list(groups.keys()):
    if groups[g]:
        groups[g] = np.concatenate(groups[g])
    else:
        groups[g] = np.array([])

print("Entries per group:")
for g, n in counts.items():
    print(f"  {g}: {n}")

# --- Plotting ---
outdir = "outputs/plots_mjj_simple_no_isdata"
os.makedirs(outdir, exist_ok=True)

# Range from combined data
all_mjj = np.concatenate([v for v in groups.values() if v.size > 0]) if any(v.size>0 for v in groups.values()) else np.array([0.0])
if all_mjj.size > 1:
    p1, p99 = np.percentile(all_mjj, [1, 99])
    xmin = max(0.0, float(p1) - 5.0)
    xmax = float(p99) + 5.0
else:
    xmin, xmax = 0.0, 2000.0

bins = np.linspace(xmin, xmax, 80)

# individual plots
for grp, arr in groups.items():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if arr.size > 0:
        ax.hist(arr, bins=bins, histtype="stepfilled", alpha=0.6, label=f"{grp} (N={arr.size})")
    else:
        ax.text(0.5, 0.5, "No entries", ha="center", va="center")
    ax.set_xlabel("dibjet_mass [GeV]")
    ax.set_ylabel("Events")
    ax.set_title(f"{grp} — dibjet_mass")
    ax.grid(alpha=0.25)
    ax.legend()
    fn = f"{outdir}/mjj_{grp}.png"
    fig.tight_layout()
    fig.savefig(fn, dpi=150)
    plt.close(fig)
    print("Wrote", fn)

# overlay plot
fig, ax = plt.subplots(figsize=(8, 5))
colors = {"ggH+VBFH": "tab:blue", "ttH": "tab:orange", "VH": "tab:green"}
for grp, arr in groups.items():
    if arr.size > 0:
        ax.hist(arr, bins=bins, histtype="step", lw=1.5,
                label=f"{grp} (N={arr.size})", color=colors.get(grp, None))
ax.set_xlabel("dibjet_mass [GeV]")
ax.set_ylabel("Events")
ax.set_title("dibjet_mass — overlay")
ax.grid(alpha=0.25)
ax.legend()
fn = f"{outdir}/mjj_overlay.png"
fig.tight_layout()
fig.savefig(fn, dpi=150)
plt.close(fig)
print("Wrote", fn)

print(f"✅ Finished. Plots saved in '{outdir}'")
