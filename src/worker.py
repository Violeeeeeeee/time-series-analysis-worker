import asyncio
import json
import os
from os import system
import shutil
import logging
from typing import Optional
from urllib.parse import urlparse

import aio_pika
import boto3
from redis.asyncio import Redis
from botocore.client import Config

from main import run_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TSA_Worker")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
JOB_QUEUE_NAME = os.getenv("JOB_QUEUE_NAME", "job_queue")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "ml-data")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

class JobProcessor:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        self.redis: Optional[Redis] = None

    async def get_redis(self) -> Redis:
        """Lazy initialization of Redis connection."""
        if not self.redis:
            self.redis = Redis.from_url(REDIS_URL, decode_responses=True)
        return self.redis

    def parse_s3_url(self, s3_url: str):
        """Extracts bucket and key from s3://bucket/key url."""
        parsed = urlparse(s3_url)
        if parsed.scheme == 's3':
            return parsed.netloc, parsed.path.lstrip('/')
        return S3_BUCKET_NAME, s3_url

    async def update_job_status(self, job_id: str, status: str, result_data: dict = None):
        """Updates the job status and merges result data into the Redis hash."""
        redis = await self.get_redis()
        key = f"job_id:{job_id}"

        if not await redis.exists(key):
            logger.error(f"Job {job_id} not found in Redis (key: {key})!")
            return

        update_payload = {"status": status}

        if result_data:
            metrics = result_data.get("metrics", {})
            update_payload["metrics_MSE"] = metrics.get("MSE", 0.0)
            update_payload["metrics_RMSE"] = metrics.get("RMSE", 0.0)
            update_payload["metrics_MAE"] = metrics.get("MAE", 0.0)
            update_payload["metrics_MAPE"] = metrics.get("MAPE", 0.0)
            update_payload["metrics_SMAPE"] = metrics.get("SMAPE", 0.0)
            update_payload["metrics_WMAPE"] = metrics.get("WMAPE", 0.0)
            update_payload["run_id"] = result_data.get("run_id", "")
            update_payload["artifact_config"] = result_data.get("artifact_config", "")
            update_payload["artifact_model"] = result_data.get("artifact_model", "")
            update_payload["artifact_forecast"] = result_data.get("artifact_forecast", "")
            update_payload["artifact_json"] = result_data.get("artifact_json", "")
            update_payload["artifact_plot"] = result_data.get("artifact_plot", "")
            update_payload["dvc_hash"] = result_data.get("dvc_hash", "")

        await redis.hset(key, mapping={k: str(v) for k, v in update_payload.items()})
        logger.info(f"Updated Redis for Job {job_id}: {status}")

    def download_file(self, bucket: str, key: str, local_path: str):
        """Downloads a file from S3."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            logger.info(f"Downloading s3://{bucket}/{key} -> {local_path}")
            self.s3_client.download_file(bucket, key, local_path)
        except Exception as e:
            logger.error(f"Failed to download s3://{bucket}/{key}: {e}")
            raise

    async def process_job(self, message: aio_pika.IncomingMessage):
        """Main callback for processing RabbitMQ messages."""
        async with message.process():
            body = json.loads(message.body)
            job_id = body.get("job_id")
            action = body.get("action")
            logger.info(f"Received Job: {job_id} | Action: {action}")

            if action == "process_dataset":
                pass
            elif action == "update_model":
                pass
            else:
                logger.warning(f"Unknown action {action}, skipping.")
                return

            redis = await self.get_redis()
            redis_key = f"job_id:{job_id}"
            job_data = await redis.hgetall(redis_key)

            if not job_data:
                logger.error(f"Job data missing in Redis for {job_id} (key: {redis_key})")
                return

            await self.update_job_status(job_id, "Processing")
            temp_dir = f"temp_{job_id}"
            try:
                user_id = job_data.get("user_id")
                raw_dataset_url = job_data.get("dataset_url")
                bucket_name, dataset_key = self.parse_s3_url(raw_dataset_url)
                dataset_filename = os.path.basename(dataset_key)
                local_data_path = f"{temp_dir}/{dataset_filename}"
                raw_config_url = job_data.get("artifact_config")
                bucket_name, config_key = self.parse_s3_url(raw_config_url)
                config_filename = os.path.basename(config_key)
                local_config_path1 = f"{temp_dir}/{config_filename}"
                local_config_path = f"{temp_dir}/config.yaml"
                self.download_file(bucket_name, dataset_key, local_data_path)
                final_config_final = ""

                try:
                    self.download_file(bucket_name, config_key, local_config_path1)
                    final_config_final = local_config_path1
                    system(f"cat {local_config_path1}")
                except Exception:
                    logger.warning("User config not found in S3, using default container config.")
                    shutil.copy("configs/config.yaml", local_config_path)
                    final_config_final = local_config_path
                    system(f"cat {local_config_path}")

                logger.info("Starting ML Pipeline in a separate thread...")
                loop = asyncio.get_running_loop()
                import functools
                pipeline_func = functools.partial(
                    run_pipeline,
                    dataset_path=local_data_path,
                    config_path=final_config_final,
                    config_filename=config_filename,
                    job_id=job_id,
                    user_id=user_id,
                    dvc_hash="raw_processing",
                    config_hash="raw_processing"
                )
                result = await loop.run_in_executor(None, pipeline_func)

                await self.update_job_status(job_id, "Done", result)

            except Exception as e:
                logger.error(f"Job {job_id} Failed: {e}", exc_info=True)
                await self.update_job_status(job_id, "Failed")
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

async def main():
    """Worker entry point."""
    logger.info("Connecting to RabbitMQ...")
    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(JOB_QUEUE_NAME, durable=True)
        logger.info("Waiting for messages...")
        processor = JobProcessor()
        await channel.set_qos(prefetch_count=1)
        await queue.consume(processor.process_job)
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped.")
