# Instructions
- Instructions: https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit


# Installation
```bash
curl https://gist.githubusercontent.com/benjaminls/4a0dbfaa8dd450739609f5876f6db942/raw/9265b538941a3dfe4ca500f63a0f2d917a32e018/install.sh -o install_FinalFit.sh && source install_FinalFit.sh
```


Upon completion, you should have a fully set up FinalFit installation and you will be in the correct directory and environment to begin working with FinalFit.


## Setup
After you start a new terminal/shell, you must run a setup script before running FinalFit. 

If you installed FinalFit using the installation script, a setup script is created in the same directory housing `CMSSW_14_1_0_pre4`. If, for some reason, there is no file named `setup_finalfit.sh` in the directory, you may copy the [file](https://gitlab.cern.ch/hhtobbgg_nu/flashggFinalFit/-/blob/d8ade89048c3fb560ebb0cd29cbb6be7f7e20132/scripts/setup_finalfit.sh) manually. 

You may find it convenient to place the setup script in a different location. In such a case, you must update the script by a line to `cd` to the directory containing `CMSSW_14_1_0_pre4`. Put this line at the top of the script. 

If you require a python environment, also place this line at the top of the script. You will find a commented box for these additions. This is also a good point to add any other environment variables you may need.


