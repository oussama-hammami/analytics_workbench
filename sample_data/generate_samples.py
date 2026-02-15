"""
Script to generate sample datasets for testing the AI/ML platform.
"""
import pandas as pd
import numpy as np
from sklearn.datasets import load_iris, make_classification, make_regression
import os

def generate_iris_dataset() -> None:
    """Generates and saves the Iris dataset as CSV."""
    iris = load_iris()
    df = pd.DataFrame(data=iris.data, columns=iris.feature_names)
    df['target'] = iris.target
    df.to_csv('./iris.csv', index=False)
    print("✓ Generated iris.csv")

def generate_classification_dataset() -> None:
    """Generates and saves a synthetic classification dataset."""
    X, y = make_classification(
        n_samples=1000,
        n_features=10,
        n_informative=8,
        n_redundant=2,
        n_classes=3,
        random_state=42
    )
    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(10)])
    df['target'] = y
    # Add some missing values
    df.loc[df.sample(50, random_state=42).index, 'feature_0'] = np.nan
    df.to_csv('./classification_dataset.csv', index=False)
    print("✓ Generated classification_dataset.csv")

def generate_regression_dataset() -> None:
    """Generates and saves a synthetic regression dataset."""
    X, y = make_regression(
        n_samples=500,
        n_features=8,
        n_informative=6,
        noise=10.0,
        random_state=42
    )
    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(8)])
    df['target'] = y
    # Add some outliers
    outlier_indices = np.random.choice(500, 20, replace=False)
    df.loc[outlier_indices, 'target'] *= 3
    df.to_csv('./regression_dataset.csv', index=False)
    print("✓ Generated regression_dataset.csv")

def generate_timeseries_dataset() -> None:
    """Generates and saves a synthetic time series dataset."""
    dates = pd.date_range(start='2020-01-01', periods=365, freq='D')
    trend = np.linspace(100, 200, 365)
    seasonal = 20 * np.sin(2 * np.pi * np.arange(365) / 365)
    noise = np.random.normal(0, 5, 365)
    values = trend + seasonal + noise

    df = pd.DataFrame({
        'date': dates,
        'value': values,
        'feature_1': np.random.randn(365),
        'feature_2': np.random.randn(365)
    })
    df.to_csv('./timeseries_dataset.csv', index=False)
    print("✓ Generated timeseries_dataset.csv")

if __name__ == "__main__":
    print("Generating sample datasets...")
    generate_iris_dataset()
    generate_classification_dataset()
    generate_regression_dataset()
    generate_timeseries_dataset()
    print("\nAll sample datasets generated successfully!")
    print(f"Location: {os.path.abspath('.')}")
