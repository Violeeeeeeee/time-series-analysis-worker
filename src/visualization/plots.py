import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

from typing import Any

def _finalize_plot(title: str, save_path: str | None = None, show: bool = True) -> None:
    """
    Internal helper to handle saving and displaying plots.

    Args:
        title (str): The title of the plot.
        save_path (str, optional): Path to save the file. If None, it is not saved.
        show (bool): Whether to call plt.show().
    """
    if save_path:
        directory = os.path.dirname(save_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to: {save_path}")

    if show:
        plt.show()

    plt.close()

def plot_comparison(
    train: pd.Series,
    test: pd.Series,
    predictions: pd.Series | np.ndarray | list,
    title: str = "Model Forecast",
    save_path: str | None = None,
    show: bool = True
) -> None:
    """
    Plots the training history (last 30 points), actual test data, and predictions.

    Args:
        train (pd.Series): Training data series.
        test (pd.Series): Test data series (ground truth).
        predictions (pd.Series | np.ndarray | list): Model predictions.
        title (str): Title of the chart.
        save_path (str | None): File path to save the image.
        show (bool): Whether to display the image.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(train.index[-30:], train[-30:], label='Train (Last 30)', color='blue', alpha=0.5)
    plt.plot(test.index, test, label='Actual', color='black')

    pred_series = pd.Series(predictions, index=test.index)
    plt.plot(test.index, pred_series, label='Predicted', color='red', linestyle='--')

    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)

    _finalize_plot(title, save_path, show)

def plot_fan_chart(
    train: pd.Series,
    test: pd.Series,
    model_fit: Any,
    save_path: str | None = None,
    show: bool = True
) -> None:
    """
    Plots a Fan Chart showing the forecast mean and Confidence Intervals (CI).
    Args:
        train (pd.Series): Historical data context.
        test (pd.Series): Future window definition (can contain NaNs for future forecast).
        model_fit (Any): Fitted statsmodels ARIMA object.
    """
    if model_fit is None:
        return

    steps = len(test)
    if steps == 0:
        print("Warning: No steps defined for Fan Chart (test data is empty). Skipping plot.")
        return

    try:
        forecast_result = model_fit.get_forecast(steps=steps)
        forecast_mean = forecast_result.predicted_mean
        conf_int = forecast_result.conf_int()
    except Exception as e:
        print(f"Error generating forecast for plot: {e}")
        return

    plt.figure(figsize=(12, 6))
    display_history = train.iloc[-100:] if len(train) > 100 else train
    plt.plot(display_history.index, display_history, label='History', color='gray', alpha=0.7)

    if not test.isna().all():
        plt.plot(test.index, test, label='Actual', color='black')

    plt.plot(test.index, forecast_mean, label='Forecast Mean', color='red')

    alphas = [0.05, 0.2, 0.4] # 95%, 80%, 60%
    opacity = 0.15

    for a in alphas:
        try:
            ci = forecast_result.conf_int(alpha=a)
            lower = ci.iloc[:, 0] if hasattr(ci, 'iloc') else ci[:, 0]
            upper = ci.iloc[:, 1] if hasattr(ci, 'iloc') else ci[:, 1]

            plt.fill_between(test.index, lower, upper,
                             color='red', alpha=opacity, label=f'{int((1-a)*100)}% CI')
            opacity += 0.15
        except Exception:
            continue

    plt.title("Fan Chart / Confidence Intervals")
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.3)

    _finalize_plot("Fan Chart", save_path, show)

def plot_scatter(
    y_true: pd.Series | np.ndarray | list[float],
    y_pred: pd.Series | np.ndarray | list[float],
    title: str = "Actual vs Predicted",
    save_path: str | None = None,
    show: bool = True
) -> None:
    """
    Generates a scatter plot with a 45-degree reference line to visualize model performance.
    Points on the diagonal line represent perfect predictions.

    Args:
        y_true (pd.Series | np.ndarray | list[float]): Actual ground truth values.
        y_pred (pd.Series | np.ndarray | list[float]): Predicted values.
        title (str | None): Title of the plot. Defaults to "Actual vs Predicted".
        save_path (str | None): Full path to save the image. If None, image is not saved.
        show (bool | None): Whether to display the plot interactively. Defaults to True.
    """
    plt.figure(figsize=(8, 8))
    plt.scatter(y_true, y_pred, alpha=0.5, color='purple')
    min_val = min(np.min(y_true), np.min(y_pred))
    max_val = max(np.max(y_true), np.max(y_pred))
    plt.plot([min_val, max_val], [min_val, max_val], color='red', linestyle='--', label='Perfect Fit')
    plt.xlabel('Actual Values')
    plt.ylabel('Predicted Values')
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)
    _finalize_plot(title, save_path, show)

def get_plot_params(config: dict[str, Any], filename: str, suffix: str = "") -> tuple[str | None, bool]:
    """
    Generates parameters for plotting configuration (save path and show boolean).

    Args:
        config (dict[str, Any]): The configuration dictionary containing visualization settings.
        filename (str): Base name of the output file (e.g., 'plot.png').
        suffix (str, optional): Unique identifier to append to the filename (e.g., 'ARIMA_1-1-1').
                                Defaults to "".

    Returns:
        A tuple containing:
        - save_path (str | None): Full path to save the image, or None if saving is disabled.
        - show (bool): Whether to display the plot interactively.
    """
    sys_conf = config.get('system_settings', {})
    viz_conf = sys_conf.get('visualization', {})
    show = viz_conf.get('show_plots', False)
    save = viz_conf.get('save_plots', True)
    save_path = None
    if save:
        output_dir = viz_conf.get('output_dir', './output_plots')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        full_filename = f"{filename}"
        save_path = os.path.join(output_dir, full_filename)
    return save_path, show
