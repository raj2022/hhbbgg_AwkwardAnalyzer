import torch
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
from utils import load_data, combine_dataframes, preprocess_data, split_data
from config import SIGNAL_FILES, BACKGROUND_FILES, COLUMNS, TEST_SIZE, RANDOM_STATE
from model import DNN
from train import train_and_evaluate

def main():
    # Device configuration
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load and preprocess signal and background data
    signal_data = load_data(SIGNAL_FILES, COLUMNS)
    background_data = load_data(BACKGROUND_FILES, COLUMNS)

    signal_df = combine_dataframes(signal_data, include_keys=["NMSSM"])
    background_df = combine_dataframes(background_data, include_keys=["GGJets", "GJetPt"])

    signal_df = preprocess_data(signal_df, label=1)
    background_df = preprocess_data(background_df, label=0)

    # Split data into train and test sets
    X_train, X_test, y_train, y_test = split_data(signal_df, background_df, test_size=TEST_SIZE)

    # Convert data to PyTorch tensors
    train_dataset = TensorDataset(torch.tensor(X_train.values, dtype=torch.float32),
                                  torch.tensor(y_train.values, dtype=torch.float32))
    test_dataset = TensorDataset(torch.tensor(X_test.values, dtype=torch.float32),
                                 torch.tensor(y_test.values, dtype=torch.float32))

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

    # Initialize model
    input_dim = X_train.shape[1]
    model = DNN(input_dim).to(device)

    # Train and evaluate the model
    train_and_evaluate(model, train_loader, test_loader, device, epochs=20, lr=0.001)

if __name__ == "__main__":
    main()
