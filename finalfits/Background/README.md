
We need to setup backgrounds seperately. To setup, The background modelling package still needs to be built with it's own makefiles. Please note that there will be verbose warnings from BOOST etc, which can be ignored. So long as the  `make` commands finish without error, then the compilation happened fine.
```bash
cd ${CMSSW_BASE}/src/flashggFinalFit/Background
cmsenv
make
```










## References:
1. https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit/-/tree/higgsdnafinalfit/Background?ref_type=heads
