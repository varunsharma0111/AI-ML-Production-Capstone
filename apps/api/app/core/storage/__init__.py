"""Storage module exposing pluggable local and S3 object storage backends."""

from __future__ import annotations

from app.core.storage.base import StorageBackend
from app.core.storage.factory import get_storage_backend
from app.core.storage.local import LocalStorageBackend
from app.core.storage.s3 import S3StorageBackend
from app.core.storage.service import StorageService

__all__ = [
    "LocalStorageBackend",
    "S3StorageBackend",
    "StorageBackend",
    "StorageService",
    "get_storage_backend",
]
