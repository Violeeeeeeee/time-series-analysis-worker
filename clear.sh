#!/bin/bash

docker-compose down -v;
rm -rf mlflow.db output_plots temp_artifacts temp_processing error.log job_*.json;
