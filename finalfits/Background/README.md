# Setup for the background
- will be working mostly inside the CMSSW env


We need to setup backgrounds seperately. To setup, The background modelling package still needs to be built with it's own makefiles. Please note that there will be verbose warnings from BOOST etc, which can be ignored. So long as the  `make` commands finish without error, then the compilation happened fine.
```bash
cd ${CMSSW_BASE}/src/flashggFinalFit/Background
cmsenv
make
```

If it fails, first try `make clean` and then `make` again.


# Backgorund f-test
https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit/-/tree/higgsdnafinalfit/Background?ref_type=heads#background-f-test







## References:
1. https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit/-/tree/higgsdnafinalfit/Background?ref_type=heads
