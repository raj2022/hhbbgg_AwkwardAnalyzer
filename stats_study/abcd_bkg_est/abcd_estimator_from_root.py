import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import uproot
import awkward as ak
import numpy as np
from abcd_estimator import compute_abcd_yields
from abcd_plotter import plot_abcd_yields, plot_closure_test

# Update with your ROOT path and tree name
ROOT_FILE = "../../outputfiles/hhbbgg_analyzer-v2-trees.root"
TREE_PATH = "Data_EraF/preselection"  # directory/tree path inside ROOT file

def load_events_from_root(filename, tree_path):
    print(f"Reading tree '{tree_path}' from {filename}")
    file = uproot.open(filename)
    tree = file[tree_path]
    arrays = tree.arrays(library="ak")
    return arrays

def main():
    events = load_events_from_root(ROOT_FILE, TREE_PATH)

    # Inject missing fields (mimicking analyzer output)
    events["lead_isScEtaEB"] = np.abs(events["lead_pho_eta"]) < 1.4442
    events["sublead_isScEtaEB"] = np.abs(events["sublead_pho_eta"]) < 1.4442

    results = compute_abcd_yields(events)

    print("\n=== ABCD Yield Report ===")
    for k, v in results.items():
        print(f"{k}: {v:.2f}")

    plot_abcd_yields(results, "../../stack_plots/abcd_yields.png")
    plot_closure_test(results, "../../stack_plots/abcd_closure.png")
    print("Successfully saved the plot in the folder ../../stack_plots")
if __name__ == "__main__":
    main()

