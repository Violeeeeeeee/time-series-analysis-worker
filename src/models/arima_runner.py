import os
import json
import numpy as np
import pandas as pd
from typing import Any
import warnings

import pmdarima as pm
from scipy.signal import periodogram
from statsmodels.tsa.stattools import adfuller, kpss
from sklearn.metrics import mean_squared_error
from skforecast.stats import Sarimax
from skforecast.recursive import ForecasterStats
from skforecast.model_selection import grid_search_stats, TimeSeriesFold

from utils.metrics import calculate_metrics, print_metrics
from visualization import plots
from utils.mlflow_manager import MLFlowLogger

class AutoARIMAFinder:
    def __init__(self, frequency: str = 'D'):
        self.freq = frequency

    def _imputation_tournament(self, series: pd.Series) -> pd.Series:
        print("--- Running Imputation Tournament ---")
        np.random.seed(42)
        missing_mask = np.random.choice([True, False], size=len(series), p=[0.1, 0.9])
        missing_mask[0], missing_mask[-1] = False, False

        dirty_data = series.copy()
        dirty_data[missing_mask] = np.nan

        methods = {
            'zeros': dirty_data.fillna(0),
            'ffill': dirty_data.ffill(),
            'linear': dirty_data.interpolate(method='time'),
            'spline': dirty_data.interpolate(method='spline', order=3) if len(dirty_data) > 3 else dirty_data.interpolate(method='linear')
        }

        results = {}
        for name, imputed in methods.items():
            rmse = np.sqrt(mean_squared_error(series[missing_mask], imputed[missing_mask]))
            results[name] = rmse

        best_method = min(results, key=results.get)
        print(f"Imputation Winner: {best_method} (RMSE: {results[best_method]:.4f})")

        clean_series = series.copy()
        if best_method == 'zeros':
            clean_series = clean_series.fillna(0)
        elif best_method == 'ffill':
            clean_series = clean_series.ffill()
        elif best_method == 'linear':
            clean_series = clean_series.interpolate(method='time')
        elif best_method == 'spline':
            clean_series = clean_series.interpolate(method='spline', order=3)

        return clean_series.asfreq(self.freq)

    def _detect_structure(self, series: pd.Series) -> dict:
        print("--- Analyzing TS Structure (Seasonality & Stationarity) ---")

        # 1. d-Voting (ADF vs KPSS)
        adf_p = adfuller(series.dropna())[1]
        kpss_p = kpss(series.dropna())[1]

        is_adf_stationary = adf_p < 0.05
        is_kpss_stationary = kpss_p > 0.05

        if is_adf_stationary and is_kpss_stationary:
            d = 0
        elif not is_adf_stationary and not is_kpss_stationary:
            d = 1
        else:
            d = 1

        # 2. Fourier m-Detection
        freqs, spectrum = periodogram(series.dropna())
        top_idx = np.argsort(spectrum)[-1]
        m_candidate = int(round(1 / freqs[top_idx])) if freqs[top_idx] > 0 else 1

        # 3. Seasonal Diff Test (OCSB)
        D = 0
        if m_candidate <= 52 and m_candidate > 1:
            try:
                # Docsb = pm.arima.nsdiffs(series, m=m_candidate, test='ocsb')
                D = pm.arima.nsdiffs(series, m=m_candidate, test='ocsb')
                # Dch = pm.arima.nsdiffs(series, m=m_candidate, test='ch')
            except Exception:
                pass

        # print(f"Structure Detected: d={d}, m={m_candidate}, D ocsb={Docsb}, D ch={Dch}")
        print(f"Structure Detected: d={d}, m={m_candidate}, D={D}")
        return {'d': d, 'D': D, 'm': m_candidate if m_candidate <= 52 and m_candidate > 1 else 0}

    def _heuristic_search(self, series: pd.Series, structure: dict) -> tuple:
        print("--- Running Fast Heuristic Search ---")
        d, D, m = structure['d'], structure['D'], max(1, structure['m'])
        seasonal = False
        if m <= 52 and m > 1:
            seasonal = True
        else:
            m = 0

        auto = pm.auto_arima(
            series, start_p=0, start_q=0, max_p=3, max_q=3,
            d=d, D=D, m=m, seasonal=seasonal,
            stepwise=True, maxiter=15,
            suppress_warnings=True,
            scoring="mse", information_criterion="aic",
            trace=True, method="lbfgs"
        )
        print("heuristic search end")
        return auto.order, auto.seasonal_order

    def build_grid(self, structure: dict, h_order: tuple, h_seasonal: tuple) -> dict:
        print("param grid started")
        p_c, d, q_c = h_order
        P_c, D, Q_c, m = h_seasonal

        p_range = sorted(list({max(0, p_c - 1), p_c, p_c + 1}))
        q_range = sorted(list({max(0, q_c - 1), q_c, q_c + 1}))

        param_grid = {
            'order': [(p, d, q) for p in p_range for q in q_range],
            'trend': [None, 'c']
        }

        if structure['m'] > 1:
            P_range = sorted(list({max(0, P_c - 1), P_c, P_c + 1}))
            Q_range = sorted(list({max(0, Q_c - 1), Q_c, Q_c + 1}))
            param_grid['seasonal_order'] = [
                (P, D, Q, m) for P in P_range for Q in Q_range
            ]
            param_grid['seasonal_order'].append((0, 0, 0, 0))
        else:
            param_grid['seasonal_order'] = [(0, 0, 0, 0)]

        print("param grid finished")
        return param_grid

class ARIMARunner:
    def __init__(self, train_data: pd.Series, test_data: pd.Series, frequency: str):
        self.raw_train = train_data
        self.raw_test = test_data
        self.freq = frequency
        self.full_raw_data = pd.concat([train_data, test_data])
        self.order = (0,0,0)
        self.seasonal_order = (0,0,0,0)
        self.trend = "c"

        if self.full_raw_data.index.freq is None:
            self.full_raw_data.index.freq = frequency

    def _save_artifacts(self, predictions: pd.Series, metrics: dict, model_fit: Any, prefix: str) -> dict[str, str]:
        artifacts_paths = {}
        output_dir = "temp_artifacts"
        os.makedirs(output_dir, exist_ok=True)

        forecast_path = os.path.join(output_dir, f"{prefix}_forecast.csv")
        predictions.to_csv(forecast_path)
        artifacts_paths["forecast"] = forecast_path

        if metrics:
            metrics_path = os.path.join(output_dir, f"{prefix}_metrics.json")
            with open(metrics_path, "w") as f:
                json.dump(metrics, f, indent=4)
            artifacts_paths["metrics"] = metrics_path

        import joblib
        model_path = os.path.join(output_dir, f"{prefix}_model.joblib")
        joblib.dump(model_fit, model_path)
        artifacts_paths["model"] = model_path

        return artifacts_paths

    def run_auto_pipeline(self, steps: int) -> tuple[pd.Series, dict, Any]:
        finder = AutoARIMAFinder(frequency=self.freq)

        clean_full_data = finder._imputation_tournament(self.full_raw_data)
        clean_train = clean_full_data.iloc[:len(self.raw_train)]

        structure = finder._detect_structure(clean_train)
        h_order, h_seasonal = finder._heuristic_search(clean_train, structure)

        smart_grid = finder.build_grid(structure, h_order, h_seasonal)
        print(f"--- Running Smart Grid Search ({len(smart_grid['order']) * len(smart_grid['seasonal_order']) * 2} models) ---")

        forecaster = ForecasterStats(estimator=Sarimax(order=(1,0,1)))

        cv = TimeSeriesFold(steps=steps, initial_train_size=len(clean_train) - steps*3, refit=False)

        results = grid_search_stats(
            forecaster=forecaster,
            y=clean_train,
            cv=cv,
            param_grid=smart_grid,
            metric='mean_absolute_error',
            return_best=True,
            verbose=False,
            show_progress=True,
        )

        best_params = results.iloc[0]['params']
        print(f"Best Params Found: {best_params}")
        self.order = best_params["order"]
        self.seasonal_order = best_params["seasonal_order"]
        self.trend = best_params["trend"]

        predictions = forecaster.predict(steps=len(self.raw_test))

        clean_test = clean_full_data.iloc[len(self.raw_train):]
        metrics = calculate_metrics(clean_test, predictions)
        metrics["best_params"] = best_params

        return predictions, metrics, forecaster

    def run_future_forecast(self, steps: int) -> tuple[pd.Series, dict, Any]:
        print(f"Running Real Future Forecast ARIMA{self.order} for {steps} steps...")
        full_history = self.full_raw_data
        try:
            warnings.filterwarnings("ignore", category=UserWarning, message='Non-invertible|Non-stationary')
            model = Sarimax(order=self.order, seasonal_order=self.seasonal_order, trend=self.trend)
            model.fit(y=full_history)
            model.summary()
            predictions = model.predict(steps=steps)
            warnings.filterwarnings("default")
            return predictions, {}, model
        except Exception as e:
            print(f"Future Forecast Failed: {e}")
            return pd.Series(), {}, None

def run_arima_cycle(
    train: pd.Series,
    test: pd.Series,
    config: dict[str, Any],
    order: tuple,
    param_str_id: str,
    mlflow_logger: MLFlowLogger) -> dict[str, float]:

    user_conf = config.get('user_parameters', {})
    freq = user_conf.get('data', {}).get('frequency', 'D')
    steps = user_conf.get('data', {}).get('steps', len(test))

    runner = ARIMARunner(train, test, frequency=freq)

    clean_suffix = "auto_sarimax"
    n_clean_suffix = "final_sarimax"

    preds, metrics, best_model = runner.run_auto_pipeline(steps=steps)
    pr, met, mod = runner.run_future_forecast(steps)

    mlflow_logger.log_params({
        "scenario": "AutoML_Grid_Search",
        "best_order": str(metrics.get("best_params", {}).get("order")),
        "best_seasonal": str(metrics.get("best_params", {}).get("seasonal_order")),
        "best_trend": str(metrics.get("best_params", {}).get("trend")),
        "steps": steps
    })

    mlflow_logger.log_params({
        "future_scenario": "forecast",
        "future_order": str(runner.order),
        "future_seasonal": str(runner.seasonal_order),
        "future_trend": str(runner.trend),
        "future_steps": steps
    })

    print_metrics({k:v for k,v in metrics.items() if k != "best_params"}, "Auto_SARIMAX")

    mlflow_logger.log_metrics({k:v for k,v in metrics.items() if k != "best_params"})


    local_artifacts = runner._save_artifacts(preds, metrics, best_model, clean_suffix)
    n_local_artifacts = runner._save_artifacts(pr, met, mod, n_clean_suffix)

    if "model" in n_local_artifacts:
        mlflow_logger.log_artifact(n_local_artifacts["model"])
    if "forecast" in n_local_artifacts:
        mlflow_logger.log_artifact(n_local_artifacts["forecast"])

    path, show = plots.get_plot_params(config, "fan_plot.png")

    full_history = pd.concat([train, test])
    plots.plot_fan_chart(full_history, pr, mod, save_path=path, show=show)

    if path and os.path.exists(path):
        mlflow_logger.log_artifact(path)
        n_local_artifacts["fan_plot"] = path

    return {
        "metrics": metrics,
        "local_paths": n_local_artifacts
    }
