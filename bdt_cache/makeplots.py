import os 
import sys 
import argparse

usage = " generalised plotting macro:" # python makeplots.py  -i files.txt --readFrom TTree --treename monoHbb_SR_boosted --variable MET --binning 20  --Xrange "200 1000" --legend "signal;top" --axistitle "USDp_{T}^{miss}USD;# of events" --plotMode overlay --areaNormalize

parser = argparse.ArgumentParser(description=usage)
#parser.add_argument("-n","--numberoffiles", dest="inputfile", type=int) ## to double check how many files are there, and also to decide weather to read histo from same file or different files
parser.add_argument("-i", "--inputfile",  dest="inputfile",default="") ## provide list in "1.root 2.root" else provide the .txt file with all the files

parser.add_argument("-readFrom","--readFrom", dest="readFrom", default="TTree") ## possible values for the moment TTree, later it can also deal with TH1F and CSV and other pythonic data-types. you name it and I will add it. 

parser.add_argument("-treename", "--treename", dest="treename", default="tree_")

parser.add_argument("-merge","--mergefiles",dest="mergefiles",default="") ## if some files need to be merged you can provide same id for those files, should provide like, 1 2 3 4 4 5, it will merge two files with process id 4 

parser.add_argument("-var", "--variable", dest="variable", default="") ## variable which you want to see save as pdf 

parser.add_argument("-binning", "--binning", dest="binning", default="10") ## if it is just an integer then use that as number of bins and if it is a list then use that as binning. provide list as numbers seprated by space in double quotes 

parser.add_argument("-Xrange", "--Xrange", dest="Xrange", default="")## sperated by space

parser.add_argument("-plotMode", "--plotMode", dest="plotMode", default="overlay") # single; overlay; stack; 

parser.add_argument("-legend", "--legend", dest="legend", default="") ## legend, would be in the same order as the file names or histogram names 

parser.add_argument("-axisT", "--axistitle", dest="axistitle", default="") ## "xAxis; yAxis" seperated by semi-colon

parser.add_argument("-exp", "--experiment", dest="experiment", default="CMS") ## add experiment name or some other text
''' add one more argument later to set the position of the legend ''' 


parser.add_argument("-plotType", "--plotType", dest="plotType", default="Preliminary")

parser.add_argument("-makeratio", "--makeratio", action="store_true", dest="makeratio")

parser.add_argument("-areaNormalize", "--areaNormalize", action="store_true", dest="areaNormalize")


parser.add_argument("-saveLog", "--saveLog",  dest="saveLog", default="Y" ) ## possible values it can accept, X, Y, XY, Z, XYZ, XZ, YZ


parser.add_argument("-saveType", "--saveType", dest="saveType", default=".pdf") ## you can save in more than one type, just provide them in double quotes seprated by single space 

#parser.add_argument("", "--", dest="", default="")


args = parser.parse_args()


from root_pandas import read_root
import numpy


def textToList(textfile):
    return [iline.rstrip()    for iline in open(textfile)]

def argsToList(arguments, delimator_=" "):
    arguments = arguments.replace("USD","$")
    return arguments.split(delimator_)

def getFileList(args_input_):
    fileList_=[]
    if ".txt" in args_input_:
        fileList_ = textToList(args_input_)
        print "reading the input files listed in the text file ", args_input_
    else:
        print "reading these files ",args_input_
        fileList_ = argsToList(args_input_)
    return fileList_


def treeToArray(filename_, treename_, variable_):
    ## this can be changed to uproot in future
    df = read_root(filename_, treename_, columns=[variable_])
    df = df[[variable_]]
    return numpy.array(df)


def GetColumn(readfrom_, filename_, treename_, variable_):
    ''' check the input type: TTree, TH1F or CSV ''' 
    column_=[]
    if readfrom_ == "TTree":
        column_ =  treeToArray(filename_, treename_, variable_)
    return column_

## ** -------------------------------** ##

## main code is here, all functions should be before this

## ** -------------------------------** ##

''' get the list of files ''' 
filelist =  getFileList(args.inputfile)
print filelist

''' get the variable array in a single variable, list ''' 
AllColumns=[ GetColumn(args.readFrom, ifile, args.treename, args.variable) for ifile in filelist]

print AllColumns


from plotutils import plotutils
pu_ = plotutils(columns=AllColumns, \
                binning=args.binning, \
                legend=argsToList(args.legend,";"), \
                axisTitle=argsToList(args.axistitle,delimator_=";"), \
                experiment=args.experiment, \
                plotType=args.plotType, \
                makeRatio=args.makeratio, \
                saveLog=args.saveLog, \
                areaNormalize = args.areaNormalize, \
                Xrange=argsToList(args.Xrange)
            )


# python makeplots.py  -i files.txt --readFrom TTree --treename monoHbb_SR_boosted --variable MET --binning 20 --legend "signal;top" --axistitle "p_{T}^miss;# of events" --plotMode overlay


if args.plotMode:
    pu_.plotOverlay()


