"""Local filesystem storage backend implementation."""

from __future__ import annotations

from pathlib import Path

from app.core.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Stores files on the local filesystem relative to a base path."""

    def __init__(
        self,
        base_dir: Path | str | None = None,
        base_directory: Path | str | None = None,
        **kwargs: object,
    ) -> None:
        path = base_dir or base_directory or "./data/storage"
        self.base_dir = Path(path).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_target_path(self, key: str) -> Path:
        clean_key = key.lstrip("/").replace("\\", "/")
        target = (self.base_dir / clean_key).resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError as err:
            raise ValueError("Path traversal outside base directory detected.") from err
        return target

    def put_object(self, key: str, content: bytes, content_type: str | None = None) -> str:
        clean_key = key.lstrip("/").replace("\\", "/")
        target_path = self._get_target_path(clean_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        return clean_key

    def get_object(self, key: str) -> bytes:
        target_path = self._get_target_path(key)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Storage object not found for key: {key}")
        return target_path.read_bytes()

    def delete_object(self, key: str) -> bool:
        target_path = self._get_target_path(key)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
        return False

    def object_exists(self, key: str) -> bool:
        try:
            target_path = self._get_target_path(key)
            return target_path.exists() and target_path.is_file()
        except ValueError:
            return False

    def save_file(self, key: str, content: bytes) -> str:
        return self.put_object(key, content)

    def read_file(self, key: str) -> bytes:
        return self.get_object(key)

    def delete_file(self, key: str) -> bool:
        return self.delete_object(key)
