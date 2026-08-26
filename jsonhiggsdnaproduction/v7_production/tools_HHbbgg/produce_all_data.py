import os
import subprocess

# Initialize VOMS proxy
print("Initializing VOMS proxy...")
subprocess.run("voms-proxy-init --rfc --voms cms -valid 192:00", shell=True, check=True)
# outbase_dir = "/eos/user/" + os.environ['USER'][:1] + "/" + os.environ['USER'] + "/HiggsDNA_v7Production/"
outbase_dir = "/eos/cms/store/group/phys_b2g/HHbbgg/sraj/"
extra_dir = ""

samples = [
    # 2022preEE
    {
        "keyword": "Run2022C",
        "cmsdas": "/EGamma/Run2022C-22Sep2023-v1/NANOAOD",
        "year": "2022preEE",
        "nano": "12"
    },
    {
        "keyword": "Run2022D",
        "cmsdas": "/EGamma/Run2022D-22Sep2023-v1/NANOAOD",
        "year": "2022preEE",
        "nano": "12"
    },

    # 2022postEE
    {
        "keyword": "Run2022E",
        "cmsdas": "/EGamma/Run2022E-22Sep2023-v1/NANOAOD",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "Run2022F",
        "cmsdas": "/EGamma/Run2022F-22Sep2023-v1/NANOAOD",
        "year": "2022postEE",
        "nano": "12"
    },
    {
        "keyword": "Run2022G",
        "cmsdas": "/EGamma/Run2022G-22Sep2023-v2/NANOAOD",
        "year": "2022postEE",
        "nano": "12"
    },

    # 2023preBPix
    {
        "keyword": "Run2023Cv1_EG0",
        "cmsdas": "/EGamma0/Run2023C-22Sep2023_v1-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv2_EG0",
        "cmsdas": "/EGamma0/Run2023C-22Sep2023_v2-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv3_EG0",
        "cmsdas": "/EGamma0/Run2023C-22Sep2023_v3-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv4_EG0",
        "cmsdas": "/EGamma0/Run2023C-22Sep2023_v4-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv1_EG1",
        "cmsdas": "/EGamma1/Run2023C-22Sep2023_v1-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv2_EG1",
        "cmsdas": "/EGamma1/Run2023C-22Sep2023_v2-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv3_EG1",
        "cmsdas": "/EGamma1/Run2023C-22Sep2023_v3-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Cv4_EG1",
        "cmsdas": "/EGamma1/Run2023C-22Sep2023_v4-v1/NANOAOD",
        "year": "2023preBPix",
        "nano": "12"
    },

    # 2023postBPix
    {
        "keyword": "Run2023Dv1_EG0",
        "cmsdas": "/EGamma0/Run2023D-22Sep2023_v1-v1/NANOAOD",
        "year": "2023postBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Dv2_EG0",
        "cmsdas": "/EGamma0/Run2023D-22Sep2023_v2-v1/NANOAOD",
        "year": "2023postBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Dv1_EG1",
        "cmsdas": "/EGamma1/Run2023D-22Sep2023_v1-v1/NANOAOD",
        "year": "2023postBPix",
        "nano": "12"
    },
    {
        "keyword": "Run2023Dv2_EG1",
        "cmsdas": "/EGamma1/Run2023D-22Sep2023_v2-v1/NANOAOD",
        "year": "2023postBPix",
        "nano": "12"
    },

    # 2024
    {
        "keyword": "Run2024C_EG0",
        "cmsdas": "/EGamma0/Run2024C-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024C_EG1",
        "cmsdas": "/EGamma1/Run2024C-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024D_EG0",
        "cmsdas": "/EGamma0/Run2024D-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024D_EG1",
        "cmsdas": "/EGamma1/Run2024D-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024E_EG0",
        "cmsdas": "/EGamma0/Run2024E-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024E_EG1",
        "cmsdas": "/EGamma1/Run2024E-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024F_EG0",
        "cmsdas": "/EGamma0/Run2024F-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024F_EG1",
        "cmsdas": "/EGamma1/Run2024F-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024G_EG0",
        "cmsdas": "/EGamma0/Run2024G-MINIv6NANOv15-v2/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024G_EG1",
        "cmsdas": "/EGamma1/Run2024G-MINIv6NANOv15-v2/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024H_EG0",
        "cmsdas": "/EGamma0/Run2024H-MINIv6NANOv15-v2/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024H_EG1",
        "cmsdas": "/EGamma1/Run2024H-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024Iv1_EG0",
        "cmsdas": "/EGamma0/Run2024I-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024Iv2_EG0",
        "cmsdas": "/EGamma0/Run2024I-MINIv6NANOv15_v2-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024Iv1_EG1",
        "cmsdas": "/EGamma1/Run2024I-MINIv6NANOv15-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },
    {
        "keyword": "Run2024Iv2_EG1",
        "cmsdas": "/EGamma1/Run2024I-MINIv6NANOv15_v2-v1/NANOAOD",
        "year": "2024",
        "nano": "15"
    },

    # 2025
    {
        "keyword": "Run2025Cv1_EG0",
        "cmsdas": "/EGamma0/Run2025C-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv2_EG0",
        "cmsdas": "/EGamma0/Run2025C-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv1_EG1",
        "cmsdas": "/EGamma1/Run2025C-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv2_EG1",
        "cmsdas": "/EGamma1/Run2025C-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv1_EG2",
        "cmsdas": "/EGamma2/Run2025C-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv2_EG2",
        "cmsdas": "/EGamma2/Run2025C-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv1_EG3",
        "cmsdas": "/EGamma3/Run2025C-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Cv2_EG3",
        "cmsdas": "/EGamma3/Run2025C-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025D_EG0",
        "cmsdas": "/EGamma0/Run2025D-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025D_EG1",
        "cmsdas": "/EGamma1/Run2025D-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025D_EG2",
        "cmsdas": "/EGamma2/Run2025D-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025D_EG3",
        "cmsdas": "/EGamma3/Run2025D-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025E_EG0",
        "cmsdas": "/EGamma0/Run2025E-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025E_EG1",
        "cmsdas": "/EGamma1/Run2025E-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025E_EG2",
        "cmsdas": "/EGamma2/Run2025E-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025E_EG3",
        "cmsdas": "/EGamma3/Run2025E-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv1_EG0",
        "cmsdas": "/EGamma0/Run2025F-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv2_EG0",
        "cmsdas": "/EGamma0/Run2025F-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv1_EG1",
        "cmsdas": "/EGamma1/Run2025F-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv2_EG1",
        "cmsdas": "/EGamma1/Run2025F-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv1_EG2",
        "cmsdas": "/EGamma2/Run2025F-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv2_EG2",
        "cmsdas": "/EGamma2/Run2025F-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv1_EG3",
        "cmsdas": "/EGamma3/Run2025F-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025Fv2_EG3",
        "cmsdas": "/EGamma3/Run2025F-PromptReco-v2/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025G_EG0",
        "cmsdas": "/EGamma0/Run2025G-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025G_EG1",
        "cmsdas": "/EGamma1/Run2025G-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025G_EG2",
        "cmsdas": "/EGamma2/Run2025G-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },
    {
        "keyword": "Run2025G_EG3",
        "cmsdas": "/EGamma3/Run2025G-PromptReco-v1/NANOAOD",
        "year": "2025",
        "nano": "15"
    },

    # 2017
    {
        "keyword": "Run2017B_EG0",
        "cmsdas": "/DoubleEG/Run2017B-UL2017_NanoAODv15-v1/NANOAOD",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "Run2017C_EG0",
        "cmsdas": "/DoubleEG/Run2017C-UL2017_NanoAODv15-v1/NANOAOD",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "Run2017D_EG0",
        "cmsdas": "/DoubleEG/Run2017D-UL2017_NanoAODv15-v1/NANOAOD",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "Run2017E_EG0",
        "cmsdas": "/DoubleEG/Run2017E-UL2017_NanoAODv15-v1/NANOAOD",
        "year": "2017",
        "nano": "15"
    },
    {
        "keyword": "Run2017F_EG0",
        "cmsdas": "/DoubleEG/Run2017F-UL2017_NanoAODv15-v1/NANOAOD",
        "year": "2017",
        "nano": "15"
    },

    # 2018
    {
        "keyword": "Run2018A_EG0",
        "cmsdas": "/EGamma/Run2018A-UL2018_NanoAODv15-v1/NANOAOD",
        "year": "2018",
        "nano": "15"
    },
    {
        "keyword": "Run2018B_EG0",
        "cmsdas": "/EGamma/Run2018B-UL2018_NanoAODv15-v1/NANOAOD",
        "year": "2018",
        "nano": "15"
    },
    {
        "keyword": "Run2018C_EG0",
        "cmsdas": "/EGamma/Run2018C-UL2018_NanoAODv15-v1/NANOAOD",
        "year": "2018",
        "nano": "15"
    },
    {
        "keyword": "Run2018D_EG0",
        "cmsdas": "/EGamma/Run2018D-UL2018_NanoAODv15-v1/NANOAOD",
        "year": "2018",
        "nano": "15"
    },

    # 2016
    {
        "keyword": "Run2016Bv1_preVFP",
        "cmsdas": "/DoubleEG/Run2016B-HIPM_UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016Bv2_preVFP",
        "cmsdas": "/DoubleEG/Run2016B-HIPM_UL2016_NanoAODv15_v2-v1/NANOAOD",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016C_preVFP",
        "cmsdas": "/DoubleEG/Run2016C-HIPM_UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016D_preVFP",
        "cmsdas": "/DoubleEG/Run2016D-HIPM_UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016E_preVFP",
        "cmsdas": "/DoubleEG/Run2016E-HIPM_UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016F_preVFP",
        "cmsdas": "/DoubleEG/Run2016F-HIPM_UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016preVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016F_postVFP",
        "cmsdas": "/DoubleEG/Run2016F-UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016G_postVFP",
        "cmsdas": "/DoubleEG/Run2016G-UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016postVFP",
        "nano": "15"
    },
    {
        "keyword": "Run2016H_postVFP",
        "cmsdas": "/DoubleEG/Run2016H-UL2016_NanoAODv15-v1/NANOAOD",
        "year": "2016postVFP",
        "nano": "15"
    }
]


allowed_years = ["2022preEE", "2022postEE", "2023preBPix", "2023postBPix", "2024", "2025"]
samples = [s for s in samples if s["year"] in allowed_years]

# Iterate over each sample and execute the command
# for sample in samples:
#     parent_dir = outbase_dir + "/" + sample['year'] + "/" + extra_dir
for sample in samples:
    year_folder = sample['year'][:4]   # "2022" or "2023"
    era_folder = sample['year'][4:]    # "preEE", "postEE", "preBPix", "postBPix"
    parent_dir = outbase_dir + "/" + year_folder + "/data/" + era_folder + "/" + extra_dir

    # Create the directory
    print(f"Creating directory: {parent_dir}")
    os.makedirs(parent_dir, exist_ok=True)
    os.chmod(parent_dir, 0o777)

    # Construct the command
    command = f"python submission/tools_HHbbgg/produce_one_data.py --keyword {sample['keyword']} --cmsdas {sample['cmsdas']} --parent-dir {parent_dir} --year {sample['year']} --nano {sample['nano']}"  # --memory 20GB"

    print(f"Executing: {command}")  # Print the command being executed
    subprocess.run(command, shell=True, check=True)

print("All jobs have been executed successfully.")
