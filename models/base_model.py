from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import numpy as np
import os
import json
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, mean_squared_error, mean_absolute_error,
    root_mean_squared_error
)


class BaseModel(ABC):
    """
    Unified interface for all models in the platform.

    Attributes:
        name: Human-readable model name
        framework: One of 'sklearn', 'keras', 'pytorch'
        model: The underlying model object
        is_trained: Whether the model has been trained
        metrics: Evaluation metrics from the last evaluate() call
        history: Training history (loss/accuracy curves for DL, empty for sklearn)
    """

    def __init__(self, name: str, framework: str):
        self.name: str = name
        self.framework: str = framework
        self.model: Any = None
        self.is_trained: bool = False
        self.metrics: Dict[str, Any] = {}
        self.history: Dict[str, Any] = {}

    @abstractmethod
    def build(self, **kwargs) -> None:
        """Construct the underlying model object and assign to self.model."""
        pass

    @abstractmethod
    def train(self, X_train, y_train, X_val=None, y_val=None, **kwargs) -> Dict[str, Any]:
        """Train self.model. Sets self.is_trained = True. Returns training history."""
        pass

    @abstractmethod
    def predict(self, X) -> np.ndarray:
        """Generate predictions using the trained model."""
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model weights + config.json to the given directory."""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load model from directory (reads config.json, then weights)."""
        pass

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the model's configuration."""
        pass

    def evaluate(self, X, y, task: str = 'classification') -> Dict[str, Any]:
        """
        Evaluate the trained model using sklearn metrics.
        Concrete method shared by all models.
        """
        if not self.is_trained:
            raise RuntimeError(f"Model '{self.name}' has not been trained yet.")

        y_pred = self.predict(X)

        metrics = {}
        if task == 'classification':
            if len(y_pred.shape) > 1 and y_pred.shape[1] > 1:
                y_pred = y_pred.argmax(axis=1)

            y_true = y.values if hasattr(y, 'values') else np.array(y)
            if len(y_true.shape) > 1 and y_true.shape[1] > 1:
                y_true = y_true.argmax(axis=1)

            metrics['accuracy'] = float(accuracy_score(y_true, y_pred))
            metrics['precision'] = float(precision_score(y_true, y_pred, average='weighted', zero_division=0))
            metrics['recall'] = float(recall_score(y_true, y_pred, average='weighted', zero_division=0))
            metrics['f1'] = float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
            metrics['confusion_matrix'] = confusion_matrix(y_true, y_pred).tolist()
        else:
            y_np = y.values if hasattr(y, 'values') else np.array(y)
            y_pred_flat = y_pred.flatten()
            metrics['mse'] = float(mean_squared_error(y_np, y_pred_flat))
            metrics['mae'] = float(mean_absolute_error(y_np, y_pred_flat))
            metrics['rmse'] = float(root_mean_squared_error(y_np, y_pred_flat))

        self.metrics = metrics
        return metrics

    def __repr__(self):
        status = "trained" if self.is_trained else "untrained"
        return f"<{self.__class__.__name__}(name='{self.name}', framework='{self.framework}', {status})>"
