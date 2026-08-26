import os
import sys

command = 'for file in $(ls ' + sys.argv[1] + '*.err); do if grep -q -m 1 "Traceback" $file; then echo $file; fi; done'
results = os.popen(command).readlines()
for iresult, result in enumerate(results):
    results[iresult] = result.strip("\n").split(".")[-2]
print(str(len(results)) + " jobs with 'Traceback', to be resubmitted:")
print("(" + " ".join(results) + ")")

command = 'for file in $(ls ' + sys.argv[1] + '*.out); do if grep -q -m 1 "No surviving events" $file; then echo $file; fi; done'
results = os.popen(command).readlines()
for iresult, result in enumerate(results):
    results[iresult] = result.strip("\n").split(".")[-2]
print(str(len(results)) + " jobs with 'No surviving events', nothing to do...")
print("(" + " ".join(results) + ")")
