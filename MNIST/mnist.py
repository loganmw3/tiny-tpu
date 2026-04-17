import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import numpy as np

# =========================
# CONFIG
# =========================
EPOCHS = 30
BATCH_SIZE = 64
LR = 0.001
SAVE_PATH = "mnist_weights.npy"

# =========================
# DATA
# =========================
transform = transforms.ToTensor()

trainset = torchvision.datasets.MNIST(
    root="./data",
    train=True,
    download=True,
    transform=transform
)

trainloader = torch.utils.data.DataLoader(
    trainset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

# =========================
# MODEL (simple + TPU-friendly)
# =========================
class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(28*28, 128)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = x.view(-1, 28*28)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x

model = Net()

# =========================
# TRAINING
# =========================
optimizer = torch.optim.Adam(model.parameters(), lr=LR)
loss_fn = nn.CrossEntropyLoss()

print("Starting training...")

for epoch in range(EPOCHS):
    total_loss = 0
    for images, labels in trainloader:
        optimizer.zero_grad()

        outputs = model(images)
        loss = loss_fn(outputs, labels)

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch+1}/{EPOCHS}, Loss: {total_loss:.4f}")

print("Training complete.")

# =========================
# SAVE WEIGHTS
# =========================
weights = {}

for name, param in model.named_parameters():
    weights[name] = param.detach().numpy()

print(weights)

np.save(SAVE_PATH, weights)

print(f"Weights saved to {SAVE_PATH}")