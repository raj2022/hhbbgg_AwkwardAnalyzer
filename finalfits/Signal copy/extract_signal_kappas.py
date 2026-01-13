# import ROOT, json

# f = ROOT.TFile.Open("../../../outputfiles/2022_All/systematics/histograms.root")

# def get_kappa_mean(path_nom, path_up):
#     h0 = f.Get(path_nom)
#     h1 = f.Get(path_up)
#     return abs(h1.GetMean() - h0.GetMean()) / h0.GetMean()

# def get_kappa_width(path_nom, path_up):
#     h0 = f.Get(path_nom)
#     h1 = f.Get(path_up)
#     return abs(h1.GetRMS() - h0.GetRMS()) / h0.GetRMS()

# out = {}

# samples = ["NMSSM_X1000_Y125"]  # extend later
# cats = ["selection"]            # or per-category later

# for s in samples:
#     out[s] = {}
#     for cat in cats:
#         base = f"{s}/{cat}"

#         out[s]["mgg_scale"] = get_kappa_mean(
#             f"{base}/diphoton_mass",
#             f"{base}/diphoton_mass__ScaleEE2G_IJazZ_up"
#         )

#         out[s]["mgg_smear"] = get_kappa_width(
#             f"{base}/diphoton_mass",
#             f"{base}/diphoton_mass__Smearing2G_IJazZ_up"
#         )

#         out[s]["mjj_jec_mu"] = get_kappa_mean(
#             f"{base}/dibjet_mass",
#             f"{base}/dibjet_mass__jec_syst_Total_up"
#         )

#         out[s]["mjj_jec_sig"] = get_kappa_width(
#             f"{base}/dibjet_mass",
#             f"{base}/dibjet_mass__jec_syst_Total_up"
#         )

#         out[s]["mjj_jer_sig"] = get_kappa_width(
#             f"{base}/dibjet_mass",
#             f"{base}/dibjet_mass__jer_syst_up"
#         )

# with open("outputs/systematics/signal_kappas.json", "w") as fout:
#     json.dump(out, fout, indent=2)

# print("Wrote signal_kappas.json")





#-----------------------------------------------------------------------------
# Cahnging script for all mass 
# ----------------------------------------



import ROOT
import json
import argparse
import os
import sys

# -----------------------
# Arguments
# -----------------------
parser = argparse.ArgumentParser(description="Produce signal kappa systematics")
parser.add_argument("--mX", type=int, required=True, help="Heavy resonance mass X")
parser.add_argument("--mY", type=int, required=True, help="Intermediate resonance mass Y")
parser.add_argument("--cat", type=str, default="selection")
parser.add_argument(
    "--infile",
    type=str,
    default="../../../outputfiles/2022_All/systematics/histograms.root",
)
parser.add_argument(
    "--outfile",
    type=str,
    default="outputs/systematics/signal_kappas.json",
)
args = parser.parse_args()

# -----------------------
# Open ROOT file
# -----------------------
f = ROOT.TFile.Open(args.infile)
if not f or f.IsZombie():
    raise RuntimeError(f"Could not open input file: {args.infile}")

# -----------------------
# Helpers
# -----------------------
def get_hist(path):
    h = f.Get(path)
    if not h:
        raise RuntimeError(f"Missing histogram: {path}")
    return h

def get_kappa_mean(path_nom, path_up):
    h0 = get_hist(path_nom)
    h1 = get_hist(path_up)
    if h0.GetMean() == 0:
        return 0.0
    return abs(h1.GetMean() - h0.GetMean()) / h0.GetMean()

def get_kappa_width(path_nom, path_up):
    h0 = get_hist(path_nom)
    h1 = get_hist(path_up)
    if h0.GetRMS() == 0:
        return 0.0
    return abs(h1.GetRMS() - h0.GetRMS()) / h0.GetRMS()

# -----------------------
# Sample definition
# -----------------------
sample = f"NMSSM_X{args.mX}_Y{args.mY}"
cat = args.cat
base = f"{sample}/{cat}"

out = {sample: {}}

# -----------------------
# Kappas
# -----------------------
out[sample]["mgg_scale"] = get_kappa_mean(
    f"{base}/diphoton_mass",
    f"{base}/diphoton_mass__ScaleEE2G_IJazZ_up",
)

out[sample]["mgg_smear"] = get_kappa_width(
    f"{base}/diphoton_mass",
    f"{base}/diphoton_mass__Smearing2G_IJazZ_up",
)

out[sample]["mjj_jec_mu"] = get_kappa_mean(
    f"{base}/dibjet_mass",
    f"{base}/dibjet_mass__jec_syst_Total_up",
)

out[sample]["mjj_jec_sig"] = get_kappa_width(
    f"{base}/dibjet_mass",
    f"{base}/dibjet_mass__jec_syst_Total_up",
)

out[sample]["mjj_jer_sig"] = get_kappa_width(
    f"{base}/dibjet_mass",
    f"{base}/dibjet_mass__jer_syst_up",
)

# -----------------------
# Write output
# -----------------------
# os.makedirs(os.path.dirname(args.outfile), exist_ok=True)
# with open(args.outfile, "w") as fout:
#     json.dump(out, fout, indent=2)

# print(f"[OK] Wrote {args.outfile} for {sample}")

# -----------------------
# Load existing JSON (if any)
# -----------------------
if os.path.exists(args.outfile):
    with open(args.outfile, "r") as fin:
        all_kappas = json.load(fin)
else:
    all_kappas = {}

# Overwrite or add this mass point
all_kappas[sample] = out[sample]

# -----------------------
# Write back
# -----------------------
os.makedirs(os.path.dirname(args.outfile), exist_ok=True)
with open(args.outfile, "w") as fout:
    json.dump(all_kappas, fout, indent=2)

print(f"[OK] Updated {args.outfile} with {sample}")
