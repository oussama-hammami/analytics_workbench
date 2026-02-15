"""
Helper utilities for the AI/ML platform.
"""
from typing import Any, Dict
import os
import joblib
import json
import yaml

def save_object(obj: Any, path: str) -> None:
    """
    Saves a Python object to disk using joblib.
    Args:
        obj: Object to save.
        path: File path.
    """
    joblib.dump(obj, path)

def load_object(path: str) -> Any:
    """
    Loads a Python object from disk using joblib.
    Args:
        path: File path.
    Returns:
        Loaded object.
    """
    return joblib.load(path)

def save_json(data: Dict, path: str) -> None:
    """
    Saves a dictionary as a JSON file.
    Args:
        data: Dictionary to save.
        path: File path.
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def load_json(path: str) -> Dict:
    """
    Loads a JSON file as a dictionary.
    Args:
        path: File path.
    Returns:
        Loaded dictionary.
    """
    with open(path, 'r') as f:
        return json.load(f)

def save_yaml(data: Dict, path: str) -> None:
    """
    Saves a dictionary as a YAML file.
    Args:
        data: Dictionary to save.
        path: File path.
    """
    with open(path, 'w') as f:
        yaml.dump(data, f)

def load_yaml(path: str) -> Dict:
    """
    Loads a YAML file as a dictionary.
    Args:
        path: File path.
    Returns:
        Loaded dictionary.
    """
    with open(path, 'r') as f:
        return yaml.safe_load(f)
