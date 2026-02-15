import os
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any
from models.base_model import BaseModel


class _CNNNetwork(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden_units: int = 32):
        super().__init__()
        self.conv1 = nn.Conv1d(1, hidden_units, kernel_size=3, padding=1)
        self.pool = nn.MaxPool1d(2)
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(hidden_units * (input_dim // 2), hidden_units)
        self.fc2 = nn.Linear(hidden_units, output_dim)
        self.relu = nn.ReLU()

    def forward(self, x):
        if len(x.shape) == 2:
            x = x.unsqueeze(1)
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.flatten(x)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class PytorchCNNModel(BaseModel):

    def __init__(self):
        super().__init__(name="PyTorch CNN", framework="pytorch")
        self._build_config = {}
        self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def build(self, input_dim: int = None, output_dim: int = None, **kwargs) -> None:
        hidden_units = kwargs.get('hidden_units', 32)
        task = kwargs.get('task', 'classification')
        self._build_config = {
            'input_dim': input_dim,
            'output_dim': output_dim,
            'hidden_units': hidden_units,
            'task': task,
        }
        self.model = _CNNNetwork(input_dim, output_dim, hidden_units)
        self.model.to(self._device)

    def train(self, X_train, y_train, X_val=None, y_val=None, **kwargs) -> Dict[str, Any]:
        epochs = kwargs.get('epochs', 10)
        batch_size = kwargs.get('batch_size', 32)
        lr = kwargs.get('lr', 0.001)
        task = self._build_config.get('task', 'classification')

        X = X_train.values if hasattr(X_train, 'values') else np.array(X_train)
        y = y_train.values if hasattr(y_train, 'values') else np.array(y_train)

        X_tensor = torch.tensor(X, dtype=torch.float32).to(self._device)

        if task == 'regression':
            y_tensor = torch.tensor(y, dtype=torch.float32).reshape(-1, 1).to(self._device)
            loss_function = nn.MSELoss()
        else:
            y_tensor = torch.tensor(y, dtype=torch.long).to(self._device)
            loss_function = nn.CrossEntropyLoss()

        optimizer = optim.Adam(self.model.parameters(), lr=lr)

        history_loss = []
        self.model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = loss_function(outputs, y_tensor)
            loss.backward()
            optimizer.step()
            history_loss.append(loss.item())

        self.history = {'loss': history_loss}
        self.is_trained = True
        return self.history

    def predict(self, X) -> np.ndarray:
        X_arr = X.values if hasattr(X, 'values') else np.array(X)
        X_tensor = torch.tensor(X_arr, dtype=torch.float32).to(self._device)
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X_tensor)
        return outputs.cpu().numpy()

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        key = self.get_config()['registry_key']
        torch.save(self.model.state_dict(), os.path.join(path, f"{key}_weights.pth"))
        with open(os.path.join(path, f"{key}_config.json"), 'w') as f:
            json.dump(self.get_config(), f, indent=2)

    def load(self, path: str) -> None:
        key = 'pytorch_cnn'
        with open(os.path.join(path, f"{key}_config.json"), 'r') as f:
            config = json.load(f)
        self._build_config = config.get('build_config', {})
        self.build(**self._build_config)
        self.model.load_state_dict(
            torch.load(os.path.join(path, f"{key}_weights.pth"), map_location=self._device)
        )
        self.model.eval()
        self.is_trained = True

    def get_config(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'framework': self.framework,
            'registry_key': 'pytorch_cnn',
            'build_config': self._build_config,
        }
