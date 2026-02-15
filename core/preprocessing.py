"""
Preprocessing utilities: missing value handling, scaling, encoding, splitting.
"""
from typing import Tuple, Optional, Dict, Any
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder, LabelEncoder
import numpy as np

class Preprocessor:
    """
    Handles preprocessing tasks for datasets.
    """
    def __init__(self):
        self.scalers: Dict[str, Any] = {}
        self.encoders: Dict[str, Any] = {}

    def handle_missing(self, df: pd.DataFrame, strategy: str = 'mean', fill_value: Optional[Any] = None) -> pd.DataFrame:
        """
        Handles missing values in a DataFrame.
        Args:
            df: Input DataFrame.
            strategy: 'mean', 'median', 'mode', or 'constant'.
            fill_value: Value to use if strategy is 'constant'.
        Returns:
            DataFrame with missing values handled.
        """
        df = df.copy()
        if strategy == 'mean':
            return df.fillna(df.mean(numeric_only=True))
        elif strategy == 'median':
            return df.fillna(df.median(numeric_only=True))
        elif strategy == 'mode':
            return df.fillna(df.mode().iloc[0])
        elif strategy == 'constant':
            return df.fillna(fill_value)
        else:
            raise ValueError("Invalid missing value strategy.")

    def scale_features(self, df: pd.DataFrame, columns: list, method: str = 'standard', scaler_name: str = 'default') -> pd.DataFrame:
        """
        Scales features using StandardScaler or MinMaxScaler.
        Args:
            df: Input DataFrame.
            columns: List of columns to scale.
            method: 'standard' or 'minmax'.
            scaler_name: Name to store the scaler under.
        Returns:
            DataFrame with scaled features.
        """
        df = df.copy()
        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        else:
            raise ValueError("Invalid scaling method.")
        df[columns] = scaler.fit_transform(df[columns])
        self.scalers[scaler_name] = scaler
        return df

    def encode_categorical(self, df: pd.DataFrame, columns: list, method: str = 'onehot', encoder_name: str = 'default') -> pd.DataFrame:
        """
        Encodes categorical features.
        Args:
            df: Input DataFrame.
            columns: List of columns to encode.
            method: 'onehot' or 'label'.
            encoder_name: Name to store the encoder under.
        Returns:
            DataFrame with encoded features.
        """
        df = df.copy()
        if method == 'onehot':
            encoder = OneHotEncoder(sparse=False, handle_unknown='ignore')
            encoded = encoder.fit_transform(df[columns])
            encoded_df = pd.DataFrame(encoded, columns=encoder.get_feature_names_out(columns), index=df.index)
            df = df.drop(columns, axis=1)
            df = pd.concat([df, encoded_df], axis=1)
        elif method == 'label':
            encoder = LabelEncoder()
            for col in columns:
                df[col] = encoder.fit_transform(df[col].astype(str))
        else:
            raise ValueError("Invalid encoding method.")
        self.encoders[encoder_name] = encoder
        return df

    def split_data(self, df: pd.DataFrame, target: str, test_size: float = 0.2, val_size: float = 0.1, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Splits data into train, validation, and test sets.
        Args:
            df: Input DataFrame.
            target: Target column name.
            test_size: Proportion for test set.
            val_size: Proportion for validation set.
            random_state: Random seed.
        Returns:
            X_train, X_val, X_test, y_train, y_val, y_test
        """
        X = df.drop(target, axis=1)
        y = df[target]
        X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
        val_relative = val_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=val_relative, random_state=random_state)
        return X_train, X_val, X_test, y_train, y_val, y_test
