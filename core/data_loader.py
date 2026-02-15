"""
Data loading utilities for various file formats.
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
import json
from pathlib import Path

class DatasetManager:
    """
    Manages multiple datasets in memory.
    """
    def __init__(self) -> None:
        """Initializes the dataset manager."""
        self.datasets: Dict[str, pd.DataFrame] = {}

    def load_csv(self, file_path: str, name: str) -> None:
        """
        Loads a CSV file into memory.
        Args:
            file_path: Path to the CSV file.
            name: Name to store the dataset under.
        """
        self.datasets[name] = pd.read_csv(file_path)

    def load_excel(self, file_path: str, name: str) -> None:
        """
        Loads an Excel file into memory.
        Args:
            file_path: Path to the Excel file.
            name: Name to store the dataset under.
        """
        self.datasets[name] = pd.read_excel(file_path)

    def load_json(self, file_path: str, name: str) -> None:
        """
        Loads a JSON file into memory.
        Args:
            file_path: Path to the JSON file.
            name: Name to store the dataset under.
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        self.datasets[name] = pd.DataFrame(data)

    def load_numpy(self, file_path: str, name: str) -> None:
        """
        Loads a NumPy file into memory.
        Args:
            file_path: Path to the NumPy file (.npy or .npz).
            name: Name to store the dataset under.
        """
        arr = np.load(file_path, allow_pickle=True)
        if isinstance(arr, np.ndarray):
            self.datasets[name] = pd.DataFrame(arr)
        elif isinstance(arr, dict):
            self.datasets[name] = pd.DataFrame(arr['arr_0'])
        else:
            raise ValueError("Unsupported NumPy file structure.")

    def get_dataset(self, name: str) -> pd.DataFrame:
        """
        Retrieves a dataset by name.
        Args:
            name: Name of the dataset.
        Returns:
            The requested DataFrame.
        """
        return self.datasets[name]

    def list_datasets(self) -> list:
        """
        Lists all loaded dataset names.
        Returns:
            List of dataset names.
        """
        return list(self.datasets.keys())

    def get_dataset_info(self, name: str) -> Dict[str, Any]:
        """
        Gets comprehensive information about a dataset.
        Args:
            name: Name of the dataset.
        Returns:
            Dictionary with dataset information (shape, columns, missing values, stats).
        """
        if name not in self.datasets:
            raise ValueError(f"Dataset '{name}' not found.")

        df = self.datasets[name]
        info = {
            'name': name,
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'missing_percentage': (df.isnull().sum() / len(df) * 100).to_dict(),
            'summary_stats': df.describe(include='all').to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum() / 1024**2  # MB
        }
        return info

    def remove_dataset(self, name: str) -> None:
        """
        Removes a dataset from memory.
        Args:
            name: Name of the dataset to remove.
        """
        if name in self.datasets:
            del self.datasets[name]
        else:
            raise ValueError(f"Dataset '{name}' not found.")
