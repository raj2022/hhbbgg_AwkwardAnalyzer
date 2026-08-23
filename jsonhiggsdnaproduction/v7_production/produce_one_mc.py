import os
import argparse
import json
import subprocess


def write_sample_txt(keyword, year, cmsdas):
    filename = f"samples_mc_{year}_{keyword}.txt"
    with open(filename, "w") as f:
        f.write(keyword + " " + cmsdas)
    return filename

def fetch_datasets(sample_file, dbs_instance='prod/global', region='Yolo'):
    command = f"python submission/tools_HHbbgg/fetch_datasets_handle.py -i {sample_file} -w {region} --dbs-instance {dbs_instance}"
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"fetch_datasets_handle.py failed (exit code {result.returncode}) for "
            f"{sample_file} -- aborting before submission. Check DAS for this dataset directly."
        )


def run_analysis(nano_version, parent_dir, keyword, year, memory):
    memoryLine = f"--memory {memory} " if memory is not None else ""
    smear = ""
    deco = ""
    doflow = "--doFlow-corrections "
    triggerGroup = ""
    if year == "2018":
        triggerGroup = '--triggerGroup ".*EGamma.*2018.*" '
    # command = (
    #     f"python scripts/run_analysis.py "
    #     f"--json-analysis runner_mc_{year}_{keyword}.json "
    #     f"--dump {parent_dir} "
    #     f"{doflow}"
    #     f"--fiducialCuts store_flag "
    #     f"{smear}"
    #     f"{deco}"
    #     f"{triggerGroup}"
    #     f"--executor dask/lxplus "
    #     # f"--queue longlunch "
    #     f"--queue workday "
    #     f"--chunk 3000 "
    #     f"{memoryLine}"
    #     f"--debug "
    #     f"--skipbadfiles "
    #     f"--nano-version {nano_version} "
    #     f"--timeout 500"
    # )
    # print(command)
    # os.system(command)
    command = (
        f"python scripts/run_analysis.py "
        f"--json-analysis runner_mc_{year}_{keyword}.json "
        f"--dump {parent_dir} "
        f"{doflow}"
        f"--fiducialCuts store_flag "
        f"{smear}"
        f"{deco}"
        f"{triggerGroup}"
        f"--executor vanilla_lxplus "
        # f"--queue longlunch "
        f"--queue workday "
        f"{memoryLine}"
        f"--debug "
        f"--nano-version {nano_version} "
        f"--timeout 500"
    )
    print(command)
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"run_analysis.py failed (exit code {result.returncode}) for {keyword} -- "
            f"check condor_q, some jobs may have already been submitted before the failure."
        )


def update_json_config(keyword, year):
    # Using final JSON (including systematics) for all the years
    if any(x in year for x in ("2025","2024", "2022", "2023", "2016", "2017", "2018")):
        json_path = "submission/tools_HHbbgg/runner_mc_template.json"
        print("Choosing runner_mc_template.json")
    with open(json_path, "r") as f:
        config = json.load(f)
    config["samplejson"] = f"samples_mc_{year}_{keyword}.json"
    if "split_mc" in config:
        if ("2024" in year) or ("2025" in year):
            config["split_mc"] = True  # Enable MC splitting for 2024 and 2025
        else:
            config["split_mc"] = False
    if "year" in config:
        config["year"].pop("GluGluToHH", None)
        config["year"][keyword] = [f"{year}"]
    if "metaconditions" in config:
        if "2016postVFP" in year:
            config["metaconditions"] = "Era2016_legacyPostVFP_v1"
        elif "2016preVFP" in year:
            config["metaconditions"] = "Era2016_legacyPreVFP_v1"
        elif "2017" in year:
            config["metaconditions"] = "Era2017_legacy_v1"
        elif "2018" in year:
            config["metaconditions"] = "Era2018_legacy_v1"
        else:
            config["metaconditions"] = "Era2022_v1"
    if "corrections" in config:
        config["corrections"][keyword] = config["corrections"].pop("GluGluToHH", [])
        if "GluGluHtoGG" in keyword:
            config["corrections"][keyword].append("NNLOPS")
        if any("jet" in corr for corr in config["corrections"][keyword]):
            jerc_idxs = [
                idx for idx, corr in enumerate(config["corrections"][keyword])
                if "jet" in corr
            ]
            for jerc_idx in jerc_idxs:
                run2_years = ["2016", "2017", "2018"]
                if any(x in year for x in run2_years):
                    config["corrections"][keyword][jerc_idx] = config["corrections"][keyword][jerc_idx].replace("_pnetNu_syst", "_pnetNu_Run2_v15_syst")
                    config["corrections"][keyword][jerc_idx] = config["corrections"][keyword][jerc_idx].replace("fatjet_syst","fatjet_Run2_v15_syst")
            # Add multi fixed WP bTag SFs for all years
        if any(x in year for x in ("2018", "2017", "2016")):
            config["corrections"][keyword].remove("bTagMultiFixedWP_UParTAK4LMTXTXXT")
            config["corrections"][keyword].append("bTagMultiFixedWP_UParTAK4LMTXTXXT_Run2_v15")
        if any(x in year for x in ("2022", "2023")):
            config["corrections"][keyword].remove("bTagMultiFixedWP_UParTAK4LMTXTXXT")
            config["corrections"][keyword].append("bTagMultiFixedWP_PNetAK4LMTXTXXT")
        if "2023" in year:
            # Temporary workaround: jer_version hardcodes JRV2, but the
            # _PNet-suffixed JER files for 2023preBPix/2023postBPix use JRV3,
            # causing jerc_jet_pnetNu_syst to crash with IndexError: map::at.
            # Falls back to plain jerc_jet_syst until fixed upstream.
            if "jerc_jet_pnetNu_syst" in config["corrections"][keyword]:
                idx = config["corrections"][keyword].index("jerc_jet_pnetNu_syst")
                config["corrections"][keyword][idx] = "jerc_jet_syst"
        if any(x in year for x in ("2018", "2017", "2016")):
            config["corrections"][keyword].append("L1PreFiring")
            if "LoosePhoIDSF" in config["corrections"][keyword]:
                config["corrections"][keyword].remove("LoosePhoIDSF")
            if "PreselSF" in config["corrections"][keyword]:
                config["corrections"][keyword].remove("PreselSF")
    if "systematics" in config:
        config["systematics"][keyword] = config["systematics"].pop("GluGluToHH", [])
        if any(x in year for x in ("2018", "2017", "2016")):
            config["systematics"][keyword].remove("bTagMultiFixedWP_UParTAK4LMTXTXXT")
            config["systematics"][keyword].append("bTagMultiFixedWP_UParTAK4LMTXTXXT_Run2_v15")
        if any(x in year for x in ("2022","2023")):
            config["systematics"][keyword].remove("bTagMultiFixedWP_UParTAK4LMTXTXXT")
            config["systematics"][keyword].append("bTagMultiFixedWP_PNetAK4LMTXTXXT")
        if any(x in year for x in ("2016","2017","2018")):
            if "LoosePhoIDSF" in config["systematics"][keyword]:
                config["systematics"][keyword].remove("LoosePhoIDSF")
            if "PreselSF" in config["systematics"][keyword]:
                config["systematics"][keyword].remove("PreselSF")
    new_filename = f"runner_mc_{year}_{keyword}.json"
    with open(new_filename, "w") as f:
        json.dump(config, f, indent=4)

    return new_filename


def main():
    parser = argparse.ArgumentParser(description="Run MC production example pipeline.")
    parser.add_argument("-k", "--keyword", required=True, help="Keyword for dataset filtering")
    parser.add_argument("-c", "--cmsdas", required=True, help="Keyword for cmsdas filtering")
    parser.add_argument("-p", "--parent-dir", required=True, help="Directory to store output parquets")
    parser.add_argument("-y", "--year", required=True, choices=["2022postEE","2022preEE","2023postBPix","2023preBPix", "2024", "2025", "2018", "2017","2016preVFP","2016postVFP"], help="year")
    parser.add_argument("-n", "--nano", required=True, help="nano-version")
    parser.add_argument("-m", "--memory", help="condor job memory")
    parser.add_argument(
        "-w",
        "--where",
        help="Specify the region for xrootd prefix (only for grid mode).",
        default="Americas",
        choices=["Americas", "Eurasia", "Yolo"],
    )
    parser.add_argument(
        "--dbs-instance",
        dest="instance",
        help="The DBS instance to use for querying datasets (only for grid mode).",
        type=str,
        default="prod/global",
        choices=["prod/global", "prod/phys01", "prod/phys02", "prod/phys03"],
    )

    args = parser.parse_args()

    # Write dataset sample file
    sample_file = write_sample_txt(args.keyword, args.year, args.cmsdas)

    # Fetch datasets
    fetch_datasets(sample_file, dbs_instance=args.instance, region=args.where)

    # Update and save JSON configuration
    update_json_config(args.keyword, args.year)

    # Launch jobs
    run_analysis(args.nano, args.parent_dir, args.keyword, args.year, args.memory)


if __name__ == "__main__":
    main()
