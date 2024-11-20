import os
import matplotlib
import sys
os.environ['MPLCONFIGDIR'] = '/uscms_data/d1/sraj/matplotlib_tmp'
import uproot
from hist import Hist
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from cycler import cycler
from normalisation import getLumi


matplotlib.use("Agg")
hep.style.use("CMS")
plt.rcParams["axes.prop_cycle"] = cycler(
    color=[
        "#3f90da", "#ffa90e", "#bd1f01", "#94a4a2",
        "#832db6", "#a96b59", "#e76300", "#b9ac70",
        "#717581", "#92dadd",
    ]
)
