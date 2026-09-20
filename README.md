# Time Series Analysis Worker

## Overview

My attempt to build a fully automatic time series analysis pipeline, handling everything from minimally preprocessed datasets to final predictions without human intervention.

## Approach

This worker is designed as a plug-in component for an existing broader architecture. To simulate integration with the main system, it implements dummy communication channels using RabbitMQ and Redis.

**Data Assumptions:** The pipeline assumes the input data is already minimally preprocessed (a clean CSV with `yyyy-mm-dd` dates, integer values, and no `Null` or `NaN` entries).

**Forecasting Models:** This project utilizes the ARIMA family of statistical models. The rationale is straightforward: if a dataset is of such low quality that even ARIMA yields weak results, there is no value in applying complex models like XGBoost or LightGBM. In such scenarios, it is sufficient to fall back on Naive forecasting (which is computationally free, as it simply shifts data), or the data collection approach itself must be re-evaluated.

## Project Structure

```text
time-series-analysis-worker/
├── run.sh                  # Main execution script for local environments
├── clear.sh                # Clear output files
├── dvc_init_local.sh       # DVC initialization for local setup
├── dvc_init_docker.sh      # DVC initialization for Docker setup
├── docker-compose.yaml     # Container orchestration
├── src/
│   ├── main.py             # Pipeline entry point (Config loading -> Training)
│   ├── worker.py           # RabbitMQ consumer & Job processor
│   ├── models/
│   │   ├── arima_runner.py     # AutoARIMA logic, Grid Search, and Forecasting
│   │   ├── baseline_runner.py  # Naive and Seasonal Naive baselines
│   │   └── batch_runner.py     # Logic for batch parameter testing
│   ├── utils/
│   │   ├── data_manager.py     # DVC data loading & preprocessing
│   │   ├── mlflow_manager.py   # Wrapper for MLflow logging
│   │   └── metrics.py          # Calculation of RMSE, MAE, MAPE, SMAPE
│   └── visualization/
│       └── plots.py            # Matplotlib generation for Fan Charts & Scatter plots
└── scripts/
    ├── convertcsv.py       # Utility to convert/format raw CSV data
    ├── register_data.py    # Script to register new datasets with DVC
    └── s3pushfile.py       # Utility to upload files directly to MinIO/S3

```

## Tech Stack

* **Modeling:** Python, ARIMA/SARIMAX, Naive Models
* **MLOps & Tracking:** MLflow, DVC
* **Integration (Message Broker & Cache):** RabbitMQ, Redis
* **Infrastructure:** Docker, Docker Compose, Bash (`run.sh`)

## Setup & Installation

### Prerequisites

* Docker & Docker Compose
* Python 3.12 (for local development)

### Environment Variables

The service requires the following environment variables (defined in a `.env` file or `docker-compose.yaml`):

```env
# --- MinIO / S3 Config ---
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
# For boto3
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=ml-data

# -- RabbitMQ, Redis ---
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
REDIS_URL=redis://redis:6379/0
JOB_QUEUE_NAME=job_queue

# --- MLflow ---
MLFLOW_TRACKING_URI=http://localhost:5001
MLFLOW_S3_ENDPOINT_URL=http://localhost:9000

```

### Preparation

First, clone the repository, prepare your environment variables by configuring the tsa.env file, and ensure all bash scripts are executable:

```bash
git clone https://github.com/Violeeeeeeee/time-series-analysis-worker.git
cd time-series-analysis-worker
chmod +x *.sh
```

> **Tip:** We use a `Makefile` to orchestrate the Docker environments. You can run `make help` in your terminal at any time to see a full list of available commands.

### Option 1: Running with Docker (Recommended)

The easiest way to start the full stack (Postgres, MinIO, MLflow, Redis, RabbitMQ, and the Worker) and run the pipeline is using `make`:

```bash
make all

```

This single command will:

1. Build and start all required containers in the background.
2. Initialize the DVC repository inside the pipeline container.
3. Execute the ML pipeline script.

**Other useful commands:**

* `make logs-worker` — View the RabbitMQ worker logs.
* `make shell` — Open an interactive bash session inside the pipeline container.
* `make clean` — Stop all containers and safely remove temporary caches, DVC files, and plot outputs.

### Option 2: Conda (Local Execution)

For local execution, you will need local instances of Redis and RabbitMQ running to test the communication layer. The execution is handled entirely by the `run.sh` script.

```bash
conda create -n tsa-worker python=3.12
conda activate tsa-worker
pip install -r requirements.txt
./dvc_init_local.sh
./run.sh

```

### Option 3: Pip / Virtualenv (Local Execution)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./dvc_init_local.sh
./run.sh

```

## Configuration Guide (`config.yaml`)

The behavior of the ML pipeline is controlled by a YAML configuration file passed with the job.

**Structure:**

```yaml
random_seed: 42
system_settings: # dont change anything here
  local_temp_dir: temp_processing
  s3:
    bucket_name: ml-data
    raw_folder: raw
    config_folder: configs
    dvc_folder: dvc_storage
    experiments_folder: experiments
  visualization:
    show_plots: false
    save_plots: true
    output_dir: ./output_plots/
user_parameters: # here you can change only values
  data:
    # Frequency: "D" (Day), "MS" (Month Start), "H" (Hour)
    frequency: D
    steps: 14 # forecast (e.g. 14 days, months, years, hours, depends on frequency)
  model:
    type: arima
    seasonality: 7

```
