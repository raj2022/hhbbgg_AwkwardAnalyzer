# %%
import torch
from torch import nn
import numpy as np
import matplotlib.pyplot as plt
from ROOT import TMVA, TFile, TTree, TCut
from subprocess import call
from os.path import isfile

# %%
# Setup TMVA
TMVA.Tools.Instance()
TMVA.PyMethodBase.PyInitialize()

# create factory without output file since it is not needed
factory = TMVA.Factory(
    "TMVAClassification",

    "!V:!Silent:Color:DrawProgressBar:Transformations=D,G:AnalysisType=Classification",
)

# %%
# Input variables
keys = [
    'bbgg_mass',
    'dibjet_pt',
    'diphoton_pt',
    'bbgg_pt',
    'lead_pho_pt',
    'sublead_pho_pt',
    'bbgg_eta',
    'bbgg_phi',
    'lead_pho_eta',
    'lead_pho_phi',
    'sublead_pho_eta',
    'sublead_pho_phi',
    'diphoton_eta',
    'diphoton_phi',
    'dibjet_eta',
    'dibjet_phi',
    'lead_bjet_pt',
    'sublead_bjet_pt',
    'lead_bjet_eta',
    'lead_bjet_phi',
    'sublead_bjet_eta',
    'sublead_bjet_phi',
    'sublead_bjet_PNetB',
    'lead_bjet_PNetB',
    'CosThetaStar_gg',
    'CosThetaStar_jj',
    'CosThetaStar_CS',
    'DeltaR_jg_min',
    'pholead_PtOverM',
    'phosublead_PtOverM',
    'FirstJet_PtOverM',
    'SecondJet_PtOverM',
    'lead_pt_over_diphoton_mass',
    'sublead_pt_over_diphoton_mass',
    'lead_pt_over_dibjet_mass',
    'sublead_pt_over_dibjet_mass',
    'diphoton_bbgg_mass',
    'dibjet_bbgg_mass',
]
# %%
# Load data
data = TFile.Open("../../outputfiles/hhbbgg_analyzer-trees.root")
signal = data.Get("GluGluToHH/preselection")
backgrounds = [data.Get("GGJets/preselection"),data.Get("GJetPt20To40/preselection"),data.Get("GJetPt40/preselection")]

dataloader = TMVA.DataLoader("dataset")

for key in keys:
    dataloader.AddVariable(key)

dataloader.AddSignalTree(signal, 1.0)
dataloader.SetSignalWeightExpression("weight_preselection")
for background in backgrounds:
    dataloader.AddBackgroundTree(background, 1.0)
dataloader.PrepareTrainingAndTestTree(
    TCut(""),
    "nTrain_Signal=4000:nTrain_Background=4000:SplitMode=Random:NormMode=NumEvents:!V",
)
dataloader.SetBackgroundWeightExpression("weight_preselection")
# %%
# Define model
model = nn.Sequential()
model.add_module("linear_1", nn.Linear(in_features=len(keys), out_features=64))
model.add_module("relu", nn.ReLU())
model.add_module("linear_2", nn.Linear(in_features=64, out_features=2))
model.add_module("softmax", nn.Softmax(dim=1))


# Construct loss function and Optimizer.
loss = torch.nn.MSELoss()
optimizer = torch.optim.SGD


# %%
# Define train function
def train(
    model,
    train_loader,
    val_loader,
    num_epochs,
    batch_size,
    optimizer,
    criterion,
    save_best,
    scheduler,
):
    trainer = optimizer(model.parameters(), lr=0.01)
    schedule, schedulerSteps = scheduler
    best_val = None

    for epoch in range(num_epochs):
        # Training Loop
        # Set to train mode
        model.train()
        running_train_loss = 0.0
        running_val_loss = 0.0
        for i, (X, y) in enumerate(train_loader):
            trainer.zero_grad()
            output = model(X)
            train_loss = criterion(output, y)
            train_loss.backward()
            trainer.step()

            # print train statistics
            running_train_loss += train_loss.item()
            if i % 32 == 31:  # print every 32 mini-batches
                print(
                    "[{}, {}] train loss: {:.3f}".format(
                        epoch + 1, i + 1, running_train_loss / 32
                    )
                )
                running_train_loss = 0.0

        if schedule:
            schedule(optimizer, epoch, schedulerSteps)

        # Validation Loop
        # Set to eval mode
        model.eval()
        with torch.no_grad():
            for i, (X, y) in enumerate(val_loader):
                output = model(X)
                val_loss = criterion(output, y)
                running_val_loss += val_loss.item()

            curr_val = running_val_loss / len(val_loader)
            if save_best:
                if best_val == None:
                    best_val = curr_val
                best_val = save_best(model, curr_val, best_val)

            # print val statistics per epoch
            print("[{}] val loss: {:.3f}".format(epoch + 1, curr_val))
            running_val_loss = 0.0

    print("Finished Training on {} Epochs!".format(epoch + 1))

    return model


# %%
# Define predict function
def predict(model, test_X, batch_size=32):
    # Set to eval mode
    model.eval()

    test_dataset = torch.utils.data.TensorDataset(torch.Tensor(test_X))
    test_loader = torch.utils.data.DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False
    )

    predictions = []
    with torch.no_grad():
        for i, data in enumerate(test_loader):
            X = data[0]
            outputs = model(X)
            predictions.append(outputs)
        preds = torch.cat(predictions)

    return preds.numpy()


# %%
# Load model objects
load_model_custom_objects = {
    "optimizer": optimizer,
    "criterion": loss,
    "train_func": train,
    "predict_func": predict,
}

# %%
# Convert the model to torchscript before saving
m = torch.jit.script(model)
torch.jit.save(m, "modelClassification.pt")
print(m)

# %%
# Book methods
factory.BookMethod(
    dataloader,
    TMVA.Types.kPyTorch,
    "PyTorch",
    "!H:!V:VarTransform=D,G:FilenameModel=modelClassification.pt:FilenameTrainedModel=trainedModelClassification.pt:NumEpochs=20:BatchSize=32",
)


# %%
# Run training, test and evaluation
factory.TrainAllMethods()
factory.TestAllMethods()
factory.EvaluateAllMethods()

# %%
# Plot ROC Curves
roc = factory.GetROCCurve(dataloader)
roc.SaveAs("dnnplots/ROC_ClassificationPyTorch.png")
roc.SaveAs("dnnplots/ROC_ClassificationPyTorch.pdf")

# %%
# Define a function to extract data from ROOT tree
def extract_data(tree, keys):
    n_entries = tree.GetEntries()
    data = np.zeros((n_entries, len(keys)))

    for i in range(n_entries):
        tree.GetEntry(i)
        for j, key in enumerate(keys):
            data[i, j] = getattr(tree, key)

    return data

# %%

# Load the data (replace with actual data loading code)
signal_data =  extract_data(signal, keys)
background_data = np.concatenate([extract_data(background, keys) for background in backgrounds])

signal_tensor = torch.tensor(signal_data, dtype=torch.float32)
background_tensor = torch.tensor(background_data, dtype=torch.float32)

# Create labels
signal_labels = torch.ones(len(signal_tensor))
background_labels = torch.zeros(len(background_tensor))

# Create datasets
signal_dataset = torch.utils.data.TensorDataset(signal_tensor, signal_labels)
background_dataset = torch.utils.data.TensorDataset(background_tensor, background_labels)

m.eval()

# Function to evaluate the model on a dataset
def evaluate_model(model, dataset, batch_size=32):
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False)
    scores = []
    labels = []
    with torch.no_grad():
        for data, label in dataloader:
            output = model(data)
            scores.append(output[:, 1].cpu().numpy())  # Assuming the second output is the score for signal
            labels.append(label.cpu().numpy())
    return np.concatenate(scores), np.concatenate(labels)

# Evaluate the model
signal_scores, signal_labels = evaluate_model(m, signal_dataset)
background_scores, background_labels = evaluate_model(m, background_dataset)

# Plot Signal and Background Discriminator
plt.figure(figsize=(10, 6))
plt.hist(signal_scores, bins=50, alpha=0.5, label='Signal', color='r', density=True)
plt.hist(background_scores, bins=50, alpha=0.5, label='Background', color='b', density=True)
plt.xlabel('Discriminator Score')
plt.ylabel('Density')
plt.legend(loc='best')
plt.title('Signal and Background Discriminator Scores')
plt.savefig('dnnplots/Discriminator_Scores.png')
plt.savefig('dnnplots/Discriminator_Scores.pdf')
plt.close()
# plt.show()

# Plot the score of input variables
def plot_variable_distribution(signal_data, background_data, variable_name, bins=50):
    plt.figure(figsize=(10, 6))
    plt.hist(signal_data, bins=bins, alpha=0.5, label='Signal', color='r', density=True)
    plt.hist(background_data, bins=bins, alpha=0.5, label='Background', color='b', density=True)
    plt.xlabel(variable_name)
    plt.ylabel('Density')
    plt.legend(loc='best')
    plt.title(f'Distribution of {variable_name}')
    plt.savefig(f'dnnplots/{variable_name}_Distribution.png')
    plt.savefig(f'dnnplots/{variable_name}_Distribution.pdf')
    # plt.show()

for i, key in enumerate(keys):
    plot_variable_distribution(signal_data[:, i], background_data[:, i], key)
    plt.close()