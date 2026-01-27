import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error

def calculate_metrics(y_true: pd.Series | np.ndarray | list, y_pred: pd.Series | np.ndarray | list) -> dict[str, float]:
    """
    Calculates common time series regression metrics (MSE, RMSE, MAE, MAPE, SMAPE, WMAPE).

    Args:
        y_true (pd.Series | np.ndarray | list): Actual ground truth values.
        y_pred (pd.Series | np.ndarray | list): Predicted values.

    Returns:
        dict[str, float]: Dictionary containing metric names and their calculated values.
    """
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100
    denominator = (np.abs(y_true) + np.abs(y_pred)) + 1e-10
    smape = 100 * np.mean(2 * np.abs(y_pred - y_true) / denominator)
    wmape = 100 * np.sum(np.abs(y_true - y_pred)) / (np.sum(np.abs(y_true)) + 1e-10)
    return {
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "MAPE": mape,
        "SMAPE": smape,
        "WMAPE": wmape
    }

def print_metrics(metrics_dict: dict[str, float], prefix: str = "") -> None:
    """
    Formatted printing of metrics to the console.

    Args:
        metrics_dict (Dict[str, float]): The dictionary of metrics to print.
        prefix (str, optional): A string prefix for the header (e.g., model name).
    """
    print(f"{prefix} Metrics:")
    for k, v in metrics_dict.items():
        print(f"\t{k:<12}: {v:.4f}")
    print("-" * 30)
