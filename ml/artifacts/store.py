"""Artifact store for versioned ML model weights with SHA-256 integrity verification."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_DIR = Path("artifacts/models")


class ArtifactStore:
    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir or DEFAULT_ARTIFACT_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_artifact(self, model_name: str, version_tag: str, artifact_data: dict[str, Any]) -> str:
        """Save model artifact to disk and return relative artifact path."""
        file_dir = self.base_dir / model_name
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / f"{version_tag}.json"

        content = json.dumps(artifact_data, indent=2, sort_keys=True)
        sha256_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        payload = {
            "sha256": sha256_hash,
            "data": artifact_data,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return str(file_path.as_posix())

    def load_artifact(self, artifact_path: str) -> dict[str, Any]:
        """Load artifact and verify SHA-256 integrity hash."""
        file_path = Path(artifact_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        expected_hash = payload.get("sha256")
        data = payload.get("data", {})
        recalculated_hash = hashlib.sha256(
            json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        ).hexdigest()

        if expected_hash and expected_hash != recalculated_hash:
            raise ValueError("Artifact integrity check failed: Hash mismatch.")

        return data
