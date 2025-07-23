# parametrized DNN for the B2G 


# importing all modules
import uproot
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, accuracy_score


import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from torch.optim import Adam


# mass points
mass_points = [ 300, 400]

# correspondng Y Values

