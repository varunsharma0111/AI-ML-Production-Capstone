"""Production S3-compatible object storage backend implementation."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.errors import DomainError
from app.core.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """S3-compatible object storage backend supporting AWS S3, MinIO, Cloudflare R2."""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str = "us-east-1",
        endpoint_url: str | None = None,
        s3_client: Any | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name

        if s3_client is not None:
            self._client = s3_client
        else:
            config = Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=10,
            )
            client_kwargs: dict[str, Any] = {
                "service_name": "s3",
                "region_name": region_name,
                "config": config,
            }
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url
            if aws_access_key_id and aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = aws_access_key_id
                client_kwargs["aws_secret_access_key"] = aws_secret_access_key

            self._client = boto3.client(**client_kwargs)

    def put_object(self, key: str, content: bytes, content_type: str | None = None) -> str:
        clean_key = key.lstrip("/")
        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=clean_key,
                Body=content,
                **extra_args,
            )
            logger.info(
                "Successfully uploaded object to S3: s3://%s/%s", self.bucket_name, clean_key
            )
            try:
                from app.core.metrics import S3_OPERATIONS_TOTAL

                S3_OPERATIONS_TOTAL.labels(operation="put", status="success").inc()
            except Exception:
                pass
            return clean_key
        except (ClientError, BotoCoreError) as err:
            logger.error("S3 error uploading object to %s: %s", clean_key, err)
            try:
                from app.core.metrics import S3_OPERATIONS_TOTAL

                S3_OPERATIONS_TOTAL.labels(operation="put", status="error").inc()
            except Exception:
                pass
            raise DomainError(
                status_code=503,
                code="storage_unavailable",
                title="S3 Storage Error",
                detail=f"Failed to upload object to S3 storage: {err}",
            ) from err

    def get_object(self, key: str) -> bytes:
        clean_key = key.lstrip("/")
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=clean_key)
            body: bytes = response["Body"].read()
            return body
        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise FileNotFoundError(f"S3 Object not found: {clean_key}") from err
            logger.error("S3 error retrieving object %s: %s", clean_key, err)
            raise DomainError(
                status_code=503,
                code="storage_unavailable",
                title="S3 Storage Error",
                detail=f"Failed to retrieve object from S3 storage: {err}",
            ) from err
        except BotoCoreError as err:
            logger.error("S3 core error retrieving object %s: %s", clean_key, err)
            raise DomainError(
                status_code=503,
                code="storage_unavailable",
                title="S3 Storage Connection Error",
                detail=f"S3 storage connection error: {err}",
            ) from err

    def delete_object(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        try:
            self._client.delete_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except (ClientError, BotoCoreError) as err:
            logger.warning("Failed to delete object from S3: %s (%s)", clean_key, err)
            return False

    def object_exists(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=clean_key)
            return True
        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "403"):
                return False
            return False
        except BotoCoreError:
            return False
