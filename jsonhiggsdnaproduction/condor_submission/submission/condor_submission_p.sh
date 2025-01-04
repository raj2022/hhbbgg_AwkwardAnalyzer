#!/bin/sh
ulimit -s unlimited
set -e
cd /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/parquet_production/HiggsDNA
mamba activate higgs-dna


if [ $1 -eq 0 ]; then
    python /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/parquet_production/HiggsDNA/scripts/run_analysis.py --json-analysis /afs/cern.ch/user/s/sraj/Analysis/Analysis_HH-bbgg/parquet_production/HiggsDNA/error.json --dump /afs/cern.ch/user/s/sraj/Analysis/output_parquet/v2_production/debugging/ --doFlow_corrections --fiducialCuts store_flag --skipCQR --Smear_sigma_m --doDeco --executor futures
fi
