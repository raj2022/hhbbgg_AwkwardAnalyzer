# #!/usr/bin/env python3

# import uproot
# import numpy as np
# from hist import Hist

# ROOT_FILE = "/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/2024_All/hhbbgg_analyzer-v2-histograms.root"

# # -------------------------------
# # Helpers
# # -------------------------------
# def clean(name):
#     return name.split(";")[0]

# def print_header(title):
#     print("\n" + "=" * 80)
#     print(title)
#     print("=" * 80)

# def hist_integral(up, path):
#     try:
#         h = Hist(up[path])
#         return float(np.sum(h.values()))
#     except Exception as e:
#         return None

# # -------------------------------
# # Open ROOT file
# # -------------------------------
# print_header("OPENING ROOT FILE")
# up = uproot.open(ROOT_FILE)
# print("File opened successfully")

# # -------------------------------
# # 1) List all top-level samples
# # -------------------------------
# print_header("TOP-LEVEL DIRECTORIES (SAMPLES)")
# samples = [clean(k) for k in up.keys()]
# for s in samples:
#     print(" ", s)

# # -------------------------------
# # 2) Check presence of key samples
# # -------------------------------
# print_header("CHECKING EXPECTED SAMPLES")

# expected = [
#     "GGJets",
#     "GJetPt20To40",
#     "GJetPt40",
#     "QCD_PT-30to40",
#     "QCD_PT-30toInf",
#     "QCD_PT-40toInf",
#     "TTGG",
#     "TTG",
# ]

# for s in expected:
#     status = "✅ FOUND" if s in samples else "❌ MISSING"
#     print(f"{s:20s} : {status}")

# # -------------------------------
# # 3) Inspect directory structure of each sample
# # -------------------------------
# print_header("SAMPLE → REGIONS")

# for s in samples:
#     try:
#         regions = [clean(k) for k in up[s].keys()]
#         print(f"\n{s}:")
#         for r in regions:
#             print("  ", r)
#     except Exception:
#         print(f"\n{s}: ❌ NOT A DIRECTORY")

# # -------------------------------
# # 4) Inspect histograms in one reference region
# # -------------------------------
# REFERENCE_REGION = "preselection"

# print_header(f"HISTOGRAMS IN REGION '{REFERENCE_REGION}'")

# for s in samples:
#     path = f"{s}/{REFERENCE_REGION}"
#     if path not in up:
#         print(f"\n{s}: ❌ region '{REFERENCE_REGION}' not found")
#         continue

#     print(f"\n{s}/{REFERENCE_REGION}:")
#     hists = [clean(k) for k in up[path].keys()]
#     for h in hists[:20]:
#         print("  ", h)
#     if len(hists) > 20:
#         print("   ...")

# # -------------------------------
# # 5) Check integrals of key histograms
# # -------------------------------
# print_header("CHECKING HISTOGRAM INTEGRALS")

# test_hists = [
#     "dibjet_mass",
#     "diphoton_mass",
#     "bbgg_phi",
# ]

# test_samples = [
#     "GGJets",
#     "QCD_PT-30to40",
#     "QCD_PT-30toInf",
#     "QCD_PT-40toInf",
# ]

# for s in test_samples:
#     print(f"\nSample: {s}")
#     for h in test_hists:
#         path = f"{s}/{REFERENCE_REGION}/{h}"
#         integral = hist_integral(up, path)
#         if integral is None:
#             print(f"  {h:20s}: ❌ NOT FOUND")
#         else:
#             print(f"  {h:20s}: integral = {integral:.4e}")

# # -------------------------------
# # 6) Summary verdict
# # -------------------------------
# print_header("SUMMARY")

# print("""
# Interpretation guide:

# ❌ Sample missing entirely:
#    → Analyzer did not write it or wrong input files

# ❌ Region missing:
#    → Selection logic or region naming mismatch

# ❌ Histogram missing:
#    → vardict mismatch OR histogram never booked

# Integral = 0:
#    → Sample processed but no events pass selections

# Non-zero integral:
#    → Sample is healthy, plotting logic should work
# """)

# print("Done.")



import uproot

root_file = "/afs/cern.ch/user/s/sraj/Analysis/hhbbgg_AwkwardAnalyzer/outputfiles/merged/2023_All/hhbbgg_analyzer-v2-histograms.root"
up = uproot.open(root_file)

print("\n==============================")
print("TOP-LEVEL SAMPLES")
print("==============================")
samples = [k.split(";")[0] for k in up.keys()]
for s in samples:
    print(" ", s)

print("\n==============================")
print("REGIONS PER SAMPLE")
print("==============================")
for s in samples:
    obj = up[s]
    if not hasattr(obj, "keys"):
        continue
    regions = [k.split(";")[0] for k in obj.keys()]
    print(f"\n{s}:")
    for r in regions:
        print("  ", r)

print("\n==============================")
print("HISTOGRAMS PER REGION (first sample)")
print("==============================")
first_sample = samples[0]
for r in up[first_sample].keys():
    rname = r.split(";")[0]
    print(f"\n{first_sample}/{rname}:")
    for h in up[first_sample][rname].keys():
        print("   ", h.split(";")[0])
