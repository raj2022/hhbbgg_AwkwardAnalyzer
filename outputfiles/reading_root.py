#!/usr/bin/env python3
# ============================================================
# Inspect TTrees: entries + branches
# ============================================================

import uproot
import pandas as pd

root_file = "merged/DD_CombinedAll/hhbbgg_analyzer-v2-trees.root"

# Explicit tree list (exactly what you pasted)
tree_names = [
    # "DDQCDGJets/processed_events;1",
    "DDQCDGJets/preselection;1",
    "DDQCDGJets/selection;1",
    "DDQCDGJets/srbbgg;1",
    "DDQCDGJets/srbbggMET;1",
    "DDQCDGJets/crantibbgg;1",
    "DDQCDGJets/crbbantigg;1",
    "DDQCDGJets/crantibbantigg;1",
    "DDQCDGJets/sideband;1",
    "DDQCDGJets/idmva_sideband;1",
    "DDQCDGJets/idmva_presel;1",
    # "Data_RunC_EG0_NOTAG_merged/processed_events;1",
    "Data_RunC_EG0_NOTAG_merged/preselection;1",
    "Data_RunC_EG0_NOTAG_merged/selection;1",
    # "Data_RunC_EG0_NOTAG_merged/srbbgg;1",
]

rows = []

with uproot.open(root_file) as f:
    for tree_name in tree_names:
        print(f"\n=== {tree_name} ===")
        tree = f[tree_name]

        nentries = tree.num_entries
        branches = list(tree.keys())

        print(f"Entries  : {nentries}")
        print(f"Branches : {len(branches)}")

        for br in branches:
            rows.append({
                "tree": tree_name,
                "branch": br
            })

# Save branch list
df = pd.DataFrame(rows)
df.to_csv("tree_branch_list.csv", index=False)

print("\nSaved branch list to tree_branch_list.csv")
