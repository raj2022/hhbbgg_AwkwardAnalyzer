# Paraemtrized DNN on the v2 HiggsDNA files
for the DNN training we were training seperately for each mass points. For the parametrized DNN, we will provide weights as well for the sample training. We divided the mass point ijnto different ranges based on its kinematics. 
With parametrized DNN, where we will provides weights into the model during the traning and we will be able to do the training for all sample in once.

Parametrized DNN on the dataset, we can implement as follows:
* pNN method is employed for a wide range of mass points
    * Train on all signal MC{m1, m2, m3...}
    * Give background MC random values of mass from {m1, m2, m3...}
*  Provide same input variable as DNN
* Split the MC signal in half, with one half used as input for the classifier, andtheother half(weight ×2) will be used for the final signal model construction
$$
f(\vec{x}; m) =
\begin{cases} 
f^1(\vec{x}) & \text{if } m = m_1 \\
f^2(\vec{x}) & \text{if } m = m_2 \\
\vdots
\end{cases}
$$
for the above taken from this preentation, [here](https://indico.cern.ch/event/1507349/contributions/6364202/attachments/3009726/5317821/preapproval.pdf)

# Loading saved model
```python
model = ParameterizedDNN(input_dim)
model.load_state_dict(torch.load("best_parametric_model.pt"))
model.to(device)
model.eval()
```



## For running the inference
- Fit on inference sample (recommended fallback)

bash
Copy code

```bash
python inference_PDnn.py \
  --points 400:125 500:95 \
  --model best_pdnn.pt \
  --signal-root ../../../output_parquet/final_production_Syst/merged \
  --bkg "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GGJets/preselection" \
       "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GJetPt20To40/preselection" \
       "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GJetPt40/preselection" \
  --background-frac 0.3 \
  --fit-scaler-on-inference \
  --outdir inference_outputs

```

- inference_outputs/inference_scores.csv
    - per‑point plots:
        - sep_unweighted_X400_Y125.png
        - sep_weighted_logy_X400_Y125.png
        - sep_weighted_density_X400_Y125.png
        - roc_X400_Y125.png (if both S and B present)
- No scaling at all

```bash
python inference_PDnn.py \
  --points 400:125 500:95 \
  --model best_pdnn.pt \
  --signal-root ../../../output_parquet/final_production_Syst/merged \
  --bkg "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GGJets/preselection" \
       "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GJetPt20To40/preselection" \
       "../../outputfiles/hhbbgg_analyzer-v2-trees.root::/GJetPt40/preselection" \
  --background-frac 0.3 \
  --no-scaler \
  --outdir inference_outputs
```

## Ref
1. https://link.springer.com/article/10.1140/epjc/s10052-016-4099-4
2. https://arxiv.org/pdf/2202.00424




# As of Sept 30, 2025

To run the `pDNN`
```bash
- python pDNN_check_working_f.py # working code with best model. 
```

- Instruction to run inference:
We are woking on the https://github.com/raj2022/hhbbgg_AwkwardAnalyzer/blob/run3_all/ML_Application/parametrized_DNN/parametrized_DNN_score.ipynb


```bash
 # simplest: artifacts in current folder (best_pdnn.pt, scaler.pkl, features_used.json)
python inference_PDnn.py -i /path/to/your/folder

# if artifacts live elsewhere:
python inference_PDnn.py -i /path/to/folder --artifacts /path/to/artifacts

# write output somewhere specific:
python inference_PDnn.py -i /path/to/folder -o /path/to/output

# recurse into subfolders and change pattern:
python inference_PDnn.py -i /path/to/folder --recursive --pattern "*_skim.parquet"

 ```


 Example to run on the folder:
 `python inference_PDnn.py -i ~/Analysis/output_root/v3_production/samples/postBPix/`
 - this would create a new folder with  `scored`, just to not mess with the original one.

