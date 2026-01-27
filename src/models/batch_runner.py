import pandas as pd
import ast

from typing import Any
from utils.mlflow_manager import MLFlowLogger

from models.arima_runner import run_arima_cycle

def run_batch_cycle(
    config: dict[str, Any],
    train: pd.Series,
    test: pd.Series,
    args: Any,
    ml_logger: MLFlowLogger
) -> tuple[dict[str, float], dict[str, Any], str]:
    """
    Reads parameters from a CSV file and runs multiple experiments.
    Each row in the CSV triggers a separate MLflow run.

    Args:
        config (dict): Global config.
        train (pd.Series): Train data.
        test (pd.Series): Test data.
        args (Any): Parsed arguments (containing hashes/paths).
        ml_logger (MLFlowLogger): Logger instance.

    Returns:
        tuple:
            - last_metrics (dict): Metrics of the last run.
            - last_params (dict): Parameters of the last run.
            - last_run_id (str): MLflow Run ID of the last run.
    """
    batch_file = config['model'].get('batch_params_file')
    print(f"\n--- Batch Mode Detected: Reading from {batch_file} ---")

    params_df = pd.read_csv(batch_file)

    last_metrics = {}
    last_params = {}
    last_run_id = "batch_run_placeholder"

    try:
        for index, row in params_df.iterrows():
            model_type = row['model_type'].lower()
            param_str = row['params']

            try:
                params = ast.literal_eval(param_str)
            except Exception as e:
                print(f"Skipping bad params {param_str}: {e}")
                continue

            # Create ID: (1, 1, 1) -> 1-1-1
            param_id = str(params).replace(" ", "").replace(",", "-").replace("(", "").replace(")", "")
            run_name = f"{model_type}_{param_id}"

            # Start MLflow run for this specific model configuration
            with ml_logger.start_run(run_name=run_name) as run:
                print(f"\n> Running {model_type.upper()} with params: {params}...")
                ml_logger.log_params({"dvc_hash": args.dvc_hash, "dataset": args.dataset_path})

                if model_type == 'arima':
                    metrics = run_arima_cycle(train, test, config, params, param_id, ml_logger)

                    # Update "last successful" data for the final report
                    last_metrics = metrics
                    last_run_id = run.info.run_id
                    last_params = {"batch_mode": True, "last_model": run_name, "model_params": params}

    except Exception as e:
        print(f"Critical error in batch processing: {e}")

    return last_metrics, last_params, last_run_id
