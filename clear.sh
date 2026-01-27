#!/bin/bash

docker-compose down -v;
rm -rf .dvc .dvcignore mlflow.db .git output_plots temp_processing error.log;
