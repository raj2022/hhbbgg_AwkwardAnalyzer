#!/usr/bin/env python3

import pyarrow.parquet as pq
import sys
from pathlib import Path

# ----------------------------
# CONFIG
# ----------------------------
PARQUET_FILE = "/eos/user/b/bsahu/HiggsDNA_v4PrelimProd/2024/merged/NMSSM-XtoYH-MX-300-MY-100/NOTAG_merged.parquet"

# REQUIRED variables from analyzer
REQUIRED_COLUMNS = [
    "run","lumi","event",

    "puppiMET_pt","puppiMET_phi",
    "puppiMET_phiJERDown","puppiMET_phiJERUp",
    "puppiMET_phiJESDown","puppiMET_phiJESUp",
    "puppiMET_phiUnclusteredDown","puppiMET_phiUnclusteredUp",
    "puppiMET_ptJERDown","puppiMET_ptJERUp",
    "puppiMET_ptJESDown","puppiMET_ptJESUp",
    "puppiMET_ptUnclusteredDown","puppiMET_ptUnclusteredUp",
    "puppiMET_sumEt",

    "Res_lead_bjet_pt","Res_lead_bjet_eta","Res_lead_bjet_phi","Res_lead_bjet_mass",
    "Res_sublead_bjet_pt","Res_sublead_bjet_eta","Res_sublead_bjet_phi","Res_sublead_bjet_mass",

    "lead_pt","lead_eta","lead_phi",
    "lead_mvaID_WP90","lead_mvaID_WP80",
    "sublead_pt","sublead_eta","sublead_phi",
    "sublead_mvaID_WP90","sublead_mvaID_WP80",

    "weight","weight_central",

    "Res_lead_bjet_btagPNetB","Res_sublead_bjet_btagPNetB",
    "Res_lead_bjet_PNetRegPtRawRes","Res_sublead_bjet_PNetRegPtRawRes",

    "lead_isScEtaEB","sublead_isScEtaEB",

    "Res_HHbbggCandidate_pt","Res_HHbbggCandidate_eta",
    "Res_HHbbggCandidate_phi","Res_HHbbggCandidate_mass",

    "Res_CosThetaStar_CS","Res_CosThetaStar_gg","Res_CosThetaStar_jj",
    "Res_DeltaR_jg_min",

    "Res_pholead_PtOverM","Res_phosublead_PtOverM",
    "Res_FirstJet_PtOverM","Res_SecondJet_PtOverM",

    "lead_mvaID","sublead_mvaID",

    "Res_DeltaR_j1g1","Res_DeltaR_j2g1",
    "Res_DeltaR_j1g2","Res_DeltaR_j2g2",

    "Res_M_X",
    "Res_DeltaPhi_j1MET","Res_DeltaPhi_j2MET",

    "Res_chi_t0","Res_chi_t1",

    "lepton1_mvaID","lepton1_pt","lepton1_pfIsoId",
    "n_jets",

    "pDNN_score",
]

# ----------------------------
# MAIN
# ----------------------------
def main():
    parquet_path = Path(PARQUET_FILE)
    if not parquet_path.exists():
        print(f"❌ File not found: {parquet_path}")
        sys.exit(1)

    pf = pq.ParquetFile(parquet_path)
    available = sorted(pf.schema.names)
    required  = sorted(REQUIRED_COLUMNS)

    missing = sorted(set(required) - set(available))
    extra   = sorted(set(available) - set(required))

    print("\n==============================")
    print(" Parquet Variable Inspection ")
    print("==============================")
    print(f"File: {parquet_path}")
    print(f"Total variables in file: {len(available)}")

    print("\n--- Available variables ---")
    for v in available:
        print(v)

    print("\n--- ❌ Missing required variables ---")
    if missing:
        for v in missing:
            print(v)
    else:
        print("None 🎉")

    print("\n--- ℹ️ Extra variables (not used by analyzer) ---")
    if extra:
        for v in extra:
            print(v)
    else:
        print("None")

    # Optional: write to files
    with open("available_vars.txt", "w") as f:
        f.write("\n".join(available))
    with open("missing_vars.txt", "w") as f:
        f.write("\n".join(missing))
    with open("extra_vars.txt", "w") as f:
        f.write("\n".join(extra))

    print("\n📁 Written:")
    print("  available_vars.txt")
    print("  missing_vars.txt")
    print("  extra_vars.txt")


if __name__ == "__main__":
    main()
