#!/usr/bin/env python3
"""
Split CERN ROOT NANOAOD files into smaller chunks with N events per file
Usage: python split_nanoaod.py <input_file> <output_dir> <events_per_file> [options]
"""

import argparse
import os
import sys
import ROOT
import numpy as np
from pathlib import Path

def split_nanoaod_file(input_file, output_dir, max_events_per_file, force=False):
    """
    Split NANOAOD file into multiple smaller files
    
    Args:
        input_file: Input ROOT file path
        output_dir: Output directory
        max_events_per_file: Maximum number of events per output file
        force: Whether to overwrite existing output files
    """
    
    # Get input file information
    is_remote = str(input_file).startswith("root://") or str(input_file).startswith("gsidcap://")
    if not is_remote:
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
    else:
        input_path = Path(input_file)  # keep for stem extraction only

    # Get filename (without path and extension)
    filename = input_path.stem

    # Create output directory structure
    output_base_dir = Path(output_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing file: {input_file}")
    print(f"Output directory: {output_base_dir}")

    # Open input file (ROOT supports xrootd URLs natively)
    input_root_file = ROOT.TFile.Open(str(input_file), "READ")
    if not input_root_file or input_root_file.IsZombie():
        raise RuntimeError(f"Cannot open file: {input_file}")
    
    try:
        # Get Events tree
        events_tree = input_root_file.Get("Events")
        if not events_tree:
            raise RuntimeError("Events tree not found in file")
        
        total_events = events_tree.GetEntries()
        print(f"Total events: {total_events}")
        
        # Calculate number of parts needed
        num_parts = (total_events + max_events_per_file - 1) // max_events_per_file
        print(f"Will split into {num_parts} files")
        
        # Get all keys from input file
        keys_list = list(input_root_file.GetListOfKeys())
        
        # Loop to create output files
        for part_num in range(num_parts):
            # Calculate event range for current part
            start_event = part_num * max_events_per_file
            end_event = min((part_num + 1) * max_events_per_file, total_events)
            num_events_in_part = end_event - start_event
            
            # Create output filename
            output_filename = f"{filename}_part{part_num+1}_of_{num_parts}.root"
            output_path = output_base_dir / output_filename
            
            # Check if file already exists
            if output_path.exists() and not force:
                print(f"File already exists, skipping: {output_path}")
                continue
            
            print(f"Creating file {part_num+1}/{num_parts}: {output_filename}")
            print(f"  Event range: {start_event} - {end_event} ({num_events_in_part} events)")
            
            # Create new ROOT file
            output_root_file = ROOT.TFile.Open(str(output_path), "RECREATE")
            if not output_root_file or output_root_file.IsZombie():
                raise RuntimeError(f"Cannot create output file: {output_path}")
            
            try:
                # Process all keys from input file
                for key in keys_list:
                    obj_name = key.GetName()
                    obj_class = key.GetClassName()
                    
                    obj = input_root_file.Get(obj_name)
                    if not obj:
                        continue
                    
                    if obj.InheritsFrom("TTree"):
                        # Handle trees
                        if obj_name == "Events":
                            # Copy Events tree with event range
                            # Create new tree
                            new_tree = obj.CloneTree(0)
                            new_tree.SetName(obj_name)
                            new_tree.SetTitle(obj.GetTitle())
                            
                            # Copy only the desired event range
                            for i in range(start_event, end_event):
                                obj.GetEntry(i)
                                new_tree.Fill()
                            
                            new_tree.Write()
                            # print(f"  Copied tree {obj_name}: {num_events_in_part} events")
                        else:
                            # Copy other trees entirely
                            new_tree = obj.CloneTree()
                            new_tree.Write()
                            # print(f"  Copied tree {obj_name}: {new_tree.GetEntries()} events")
                    else:
                        # Copy non-tree objects (histograms, metadata, etc.)
                        try:
                            obj.Write()
                            print(f"  Copied object: {obj_class} : {obj_name}")
                        except Exception as e:
                            print(f"  Warning: Cannot copy {obj_name}: {e}")
                            continue
                
                # Write and close
                output_root_file.Write()
                output_root_file.Purge()  # Remove unused objects
                
                print(f"  Done: {output_path}")
                
            except Exception as e:
                print(f"Error creating output file {output_path}: {e}")
                output_root_file.Close()
                if output_path.exists():
                    output_path.unlink()
                raise
            finally:
                output_root_file.Close()
    
    finally:
        input_root_file.Close()


def collect_filename_to_json(split_output_dir, sample_name, output_json_path):
    """
    Collect all split files in the output directory and save their paths to a JSON file.
    
    Args:
        split_output_dir: Directory containing split files
        sample_name: Name of the sample (used as key in JSON)
        output_json_path: Path to save the JSON file
    """
    import json
    
    split_output_path = Path(split_output_dir)
    if not split_output_path.exists():
        raise FileNotFoundError(f"Split output directory not found: {split_output_dir}")
    
    # Find all ROOT files in the directory
    root_files = list(split_output_path.glob("*.root"))
    
    if not root_files:
        print(f"No ROOT files found in {split_output_dir} for sample {sample_name}.")
        return
    
    # Create a dictionary to hold the file paths
    data = {sample_name: [str(f.resolve()) for f in root_files]}
    
    # Save to JSON
    with open(output_json_path, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Saved file paths to JSON: {output_json_path}")

def split_nanoaod_sample(input_dir, output_dir, max_events_per_file, pattern="*.root", force=False):
    """
    Batch split all NANOAOD files in a directory
    
    Args:
        input_dir: Input directory
        output_dir: Output directory
        max_events_per_file: Maximum number of events per output file
        pattern: File matching pattern
        force: Whether to overwrite existing output files
    """
    
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Get sample name from input directory, the last part of the path
    sample_name = input_path.name
    
    # Find all matching files
    root_files = list(input_path.glob(pattern))
    
    if not root_files:
        print(f"No files matching {pattern} found in directory {input_dir} for sample {sample_name}.")
        return
    
    print(f"Found {len(root_files)} files to process")
    
    # Process each file
    for i, root_file in enumerate(root_files, 1):
        print(f"\nProcessing file {i}/{len(root_files)}")
        try:
            split_nanoaod_file(root_file, output_dir, max_events_per_file, force)
        except Exception as e:
            print(f"Error processing file {root_file}: {e}")
            continue
    collect_filename_to_json(output_dir, sample_name, os.path.join(output_dir, f"{sample_name}_split_files.json"))

def main():
    parser = argparse.ArgumentParser(
        description='Split CERN ROOT NANOAOD files into smaller chunks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split a single file
  python split_nanoaod.py input.root output_dir 10000
  
  # Split all files in a directory
  python split_nanoaod.py /path/to/input_dir output_dir 10000 --pattern "*.root"
  
  # Force overwrite existing files
  python split_nanoaod.py input.root output_dir 10000 --force
        """
    )
    
    parser.add_argument('input_path', 
                        help='Input file or directory path')
    parser.add_argument('output_dir', 
                        help='Output directory')
    parser.add_argument('-m', '--max-events', 
                        type=int,
                        default = 20_000,
                        help='Maximum number of events per output file')
    parser.add_argument('--pattern', 
                        default='*.root',
                        help='File matching pattern when input path is a directory (default: *.root)')
    parser.add_argument('--force', 
                        action='store_true',
                        help='Overwrite existing output files')
    parser.add_argument('--verbose', 
                        action='store_true',
                        help='Show verbose output')
    
    args = parser.parse_args()
    
    try:
        input_arg = args.input_path

        # Remote URLs (xrootd, gsidcap) — treat as single files
        is_remote = input_arg.startswith("root://") or input_arg.startswith("gsidcap://")
        if is_remote:
            split_nanoaod_file(input_arg, args.output_dir, args.max_events, args.force)
        else:
            input_path = Path(input_arg)
            if input_path.is_file():
                split_nanoaod_file(input_arg, args.output_dir, args.max_events, args.force)
            elif input_path.is_dir():
                split_nanoaod_sample(input_arg, args.output_dir, args.max_events,
                                     args.pattern, args.force)
            else:
                print(f"Error: {input_arg} is neither a file nor a directory")
                sys.exit(1)
        
        print("\nProcessing completed!")
        
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
