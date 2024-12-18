#!/bin/sh
ulimit -s unlimited
set -e
cd /afs/cern.ch/work/p/ptiwari/cmsCombineTool/CMSSW_11_3_4/src
export SCRAM_ARCH=slc7_amd64_gcc700
source /cvmfs/cms.cern.ch/cmsset_default.sh
eval `scramv1 runtime -sh`
cd /afs/cern.ch/work/p/ptiwari/cmsCombineTool/CMSSW_11_3_4/src/limitmodels/bb+DM_analysis/bbDMlimitmodelrateParam_oneRP

if [ $1 -eq 0 ]; then
    source /afs/cern.ch/work/p/ptiwari/cmsCombineTool/CMSSW_11_3_4/src/limitmodels/bb+DM_analysis/bbDMlimitmodelrateParam_oneRP/makeGOF_onData.sh
fi
