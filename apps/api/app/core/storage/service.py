"""Storage service wrapping configured backend (Local or S3)."""

from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.core.storage.base import StorageBackend
from app.core.storage.factory import get_storage_backend


class StorageService:
    """Unified file storage service abstraction for dataset upload and retrieval."""

    def __init__(
        self,
        backend: StorageBackend | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.backend = backend or get_storage_backend(settings)

    def save_dataset_file(
        self,
        workspace_id: UUID | str,
        dataset_id: UUID | str,
        filename: str,
        content: bytes,
    ) -> str:
        """Persist dataset file using active storage backend."""
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename with path traversal characters.")
        ext = filename.split(".")[-1] if "." in filename else "csv"
        key = f"workspaces/{workspace_id}/datasets/{dataset_id}.{ext}"
        return self.backend.put_object(key, content)

    def read_dataset_file(self, file_path_or_key: str) -> bytes:
        """Retrieve dataset bytes using active storage backend."""
        return self.backend.get_object(file_path_or_key)

    def delete_dataset_file(self, file_path_or_key: str) -> None:
        """Delete dataset file from active storage backend."""
        self.backend.delete_object(file_path_or_key)
