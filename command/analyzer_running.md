# Scripts to run the analyzer
- 2022 only (PreEE + PostEE)
```bash
python hhbbgg_analyzer_multiple.py \
  --config-years 2022 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022/PreEE/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022/PostEE/scored \
  --tag 2022
```
- 2023 only (preBPix + postBPix)
```bash
python hhbbgg_analyzer_multiple.py \
  --config-years 2023 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023/preBPix/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023/postBPix/scored \
  --tag 2023
```

- 2022 + 2023 
```bash
python hhbbgg_analyzer_multiple.py \
  --config-years 2022,2023 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022/PreEE/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022/PostEE/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023/preBPix/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023/postBPix/scored \
  --tag 22plus23
```
- 2022 + 2023 + 2024
```bash
python hhbbgg_analyzer_multiple.py \
  --config-years 2022,2023,2024 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022/PreEE/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022/PostEE/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023/preBPix/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023/postBPix/scored \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2024/scored \
  --tag 22plus23plus24
```

If you don’t care about the tag name, you can omit `--tag`:
```bash
python hhbbgg_analyzer_multiple.py \
  --config-years 2022,2023 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2022 \
  -i /afs/cern.ch/user/s/sraj/Analysis/output_root/sample_final_nominal/2023
```
Output directory:
```bash
outputfiles/merged/2022_2023/
```