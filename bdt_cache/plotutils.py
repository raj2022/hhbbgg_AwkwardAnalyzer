import os 
import sys 

import numpy as np
import matplotlib 
matplotlib.use("pdf") 
import matplotlib.pyplot as plt 
## https://matplotlib.org/tutorials/introductory/usage.html#sphx-glr-tutorials-introductory-usage-py
## https://matplotlib.org/api/_as_gen/matplotlib.axes.Axes.hist.html#matplotlib.axes.Axes.hist
class plotutils:
    def __init__(self, columns, binning, legend, axisTitle, experiment, plotType, makeRatio, saveLog, Xrange, areaNormalize=False  ):
        self.columns_    = columns
        self.binning_    = binning
        self.legend_     = legend
        self.axisTitle_  = axisTitle
        self.experiment_ = experiment
        self.plotType_   = plotType
        self.makeRatio_  = makeRatio
        self.saveLog_    = saveLog
        self.Xrange_     = [float(Xrange[0]), float(Xrange[1])]
        self.areaNormalize_   = areaNormalize
        #self.   = 
        #self.   = 
        
        #print "inide init of class 
        print self.columns_, self.binning_, self.legend_, self.axisTitle_, self.experiment_, self.plotType_, self.makeRatio_, self.saveLog_

    def setrootfiles(self):
        return 0
    def getrootfiles(self):
        return 0
    def getvariables(self):
        return 0
    def plotSingle(self):
        return 0
    def plotOverlay(self):
        
        fig, ax = plt.subplots()
        
        print "inside the plotOverlay() function"
        
        weight_column_ = [np.ones_like(icol) for icol in self.columns_ ]

        if self.areaNormalize_: weight_column_ = [np.ones_like(icol)/len(icol) for icol in self.columns_ ]   
        
        ## following line takes care of the overflow and underflow bins
        self.columns_ = [np.clip(icol, float(self.Xrange_[0]), float(self.Xrange_[1]) )  for icol in self.columns_]
        
        print 'weight_column_--', weight_column_
        ax.hist( self.columns_, \
                 bins=int(self.binning_),\
                 histtype='step', \
                 weights=weight_column_, \
                 range=self.Xrange_,\
                 label=self.legend_)
        print self.legend_
        ax.legend()
        
        figureTitle = self.experiment_ + " " + self.plotType_
        ax.set_title(figureTitle, x=0.2)
        #ax1.legend("HHZ 1",loc="upper right")
        if len(self.axisTitle_)==2: 
            #ax.set_xlabel(r'$p_T^{miss}$',x=0.88)#self.axisTitle_[0])
            ax.set_xlabel(self.axisTitle_[0], x=0.88)
            ax.set_ylabel(self.axisTitle_[1])
        
        plt.savefig("test.pdf")
        return 0
    def plotStack(self):
        return 0
    def plotEfficiency(self):
        return 0
    def plotEfficiencyOverlay(self):
        return 0
    def plot1DLimits(self):
        return 0
    def plotLimitsOverlay(self):
        return 0
    def plot2dLimits(self):
        return 0
        
