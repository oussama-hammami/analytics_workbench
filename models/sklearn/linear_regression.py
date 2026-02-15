import os
import json
import joblib
import numpy as np
from typing import Dict, Any
from sklearn.linear_model import LinearRegression
from models.base_model import BaseModel


class LinearRegressionModel(BaseModel):

    def __init__(self):
        super().__init__(name="Linear Regression", framework="sklearn")
        self._build_kwargs = {}

    def build(self, **kwargs) -> None:
        self._build_kwargs = {k: v for k, v in kwargs.items() if k != 'task'}
        self.model = LinearRegression(**self._build_kwargs)

    def train(self, X_train, y_train, X_val=None, y_val=None, **kwargs) -> Dict[str, Any]:
        if self.model is None:
            self.build(**self._build_kwargs)
        X = X_train.values if hasattr(X_train, 'values') else np.array(X_train)
        y = y_train.values if hasattr(y_train, 'values') else np.array(y_train)
        self.model.fit(X, y)
        self.is_trained = True
        self.history = {}
        return self.history

    def predict(self, X) -> np.ndarray:
        X_arr = X.values if hasattr(X, 'values') else np.array(X)
        return self.model.predict(X_arr)

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        key = self.get_config()['registry_key']
        joblib.dump(self.model, os.path.join(path, f"{key}_weights.pkl"))
        with open(os.path.join(path, f"{key}_config.json"), 'w') as f:
            json.dump(self.get_config(), f, indent=2)

    def load(self, path: str) -> None:
        key = 'linear_regression'
        with open(os.path.join(path, f"{key}_config.json"), 'r') as f:
            config = json.load(f)
        self._build_kwargs = config.get('build_kwargs', {})
        self.model = joblib.load(os.path.join(path, f"{key}_weights.pkl"))
        self.is_trained = True

    def get_config(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'framework': self.framework,
            'registry_key': 'linear_regression',
            'build_kwargs': self._build_kwargs,
        }
