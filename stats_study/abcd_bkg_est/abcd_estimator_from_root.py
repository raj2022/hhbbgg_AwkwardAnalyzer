#import sys, os
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
#
#
#import uproot
#import awkward as ak
#import numpy as np
#from abcd_estimator import compute_abcd_yields
#from abcd_plotter import plot_abcd_yields, plot_closure_test
#
## Update with ROOT path and tree name
#ROOT_FILE = "../../outputfiles/hhbbgg_analyzer-v2-trees.root"
#TREE_PATH = "Data_EraF/preselection"  # directory/tree path inside ROOT file
#
#def load_events_from_root(filename, tree_path):
#    print(f"Reading tree '{tree_path}' from {filename}")
#    file = uproot.open(filename)
#    tree = file[tree_path]
#    arrays = tree.arrays(library="ak")
#    return arrays
#
#def main():
#    events = load_events_from_root(ROOT_FILE, TREE_PATH)
#
#    # Inject missing fields (mimicking analyzer output)
#    events["lead_isScEtaEB"] = np.abs(events["lead_pho_eta"]) < 1.4442
#    events["sublead_isScEtaEB"] = np.abs(events["sublead_pho_eta"]) < 1.4442
#
#    results = compute_abcd_yields(events)
#
#    print("\n=== ABCD Yield Report ===")
#    for k, v in results.items():
#        print(f"{k}: {v:.2f}")
#
#    plot_abcd_yields(results, "../../stack_plots/abcd_yields.png")
#    plot_closure_test(results, "../../stack_plots/abcd_closure.png")
#    print("Successfully saved the plot in the folder ../../stack_plots")
#if __name__ == "__main__":
#    main()


import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import uproot
import awkward as ak
import numpy as np
from abcd_estimator import compute_abcd_yields
from abcd_plotter import plot_abcd_yields, plot_closure_test

ROOT_FILE = "../../outputfiles/hhbbgg_analyzer-v2-trees.root"
TREE_DIR_SUFFIX = "preselection"

# List of all the dataset names (from .parquet filenames, without .parquet)
DATASETS = [
    "Data_EraE", "Data_EraF", "Data_EraG", "GGJets", "GJetPt20To40", "GJetPt40",
    "GluGluHToGG", "GluGluToHH",
    "NMSSM_X300_Y100", "NMSSM_X300_Y125", "NMSSM_X300_Y150",
    "NMSSM_X400_Y100", "NMSSM_X400_Y125", "NMSSM_X400_Y150",
    "NMSSM_X500_Y100", "NMSSM_X500_Y125", "NMSSM_X500_Y150",
    "QCD_PT-30To40", "QCD_PT-30ToInf", "QCD_PT-40ToInf",
    "ttHToGG", "VBFHToGG", "VHToGG"
]

def load_events_from_root(filename, tree_path):
    print(f"Reading tree '{tree_path}' from {filename}")
    file = uproot.open(filename)
    tree = file[tree_path]
    arrays = tree.arrays(library="ak")
    return arrays

def main():
    all_results = {}
    output_lines = []

    for dataset in DATASETS:
        tree_path = f"{dataset}/{TREE_DIR_SUFFIX}"
        try:
            events = load_events_from_root(ROOT_FILE, tree_path)
            events["lead_isScEtaEB"] = np.abs(events["lead_pho_eta"]) < 1.4442
            events["sublead_isScEtaEB"] = np.abs(events["sublead_pho_eta"]) < 1.4442

            results = compute_abcd_yields(events)
            all_results[dataset] = results

            print(f"\n=== ABCD Yield Report for {dataset} ===")
            output_lines.append(f"\n=== ABCD Yield Report for {dataset} ===")
            for k, v in results.items():
                output_lines.append(f"{k}: {v:.2f}")
                print(f"{k}: {v:.2f}")
        except Exception as e:
            output_lines.append(f"Failed to process {dataset}: {e}")
            print(f"Failed to process {dataset}: {e}")

    # Optionally: plot one of them or a combined result
    # plot_abcd_yields(all_results["Data_EraF"], "abcd_yields.png")
    # plot_closure_test(all_results["Data_EraF"], "abcd_closure.png")

    # Write results to a text file
    with open("abcd_yields.txt","w") as f:
        for line in output_lines:
            f.write(line + "\n")

    print("\nFinished processing all datasets.Results saved to abcd_yields.txt.")

if __name__ == "__main__":
    main()


#import uproot
#import awkward as ak
#import numpy as np
#import os
#
#from abcd_estimator import compute_abcd_yields
#from abcd_plotter import plot_abcd_yields, plot_closure_test
#
#ROOT_FILE = "../../outputfiles/hhbbgg_analyzer-v2-trees.root"
#TREE_NAME = "preselection"  # common sub-tree in all directories
#
#def load_events_from_root(filename, full_path):
#    print(f"Reading tree '{full_path}' from {filename}")
#    file = uproot.open(filename)
#    tree = file[full_path]
#    arrays = tree.arrays(library="ak")
#    return arrays
#
#def process_all_datasets(root_file):
#    file = uproot.open(root_file)
#    dataset_dirs = [k for k in file.keys() if TREE_NAME in file[k].keys()]
#
#    os.makedirs("stack_plots", exist_ok=True)
#
#    for dataset in dataset_dirs:
#        full_tree_path = f"{dataset}/{TREE_NAME}"
#        try:
#            events = load_events_from_root(root_file, full_tree_path)
#
#            # Add missing fields if necessary
#            events["lead_isScEtaEB"] = np.abs(events["lead_pho_eta"]) < 1.4442
#            events["sublead_isScEtaEB"] = np.abs(events["sublead_pho_eta"]) < 1.4442
#
#            results = compute_abcd_yields(events)
#
#            print(f"\n=== ABCD Yield Report: {dataset} ===")
#            for k, v in results.items():
#                print(f"{k}: {v:.2f}")
#
#            plot_abcd_yields(results, f"../../stack_plots/abcd_yields_{dataset}.png")
#            plot_closure_test(results, f"../../stack_plots/abcd_closure_{dataset}.png")
#
#        except Exception as e:
#            print(f"⚠️ Skipping {dataset} due to error: {e}")
#
#def main():
#    process_all_datasets(ROOT_FILE)
#
#if __name__ == "__main__":
#    main()
#
