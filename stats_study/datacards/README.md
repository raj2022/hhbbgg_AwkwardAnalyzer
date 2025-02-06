# Datacard prepration



- Convert the datacard to a workspace
```bash
text2workspace.py datacard.txt -o workspace.root
```

- Run combine for limit setting 
    -    Expected Limit Calculation
```bash
combine -M AsymptoticLimits -d workspace.root
```
    -  Signal Strength ($\mu$) Fit
    ```bash
    combine -M MaxLikelihoodFit -d workspace.root --saveShapes --saveWithUncertainties
    ```
    - Goodness of Fit (GOF) Test
    ```bash
    combine -M GoodnessOfFit -d workspace.root --algo=saturated
    ```

