"""Comprehensive security, RBAC, workspace isolation, and failure mode test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from pathlib import Path

from app.core.errors import AuthorizationError, DomainError
from app.core.storage import LocalStorageBackend, S3StorageBackend, StorageService
from app.domains.identity.policy import Permission, require_permission
from ml.artifacts.store import ArtifactStore
from services.ml_inference.predictor import ControlledInferencePredictor


def test_rbac_permission_checks() -> None:
    """Verify RBAC policy correctly allows and denies permissions by role."""
    # Viewer role
    with pytest.raises(AuthorizationError):
        require_permission("viewer", Permission.DATASET_CREATE)
    with pytest.raises(AuthorizationError):
        require_permission("viewer", Permission.MODEL_TRAIN)

    # Editor role
    require_permission("editor", Permission.DATASET_CREATE)
    require_permission("editor", Permission.MODEL_TRAIN)
    with pytest.raises(AuthorizationError):
        require_permission("editor", Permission.WORKSPACE_DELETE)

    # Owner role
    require_permission("owner", Permission.DATASET_CREATE)
    require_permission("owner", Permission.WORKSPACE_DELETE)


def test_path_traversal_prevention(tmp_path: Path) -> None:
    """Verify LocalStorageBackend and StorageService reject path traversal attempts."""
    backend = LocalStorageBackend(base_directory=str(tmp_path))
    service = StorageService(backend=backend)

    ws_id = uuid4()
    ds_id = uuid4()

    with pytest.raises(ValueError, match="Invalid filename with path traversal characters"):
        service.save_dataset_file(ws_id, ds_id, "../../../etc/passwd", b"data")

    with pytest.raises(ValueError, match="Path traversal outside base directory detected"):
        backend.put_object("../../outside.txt", b"malicious content")


def test_corrupted_artifact_integrity_rejection(mock_s3_client: MagicMock) -> None:
    """Verify predictor rejects artifacts with tampered payload / SHA-256 mismatch."""
    backend = S3StorageBackend(bucket_name="auraml-test-bucket", s3_client=mock_s3_client)
    store = ArtifactStore(backend=backend)

    tampered_data = {
        "model_name": "tampered_model",
        "version_tag": "v1.0.0",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "weights": [1.0],
    }

    mock_body = MagicMock()
    import json

    mock_body.read.return_value = json.dumps(tampered_data).encode("utf-8")
    mock_s3_client.get_object.return_value = {"Body": mock_body}

    predictor = ControlledInferencePredictor(artifact_store=store)

    with pytest.raises(DomainError) as exc_info:
        predictor.predict(
            model_status="approved",
            artifact_path="workspaces/ws1/models/tampered_model/v1.0.0.json",
            input_features={"f1": 1.0},
        )

    assert exc_info.value.code == "artifact_corrupted"
    assert exc_info.value.status_code == 400


def test_unapproved_model_inference_denied() -> None:
    """Verify inference is denied for models not in approved, staging, or production status."""
    predictor = ControlledInferencePredictor()
    with pytest.raises(DomainError) as exc_info:
        predictor.predict(
            model_status="draft",
            artifact_path="workspaces/ws1/models/m1/v1.0.0.json",
            input_features={"f1": 1.0},
        )

    assert exc_info.value.code == "model_not_approved"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_redis_reconnect_resilience() -> None:
    """Verify RedisManager handles transient connection failures gracefully."""
    from app.core.redis import RedisManager

    manager = RedisManager(redis_url="redis://localhost:6379/0")
    manager._client = AsyncMock()
    manager._client.ping.side_effect = [Exception("Transient connection reset"), True]

    # First ping fails
    res1 = await manager.ping()
    assert res1 is False

    # Second ping succeeds
    res2 = await manager.ping()
    assert res2 is True
