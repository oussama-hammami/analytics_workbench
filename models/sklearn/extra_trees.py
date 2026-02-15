import os
import json
import joblib
import numpy as np
from typing import Dict, Any
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from models.base_model import BaseModel


class ExtraTreesModel(BaseModel):

    def __init__(self):
        super().__init__(name="Extra Trees", framework="sklearn")
        self._task = None
        self._build_kwargs = {}

    def build(self, task: str = 'classification', **kwargs) -> None:
        self._task = task
        self._build_kwargs = {k: v for k, v in kwargs.items() if k != 'task'}
        if task == 'classification':
            self.model = ExtraTreesClassifier(**self._build_kwargs)
        else:
            self.model = ExtraTreesRegressor(**self._build_kwargs)

    def train(self, X_train, y_train, X_val=None, y_val=None, **kwargs) -> Dict[str, Any]:
        if self.model is None:
            unique_count = y_train.nunique() if hasattr(y_train, 'nunique') else len(np.unique(y_train))
            task = 'classification' if unique_count < 20 else 'regression'
            self.build(task=task, **self._build_kwargs)
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
        key = 'extra_trees'
        with open(os.path.join(path, f"{key}_config.json"), 'r') as f:
            config = json.load(f)
        self._task = config.get('task', 'classification')
        self._build_kwargs = config.get('build_kwargs', {})
        self.model = joblib.load(os.path.join(path, f"{key}_weights.pkl"))
        self.is_trained = True

    def get_config(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'framework': self.framework,
            'registry_key': 'extra_trees',
            'task': self._task,
            'build_kwargs': self._build_kwargs,
        }
