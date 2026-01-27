# Time Series Analysis (TSA) Worker

> ** Status: Experimental**
> This codebase contains temporary implementations and workarounds intended to validate the architecture. It is not yet optimized for production use.

## Architectural Concept

The worker is designed to be stateless. It does not rely on local persistent data but fetches versioned datasets from an S3 cache based on instructions from a job scheduler.

**Data Flow:**
1.  **Ingestion:** Raw data is uploaded to S3 (User space).
2.  **Versioning:** Data is registered in DVC -> moved to DVC S3 Cache -> Raw data is discarded.
3.  **Execution:** Worker pulls specific data version (Hash) -> Trains Model -> Logs to MLflow.

## Features (Implemented)

* **DVC Integration:** Automated registration of datasets and configuration files.
* **MLflow Tracking:** Logging of metrics, parameters, and artifacts (plots/configs).
* **Dockerized Backends:** MinIO (Object Storage) and PostgreSQL (Metadata Store).
* **Simulation Scripts:** Bash and Python scripts to emulate the Backend <-> Worker lifecycle.

## Project Structure

```text
tsa/
├── configs/             # Configuration templates
├── data/                # Local source data (for simulation only)
├── scripts/             # Backend simulation scripts (Upload/Register)
├── src/                 # Application source code
├── docker-compose.yaml  # Infrastructure (MinIO, Postgres)
├── dvc_init.sh          # Init script + Starts MLflow Server locally
├── main.py              # Worker entry point
├── run.sh               # Full pipeline simulation
└── requirements.txt     # Python dependencies

```

## Environment Setup

### 1. Prerequisites

* Python 3.10+
* Docker & Docker Compose
* Git

### 2. Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### 3. Infrastructure

Start the storage and database containers:

```bash
docker-compose up -d

```

*Note: This starts MinIO (S3) and PostgreSQL. It does NOT start the MLflow server container.*

### 4. Initialization

Run the initialization script. This initializes Git/DVC, configures remotes, and **starts the MLflow server locally**:

```bash
./dvc_init.sh

```

## Usage / Simulation

The `run.sh` script simulates the entire lifecycle of a job coming from a backend:

```bash
./run.sh

```

**What happens inside `run.sh`:**

1. **Backend Upload:** Pushes local CSVs to `s3://wandb-data/{user}/raw/`.
2. **Registration:**
* Downloads raw data.
* Calculates DVC hashes.
* Pushes data to `s3://wandb-data/{user}/dvc_storage/`.


3. **Training:**
* Executes `main.py` with the calculated hashes.
* Worker pulls data from DVC storage.
* Logs results to MLflow.



## Accessing Services

* **MLflow UI:** [http://localhost:5001](https://www.google.com/search?q=http://localhost:5001)
* View experiment runs and artifacts.


* **MinIO Console:** [http://localhost:9001](https://www.google.com/search?q=http://localhost:9001)
* **User:** `minioadmin` | **Pass:** `minioadmin`
* Check `wandb-data` bucket to see how data is organized between `/raw` and `/dvc_storage`.


## Known Limitations & "Crutches"

* **Local MLflow:** MLflow runs as a background process on the host machine, not in Docker.
* **Sync Processing:** The worker processes jobs synchronously.
* **Data Duplication:** The simulation currently downloads raw data to a temp folder before hashing it (due to DVC limitations with remote-only add).



# SKU ML Service

Data processing and forecasting microservice for the "SKU" sales forecasting system.
Built on **FastAPI**.

## Features

* **JWT Authorization:** Issuance of Access tokens.
* **Data Processing:** Ability to upload a `.csv` or `.xlsl` file with sales information.
* **Data Visualization:** Service can return history data for analize
* **Forcasting:** Job creation for workers to process information and make sales predictions
* **Architecture:** Strict layer separation: `Router` -> `Service` -> `Repository` -> `Database`.
* **Async Database:** Fully asynchronous PostgreSQL interaction via `SQLAlchemy 2.0` + `asyncpg`.

---

## Tech Stack

* **Python:** 3.12+
* **Framework:** FastAPI
* **DB:** PostgreSQL, MinIO
* **ORM:** SQLAlchemy (Async)
* **Migrations:** Alembic
* **Data Processing:** Pandas
* **Validation:** Pydantic v2
* **Message Brokers:**: Redis, RabbitMQ

---

## Project Structure

The project implements a layered architecture:

```text
auth_service/
├── alembic/versions     # Database migrations
├── src/
│   ├── core/            # security
│   ├── db/              # DB connection and SQLAlchemy models
│   ├── repositories/    # Database interactions (CRUD without business logic)
│   ├── services/        # Business logic (validation, hashing, decision making)
│   ├── routers/         # API Endpoints (Controller layer)
│   ├── utils/           # Utilities for data processing
│   ├── schemas.py       # Pydantic models (DTOs) for Request/Response
│   ├── dependencies.py  # Dependency Injection (layer wiring)
│   ├── config.py        # Environment variable management
│   └── main.py          # Entrypoint
├── requirements.txt     # Dependencies
├── entrypoint.sh        # Runs migrations before starting server. For Docker
└── Dockerfile
```

##  **Setup and Execution**
1. Prerequisites
* **Docker** and **docker-compose** installed
* Python 3.12+
* Generated RSA keys in `../common` folder

2. RSA key generation
The service uses asymmetric encryption for JWTs. Create a `common` folder one level above the service directory and generate the keys:
```bash
mkdir -p ../common
cd ../common
openssl genrsa -out jwt-private.pem 2048
openssl rsa -in jwt-private.pem -outform PEM -pubout -out jwt-public.pem
```

3. Environment Variables (.env)
Create a .env file in the root of the auth_service folder. Configuration example:
```TOML
# DATABASE
DB_USER=""
DB_PASSWORD=""
DB_HOST=""
DB_PORT=
DB_NAME=""

# MINIO
MINIO_ENDPOINT=""
MINIO_ACCESS_KEY=""
MINIO_SECRET_KEY=""
MINIO_BUCKET=""
MINIO_SECURE=False

# MESSAGE BROKERS
REDIS_URL = ""
RABBITMQ_URL = ""
JOB_QUEUE_NAME = ""

# AUTHORIZATION
AUTH_SERVICE_URL = ""
PUBLIC_KEY_PATH = ""
ALGORITHM = ""

# LOGS FORMAT - JSON
JSON_LOGS = bool
```

4. API documentation
FastAPI automatically generates documentation. Once the server is running, visit:
* **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## **Key Endpoints**

**Ingestion**
 * `POST /ingestion/upload` - Upload `.csv` or `.xlsx` file to process.
 * `GET /ingestion/datasets` - Get list of all uploaded datasets.
 * `POST /ingestion/set_dataset_config` - Set(create/update) dataset configuration for processing
 * `GET /ingestion/get_dataset_config` - Get current dataset configuration

**SKU**
 * `GET /skus/` - Get list of all uploaded SKUs.

**History**
 * `GET /history/{article}` - Get history data of certain SKU.

**Forecast**
 * `POST /forecast/calculate` - Calculate forecast for certain SKU.
 * `GET /forecast/status/{job_id}` - Get status of certain forecasting job.
 * `GET /forecast/get_all_jobs` - Get list of job history (ongoing jobs are included)
 * `GET /forecast/analytics/{article}` - Get history + forecast timeline for article (optionally is available to add job_id to check certain job forecast history)

**Admin**

 * `GET /admin/datasets` – Get list of all datasets (all users).
 * `DELETE /admin/datasets/{dataset_id}` – Delete dataset by ID.

 * `GET /admin/jobs` – Get list of all forecasting jobs (all users).
 * `GET /admin/jobs/{job_id}/analytics` – Get full analytics for a specific job (history + forecast + metrics).

 * `GET /admin/users/{user_id}/skus` – Get all SKUs of a specific user.
 * `GET /admin/users/{user_id}/skus/{article}/history` – Get sales history for a specific user SKU.

**Statistic**
 * `GET /ingestion/get_dataset_config` - Get dashboard with forecasts and leaderboard
 * `GET /statistic/forecasts_analysis/` - Get history of forecast jobs with additional information
 * `GET /statistic/get_accuracy_evaluation` - Get analytics after update of existing dataset, only if dataset was processed with old data, and hasn't been processed with new(INACTIVE IN FRONTEND)



## **Migrations (Alembic)**
If you modify models in `src/db/models.py`, create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head

# In case of docker(docker-compose) run, migrations will be completed automatically via entrypoint.sh (migrations must be in ml_service/alembic/versions folder)
```

## **Important Notes**
