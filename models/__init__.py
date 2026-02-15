import os
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import json
from models.base_model import BaseModel

from models.sklearn.linear_regression import LinearRegressionModel
from models.sklearn.logistic_regression import LogisticRegressionModel
from models.sklearn.random_forest import RandomForestModel
from models.sklearn.extra_trees import ExtraTreesModel
from models.sklearn.svm import SVMModel
from models.sklearn.knn import KNNModel

from models.keras.keras_mlp import KerasMLPModel
from models.keras.keras_cnn import KerasCNNModel
from models.keras.keras_rnn import KerasRNNModel
from models.keras.keras_lstm import KerasLSTMModel
from models.keras.keras_gru import KerasGRUModel

from models.pytorch.pytorch_mlp import PytorchMLPModel
from models.pytorch.pytorch_cnn import PytorchCNNModel
from models.pytorch.pytorch_rnn import PytorchRNNModel
from models.pytorch.pytorch_lstm import PytorchLSTMModel
from models.pytorch.pytorch_gru import PytorchGRUModel

MODEL_REGISTRY = {
    # Sklearn
    "linear_regression": LinearRegressionModel,
    "logistic_regression": LogisticRegressionModel,
    "random_forest": RandomForestModel,
    "extra_trees": ExtraTreesModel,
    "svm": SVMModel,
    "knn": KNNModel,
    # Keras
    "keras_mlp": KerasMLPModel,
    "keras_cnn": KerasCNNModel,
    "keras_rnn": KerasRNNModel,
    "keras_lstm": KerasLSTMModel,
    "keras_gru": KerasGRUModel,
    # PyTorch
    "pytorch_mlp": PytorchMLPModel,
    "pytorch_cnn": PytorchCNNModel,
    "pytorch_rnn": PytorchRNNModel,
    "pytorch_lstm": PytorchLSTMModel,
    "pytorch_gru": PytorchGRUModel,
}

FRAMEWORK_MODELS = {
    "Scikit-Learn": ["linear_regression", "logistic_regression", "random_forest", "extra_trees", "svm", "knn"],
    "Keras": ["keras_mlp", "keras_cnn", "keras_rnn", "keras_lstm", "keras_gru"],
    "PyTorch": ["pytorch_mlp", "pytorch_cnn", "pytorch_rnn", "pytorch_lstm", "pytorch_gru"],
}

# Maps each model to its supported task types
MODEL_SUPPORTED_TASKS = {
    # Sklearn
    "linear_regression": ["regression"],
    "logistic_regression": ["classification"],
    "random_forest": ["classification", "regression"],
    "extra_trees": ["classification", "regression"],
    "svm": ["classification", "regression"],
    "knn": ["classification", "regression"],
    # Keras
    "keras_mlp": ["classification", "regression"],
    "keras_cnn": ["classification", "regression"],
    "keras_rnn": ["classification", "regression"],
    "keras_lstm": ["classification", "regression"],
    "keras_gru": ["classification", "regression"],
    # PyTorch
    "pytorch_mlp": ["classification", "regression"],
    "pytorch_cnn": ["classification", "regression"],
    "pytorch_rnn": ["classification", "regression"],
    "pytorch_lstm": ["classification", "regression"],
    "pytorch_gru": ["classification", "regression"],
}


def get_model(name: str) -> BaseModel:
    """Factory function. Returns a new untrained model instance."""
    if name not in MODEL_REGISTRY:
        raise KeyError(f"Unknown model '{name}'. Available: {list(MODEL_REGISTRY.keys())}")
    return MODEL_REGISTRY[name]()


def list_models(framework: str = None) -> list:
    """Returns available model registry keys, optionally filtered by framework."""
    if framework is None:
        return list(MODEL_REGISTRY.keys())
    return FRAMEWORK_MODELS.get(framework, [])


import glob as _glob


def load_model_from_path(path: str) -> BaseModel:
    """Load a single saved model. Looks for {key}_config.json files first,
    falls back to legacy config.json for backwards compatibility."""
    config_files = sorted(_glob.glob(os.path.join(path, "*_config.json")))
    if config_files:
        with open(config_files[0], 'r') as f:
            config = json.load(f)
    else:
        with open(os.path.join(path, "config.json"), 'r') as f:
            config = json.load(f)
    model_key = config['registry_key']
    model = get_model(model_key)
    model.load(path)
    return model


def load_all_models_from_path(path: str) -> dict:
    """Load all saved models from a directory.
    Returns a dict mapping registry_key -> loaded model instance."""
    models = {}
    config_files = sorted(_glob.glob(os.path.join(path, "*_config.json")))
    for config_file in config_files:
        with open(config_file, 'r') as f:
            config = json.load(f)
        model_key = config['registry_key']
        model = get_model(model_key)
        model.load(path)
        models[model_key] = model
    return models
