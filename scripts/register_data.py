import os
import boto3
import argparse
import subprocess
import shutil
import yaml
from dotenv import load_dotenv
from typing import Any

load_dotenv()

def load_yaml_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def setup_dvc_remote(user_id: str, bucket: str, dvc_folder_name: str) -> None:
    """
    Configures a local DVC remote to point to the user's specific S3 folder.

    Uses the '--local' flag to modify '.dvc/config.local' instead of the versioned
    '.dvc/config', ensuring these user-specific settings are not tracked by Git.

    Args:
        user_id (str): The unique identifier of the user.
        bucket (str): S3 bucket name.
        dvc_folder_name (str): dvc folder name.
    """
    remote_name = "user_remote"
    remote_url = f"s3://{bucket}/{user_id}/{dvc_folder_name}"

    print(f"Configuring DVC remote '{remote_name}' -> {remote_url}")

    subprocess.run(["dvc", "remote", "remove", remote_name, "--local"], stderr=subprocess.DEVNULL)

    subprocess.run(["dvc", "remote", "add", "-d", remote_name, remote_url, "--local"], check=True)

    endpoint = os.getenv('S3_ENDPOINT_URL')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

    subprocess.run(["dvc", "remote", "modify", remote_name, "endpointurl", endpoint, "--local"], check=True)
    subprocess.run(["dvc", "remote", "modify", remote_name, "access_key_id", access_key, "--local"], check=True)
    subprocess.run(["dvc", "remote", "modify", remote_name, "secret_access_key", secret_key, "--local"], check=True)
    subprocess.run(["dvc", "remote", "modify", remote_name, "use_ssl", "false", "--local"], check=True)


def process_file(s3_client: Any, bucket: str, s3_key: str, temp_dir: str) -> tuple[str, str, str]:
    """
    Downloads a raw file from S3, adds it to DVC tracking, and extracts its hash.

    Args:
        s3_client (Any): Boto3 S3 client instance.
        bucket (str): S3 bucket name.
        s3_key (str): Path to the file in S3.
        temp_dir (str): Local temporary directory for processing.

    Returns:
        Tuple[str, str, str]: (local_file_path, dvc_md5_hash, dvc_file_path)
    """
    filename = os.path.basename(s3_key)
    local_path = os.path.join(temp_dir, filename)

    print(f"Downloading {s3_key}...")
    s3_client.download_file(bucket, s3_key, local_path)

    print(f"DVC Add {filename}...")
    subprocess.run(["dvc", "add", local_path], check=True)

    dvc_file = f"{local_path}.dvc"
    with open(dvc_file, "r") as f:
        dvc_meta = yaml.safe_load(f)
        file_hash = dvc_meta["outs"][0]["md5"]

    return local_path, file_hash, dvc_file


def register_dataset(user_id: str, dataset_name: str, local_config_path: str) -> None:
    """
    Main orchestration function:
    1. Sets up the DVC remote.
    2. Downloads raw data and config from S3.
    3. Registers them with DVC (calculating hashes).
    4. Pushes the DVC-tracked files to the S3 DVC storage.
    5. Prints specific key-value pairs for the Bash script to parse.
    """
    bucket = os.getenv('S3_BUCKET_NAME')

    config_data = load_yaml_config(local_config_path)
    sys_settings = config_data['system_settings']

    temp_dir_name = sys_settings['local_temp_dir']
    raw_folder = sys_settings['s3']['raw_folder']
    dvc_folder = sys_settings['s3']['dvc_folder']

    setup_dvc_remote(user_id, bucket, dvc_folder)

    if os.path.exists(temp_dir_name):
            shutil.rmtree(temp_dir_name)
    os.makedirs(temp_dir_name)

    s3 = boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT_URL'))

    s3_data_key = f"{user_id}/{raw_folder}/{dataset_name}"
    s3_config_key = f"{user_id}/{raw_folder}/config.yaml"

    local_data_path, data_hash, data_dvc = process_file(s3, bucket, s3_data_key, temp_dir_name)

    local_config_path, config_hash, config_dvc = process_file(s3, bucket, s3_config_key, temp_dir_name)

    print("Pushing to DVC remote...")
    subprocess.run(["dvc", "push", data_dvc, config_dvc], check=True)

    print(f"OUTPUT_DATA_HASH={data_hash}")
    print(f"OUTPUT_CONFIG_HASH={config_hash}")
    print(f"OUTPUT_DATA_PATH={local_data_path}")
    print(f"OUTPUT_CONFIG_PATH={local_config_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", required=True)
    parser.add_argument("--dataset_name", required=True)
    parser.add_argument("--local_config_path", required=True, help="Path to local config to read settings")
    args = parser.parse_args()

    register_dataset(args.user_id, args.dataset_name, args.local_config_path)
