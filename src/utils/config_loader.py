import yaml
import argparse
import os
from typing import Any

def load_config(config_path: str) -> dict[str, Any]:
    """
    Loads configuration from a YAML file.

    Args:
        config_path (str): Path to the YAML file.

    Returns:
        dict[str, Any]: Dictionary containing configuration parameters.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {config_path}: {e}")
        exit(1)

def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments for the worker execution.

    Returns:
        argparse.Namespace: Object containing parsed arguments including:
            - dataset_path: Path to the cached dataset.
            - config_path: Path to the cached config.
            - dvc_hash/config_hash: Integrity checksums.
            - job_id/user_id: Identifiers for tracking and artifacts.
    """
    parser = argparse.ArgumentParser(description="Time Series Analysis Pipeline")
    parser.add_argument(
        '--rev',
        type=str,
        default=None,
        help='Git commit hash (or tag) to retrieve data version from DVC. Default: None (current workspace).'
    )
    parser.add_argument('--dataset_path', type=str, required=True, help='Path to the dvc-tracked dataset file')
    parser.add_argument('--dvc_hash', type=str, required=True, help='DVC hash of the dataset')
    parser.add_argument('--config_path', type=str, required=True, help='Path to the cached YAML config file')
    parser.add_argument('--config_hash', type=str, required=True, help='DVC hash of the config')
    parser.add_argument('--job_id', type=str, required=True, help='Unique Job ID (RabbitMQ)')
    parser.add_argument('--user_id', type=str, required=True, help='User ID')
    return parser.parse_args()
