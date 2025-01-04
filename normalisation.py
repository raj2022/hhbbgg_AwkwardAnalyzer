import os
def getXsec(samplename):
    sampdlename = str(samplename).split("/")[-1].replace(".root", "").strip()
    print(f"Extracted sample name: '{samplename}'")  # Debugging line

    #samplename = str(samplename).split("/")[-1]
    # Branching ratio
    BR_HToGG = 2.270e-03
    BR_HTobb = 5.824e-01
    BR_HTogg = 2.270e-03  # https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR
    #if samplename in nmssm_samples:
    if "NMSSM_X" in samplename:
        xsec = 1.0
    elif "GGJets" in samplename:
        xsec = 88.75
    elif "GJetPt20to40" in samplename:
        xsec = 242.5
    elif "GJetPt40" in samplename:
        xsec = 919.1
    elif "GluGluHtoGG" in samplename:
        xsec = 52.23 * BR_HToGG
    elif "ttHToGG" in samplename:
        xsec = 0.0013
    elif "VBFHToGG" in samplename:
        xsec = 0.00926
    elif "VHToGG" in samplename:
        xsec = 0.00545
    else:
        raise ValueError("cross-section not found")
    return xsec

def getLumi():
    integrated_luminosities = {
        "Data_EraE": 5.8070,
        "Data_EraF": 17.7819,
        "Data_EraG": 3.0828,
    }
    # Total integrated luminosity
    total_integrated_luminosity = sum(integrated_luminosities.values())
    return total_integrated_luminosity

