import pandas as pd
from typing import Any

from utils.metrics import calculate_metrics, print_metrics
from visualization import plots
from utils.mlflow_manager import MLFlowLogger

class BaselineRunner:
    def __init__(self, train: pd.Series, test: pd.Series, seasonality: int):
        """
        Initializes the Baseline Runner.

        Args:
            train (pd.Series): Training data.
            test (pd.Series): Testing data.
            seasonality (int): The lag period for seasonal naive (default 12).
        """
        self.train = train
        self.test = test
        self.seasonality = seasonality

    def run_simple_naive(self) -> tuple[pd.Series, dict[str, float]]:
        """
        Runs Simple Naive Forecast (y_t = y_{t-1}).

        Returns:
            Tuple:
                - pred_series (pd.Series): Series of predictions aligned with test index.
                - metrics (Dict[str, float]): Calculated evaluation metrics.
        """
        print("Running Simple Naive Baseline...")
        last_train_point = self.train.iloc[-1:]
        data_for_shift = pd.concat([last_train_point, self.test.iloc[:-1]])
        predictions = data_for_shift.values
        pred_series = pd.Series(predictions, index=self.test.index)
        metrics = calculate_metrics(self.test, pred_series)
        return pred_series, metrics

    def run_seasonal_naive(self) -> tuple[pd.Series, dict[str, float]]:
        """
        Runs Seasonal Naive Forecast (y_t = y_{t-seasonality}).

        Returns:
            Tuple:
                - predictions (pd.Series): Series of predictions aligned with test index.
                - metrics (Dict[str, float]): Calculated evaluation metrics.
        """
        print(f"Running Seasonal Naive Baseline (lag={self.seasonality})...")
        history_needed = self.train.iloc[-self.seasonality:]
        full_data = pd.concat([history_needed, self.test])
        predictions = full_data.shift(self.seasonality).dropna()
        predictions = predictions.loc[self.test.index]
        metrics = calculate_metrics(self.test, predictions)
        return predictions, metrics


def run_baseline_cycle(
    train: pd.Series,
    test: pd.Series,
    config: dict[str, Any],
    mlflow_logger: MLFlowLogger
) -> dict[str, float]:
    """
    Executes the Baseline modeling cycle: Run Models -> Log to MLflow -> Plot.
    Runs both Simple Naive and Seasonal Naive.

    Args:
        train (pd.Series): Training data.
        test (pd.Series): Testing data.
        config (dict): Configuration dictionary.
        mlflow_logger (MLFlowLogger): Logger instance.

    Returns:
        dict[str, float]: Combined metrics from all baseline models.
    """
    user_conf = config.get('user_parameters', {}).get('model', {})
    seasonality = user_conf.get('seasonality', 7)
    runner = BaselineRunner(train, test, seasonality)

    mlflow_logger.log_params({"seasonality": seasonality, "model_type": "baseline"})

    combined_metrics = {}

    preds_naive, m_naive = runner.run_simple_naive()
    print_metrics(m_naive, "Simple Naive")

    prefixed_m_naive = {f"simple_naive_{k}": v for k, v in m_naive.items()}
    mlflow_logger.log_metrics(prefixed_m_naive)
    combined_metrics.update(prefixed_m_naive)

    path, show = plots.get_plot_params(config, "simple_naive.png", suffix="Baseline")
    plots.plot_comparison(train, test, preds_naive, "Simple Naive", save_path=path, show=show)
    if path:
        mlflow_logger.log_artifact(path)

    preds_s_naive, s_naive = runner.run_seasonal_naive()
    print_metrics(s_naive, "Seasonal Naive")

    prefixed_s_naive = {f"seasonal_naive_{k}": v for k, v in s_naive.items()}
    mlflow_logger.log_metrics(prefixed_s_naive)
    combined_metrics.update(prefixed_s_naive)

    path, show = plots.get_plot_params(config, "seasonal_naive.png", suffix="Baseline")
    plots.plot_comparison(train, test, preds_s_naive, "Seasonal Naive", save_path=path, show=show)
    if path:
        mlflow_logger.log_artifact(path)

    return combined_metrics
