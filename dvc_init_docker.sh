#!/bin/bash
set -e

git config --global --add safe.directory /app

if [ ! -d ".git" ]; then
    echo "Initializing Git..."
    git init
    git branch -M main
    git config user.email "docker@mlflow.local"
    git config user.name "Docker Runner"
fi

if [ ! -d ".dvc" ]; then
    echo "Initializing DVC..."
    dvc init

    dvc remote add -d -f user_remote s3://ml-data/dvc_storage
    dvc remote modify user_remote endpointurl http://minio:9000
    dvc remote modify user_remote access_key_id minioadmin
    dvc remote modify user_remote secret_access_key minioadmin
    dvc remote modify user_remote use_ssl false

    git add .
    git commit -m "Initialize DVC"
fi
