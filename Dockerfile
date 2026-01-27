# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (git for DVC, gettext-base for envsubst)
RUN apt-get update && apt-get install -y \
    git \
    gettext-base \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Fix git ownership issue for the mounted directory
RUN git config --global --add safe.directory /app

COPY requirements.txt /app
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./src /app/src
COPY ./configs /app/configs
COPY ./scripts /app/scripts

COPY ./dvc_init_docker.sh ./clear.sh ./requirements.txt ./run.sh /app/

# Ensure the new entrypoint script is executable
RUN chmod +x *.sh
RUN chmod +x /app/scripts/*.py

CMD ["/app/run.sh"]

