"""Artifact store for versioned ML model weights with SHA-256 integrity verification."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from app.core.storage import LocalStorageBackend, StorageBackend, get_storage_backend

logger = logging.getLogger(__name__)

DEFAULT_ARTIFACT_DIR = Path("artifacts/models")


class ArtifactStore:
    """Storage-agnostic artifact store for ML model weights supporting S3 and Local storage."""

    def __init__(
        self,
        backend: StorageBackend | None = None,
        base_dir: Path | str | None = None,
    ) -> None:
        if backend is not None:
            self.backend = backend
        elif base_dir is not None:
            self.backend = LocalStorageBackend(base_dir=base_dir)
        else:
            self.backend = get_storage_backend()

    def save_artifact(
        self,
        model_name: str,
        version_tag: str,
        artifact_data: dict[str, Any],
        workspace_id: UUID | str | None = None,
    ) -> str:
        """Save model artifact to storage backend and return storage-agnostic relative key."""
        content = json.dumps(artifact_data, indent=2, sort_keys=True)
        sha256_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        payload = {
            "sha256": sha256_hash,
            "data": artifact_data,
        }

        payload_bytes = json.dumps(payload, indent=2).encode("utf-8")

        if workspace_id:
            key = f"workspaces/{workspace_id}/models/{model_name}/{version_tag}.json"
        else:
            key = f"models/{model_name}/{version_tag}.json"

        self.backend.put_object(key, payload_bytes, content_type="application/json")
        return key

    def load_artifact(self, artifact_path: str) -> dict[str, Any]:
        """Load artifact from storage backend and verify SHA-256 integrity hash."""
        content_bytes: bytes | None = None

        # 1. Primary retrieval attempt via storage backend key
        try:
            content_bytes = self.backend.get_object(artifact_path)
        except FileNotFoundError:
            content_bytes = None

        # 2. Legacy local filesystem path fallback
        if content_bytes is None:
            p = Path(artifact_path)
            if p.is_absolute() and p.exists():
                content_bytes = p.read_bytes()
            else:
                clean_rel = artifact_path.lstrip("/").replace("\\", "/")
                if clean_rel.startswith("artifacts/models/"):
                    clean_rel = clean_rel[len("artifacts/models/") :]
                elif clean_rel.startswith("models/"):
                    clean_rel = clean_rel[len("models/") :]

                fallback_path = DEFAULT_ARTIFACT_DIR / clean_rel
                if fallback_path.exists():
                    content_bytes = fallback_path.read_bytes()

        if content_bytes is None:
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        try:
            payload = json.loads(content_bytes.decode("utf-8"))
        except json.JSONDecodeError as err:
            raise ValueError(f"Corrupted JSON payload in artifact: {err}") from err

        expected_hash = payload.get("sha256")
        data = payload.get("data", {})
        recalculated_hash = hashlib.sha256(
            json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        ).hexdigest()

        if expected_hash and expected_hash != recalculated_hash:
            raise ValueError("Artifact integrity check failed: Hash mismatch.")

        return cast(dict[str, Any], data)


def model_path_fallback(rel_path: str) -> Path:
    return Path(rel_path)
