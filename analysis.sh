#!/bin/bash

# Run the analyzer script
# python hhbbgg_Analyzer.py -i ../../output_root/
# python hhbbgg_Analyzer.py -i /Users/ptiwari/cmscern/eos/DoNotSync/hhtobbgg/HiggsDNA_root/v1/Run3_2022postEE_merged/
if [ $? -ne 0 ]; then
	echo "Error: hhbbgg_Analyzer.py failed to execute."
	exit 1
fi
echo "Analyzer script completed. Moving to the next step."

# Run the plotter script
python hhbbgg_Plotter.py
if [ $? -ne 0 ]; then
	echo "Error: hhbbgg_Plotter.py failed to execute."
	exit 1
fi
echo "Plotter script completed. Moving to the next step."

# Sync the plots to the remote server
# rsync -av stack_plots/ sraj@lxplus.cern.ch:~/sraj/www/CUA/HH-bbgg/stack_plots
rsync -av stack_plots/ ptiwari@lxplus.cern.ch:/eos/user/p/ptiwari/www/HHbbGG/hhbbgg_stack_plots_v1/
if [ $? -ne 0 ]; then
	echo "Error: rsync failed to synchronize the files."
	exit 1
fi
echo "Synchronization completed successfully."

echo "All tasks completed successfully."
