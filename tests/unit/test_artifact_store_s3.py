"""Unit tests for S3-compatible ArtifactStore and StorageBackend implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.storage.local import LocalStorageBackend
from app.core.storage.s3 import S3StorageBackend
from ml.artifacts.store import ArtifactStore
from services.ml_inference.predictor import ControlledInferencePredictor


@pytest.fixture
def temp_local_backend(tmp_path: Path) -> LocalStorageBackend:
    return LocalStorageBackend(base_dir=tmp_path / "storage")


@pytest.fixture
def mock_s3_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def s3_backend(mock_s3_client: MagicMock) -> S3StorageBackend:
    return S3StorageBackend(
        bucket_name="auraml-test-bucket",
        s3_client=mock_s3_client,
    )


def test_1_local_artifact_store_save_and_load(temp_local_backend: LocalStorageBackend) -> None:
    """Verify Local ArtifactStore saves and loads model artifacts."""
    store = ArtifactStore(backend=temp_local_backend)
    data = {"weights": [0.1, 0.2], "target_classes": ["neg", "pos"]}

    key = store.save_artifact("test_model", "v1.0.0", data)
    assert key == "models/test_model/v1.0.0.json"

    loaded = store.load_artifact(key)
    assert loaded["weights"] == [0.1, 0.2]


def test_2_s3_artifact_store_save_and_load(
    s3_backend: S3StorageBackend, mock_s3_client: MagicMock
) -> None:
    """Verify S3 ArtifactStore calls put_object and get_object on S3 backend."""
    store = ArtifactStore(backend=s3_backend)
    data = {"weights": [0.5, 0.5], "feature_names": ["f1", "f2"]}

    # Mock get_object response
    saved_bytes: list[bytes] = []

    def fake_put_object(Bucket: str, Key: str, Body: bytes | str, **kwargs: Any) -> None:
        saved_bytes.append(Body if isinstance(Body, bytes) else Body.encode("utf-8"))

    mock_s3_client.put_object.side_effect = fake_put_object

    key = store.save_artifact("s3_model", "v2.0.0", data)
    assert key == "models/s3_model/v2.0.0.json"
    mock_s3_client.put_object.assert_called_once()

    # Setup get_object return
    mock_body = MagicMock()
    mock_body.read.return_value = saved_bytes[0]
    mock_s3_client.get_object.return_value = {"Body": mock_body}

    loaded = store.load_artifact(key)
    assert loaded["feature_names"] == ["f1", "f2"]


def test_3_upload_save_artifact_returns_key(temp_local_backend: LocalStorageBackend) -> None:
    """Verify save_artifact returns canonical object key."""
    store = ArtifactStore(backend=temp_local_backend)
    key = store.save_artifact("sentiment", "v1.0.0", {"a": 1})
    assert key.endswith("v1.0.0.json")


def test_4_download_load_artifact_retrieves_data(temp_local_backend: LocalStorageBackend) -> None:
    """Verify load_artifact reads object key content accurately."""
    store = ArtifactStore(backend=temp_local_backend)
    key = store.save_artifact("classifier", "v1.0.0", {"version": "v1"})
    loaded = store.load_artifact(key)
    assert loaded["version"] == "v1"


def test_5_missing_artifact_raises_file_not_found(temp_local_backend: LocalStorageBackend) -> None:
    """Verify loading missing key raises FileNotFoundError."""
    store = ArtifactStore(backend=temp_local_backend)
    with pytest.raises(FileNotFoundError):
        store.load_artifact("non_existent_key.json")


def test_6_sha256_integrity_verification_success(temp_local_backend: LocalStorageBackend) -> None:
    """Verify SHA-256 hash check passes for untampered artifacts."""
    store = ArtifactStore(backend=temp_local_backend)
    data = {"metrics": {"accuracy": 0.95}}
    key = store.save_artifact("honest_model", "v1.0.0", data)
    loaded = store.load_artifact(key)
    assert loaded["metrics"]["accuracy"] == 0.95


def test_7_tampered_artifact_rejection(temp_local_backend: LocalStorageBackend) -> None:
    """Verify load_artifact raises ValueError on hash mismatch."""
    store = ArtifactStore(backend=temp_local_backend)
    data = {"weights": [1.0, 2.0]}
    key = store.save_artifact("tampered_model", "v1.0.0", data)

    # Directly alter content on backend
    raw_bytes = temp_local_backend.get_object(key)
    payload = json.loads(raw_bytes.decode("utf-8"))
    payload["data"]["weights"] = [999.0, 999.0]  # Tamper with weights
    temp_local_backend.put_object(key, json.dumps(payload).encode("utf-8"))

    with pytest.raises(ValueError, match="Artifact integrity check failed"):
        store.load_artifact(key)


def test_8_workspace_isolation_in_key_structure(temp_local_backend: LocalStorageBackend) -> None:
    """Verify workspace_id is prepended to object storage keys."""
    ws_id = uuid4()
    store = ArtifactStore(backend=temp_local_backend)
    key = store.save_artifact("isolated_model", "v1.0.0", {"test": True}, workspace_id=ws_id)
    assert key == f"workspaces/{ws_id}/models/isolated_model/v1.0.0.json"


def test_9_model_version_isolation_in_key_structure(
    temp_local_backend: LocalStorageBackend,
) -> None:
    """Verify different versions produce distinct non-colliding object keys."""
    store = ArtifactStore(backend=temp_local_backend)
    key1 = store.save_artifact("model_a", "v1.0.0", {"v": 1})
    key2 = store.save_artifact("model_a", "v2.0.0", {"v": 2})

    assert key1 != key2
    assert store.load_artifact(key1)["v"] == 1
    assert store.load_artifact(key2)["v"] == 2


def test_10_s3_unavailable_error_handling(
    s3_backend: S3StorageBackend, mock_s3_client: MagicMock
) -> None:
    """Verify S3 ClientError translates into DomainError."""
    store = ArtifactStore(backend=s3_backend)
    mock_s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "S3 Service Down"}}, "GetObject"
    )

    with pytest.raises(DomainError) as exc_info:
        store.load_artifact("some/key.json")
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "storage_unavailable"


def test_11_inference_using_s3_backed_artifact(
    s3_backend: S3StorageBackend, mock_s3_client: MagicMock
) -> None:
    """Verify ControlledInferencePredictor executes predictions using S3-backed artifacts."""
    store = ArtifactStore(backend=s3_backend)

    artifact_data = {
        "model_name": "s3_predictor",
        "version_tag": "v1.0.0",
        "model_type": "random_forest",
        "feature_names": ["f1", "f2"],
        "weights": [0.5, 0.5],
        "target_classes": ["negative", "positive"],
    }

    # Save to mock s3
    saved_bytes: list[bytes] = []

    def fake_put_object(Bucket: str, Key: str, Body: bytes | str, **kwargs: Any) -> None:
        saved_bytes.append(Body if isinstance(Body, bytes) else Body.encode("utf-8"))

    mock_s3_client.put_object.side_effect = fake_put_object

    key = store.save_artifact("s3_predictor", "v1.0.0", artifact_data)

    mock_body = MagicMock()
    mock_body.read.return_value = saved_bytes[0]
    mock_s3_client.get_object.return_value = {"Body": mock_body}

    predictor = ControlledInferencePredictor(artifact_store=store)
    result, latency = predictor.predict(
        model_status="approved",
        artifact_path=key,
        input_features={"f1": 1.0, "f2": 2.0},
    )

    assert result["prediction"] in ("positive", "negative")
    assert "confidence" in result
    assert latency >= 0.0


def test_12_existing_local_development_behavior(tmp_path: Path) -> None:
    """Verify default Settings with local storage backend works seamlessly."""
    cfg = Settings(storage_backend="local", storage_path=str(tmp_path / "dev_storage"))
    backend = LocalStorageBackend(base_dir=cfg.storage_path)
    store = ArtifactStore(backend=backend)

    key = store.save_artifact("dev_model", "v1.0.0", {"env": "local"})
    assert store.load_artifact(key)["env"] == "local"
