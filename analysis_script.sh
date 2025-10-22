#!/bin/bash

echo "Starting the Analyzer script"
echo "============================="

# Running with DD bkg estimation adn tempelate fitting
python hhbbgg_analyzer_lxplus_par.py --year 2023 --era All \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postEE/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/preBPix/ \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/v3_production/samples/postBPix/ \
  --tag DD_CombinedAll

echo "Analyzer script completed."



echo "Starting the plotter"
hhbbgg_Analyzer.py
echo "Plotter script completed"

# moving the plotter from stacks plot to the folder

DEST_DIR=~/sraj/www/CUA/HH-bbgg/all_plots/Data_MC

echo "Starting plot copy process..."

# Check if the destination directory exists
if [ ! -d "$DEST_DIR" ]; then
    echo "Destination folder not found. Creating: $DEST_DIR"
    mkdir -p "$DEST_DIR"
else
    echo "Destination folder already exists: $DEST_DIR"
fi


# Copy index.php to the destination folder
echo "Copying index.php to $DEST_DIR..."
cp "$DEST_DIR/index.php" "$DEST_DIR"


# Copy stack_plots folder
echo "Copying stack_plots/ to $DEST_DIR..."
cp -r stack_plots/ "$DEST_DIR/"


echo "✅ All files copied successfully!"
