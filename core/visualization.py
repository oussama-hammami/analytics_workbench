"""
Visualization utilities for data exploration.
"""
from typing import Optional, List
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class Visualizer:
    """
    Provides visualization methods for data exploration.
    """
    def __init__(self):
        pass

    def plot_histogram(self, df: pd.DataFrame, column: str) -> None:
        """
        Plots a histogram for a given column.
        Args:
            df: Input DataFrame.
            column: Column to plot.
        """
        plt.figure(figsize=(8, 4))
        sns.histplot(df[column].dropna(), kde=True)
        plt.title(f"Histogram of {column}")
        plt.show()

    def plot_boxplot(self, df: pd.DataFrame, column: str) -> None:
        """
        Plots a boxplot for a given column.
        Args:
            df: Input DataFrame.
            column: Column to plot.
        """
        plt.figure(figsize=(8, 4))
        sns.boxplot(x=df[column])
        plt.title(f"Boxplot of {column}")
        plt.show()

    def plot_scatter(self, df: pd.DataFrame, x: str, y: str) -> None:
        """
        Plots a scatter plot between two columns.
        Args:
            df: Input DataFrame.
            x: X-axis column.
            y: Y-axis column.
        """
        plt.figure(figsize=(8, 4))
        sns.scatterplot(x=df[x], y=df[y])
        plt.title(f"Scatter Plot: {x} vs {y}")
        plt.show()

    def plot_correlation_heatmap(self, df: pd.DataFrame) -> None:
        """
        Plots a correlation heatmap for the DataFrame.
        Args:
            df: Input DataFrame.
        """
        plt.figure(figsize=(10, 8))
        corr = df.corr(numeric_only=True)
        sns.heatmap(corr, annot=True, cmap='coolwarm')
        plt.title("Correlation Heatmap")
        plt.show()

    def plot_feature_vs_target(self, df: pd.DataFrame, feature: str, target: str) -> None:
        """
        Plots a feature vs target plot.
        Args:
            df: Input DataFrame.
            feature: Feature column.
            target: Target column.
        """
        plt.figure(figsize=(8, 4))
        sns.scatterplot(x=df[feature], y=df[target])
        plt.title(f"{feature} vs {target}")
        plt.show()

    def plot_interactive_histogram(self, df: pd.DataFrame, column: str) -> go.Figure:
        """
        Creates an interactive histogram using Plotly.
        Args:
            df: Input DataFrame.
            column: Column to plot.
        Returns:
            Plotly Figure object.
        """
        fig = px.histogram(df, x=column, marginal="box", title=f"Distribution of {column}")
        return fig

    def plot_interactive_scatter(self, df: pd.DataFrame, x: str, y: str, color: Optional[str] = None) -> go.Figure:
        """
        Creates an interactive scatter plot using Plotly.
        Args:
            df: Input DataFrame.
            x: X-axis column.
            y: Y-axis column.
            color: Optional color-coding column.
        Returns:
            Plotly Figure object.
        """
        fig = px.scatter(df, x=x, y=y, color=color, title=f"{x} vs {y}")
        return fig

    def plot_interactive_correlation(self, df: pd.DataFrame) -> go.Figure:
        """
        Creates an interactive correlation heatmap using Plotly.
        Args:
            df: Input DataFrame.
        Returns:
            Plotly Figure object.
        """
        corr = df.corr(numeric_only=True)
        fig = go.Figure(data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            colorscale='RdBu',
            zmid=0
        ))
        fig.update_layout(title="Correlation Heatmap", width=800, height=800)
        return fig

    def plot_pairplot(self, df: pd.DataFrame, columns: List[str], hue: Optional[str] = None) -> None:
        """
        Creates a pairplot for selected columns.
        Args:
            df: Input DataFrame.
            columns: List of columns to include.
            hue: Optional column for color coding.
        """
        sns.pairplot(df[columns + ([hue] if hue and hue not in columns else [])], hue=hue)
        plt.show()

    def plot_learning_curves(self, history: dict) -> go.Figure:
        """
        Plots learning curves from training history.
        Args:
            history: Training history dictionary.
        Returns:
            Plotly Figure object.
        """
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Loss", "Accuracy"))

        # Loss plot
        if 'loss' in history:
            fig.add_trace(
                go.Scatter(y=history['loss'], name='Train Loss', mode='lines'),
                row=1, col=1
            )
        if 'val_loss' in history:
            fig.add_trace(
                go.Scatter(y=history['val_loss'], name='Val Loss', mode='lines'),
                row=1, col=1
            )

        # Accuracy plot
        if 'accuracy' in history:
            fig.add_trace(
                go.Scatter(y=history['accuracy'], name='Train Accuracy', mode='lines'),
                row=1, col=2
            )
        if 'val_accuracy' in history:
            fig.add_trace(
                go.Scatter(y=history['val_accuracy'], name='Val Accuracy', mode='lines'),
                row=1, col=2
            )

        fig.update_xaxes(title_text="Epoch", row=1, col=1)
        fig.update_xaxes(title_text="Epoch", row=1, col=2)
        fig.update_yaxes(title_text="Loss", row=1, col=1)
        fig.update_yaxes(title_text="Accuracy", row=1, col=2)
        fig.update_layout(height=400, showlegend=True)
        return fig
