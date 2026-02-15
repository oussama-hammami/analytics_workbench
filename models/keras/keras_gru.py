import os
import json
import numpy as np
from typing import Dict, Any
from tensorflow import keras
from tensorflow.keras import layers, models
from models.base_model import BaseModel


class KerasGRUModel(BaseModel):

    def __init__(self):
        super().__init__(name="Keras GRU", framework="keras")
        self._build_config = {}

    def build(self, input_shape: int = None, output_shape: int = None, **kwargs) -> None:
        hidden_units = kwargs.get('hidden_units', 32)
        optimizer = kwargs.get('optimizer', 'adam')
        loss = kwargs.get('loss', 'categorical_crossentropy')
        output_activation = kwargs.get('output_activation', 'softmax')
        metrics_list = kwargs.get('metrics', ['accuracy'])

        self._build_config = {
            'input_shape': input_shape,
            'output_shape': output_shape,
            'hidden_units': hidden_units,
            'optimizer': optimizer,
            'loss': loss,
            'output_activation': output_activation,
        }

        self.model = models.Sequential([
            layers.Input(shape=(input_shape, 1)),
            layers.GRU(hidden_units),
            layers.Dense(output_shape, activation=output_activation)
        ])
        self.model.compile(optimizer=optimizer, loss=loss, metrics=metrics_list)

    def _reshape(self, X):
        X_arr = X.values if hasattr(X, 'values') else np.array(X)
        if len(X_arr.shape) == 2:
            X_arr = X_arr.reshape(X_arr.shape[0], X_arr.shape[1], 1)
        return X_arr

    def train(self, X_train, y_train, X_val=None, y_val=None, **kwargs) -> Dict[str, Any]:
        epochs = kwargs.get('epochs', 10)
        batch_size = kwargs.get('batch_size', 32)

        X = self._reshape(X_train)
        y = y_train.values if hasattr(y_train, 'values') else np.array(y_train)

        validation_data = None
        if X_val is not None and y_val is not None:
            X_v = self._reshape(X_val)
            y_v = y_val.values if hasattr(y_val, 'values') else np.array(y_val)
            validation_data = (X_v, y_v)

        history = self.model.fit(
            X, y,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0
        )
        self.history = history.history
        self.is_trained = True
        return self.history

    def predict(self, X) -> np.ndarray:
        return self.model.predict(self._reshape(X), verbose=0)

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        key = self.get_config()['registry_key']
        self.model.save(os.path.join(path, f"{key}_weights.h5"))
        with open(os.path.join(path, f"{key}_config.json"), 'w') as f:
            json.dump(self.get_config(), f, indent=2)

    def load(self, path: str) -> None:
        key = 'keras_gru'
        with open(os.path.join(path, f"{key}_config.json"), 'r') as f:
            config = json.load(f)
        self._build_config = config.get('build_config', {})
        self.model = keras.models.load_model(os.path.join(path, f"{key}_weights.h5"), compile=False)
        self.is_trained = True

    def get_config(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'framework': self.framework,
            'registry_key': 'keras_gru',
            'build_config': self._build_config,
        }
