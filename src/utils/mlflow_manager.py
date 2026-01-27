import mlflow
import mlflow.sklearn
import os

from typing import Any
class MLFlowLogger:
    """Wrapper for MLflow to handle setup and logging cleanly."""

    def __init__(self, experiment_name: str, tracking_uri: str, artifact_location: str = ""):
        """Initializes the MLFlow wrapper and sets the experiment.

        Args:
            experiment_name: Name of the experiment in MLflow.
            tracking_uri: HTTP URL of the MLflow server (e.g., 'http://localhost:5000').
            artifact_location: S3 or local path where artifacts will be stored.
                               If empty, MLflow uses the default server artifact root.
        """
        mlflow.set_tracking_uri(tracking_uri)
        try:
            if not mlflow.get_experiment_by_name(experiment_name):
                mlflow.create_experiment(experiment_name, artifact_location=artifact_location)
            mlflow.set_experiment(experiment_name)
        except Exception as e:
            print(f"Error setting experiment: {e}")

        self.experiment_name = experiment_name
        self.run_id = None

    def start_run(self, run_name: str | None = None):
        """Starts an MLflow run context."""
        return mlflow.start_run(run_name=run_name)

    def log_params(self, params: dict[str, Any]):
        """Logs a dictionary of parameters."""
        for key, value in params.items():
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None):
        """Logs a dictionary of metrics."""
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)

    def log_figure(self, figure, artifact_file: str):
        """Logs a matplotlib figure."""
        mlflow.log_figure(figure, artifact_file)

    def log_artifact(self, local_path: str):
        """Logs a local file as an artifact."""
        if os.path.exists(local_path):
            mlflow.log_artifact(local_path)
        else:
            print(f"Warning: Artifact {local_path} not found.")

    def log_model(self, model, artifact_path: str = "model"):
        """Logs a generic model (statsmodels or sklearn)."""
        if hasattr(model, 'save'):
             mlflow.statsmodels.log_model(model, artifact_path)
        else:
             mlflow.sklearn.log_model(model, artifact_path)

    def get_run_id(self):
        """Returns the current active run ID."""
        return mlflow.active_run().info.run_id
