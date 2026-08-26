import os
import sys

command = 'ls ' + sys.argv[1] + '*Events_0* -1 | wc -l'
results = os.system(command)
print("...condor jobs produced output.")
