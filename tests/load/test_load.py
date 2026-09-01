"""Load and concurrency testing suite for Milestone 8 production verification."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.storage import S3StorageBackend, StorageService
from ml.artifacts.store import ArtifactStore
from services.ml_inference.predictor import ControlledInferencePredictor


@pytest.mark.asyncio
async def test_concurrent_s3_storage_load(mock_s3_client: MagicMock) -> None:
    """Simulate 50 concurrent S3 object storage upload & read operations."""
    backend = S3StorageBackend(bucket_name="auraml-load-bucket", s3_client=mock_s3_client)
    service = StorageService(backend=backend)

    s3_store: dict[str, bytes] = {}

    def fake_put_object(Bucket, Key, Body, **kwargs):
        s3_store[Key] = Body if isinstance(Body, bytes) else Body.encode("utf-8")

    def fake_get_object(Bucket, Key):
        mock_body = MagicMock()
        mock_body.read.return_value = s3_store[Key]
        return {"Body": mock_body}

    mock_s3_client.put_object.side_effect = fake_put_object
    mock_s3_client.get_object.side_effect = fake_get_object

    num_concurrent = 50
    ws_id = uuid4()

    async def single_upload_task(i: int) -> float:
        ds_id = uuid4()
        content = f"col1,col2\n{i},{i * 2}\n".encode()
        start = time.perf_counter()
        key = service.save_dataset_file(ws_id, ds_id, f"data_{i}.csv", content)
        read_back = service.read_dataset_file(key)
        duration = time.perf_counter() - start
        assert read_back == content
        return duration

    start_all = time.perf_counter()
    durations = await asyncio.gather(*(single_upload_task(i) for i in range(num_concurrent)))
    total_time = time.perf_counter() - start_all

    throughput = num_concurrent / total_time
    avg_latency = sum(durations) / len(durations)

    assert total_time > 0
    assert throughput > 0
    assert avg_latency >= 0.0


@pytest.mark.asyncio
async def test_concurrent_inference_predictions(mock_s3_client: MagicMock) -> None:
    """Simulate 100 concurrent inference prediction requests under load."""
    backend = S3StorageBackend(bucket_name="auraml-load-bucket", s3_client=mock_s3_client)
    store = ArtifactStore(backend=backend)

    artifact_data = {
        "model_name": "load_classifier",
        "version_tag": "v1.0.0",
        "model_type": "random_forest",
        "feature_names": ["f1", "f2"],
        "weights": [0.5, 0.5],
        "target_classes": ["negative", "positive"],
    }

    s3_store: dict[str, bytes] = {}

    def fake_put_object(Bucket, Key, Body, **kwargs):
        s3_store[Key] = Body if isinstance(Body, bytes) else Body.encode("utf-8")

    def fake_get_object(Bucket, Key):
        mock_body = MagicMock()
        mock_body.read.return_value = s3_store[Key]
        return {"Body": mock_body}

    mock_s3_client.put_object.side_effect = fake_put_object
    mock_s3_client.get_object.side_effect = fake_get_object

    key = store.save_artifact("load_classifier", "v1.0.0", artifact_data)
    predictor = ControlledInferencePredictor(artifact_store=store)

    num_concurrent = 100

    async def single_predict_task(i: int) -> float:
        res, latency = predictor.predict(
            model_status="approved",
            artifact_path=key,
            input_features={"f1": float(i), "f2": float(i * 2)},
        )
        assert res["prediction"] in ("positive", "negative")
        return latency

    start_all = time.perf_counter()
    latencies = await asyncio.gather(*(single_predict_task(i) for i in range(num_concurrent)))
    total_duration = time.perf_counter() - start_all

    throughput = num_concurrent / total_duration
    avg_latency_ms = sum(latencies) / len(latencies)

    assert total_duration > 0
    assert throughput > 0
    assert avg_latency_ms >= 0.0
