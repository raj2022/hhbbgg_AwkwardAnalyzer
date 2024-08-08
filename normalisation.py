def getXsec(samplename):
    samplename = str(samplename).split("/")[-1].replace(".root", "")
    # Branching ratio
    BR_HToGG = 2.270e-03
    BR_HTobb = 5.824e-01
    BR_HTogg = 2.270e-03  # https://twiki.cern.ch/twiki/bin/view/LHCPhysics/CERNYellowReportPageBR
    
    # List of specific sample names with cross-section 1
    nmssm_samples = [
        "NMSSM_X300_Y100", "NMSSM_X400_Y80", "NMSSM_X550_Y100", "NMSSM_X600_Y80", "NMSSM_X700_Y100",
        "NMSSM_X300_Y60", "NMSSM_X400_Y90", "NMSSM_X550_Y60", "NMSSM_X600_Y90", "NMSSM_X700_Y60",
        "NMSSM_X300_Y70", "NMSSM_X400_Y95", "NMSSM_X550_Y70", "NMSSM_X600_Y95", "NMSSM_X700_Y70",
        "NMSSM_X300_Y80", "NMSSM_X500_Y100", "NMSSM_X550_Y80", "NMSSM_X650_Y100", "NMSSM_X700_Y80",
        "NMSSM_X300_Y90", "NMSSM_X500_Y60", "NMSSM_X550_Y90", "NMSSM_X650_Y60", "NMSSM_X700_Y90",
        "NMSSM_X300_Y95", "NMSSM_X500_Y70", "NMSSM_X550_Y95", "NMSSM_X650_Y70", "NMSSM_X700_Y95",
        "NMSSM_X400_Y100", "NMSSM_X500_Y80", "NMSSM_X600_Y100", "NMSSM_X650_Y80",
        "NMSSM_X400_Y60", "NMSSM_X500_Y90", "NMSSM_X600_Y60", "NMSSM_X650_Y90",
        "NMSSM_X400_Y70", "NMSSM_X500_Y95", "NMSSM_X600_Y70", "NMSSM_X650_Y95"
    ]

    if samplename in nmssm_samples:
        xsec = 1.0
    elif "GGJets" in samplename:
        xsec = 88.75
    elif "GJetPt20To40" in samplename:
        xsec = 242.5
    elif "GJetPt40" in samplename:
        xsec = 919.1
    elif "GluGluHToGG" in samplename:
        xsec = 52.23 * BR_HToGG
    elif "GluGluToHH" in samplename:
        xsec = 34.43 * BR_HTobb * BR_HTogg * 2
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

