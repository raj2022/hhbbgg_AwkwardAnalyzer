# import os
# def getXsec(samplename):
#     sampdlename = str(samplename).split("/")[-1].replace(".root", "").strip()
#     print(f"Extracted sample name: '{samplename}'")  # Debugging line

#     #samplename = str(samplename).split("/")[-1]
#     # Branching ratio
#     BR_HToGG = 2.270e-03
#     BR_HTobb = 5.824e-01
#     BR_HTogg = 2.270e-03  # https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR
#     #if samplename in nmssm_samples:
#     if "NMSSM_X" in samplename:
#         xsec = 1.0
#     elif "GluGluToHH" in samplename:
#         xsec = 1.0
#     elif "GGJets" in samplename:
#         xsec = 88.75
#     elif "GJetPt20To40" in samplename:
#         xsec = 242.5
#     elif "GJetPt40" in samplename:
#         xsec = 919.1
#     elif "GluGluHToGG" in samplename:
#         xsec = 52.23 * BR_HToGG
#     elif "ttHToGG" in samplename:
#         xsec = 0.0013
#     elif "VBFHToGG" in samplename:
#         xsec = 0.00926
#     elif "VHToGG" in samplename:
#         xsec = 0.00545
#     elif "QCD_PT-30To40" in samplename:
#         xsec = 25950
#     elif "QCD_PT-30ToInf"  in samplename:
#         xsec = 252200
#     elif "QCD_PT-40ToInf"  in samplename:
#         xsec = 124700
#     elif "DDQCDGJET" in samplename:   # Data-driven bkg estiamtion
#         xsec = 1
#     else:
#         raise ValueError("cross-section not found")
#     return xsec

# def getLumi():
#     integrated_luminosities = {
#         # Data eras in fb^-1 (from https://twiki.cern.ch/twiki/bin/view/CMS/PdmV2016Data)
#         "Data_EraC": 5.0104,
#         "Data_EraD": 2.9700,
#         "Data_EraE": 5.8070,
#         "Data_EraF": 17.7819,
#         "Data_EraG": 3.0828,
#         # Data eras : 2023 
#         "Data_EraC_2023": 17.794,
#         "Data_EraD_2023": 9.451,
        
#     }
#     # Total integrated luminosity
#     total_integrated_luminosity = sum(integrated_luminosities.values())
#     return total_integrated_luminosity


# normalisation.py
import os

# --- Branching ratios if needed ---
BR_HToGG = 2.270e-03
BR_HTobb = 5.824e-01

# ---------------------------------------------------------------------
# Cross sections (pb)
# Matching is case-insensitive; we also strip '_' and '-' in the filename.
# Adjust numeric values to your official ones if needed.
# ---------------------------------------------------------------------
XSEC_PATTERNS = [
    # NMSSM / signals
    ("nmssm_x",               1.0),
    ("gluglutohh",            1.0),

    # Prompt photon backgrounds (from your file list)
    ("ggjetsmgg40to80",      88.75),
    ("ggjetsmgg80",          88.75),   # change if you use a different xsec for MGG-80(need to be confirmed)
    ("gjetpt20to40",        242.5),
    ("gjetpt40",            919.1),

    # Higgs -> gamma gamma
    ("glugluh to gg", 52.23 * BR_HToGG),  # safety: if spaces/typos appear
    ("glugluhtogg",   52.23 * BR_HToGG),  # matches "GluGluHtoGG" / "GluGluHToGG"

    # ttH, VBFH, VH (gamma gamma)
    ("tthtogg",         0.0013),   # matches ttHtoGG / ttHToGG
    ("vbfhtogg",        0.00926),  # matches VBFHtoGG / VBFHToGG
    ("vhtogg",          0.00545),  # matches VHtoGG / VHToGG
    ("ttgg",           1.0), 
    ("ttg",           1.0),

    # QCD (match your files: QCDPt30To40, QCDPt40ToInf)
    ("qcdpt30to40",    25950.0),
    ("qcdpt40toinf",  124700.0),
    ("qcdpt30toinf",  252200.0),   # only if such a sample exists
    # Data-driven template
    ("ddqcdgjet",          1.0),
    ("_rescaled",           1.0),
    ("ggjets_low_rescaled", 1.0),
    ("ggjets_high_rescaled",1.0),
]

def _norm_name_for_match(path_or_name: str) -> str:
    base = os.path.basename(str(path_or_name)).lower()
    # strip common separators for easier matching
    base = base.replace("_", "").replace("-", "").replace(".parquet", "").replace(".root", "")
    return base

def getXsec(path_or_name) -> float:
    """Return cross-section (pb) by matching substrings in the filename."""
    base = _norm_name_for_match(path_or_name)
    for key, val in XSEC_PATTERNS:
        if key in base:
            return float(val)
    # Default: 1.0 to avoid crash (or raise if you prefer strict behavior)
    # raise ValueError(f"Cross-section not found for: {os.path.basename(str(path_or_name))}")
    return 1.0

# ---------------------------------------------------------------------
# Luminosities (fb^-1)
# 2022: C,D = PreEE ; E,F,G = PostEE
# 2023: your provided numbers: Era C = 17.794, Era D = 9.451
# ---------------------------------------------------------------------
LUMI_2022 = {
    "C": 5.0104,
    "D": 2.9700,
    "E": 5.8070,
    "F": 17.7819,
    "G": 3.0828,
}
LUMI_2023 = {
    # From your message
    "C": 17.794,   # preBPix
    "D": 9.451,    # postBPix
}

def getLumi(year=None, era=None) -> float:
    """
    Return luminosity in fb^-1 for the given year/era.
    - 2022 PreEE = C + D
      2022 PostEE = E + F + G
    - 2023 preBPix = C
      2023 postBPix = D
    If year/era not given, returns total of known periods for that year.
    """
    y = str(year) if year is not None else None
    e = str(era).lower() if era is not None else None

    if y == "2022":
        if e in ("preee", "pre"):
            return LUMI_2022["C"] + LUMI_2022["D"] 
        if e in ("postee", "post"):
            return LUMI_2022["E"] + LUMI_2022["F"] + LUMI_2022["G"]
        return sum(LUMI_2022.values())

    if y == "2023":
        if e in ("prebpix", "pre"):
            return LUMI_2023["C"]
        if e in ("postbpix", "post"):
            return LUMI_2023["D"]
        return sum(LUMI_2023.values())

    # Fallback if unknown
    return 1.0
