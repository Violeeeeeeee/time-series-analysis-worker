import os
import json
import sys
import traceback
from typing import Any, Dict

from utils.config_loader import load_config, parse_args
from utils.mlflow_manager import MLFlowLogger
from utils.data_manager import DVCDataManager

from models.baseline_runner import run_baseline_cycle
from models.arima_runner import run_arima_cycle

def construct_s3_url(artifact_root, filename: str) -> str:
    """Helper to build the S3 URL for a specific artifact."""
    if not filename:
        return ""
    return f"{artifact_root.rstrip('/')}/artifacts/{filename}"

def run_pipeline(
    dataset_path: str,
    config_path: str,
    config_filename: str,
    job_id: str,
    user_id: str,
    dvc_hash: str,
    config_hash: str = "N/A"
) -> Dict[str, Any]:
    """
    Executes the analysis pipeline programmatically.
    """
    print(f"--- Loading Config from: {config_path} ---")
    config = load_config(config_path)

    sys_conf = config.get('system_settings', {})
    user_conf = config.get('user_parameters', {})

    bucket = sys_conf.get('s3', {}).get('bucket_name', 'ml-data')
    exp_folder = sys_conf.get('s3', {}).get('experiments_folder', 'experiments')
    config_dir = sys_conf.get('s3', {}).get('config_folder', 'configs')
    exp_folder = sys_conf.get('s3', {}).get('experiments_folder', 'experiments')

    artifact_root_base = f"s3://{bucket}/{user_id}/{exp_folder}/{job_id}"
    config_root_base = f"s3://{bucket}/{user_id}/{config_dir}"
    print(f"--- Starting Job Pipeline: {job_id} ---")

    ml_logger = MLFlowLogger(
        experiment_name=job_id,
        tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"),
        artifact_location=artifact_root_base
    )

    data_manager = DVCDataManager()
    train, test = data_manager.load_and_preprocess(config, dataset_path=dataset_path)

    model_conf = user_conf.get('model', {})
    order = tuple(model_conf.get('order_arima', [1, 1, 1]))
    param_id = str(order).replace(" ", "")

    final_result_arima = {}

    print("\n--- Running Baselines ---")
    with ml_logger.start_run(run_name="Baselines") as run:
        ml_logger.log_params({
            "dvc_data_hash": dvc_hash,
            "dvc_config_hash": config_hash,
            "dataset_path": dataset_path,
            "user_freq": user_conf.get('data', {}).get('frequency')
        })
        ml_logger.log_artifact(config_path)
        run_baseline_cycle(train, test, config, ml_logger)

    print("\n--- Single Run Mode (ARIMA) ---")
    run_id = ""
    with ml_logger.start_run(run_name="Single_ARIMA") as run:
        ml_logger.log_params({
            "dvc_data_hash": dvc_hash,
            "dataset": dataset_path
        })
        ml_logger.log_artifact(config_path)

        final_result_arima = run_arima_cycle(train, test, config, order, param_id, ml_logger)
        run_id = run.info.run_id

    run_artifact_root = f"{artifact_root_base}/{run_id}"
    local_paths = final_result_arima.get('local_paths', {})
    metrics = final_result_arima.get('metrics', {})

    def get_url(key):
        path = local_paths.get(key)
        return construct_s3_url(run_artifact_root, os.path.basename(path)) if path else ""

    output_data = {
        "status": "success",
        "job_id": job_id,
        "user_id": user_id,
        "run_id": run_id,
        "dvc_hash": dvc_hash,
        "dataset_name": user_conf.get('data', {}).get('filename', 'unknown'),
        "metrics": metrics,
        "artifact_config": f"{config_root_base}/{config_filename}",
        "artifact_model": get_url("model"),
        "artifact_forecast": get_url("forecast"),
        "artifact_json": get_url("metrics"),
        "artifact_plot": get_url("forecast_plot"),
        "plot_fan": get_url("fan_plot"),
        "plot_scatter": get_url("scatter_plot")
    }

    return output_data

def main() -> None:
    """CLI Entry point."""
    try:
        args = parse_args()
        result = run_pipeline(
            dataset_path=args.dataset_path,
            config_path=args.config_path,
            job_id=args.job_id,
            user_id=args.user_id,
            dvc_hash=args.dvc_hash,
            config_hash=args.config_hash
        )

        with open(f"{args.job_id}_results.json", "w") as f:
            json.dump(result, f, indent=4)

        print(f"Training finished. Results saved to {args.job_id}_results.json")

    except Exception as e:
        print(f"CRITICAL ERROR IN MAIN.PY: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
