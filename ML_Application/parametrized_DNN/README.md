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


## Ref
1. https://link.springer.com/article/10.1140/epjc/s10052-016-4099-4
2. https://arxiv.org/pdf/2202.00424
