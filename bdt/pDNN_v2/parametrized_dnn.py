
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import os

# Define a Parametrized DNN class
class ParametrizedDNN(nn.Module):
    def __init__(self, input_size, hidden_sizes, output_size, activation='relu', dropout_rate=0.0):
        super(ParametrizedDNN, self).__init__()
        self.layers = nn.ModuleList()
        self.activation_function = self._get_activation_function(activation)
        self.dropout_rate = dropout_rate

        prev_size = input_size
        for hidden_size in hidden_sizes:
            self.layers.append(nn.Linear(prev_size, hidden_size))
            prev_size = hidden_size

        self.layers.append(nn.Linear(prev_size, output_size))
        if dropout_rate > 0:
            self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        for layer in self.layers[:-1]:
            x = self.activation_function(layer(x))
            if self.dropout_rate > 0:
                x = self.dropout(x)
        return self.layers[-1](x)

    def _get_activation_function(self, activation):
        activations = {
            'relu': nn.ReLU(),
            'tanh': nn.Tanh(),
            'sigmoid': nn.Sigmoid(),
            'leaky_relu': nn.LeakyReLU()
        }
        return activations.get(activation, nn.ReLU())

def train(model, train_loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    for batch in train_loader:
        inputs, targets = batch
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(train_loader)

def evaluate(model, test_loader, criterion, device):
    model.eval()
    total_loss = 0
    with torch.no_grad():
        for batch in test_loader:
            inputs, targets = batch
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            total_loss += loss.item()
    return total_loss / len(test_loader)

def main(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load data
    X_train = np.load(args.train_data_x)
    y_train = np.load(args.train_data_y)
    X_test = np.load(args.test_data_x)
    y_test = np.load(args.test_data_y)

    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.long))
    test_dataset = TensorDataset(torch.tensor(X_test, dtype=torch.float32), torch.tensor(y_test, dtype=torch.long))

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size)

    # Model setup
    model = ParametrizedDNN(
        input_size=X_train.shape[1],
        hidden_sizes=args.hidden_sizes,
        output_size=len(np.unique(y_train)),
        activation=args.activation,
        dropout_rate=args.dropout_rate
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate, weight_decay=args.l2_reg)

    # Training loop
    for epoch in range(args.epochs):
        train_loss = train(model, train_loader, criterion, optimizer, device)
        test_loss = evaluate(model, test_loader, criterion, device)
        print(f'Epoch {epoch + 1}/{args.epochs}, Train Loss: {train_loss:.4f}, Test Loss: {test_loss:.4f}')

    # Save the model
    os.makedirs(args.output_dir, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(args.output_dir, 'dnn_model.pth'))
    print('Model saved to:', os.path.join(args.output_dir, 'dnn_model.pth'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train a Parametrized DNN on given data.')
    parser.add_argument('--train_data_x', type=str, required=True, help='Path to the training data (features).')
    parser.add_argument('--train_data_y', type=str, required=True, help='Path to the training data (labels).')
    parser.add_argument('--test_data_x', type=str, required=True, help='Path to the test data (features).')
    parser.add_argument('--test_data_y', type=str, required=True, help='Path to the test data (labels).')
    parser.add_argument('--hidden_sizes', nargs='+', type=int, default=[64, 128, 64], help='List of hidden layer sizes.')
    parser.add_argument('--activation', type=str, default='relu', help='Activation function: relu, tanh, sigmoid, etc.')
    parser.add_argument('--dropout_rate', type=float, default=0.0, help='Dropout rate.')
    parser.add_argument('--learning_rate', type=float, default=0.001, help='Learning rate for the optimizer.')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size for training.')
    parser.add_argument('--epochs', type=int, default=10, help='Number of training epochs.')
    parser.add_argument('--l2_reg', type=float, default=0.0, help='L2 regularization (weight decay).')
    parser.add_argument('--output_dir', type=str, default='./output', help='Directory to save the trained model.')

    args = parser.parse_args()
    main(args)

