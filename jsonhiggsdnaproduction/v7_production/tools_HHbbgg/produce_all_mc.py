import os
import subprocess

# Initialize VOMS proxy
print("Initializing VOMS proxy...")
subprocess.run("voms-proxy-init --rfc --voms cms -valid 192:00", shell=True, check=True)
# outbase_dir = "/eos/user/" + os.environ['USER'][:1] + "/" + os.environ['USER'] + "/HiggsDNA_v7Production/"
outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/"
extra_dir = ""

samples = [

    # Necessary samples
    # GluGlutoHH_kl-1p00_kt-1p00_c2-0p00
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v3/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-1p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-1p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv15-PowhegBugFix_150X_mcRun2_asymptotic_preVFP_v1-v3/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv15-PowhegBugFix_150X_mcRun2_asymptotic_v1-v7/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-PowhegBugFix_150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-1p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-1p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv15-PowhegBugFix_150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # GluGlutoHH_kl-0p00_kt-1p00_c2-0p00
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-0p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-0p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv15-PowhegBugFix_150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv15-PowhegBugFix_150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-PowhegBugFix_150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-0p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-0p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv15-PowhegBugFix_150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # GluGlutoHH_kl-2p45_kt-1p00_c2-0p00
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-2p45_kt-1p00_c2-0p00_LHEweights_TuneCP5_13p6TeV_powheg-pythia/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-2p45_kt-1p00_c2-0p00_LHEweights_TuneCP5_13p6TeV_powheg-pythia/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-2p45_kt-1p00_c2-0p00_LHEweights_TuneCP5_13p6TeV_powheg-pythia/Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-2p45_kt-1p00_c2-0p00_LHEweights_TuneCP5_13p6TeV_powheg-pythia/Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "12"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-2p45-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-2p45-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-2p45_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv15-PowhegBugFix_150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-2p45_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv15-PowhegBugFix_150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-2p45_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-PowhegBugFix_150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-2p45_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-2p45_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv15-PowhegBugFix_150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # GluGlutoHH_kl-5p00_kt-1p00_c2-0p00
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v1/NANOAODSIM",
        "year": "2022postEE",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGlutoHHto2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-5p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluHHto2B2G_Par-c2-0p00-kl-5p00-kt-1p00_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-PowhegBugFix_150X_mcRun3_2024_realistic_v2-v1/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv15-PowhegBugFix_150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv15-PowhegBugFix_150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-PowhegBugFix_150X_mc2017_realistic_v1-v11/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "GluGlutoHH_kl-5p00_kt-1p00_c2-0p00",
        "cmsdas": "/GluGluToHHTo2B2G_kl-5p00_kt-1p00_c2-0p00_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv15-PowhegBugFix_150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # VBFHH_CV-1p000_C2V-1p000_C3-1p000
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHto2B2G_CV_1_C2V_1_C3_1_TuneCP5_13p6TeV_madgraph-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHto2B2G_CV_1_C2V_1_C3_1_TuneCP5_13p6TeV_madgraph-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHto2B2G_CV_1_C2V_1_C3_1_TuneCP5_13p6TeV_madgraph-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHto2B2G_CV_1_C2V_1_C3_1_TuneCP5_13p6TeV_madgraph-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHto2B2G_Par-CV-1-C2V-1-C3-1_TuneCP5_13p6TeV_madgraph-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHto2B2G_Par-CV-1-C2V-1-C3-1_TuneCP5_13p6TeV_madgraph-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHTo2B2G_kl_1p00_cv_1p00_c2v_1p00_TuneCP5_13TeV_madgraph-pythia8/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHTo2B2G_kl_1p00_cv_1p00_c2v_1p00_TuneCP5_13TeV_madgraph-pythia8/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHTo2B2G_kl_1p00_cv_1p00_c2v_1p00_TuneCP5_13TeV_madgraph-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "VBFHH_CV-1p000_C2V-1p000_C3-1p000",
        "cmsdas": "/VBFHHTo2B2G_kl_1p00_cv_1p00_c2v_1p00_TuneCP5_13TeV_madgraph-pythia8/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # GluGluHtoGG
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "13"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1_ext1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1_ext1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1_ext1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "GluGluHtoGG",
        "cmsdas": "/GluGluHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1_ext1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # ttHtoGG
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-madspin-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-madspin-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-madspin-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-madspin-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/TTH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/TTH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHJetToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHJetToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHJetToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "ttHtoGG",
        "cmsdas": "/ttHJetToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # VBFHtoGG
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHtoGG_M-125_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHtoGG_M-125_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHto2G_M-125_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHto2G_M-125_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v4/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnlo-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnlo-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHToGG_M125_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHToGG_M125_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHToGG_M125_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "VBFHtoGG",
        "cmsdas": "/VBFHToGG_M125_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # VHtoGG
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-madspin-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHtoGG_M-125_TuneCP5_13p6TeV_amcatnloFXFX-madspin-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v5/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHto2G_M-125_TuneCP5_13p6TeV_amcatnloFxFx-madspin-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHto2G_M-125_TuneCP5_13p6TeV_amcatnloFxFx-madspin-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v3/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "ZHtoGG",
        "cmsdas": "/ZH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "WmHtoGG",
        "cmsdas": "/WminusH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "WpHtoGG",
        "cmsdas": "/WplusH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "ZHtoGG",
        "cmsdas": "/ZH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "WmHtoGG",
        "cmsdas": "/WminusH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "WpHtoGG",
        "cmsdas": "/WplusH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "VHtoGG",
        "cmsdas": "/VHToGG_M125_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # bbHtoGG
    {
        "keyword": "bbHtoGG",
        "cmsdas": "/BBHto2G_M-125_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v3/NANOAODSIM",
        "year": "2022preEE",
        "nano": "13"
    },
    {
        "keyword": "bbHtoGG",
        "cmsdas": "/BBHto2G_M-125_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "13"
    },
    {
        "keyword": "bbHtoGG",
        "cmsdas": "/BBHto2G_M-125_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "bbHtoGG",
        "cmsdas": "/BBHto2G_M-125_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "bbHtoGG",
        "cmsdas": "/BBH-Hto2G_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "bbHtoGG",
        "cmsdas": "/BBH-Hto2G_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },

    # GGJets_MGG-40to80
    {
        "keyword": "GGJets_MGG-40to80",
        "cmsdas": "/GG-Box-3Jets_MGG-40to80_13p6TeV_sherpa/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "GGJets_MGG-40to80",
        "cmsdas": "/GG-Box-3Jets_MGG-40to80_13p6TeV_sherpa/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "GGJets_MGG-40to80",
        "cmsdas": "/GG-Box-3Jets_MGG-40to80_13p6TeV_sherpa/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "GGJets_MGG-40to80",
        "cmsdas": "/GG-Box-3Jets_MGG-40to80_13p6TeV_sherpa/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "GGJets_MGG-40to80",
        "cmsdas": "/GG-Box-3Jets_Bin-MGG-40to80_TuneSherpaDef_13p6TeV_sherpaMEPS/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GGJets_MGG-40to80",
        "cmsdas": "/GG-Box-3Jets_Bin-MGG-40to80_TuneSherpaDef_13p6TeV_sherpaMEPS/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },

    # GGJets_MGG-80
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/GG-Box-3Jets_MGG-80_13p6TeV_sherpa/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/GG-Box-3Jets_MGG-80_13p6TeV_sherpa/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/GG-Box-3Jets_MGG-80_13p6TeV_sherpa/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/GG-Box-3Jets_MGG-80_13p6TeV_sherpa/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/GG-Box-3Jets_Bin-MGG-80_TuneSherpaDef_13p6TeV_sherpaMEPS/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/GG-Box-3Jets_Bin-MGG-80_TuneSherpaDef_13p6TeV_sherpaMEPS/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/DiPhotonJetsBox_MGG-80toInf_13TeV-sherpa/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/DiPhotonJetsBox_MGG-80toInf_13TeV-sherpa/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/DiPhotonJetsBox_MGG-80toInf_13TeV-sherpa/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "GGJets_MGG-80",
        "cmsdas": "/DiPhotonJetsBox_MGG-80toInf_13TeV-sherpa/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # TTGG
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v2/NANOAODSIM",
        "year": "2022preEE",
        "nano": "13"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v1/NANOAODSIM",
        "year": "2023preBPix",
        "nano": "13"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v1/NANOAODSIM",
        "year": "2023postBPix",
        "nano": "13"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8/RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1-v2/NANOAODSIM",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1-v1/NANOAODSIM",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1/NANOAODSIM",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "TTGG",
        "cmsdas": "/TTGG_TuneCP5_13TeV-amcatnlo-pythia8/RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1/NANOAODSIM",
        "year": "2018",
        "nano": "15"
    },

    # Not strictly necessary samples
    # # TTG_PTG-10to100
    # {
    #     "keyword": "TTG_PTG-10to100",
    #     "cmsdas": "/TTG-1Jets_PTG-10to100_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-10to100",
    #     "cmsdas": "/TTG-1Jets_PTG-10to100_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-10to100",
    #     "cmsdas": "/TTG-1Jets_PTG-10to100_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-10to100",
    #     "cmsdas": "/TTG-1Jets_PTG-10to100_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v1/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # TTG_PTG-100to200
    # {
    #     "keyword": "TTG_PTG-100to200",
    #     "cmsdas": "/TTG-1Jets_PTG-100to200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-100to200",
    #     "cmsdas": "/TTG-1Jets_PTG-100to200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-100to200",
    #     "cmsdas": "/TTG-1Jets_PTG-100to200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-100to200",
    #     "cmsdas": "/TTG-1Jets_PTG-100to200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v1/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # TTG_PTG-200
    # {
    #     "keyword": "TTG_PTG-200",
    #     "cmsdas": "/TTG-1Jets_PTG-200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer22NanoAODv13-133X_mcRun3_2022_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-200",
    #     "cmsdas": "/TTG-1Jets_PTG-200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer22EENanoAODv13-133X_mcRun3_2022_realistic_postEE_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-200",
    #     "cmsdas": "/TTG-1Jets_PTG-200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "TTG_PTG-200",
    #     "cmsdas": "/TTG-1Jets_PTG-200_TuneCP5_13p6TeV_amcatnloFXFXold-pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v1/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # TT
    # {
    #     "keyword": "TT",
    #     "cmsdas": "/TT_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "TT",
    #     "cmsdas": "/TT_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v2/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "12"
    # },

    # # QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80
    # {
    #     "keyword": "QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80",
    #     "cmsdas": "/QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80_TuneCP5_13p6TeV_pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80",
    #     "cmsdas": "/QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80_TuneCP5_13p6TeV_pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80",
    #     "cmsdas": "/QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80_TuneCP5_13p6TeV_pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80",
    #     "cmsdas": "/QCD_PT-30toInf_DoubleEMEnriched_MGG-40to80_TuneCP5_13p6TeV_pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # GJet_PT-20to40_DoubleEMEnriched_MGG-80
    # {
    #     "keyword": "GJet_PT-20to40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-20to40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "GJet_PT-20to40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-20to40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "GJet_PT-20to40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-20to40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "GJet_PT-20to40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-20to40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # GJet_PT-40_DoubleEMEnriched_MGG-80
    # {
    #     "keyword": "GJet_PT-40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "GJet_PT-40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "GJet_PT-40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "GJet_PT-40_DoubleEMEnriched_MGG-80",
    #     "cmsdas": "/GJet_PT-40_DoubleEMEnriched_MGG-80_TuneCP5_13p6TeV_pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf
    # {
    #     "keyword": "QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v1/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-30to40_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v1/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },

    # # QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf
    # {
    #     "keyword": "QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM",
    #     "year": "2022preEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM",
    #     "year": "2022postEE",
    #     "nano": "12"
    # },
    # {
    #     "keyword": "QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer23NanoAODv13-133X_mcRun3_2023_realistic_ForNanov13_v1-v2/NANOAODSIM",
    #     "year": "2023preBPix",
    #     "nano": "13"
    # },
    # {
    #     "keyword": "QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf",
    #     "cmsdas": "/QCD_PT-40toInf_DoubleEMEnriched_MGG-80toInf_TuneCP5_13p6TeV_pythia8/Run3Summer23BPixNanoAODv13-133X_mcRun3_2023_realistic_postBPix_ForNanov13_v2-v2/NANOAODSIM",
    #     "year": "2023postBPix",
    #     "nano": "13"
    # },
]


allowed_years = ["2022preEE", "2022postEE", "2023preBPix", "2023postBPix", "2024", "2025"]
samples = [s for s in samples if s["year"] in allowed_years]

# Iterate over each sample and execute the command
# for sample in samples:
#     parent_dir = outbase_dir + "/" + sample['year'] + "/" + extra_dir
for sample in samples:
    year_folder = sample['year'][:4]
    era_folder = sample['year'][4:]
    parent_dir = outbase_dir + "/" + year_folder + "/sim/" + era_folder + "/" + extra_dir

    # Create the directory
    print(f"Creating directory: {parent_dir}")
    os.makedirs(parent_dir, exist_ok=True)
    os.chmod(parent_dir, 0o777)

    # Construct the command
    command = f"python submission/tools_HHbbgg/produce_one_mc.py --keyword {sample['keyword']} --cmsdas {sample['cmsdas']} --parent-dir {parent_dir} --year {sample['year']} --nano {sample['nano']} --memory 25GB"  # --memory 20GB{(' --dbs-instance '+sample['dbs-instance']) if 'dbs-instance' in sample.keys() else ''}{(' --where '+sample['where']) if 'where' in sample.keys() else ''}"

    print(f"Executing: {command}")  # Print the command being executed
    subprocess.run(command, shell=True, check=True)

print("All jobs have been executed successfully.")
