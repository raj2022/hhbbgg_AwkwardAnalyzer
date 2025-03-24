#!/bin/bash

if ! command -v cmsrel 2>&1 >/dev/null; then
    echo "cmsrel command not found. Fix your setup before running this script."
    kill -INT $$ # equivalent to ctrl+c, does not kill shell when sourcing script
fi

if ! command -v cmsenv 2>&1 >/dev/null; then
    echo "cmsenv command not found. Fix your setup before running this script."
    kill -INT $$
fi

if ! command -v git 2>&1 >/dev/null; then
    echo "git command not found. Fix your setup before running this script."
    kill -INT $$
fi

if ! command -v scram 2>&1 >/dev/null; then
    echo "scram command not found. Fix your setup before running this script."
    kill -INT $$
fi

echo
echo "Installing FinalFit for Early Run 3 HH->bbgg Analysis..."

echo
echo "Installing at $(pwd)"

# mkdir -p FinalFit
# cd FinalFit
export SCRAM_ARCH=el9_amd64_gcc12

use_existing="0" # base case for putting CMSSW_14_1_0_pre4 in current directory

# Check if CMSSW_14_1_0_pre4 directory already in current directory
if [ -d "CMSSW_14_1_0_pre4" ]; then
    echo
    echo "CMSSW_14_1_0_pre4 directory already exists."
    echo
    read -p ">>> Install in existing CMSSW_14_1_0_pre4 directory? (y/n): " use_existing
else
    echo
    echo "CMSSW_14_1_0_pre4 directory does not exist."
    echo
fi

if [ $use_existing == "0" ]; then
    echo "Setting up CMSSW_14_1_0_pre4"
    cmsrel CMSSW_14_1_0_pre4
    cd CMSSW_14_1_0_pre4/src
fi

if [ $use_existing == "n" ]; then
    read -p "Enter name of the directory to create: " dir_name
    mkdir -p $dir_name
    cd $dir_name
    echo "Setting up CMSSW_14_1_0_pre4"
    cmsrel CMSSW_14_1_0_pre4
    cd CMSSW_14_1_0_pre4/src
fi

if [ $use_existing == "y" ]; then
    cd CMSSW_14_1_0_pre4/src
fi

# Ok, now we are in the CMSSW_14_1_0_pre4/src directory and are ready to run cmsenv

echo "Setting up CMSSW environment"
cmsenv

# If CMSSW_BASE is not set, something went wrong
if [ -z "$CMSSW_BASE" ]; then
    echo "CMSSW_BASE is not set. Something went wrong. Exiting..."
    exit 1
fi

# COMBINE_TAG=07b56c67ba6e4304b42c3a6cdba710d59c719192 # original tag
# COMBINE_TAG=9a205555584a6803487f00d2cee6969cdeabd0cb # tag with makeXS bug fix
COMBINE_TAG=combine_v10_fix # using new branch with fix
COMBINEHARVESTER_TAG=94017ba5a3a657f7b88669b1a525b19d34ea41a2
FINALFIT_TAG=higgsdnafinalfit

echo "Cloning hhbbgg docs"
git clone https://gitlab.cern.ch/hhbbgg/docs.git

# Install Combine with the latest EL9 compatible branch
echo "Cloning Combine with fix"
# git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
# We need to clone my fork since the branch in the original repo has a bug
git clone https://github.com/benjaminls/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
cd HiggsAnalysis/CombinedLimit && git fetch origin ${COMBINE_TAG} && git checkout ${COMBINE_TAG}

# Install CombineHarvester
echo "Install CombineTools in CombineHarvester"
cd ${CMSSW_BASE}/src
bash <(curl -s https://raw.githubusercontent.com/cms-analysis/CombineHarvester/${COMBINEHARVESTER_TAG}/CombineTools/scripts/sparse-checkout-https.sh)
cd CombineHarvester && git fetch origin ${COMBINEHARVESTER_TAG} && git checkout ${COMBINEHARVESTER_TAG}


echo "Compiling libraries"
cd ${CMSSW_BASE}/src
cmsenv
scram b clean
scram b -j 16

# Install Final Fit package
git clone -b $FINALFIT_TAG https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit.git
cd flashggFinalFit/

cp scripts/setup_finalfit.sh ../../../setup_finalfit.sh


# Setup 
eval `scramv1 runtime -sh`

export PYTHONPATH=$PYTHONPATH:${CMSSW_BASE}/src/flashggFinalFit/tools

# source ../../../setup_finalfit.sh

echo "Done"