#!/bin/bash

echo "Setup flashggFinalFit..."

#######################################
#      ADD OPTIONAL LINES HERE        #
#######################################

#:: example
# conda activate env1
# export PATH=$PATH:/path/to/your/executable
# cd /path/to/directory/containing/CMSSW/directory

#######################################


export SCRAM_ARCH=el9_amd64_gcc12

# Check if CMSSW_14_1_0_pre4 directory in current directory
if [ -d "CMSSW_14_1_0_pre4" ]; then
    cd CMSSW_14_1_0_pre4/src
else
    echo "Cannot find CMSSW_14_1_0_pre4 directory. Run script from directory containing CMSSW_14_1_0_pre4 directory."
    exit 1
fi

cmsenv

if [ -d "flashggFinalFit" ]; then
    cd flashggFinalFit
else
    echo "Cannot find flashggFinalFit directory. Ensure flashggFinalFit is installed correctly."
    exit 1
fi

eval `scramv1 runtime -sh`

export PYTHONPATH=$PYTHONPATH:${CMSSW_BASE}/src/flashggFinalFit/tools