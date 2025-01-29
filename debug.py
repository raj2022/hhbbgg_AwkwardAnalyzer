import os
import optparse
import uproot
import pandas as pd
import awkward as ak
import pyarrow.parquet as pq
from pyarrow import Table
import pyarrow
import gc  # For memory cleanup
from config.utils import lVector  # Utility function for physics calculations

# Command-line argument parsing
usage = "usage: %prog [options] arg1 arg2"
parser = optparse.OptionParser(usage)
parser.add_option(
    "-i",
    "--inFile",
    type="string",
    dest="inputfiles_",
    help="Either a single input Parquet file or a directory of Parquet files",
)
(options, args) = parser.parse_args()

if not options.inputfiles_:
    raise ValueError("Please provide an input Parquet file or directory using -i or --inFile")
inputfiles_ = options.inputfiles_

# Process Parquet file in chunks of 10,000 rows
def process_parquet_file(inputfile, outputrootfile):
    print(f"Processing Parquet file: {inputfile}")
    
    required_columns = [
        "run", "lumi", "event",
        "puppiMET_pt", "puppiMET_phi",
        "Res_lead_bjet_pt", "Res_lead_bjet_eta", "Res_lead_bjet_phi", "Res_lead_bjet_mass",
        "lead_pt", "lead_eta", "lead_phi",
        "sublead_pt", "sublead_eta", "sublead_phi",
        "weight", "weight_central",
        "Res_HHbbggCandidate_mass"
    ]

    parquet_file = pq.ParquetFile(inputfile)
    fulltree_ = ak.Array([])  # Empty Awkward Array for storage

    # Iterate over chunks of 10,000 rows
    for batch in parquet_file.iter_batches(batch_size=10000, columns=required_columns):
        df = batch.to_pandas()  # Convert chunk to Pandas DataFrame
        tree_ = ak.from_arrow(pyarrow.Table.from_pandas(df))  

        print(f"Processing batch of {len(tree_)} events.")

        # Zip data into an Awkward Array
        cms_events = ak.zip(
            {
                "run": tree_["run"],
                "lumi": tree_["lumi"],
                "event": tree_["event"],
                "puppiMET_pt": tree_["puppiMET_pt"],
                "puppiMET_phi": tree_["puppiMET_phi"],
                "lead_bjet_pt": tree_["Res_lead_bjet_pt"],
                "lead_bjet_eta": tree_["Res_lead_bjet_eta"],
                "lead_bjet_phi": tree_["Res_lead_bjet_phi"],
                "lead_pho_pt": tree_["lead_pt"],
                "lead_pho_eta": tree_["lead_eta"],
                "lead_pho_phi": tree_["lead_phi"],
                "sublead_pho_pt": tree_["sublead_pt"],
                "sublead_pho_eta": tree_["sublead_eta"],
                "sublead_pho_phi": tree_["sublead_phi"],
                "bbgg_mass": tree_["Res_HHbbggCandidate_mass"],
                "weight": tree_["weight"],
                "weight_central": tree_["weight_central"],
            },
            depth_limit=1,
        )

        # Compute additional physics variables
        dibjet_ = lVector(
            cms_events["lead_bjet_pt"],
            cms_events["lead_bjet_eta"],
            cms_events["lead_bjet_phi"],
            cms_events["lead_bjet_pt"],  # Assuming lead & sublead have the same mass
            cms_events["lead_bjet_eta"],
            cms_events["lead_bjet_phi"],
            cms_events["lead_bjet_pt"] * 0.1,  # Assigning an approximate mass
            cms_events["lead_bjet_pt"] * 0.1,
        )
        diphoton_ = lVector(
            cms_events["lead_pho_pt"],
            cms_events["lead_pho_eta"],
            cms_events["lead_pho_phi"],
            cms_events["sublead_pho_pt"],
            cms_events["sublead_pho_eta"],
            cms_events["sublead_pho_phi"],
        )

        # Store derived variables
        cms_events["dibjet_mass"] = dibjet_.mass
        cms_events["dibjet_pt"] = dibjet_.pt
        cms_events["diphoton_mass"] = diphoton_.mass
        cms_events["diphoton_pt"] = diphoton_.pt

        fulltree_ = ak.concatenate([fulltree_, cms_events], axis=0)

    print(f"Finished processing {len(fulltree_)} total events from {inputfile}")

    # Convert all fields to NumPy-compatible types
    numpy_compatible_tree = {key: ak.to_numpy(fulltree_[key]) for key in fulltree_.fields}

    # Write to ROOT file
    outputrootfile["tree"]["processed_events"] = numpy_compatible_tree

    print(f"Saved processed data to ROOT file.")

# Define output directory
output_dir = "outputfiles"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Collect input files
if os.path.isfile(inputfiles_):
    inputfiles = [inputfiles_]
else:
    inputfiles = [
        f"{inputfiles_}/{infile_}"
        for infile_ in os.listdir(inputfiles_)
        if infile_.endswith(".parquet")
    ]

# Create output ROOT file
outputrootfile = {
    "tree": uproot.recreate(f"{output_dir}/hhbbgg_analyzer_processed.root"),
}

# Main function
def main():
    for infile_ in inputfiles:
        process_parquet_file(infile_, outputrootfile)

if __name__ == "__main__":
    main()
