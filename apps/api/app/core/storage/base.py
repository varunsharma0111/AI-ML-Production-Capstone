"""Abstract storage backend protocol for blob and artifact persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract interface for object storage operations (Local filesystem or S3)."""

    @abstractmethod
    def put_object(self, key: str, content: bytes, content_type: str | None = None) -> str:
        """Persist object content at specified key and return canonical object key."""
        ...

    @abstractmethod
    def get_object(self, key: str) -> bytes:
        """Fetch bytes content for key or raise FileNotFoundError if missing."""
        ...

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete object at key if it exists."""
        ...

    @abstractmethod
    def object_exists(self, key: str) -> bool:
        """Check if object exists at key."""
        ...
