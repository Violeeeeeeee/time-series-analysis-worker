#!/bin/bash
set -e

git init .
git branch -M main

dvc init
dvc remote add -d -f minio s3://ml-data
dvc remote modify minio endpointurl http://localhost:9000
dvc remote modify minio access_key_id minioadmin
dvc remote modify minio secret_access_key minioadmin
dvc remote modify minio use_ssl false

git add .
git commit -m "m"

mlflow server --backend-store-uri postgresql://postgres:postgres@localhost:5433/ml_service_db --default-artifact-root s3://ml-data/mlflow/ --host 0.0.0.0 --port 5001
