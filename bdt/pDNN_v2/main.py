import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

class ParametrizedDNN(nn.Module):
    def __init__(self, input_size, hidden_sizes, output_size, activation='relu', dropout_rate=0.0):
        """
        Parameters:
        - input_size (int): Size of the input features.
        - hidden_sizes (list of int): List containing the sizes of the hidden layers.
        - output_size (int): Size of the output layer (number of classes or regression outputs).
        - activation (str): Activation function ('relu', 'tanh', 'sigmoid', etc.).
        - dropout_rate (float): Dropout rate (default is 0.0, meaning no dropout).
        """
        super(ParametrizedDNN, self).__init__()

        self.layers = nn.ModuleList()
        self.activation_function = self._get_activation_function(activation)
        self.dropout_rate = dropout_rate

        # Input layer
        prev_size = input_size
        
        # Hidden layers
        for hidden_size in hidden_sizes:
            self.layers.append(nn.Linear(prev_size, hidden_size))
            prev_size = hidden_size

        # Output layer
        self.layers.append(nn.Linear(prev_size, output_size))

        # Dropout layer if specified
        if dropout_rate > 0:
            self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        for layer in self.layers[:-1]:
            x = layer(x)
            x = self.activation_function(x)
            if self.dropout_rate > 0:
                x = self.dropout(x)

        # Output layer without activation
        x = self.layers[-1](x)
        return x

    def _get_activation_function(self, activation):
        activation = activation.lower()
        if activation == 'relu':
            return F.relu
        elif activation == 'tanh':
            return torch.tanh
        elif activation == 'sigmoid':
            return torch.sigmoid
        elif activation == 'leaky_relu':
            return F.leaky_relu
        else:
            raise ValueError(f"Unsupported activation function: {activation}")

# Example usage
if __name__ == "__main__":
