#!/bin/bash

if [ -z "$DB_HOST" ] && [ -f .env ]; then
  echo "Local run detected. Loading .env..."
  export $(echo $(cat .env | sed 's/#.*//g' | xargs) | envsubst)
else
  echo "Docker run detected. Using environment variables from container."
fi

JOB_ID="job_$(date +%s)"
USER_ID="user_124"
DATASET_NAME="daily-total-female-births.csv"

LOCAL_SOURCE_FILE="data/daily-total-female-births.csv"
LOCAL_CONFIG_FILE="configs/config.yaml"

echo "--- Starting Pipeline for Job: $JOB_ID (User: $USER_ID) ---"

echo "\n--- STEP 1: Backend Upload ---"
python scripts/s3pushfile.py \
    --data_file "$LOCAL_SOURCE_FILE" \
    --config_file "$LOCAL_CONFIG_FILE" \
    --user "$USER_ID" \
    --data_name "$DATASET_NAME"

echo "\n--- STEP 2: DVC Register & Cache ---"
REG_OUTPUT=$(python scripts/register_data.py \
    --user_id "$USER_ID" \
    --dataset_name "$DATASET_NAME" \
    --local_config_path "$LOCAL_CONFIG_FILE")

DATA_HASH=$(echo "$REG_OUTPUT" | grep "OUTPUT_DATA_HASH=" | cut -d'=' -f2)
CONFIG_HASH=$(echo "$REG_OUTPUT" | grep "OUTPUT_CONFIG_HASH=" | cut -d'=' -f2)
DATA_PATH=$(echo "$REG_OUTPUT" | grep "OUTPUT_DATA_PATH=" | cut -d'=' -f2)
CONFIG_PATH=$(echo "$REG_OUTPUT" | grep "OUTPUT_CONFIG_PATH=" | cut -d'=' -f2)

if [ -z "$DATA_HASH" ] || [ -z "$CONFIG_HASH" ]; then
    echo "[X] Failed to register data or config. Stopping."
    echo "Output was: $REG_OUTPUT"
    exit 1
fi

echo "   > Data Hash: $DATA_HASH"
echo "   > Config Hash: $CONFIG_HASH"
echo "   > Cached Data Path: $DATA_PATH"
echo "   > Cached Config Path: $CONFIG_PATH"


echo "\n--- STEP 3: Training ---"

if python src/main.py \
    --dataset_path "$DATA_PATH" \
    --config_path "$CONFIG_PATH" \
    --dvc_hash "$DATA_HASH" \
    --config_hash "$CONFIG_HASH" \
    --job_id "$JOB_ID" \
    --user_id "$USER_ID" 2> error.log; then

    echo "[Y] Training passed successfully!"
    echo "Results saved to results.json"

    echo "Cleaning up temp files..."
    rm -rf temp_processing
else
    echo "[X] Training FAILED!"
    cat error.log | tail -n 10
    exit 1
fi

echo "\nPipeline Finished."
