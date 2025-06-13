# Statistics Study
Modelling signal and the backrounds simultaneously using different functions such as Gaussian, Crystall ball, double side crystall ball, Bernestein Polynomials, etc. 

For the fitting and limit calcuation, mostly taking help from Benjamin's code documented here, https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit . It's still in progress and as mentioned by him this code mostly works for the Non-resonant case while we need to figure out for our resonant case. 

# CMSSW implementation
https://cms-sw.github.io/ 
https://github.com/cms-sw/cmssw 

```bash
export SCRAM_ARCH=slc7_amd64_gcc700
cmsrel CMSSW_10_2_13
cd CMSSW_10_2_13/src
cmsenv
```
# Get combine 
```bash
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
cd HiggsAnalysis/CombinedLimit
git checkout tags/V8.2.0
scram b -j 8
cd ../../
cmsenv
```

```bash
text2workspace.py datacard.txt -o workspace.root
```

Complete command on the activation of  `text2workspace.py`: 
```bash
# Go to your CMSSW release
cd ~/path/to/CMSSW_15_0_7/src

# Set up CMSSW environment
cmsenv

# Clone the Combine tool
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
cd HiggsAnalysis/CombinedLimit
git checkout v9.0.0  # or another appropriate version

# Go back and build
cd $CMSSW_BASE/src
scram b -j 8

# Re-initialize environment after build
cmsenv

# Verify installation
which text2workspace.py

# Now you're ready to run:
text2workspace.py datacard.txt -o workspace.root
```

## References:
Fitting diphoton mass($m_{\gamma\gamma})$ and dibjet mass($m_{jj}$) following the same fitting instruction as we have from the Lata's analysis note, in section 5.4.1 of the analysis. Lata mentioned about the correlation, https://cms.cern.ch/iCMS/analysisadmin/cadilines?line=HIG-21-011.
