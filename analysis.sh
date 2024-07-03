#!/bin/bash

# Run the analyzer script
python hhbbgg_Analyzer.py -i ../../output_root/
# python hhbbgg_Analyzer.py -i /Users/ptiwari/cmscern/eos/DoNotSync/hhtobbgg/HiggsDNA_root/v1/Run3_2022postEE_merged/
if [ $? -ne 0 ]; then
        echo "Error: hhbbgg_Analyzer.py failed to execute."
        ANALYZER_FAILED=true
else
        echo "Analyzer script completed. Moving to the next step."
fi

# Run the plotter script
python hhbbgg_Plotter.py
if [ $? -ne 0 ]; then
        echo "Error: hhbbgg_Plotter.py failed to execute."
        PLOTTER_FAILED=true
else
        echo "Plotter script completed. Moving to the next step."
fi

# Sync the plots to the remote server
rsync -av stack_plots/ sraj@lxplus.cern.ch:/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/plots_v1/ecal_selection/region_selection

if [ $? -ne 0 ]; then
        echo "Error: rsync failed to synchronize the files."
        SYNC_FAILED=true
else
        echo "Synchronization completed successfully."
fi

# Overall status message
if [ "$ANALYZER_FAILED" = true ] || [ "$PLOTTER_FAILED" = true ] || [ "$SYNC_FAILED" = true ]; then
        echo "One or more tasks failed. Please check the error messages above."
else
        echo "All tasks completed successfully."
fi

