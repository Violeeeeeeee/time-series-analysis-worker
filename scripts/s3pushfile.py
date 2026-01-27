import boto3
import os
import argparse
import yaml
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

def load_yaml_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def upload_to_raw_s3(
    local_data_path: str,
    local_config_path: str,
    user_id: str,
    dataset_name: str,
    config_path_for_names: str
) -> tuple[str, str]:
    """
    Simulates the Backend behavior: uploads local user files to the 'raw' S3 folder.

    Args:
        local_data_path (str): Path to the local dataset file.
        local_config_path (str): Path to the local config file.
        user_id (str): User identifier.
        dataset_name (str): Name of the dataset file in S3.
        config_path_for_names (str): path of the config file in S3.

    Returns:
        Tuple[str, str]: The S3 keys for the uploaded data and config.
    """
    config_data = load_yaml_config(config_path_for_names)
    raw_folder = config_data['system_settings']['s3']['raw_folder']
    s3 = boto3.client('s3',
                      endpoint_url=os.getenv('S3_ENDPOINT_URL'),
                      aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                      config=Config(signature_version='s3v4'))

    bucket = os.getenv('S3_BUCKET_NAME')
    data_key = f"{user_id}/{raw_folder}/{dataset_name}"
    print(f"Backend: Uploading Data to s3://{bucket}/{data_key} ...")
    s3.upload_file(local_data_path, bucket, data_key)

    config_key = f"{user_id}/{raw_folder}/config.yaml"
    print(f"Backend: Uploading Config to s3://{bucket}/{config_key} ...")
    s3.upload_file(local_config_path, bucket, config_key)

    print("Backend: Upload complete.")
    return data_key, config_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate backend file upload to S3.")
    parser.add_argument("--data_file", required=True, help="Local path to dataset")
    parser.add_argument("--config_file", required=True, help="Local path to config")
    parser.add_argument("--user", required=True, help="User ID")
    parser.add_argument("--data_name", required=True, help="Target dataset name (e.g. data.csv)")

    args = parser.parse_args()
    upload_to_raw_s3(args.data_file, args.config_file, args.user, args.data_name, args.config_file)
