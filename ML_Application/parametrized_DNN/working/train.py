import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
from sklearn.metrics import roc_curve, auc, accuracy_score
import matplotlib.pyplot as plt


def train_model(model, criterion, optimizer, dataloader, device):
    """
    Train the model for one epoch

    Args:
        model (nn.Module): The PyTorch model to train.
        criterion: Loss function
        optimizer: Optimization algorithm
        dataloader: DataLoader for training data
        device: Device to run training on (CPU/GPU)
        
    returns:
        float: Average loss for the epoch.
    """
    
    model.train()
    total_loss = 0
    for X_batch, y_batch in dataloader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        
        # Forward pass
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
    return total_loss/ len(dataloader)

def evaluate_model(model, dataloader, device):
    """
    Evaluate the model on test data.

    Args:
        model (nn.Module): The PyTorch model to evaluate.
        dataloader: DataLoader for test data.
        device: Device to run evaluation on (CPU/GPU).

    Returns:
        tuple: True labels, predicted probabilities.
    """
    model.eval()
    y_true, y_pred = [], []

    with torch.no_grad():
        for X_batch, y_batch in dataloader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            outputs = model(X_batch)
            y_true.extend(y_batch.cpu().numpy())
            y_pred.extend(outputs.cpu().numpy())

    return y_true, y_pred


def plot_roc_curve(y_true, y_pred):
    """
    Plot ROC curve and calculate AUC.

    Args:
        y_true (list): True labels.
        y_pred (list): Predicted probabilities.
    """
    fpr, tpr, _ = roc_curve(y_true, y_pred)
    roc_auc = auc(fpr, tpr)

    plt.figure()
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.show()

def train_and_evaluate(model, train_loader, test_loader, device, epochs=10, lr=0.001):
    """
    Train and evaluate the model.

    Args:
        model (nn.Module): The PyTorch model to train and evaluate.
        train_loader: DataLoader for training data.
        test_loader: DataLoader for testing data.
        device: Device to run training on (CPU/GPU).
        epochs (int): Number of training epochs.
        lr (float): Learning rate.
    """
    # Define loss and optimizer
    criterion = nn.BCELoss()
    optimizer = Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        train_loss = train_model(model, criterion, optimizer, train_loader, device)
        print(f"Epoch {epoch + 1}/{epochs}, Loss: {train_loss:.4f}")

    # Evaluate the model
    y_true, y_pred = evaluate_model(model, test_loader, device)
    plot_roc_curve(y_true, y_pred)
    print(f"Accuracy: {accuracy_score(y_true, (np.array(y_pred) > 0.5).astype(int)):.2f}")

