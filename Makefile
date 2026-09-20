COMPOSE = docker-compose
PIPELINE_CONTAINER = ml_pipeline_runner
WORKER_CONTAINER = tsa_worker_container

.PHONY: help up build down logs-worker shell init-dvc run-pipeline clean all

help:
	@echo "Available commands:"
	@echo "  make up            - Start all containers in the background"
	@echo "  make build         - Rebuild and start all containers"
	@echo "  make down          - Stop and remove all containers"
	@echo "  make logs-worker   - Tail logs from the TSA worker container"
	@echo "  make shell         - Open bash inside the pipeline container"
	@echo "  make init-dvc      - Initialize DVC inside the pipeline container"
	@echo "  make run-pipeline  - Execute the ML pipeline script"
	@echo "  make clean         - Stop containers and remove temporary files/caches"
	@echo "  make all           - Build infra, init DVC, and run pipeline"

up:
	$(COMPOSE) up -d

build:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs-worker:
	docker logs -f $(WORKER_CONTAINER)

shell:
	docker exec -it $(PIPELINE_CONTAINER) bash

init-dvc:
	docker exec -it $(PIPELINE_CONTAINER) ./dvc_init_docker.sh

run-pipeline:
	docker exec -it $(PIPELINE_CONTAINER) ./run.sh

clean:
	$(COMPOSE) down
	docker run --rm -v $(PWD):/app alpine sh -c "rm -rf /app/.dvc/cache /app/temp_processing/ /app/temp_artifacts/ /app/output_plots/ /app/error.log"
	@echo "Cleaned up temporary directories and stopped containers."

all: build init-dvc run-pipeline
