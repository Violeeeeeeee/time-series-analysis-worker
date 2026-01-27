# Time Series Analysis (TSA) Worker Documentation

## 1. Project Overview

The **TSA Worker** is an asynchronous microservice designed to perform automated time series forecasting. It operates as a stateless consumer that listens for jobs via **RabbitMQ**, processes datasets using **ARIMA/SARIMAX** models, logs experiments to **MLflow**, and stores results in **S3 (MinIO)** and **Redis**.

**Key Features:**

* **Automated Pipeline:** Handles data loading, preprocessing, baseline comparison, and advanced modeling.
* **AutoML Capabilities:** Automatically detects stationarity (), seasonality (), and optimal ARIMA orders .
* **Experiment Tracking:** Full integration with MLflow for metrics, parameters, and artifact storage.
* **Stateless Architecture:** Uses DVC(doesn\`t work for mvp right now) and S3 to fetch data on demand, ensuring reproducibility.

---

## 2. System Architecture

The worker fits into the broader **SKU ML Service** ecosystem.

**Data Flow:**

1. **Job Ingestion:** The worker receives a JSON payload from RabbitMQ .
2. **Data Fetching:** Downloads the raw dataset (`.csv`, 0 column date and 1 column value) and configuration (`.yaml`) from S3.
3. **Training:**
* Runs **Baseline Models** (Simple Naive, Seasonal Naive).
* Runs **AutoARIMA** to find the best hyperparameters.
* Generates forecasts and confidence intervals (Fan Charts).


4. **Artifact Logging:** Saves forecasts, plots, models, and metrics to MLflow and S3.
5. **Status Update:** Updates the job status and result paths in Redis.

---

## 3. Setup & Installation

### Prerequisites

* Docker & Docker Compose
* Python 3.12+ (for local development)

### Environment Variables

The service requires the following environment variables (defined in `.env` or `docker-compose.yaml`):

```{.env}
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

### Running with Docker

To start the full stack (including DB, MinIO, MLflow, and the Worker):

```bash
docker-compose up --build -d
```

---

## 4. Configuration Guide (`config.yaml`)

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

---

## 5. Project Structure

```text
src/
├── main.py                 # Pipeline entry point (Config loading -> Training)
├── worker.py               # RabbitMQ consumer & Job processor
├── models/
│   ├── arima_runner.py     # AutoARIMA logic, Grid Search, and Forecasting
│   ├── baseline_runner.py  # Naive and Seasonal Naive baselines
│   └── batch_runner.py     # Logic for batch parameter testing
├── utils/
│   ├── data_manager.py     # DVC data loading & preprocessing
│   ├── mlflow_manager.py   # Wrapper for MLflow logging
│   └── metrics.py          # Calculation of RMSE, MAE, MAPE, SMAPE
└── visualization/
    └── plots.py            # Matplotlib generation for Fan Charts & Scatter plots

```
