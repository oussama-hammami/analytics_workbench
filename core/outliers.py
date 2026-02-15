"""
Outlier detection utilities using statistical and ML techniques.
"""
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN

class OutlierDetector:
    """
    Detects outliers using various methods.
    """
    def __init__(self):
        pass

    def z_score(self, df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.Series:
        """
        Detects outliers using Z-score method.
        Args:
            df: Input DataFrame.
            column: Column to check.
            threshold: Z-score threshold.
        Returns:
            Boolean Series indicating outliers.
        """
        z_scores = (df[column] - df[column].mean()) / df[column].std()
        return np.abs(z_scores) > threshold

    def iqr(self, df: pd.DataFrame, column: str, factor: float = 1.5) -> pd.Series:
        """
        Detects outliers using IQR method.
        Args:
            df: Input DataFrame.
            column: Column to check.
            factor: IQR multiplier.
        Returns:
            Boolean Series indicating outliers.
        """
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - factor * IQR
        upper = Q3 + factor * IQR
        return (df[column] < lower) | (df[column] > upper)

    def isolation_forest(self, df: pd.DataFrame, columns: List[str], contamination: float = 0.05, random_state: int = 42) -> pd.Series:
        """
        Detects outliers using Isolation Forest.
        Args:
            df: Input DataFrame.
            columns: Columns to use.
            contamination: Proportion of outliers.
            random_state: Random seed.
        Returns:
            Boolean Series indicating outliers.
        """
        iso = IsolationForest(contamination=contamination, random_state=random_state)
        preds = iso.fit_predict(df[columns])
        return preds == -1

    def dbscan(self, df: pd.DataFrame, columns: List[str], eps: float = 0.5, min_samples: int = 5) -> pd.Series:
        """
        Detects outliers using DBSCAN clustering.
        Args:
            df: Input DataFrame.
            columns: Columns to use.
            eps: DBSCAN eps parameter.
            min_samples: DBSCAN min_samples parameter.
        Returns:
            Boolean Series indicating outliers.
        """
        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(df[columns])
        return labels == -1

    def remove_outliers(self, df: pd.DataFrame, outlier_mask: pd.Series) -> pd.DataFrame:
        """
        Removes outliers from the DataFrame based on a boolean mask.
        Args:
            df: Input DataFrame.
            outlier_mask: Boolean Series indicating which rows are outliers.
        Returns:
            DataFrame with outliers removed.
        """
        return df[~outlier_mask].copy()

    def get_outlier_summary(self, outlier_mask: pd.Series) -> dict:
        """
        Provides a summary of detected outliers.
        Args:
            outlier_mask: Boolean Series indicating outliers.
        Returns:
            Dictionary with outlier statistics.
        """
        return {
            'total_outliers': outlier_mask.sum(),
            'outlier_percentage': (outlier_mask.sum() / len(outlier_mask) * 100),
            'outlier_indices': outlier_mask[outlier_mask].index.tolist()
        }
