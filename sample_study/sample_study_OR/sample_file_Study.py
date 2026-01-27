import uproot

up = uproot.open("outputfiles/hhbbgg_analyzer-v2-histograms.root")

# print top-level directories
print("Top-level samples:")
for k in up.keys():
    print(k)

sample = "Data_EraF"   # pick one that exists
print("\nRegions in", sample)
for k in up[sample].keys():
    print(k)


region = "srbbgg"
print("\nVariables in", sample, region)
for k in up[f"{sample}/{region}"].keys():
    print(k)


