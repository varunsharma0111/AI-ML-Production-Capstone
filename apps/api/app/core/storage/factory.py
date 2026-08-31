"""Storage backend factory based on environment settings."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.storage.base import StorageBackend
from app.core.storage.local import LocalStorageBackend
from app.core.storage.s3 import S3StorageBackend


def get_storage_backend(settings: Settings | None = None) -> StorageBackend:
    """Instantiate and return the configured StorageBackend (local or s3)."""
    cfg = settings or get_settings()

    if cfg.storage_backend == "s3":
        return S3StorageBackend(
            bucket_name=cfg.s3_bucket,
            aws_access_key_id=cfg.s3_access_key_id,
            aws_secret_access_key=cfg.s3_secret_access_key,
            region_name=cfg.s3_region,
            endpoint_url=cfg.s3_endpoint_url,
        )
    return LocalStorageBackend(base_dir=cfg.storage_path)
