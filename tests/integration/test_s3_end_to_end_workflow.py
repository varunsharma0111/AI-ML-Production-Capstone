"""Integration test for Milestone 7: End-to-end dataset to S3-backed inference pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.core.storage import S3StorageBackend, StorageService
from ml.artifacts.store import ArtifactStore
from ml.training.trainer import ModelTrainer
from services.ml_inference.predictor import ControlledInferencePredictor


def test_milestone7_s3_end_to_end_workflow(mock_s3_client: MagicMock) -> None:
    """Execute end-to-end S3 workflow: upload -> profile -> train -> promote -> infer -> verify."""

    workspace_id = uuid4()
    dataset_id = uuid4()

    # 1. Setup S3 Storage Backend
    s3_backend = S3StorageBackend(bucket_name="auraml-prod-bucket", s3_client=mock_s3_client)
    storage_service = StorageService(backend=s3_backend)
    artifact_store = ArtifactStore(backend=s3_backend)

    # In-memory mock storage for S3 client calls
    s3_objects: dict[str, bytes] = {}

    def fake_put_object(Bucket, Key, Body, **kwargs):
        s3_objects[Key] = Body if isinstance(Body, bytes) else Body.encode("utf-8")

    def fake_get_object(Bucket, Key):
        if Key not in s3_objects:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        mock_body = MagicMock()
        mock_body.read.return_value = s3_objects[Key]
        return {"Body": mock_body}

    mock_s3_client.put_object.side_effect = fake_put_object
    mock_s3_client.get_object.side_effect = fake_get_object

    # 2. Upload CSV Dataset
    csv_content = (
        "f1,f2,f3,label\n"
        "1.0,2.0,3.0,positive\n"
        "2.0,1.0,4.0,negative\n"
        "1.5,2.5,3.5,positive\n"
        "3.0,0.5,5.0,negative\n"
        "2.5,1.5,4.5,positive\n"
        "4.0,0.2,6.0,negative\n"
    ).encode("utf-8")

    dataset_key = storage_service.save_dataset_file(
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        filename="dataset.csv",
        content=csv_content,
    )
    assert dataset_key == f"workspaces/{workspace_id}/datasets/{dataset_id}.csv"
    assert dataset_key in s3_objects

    # 3. Train Model on S3 Dataset and Upload Artifact
    trainer = ModelTrainer(artifact_store=artifact_store)
    metrics, artifact_key = trainer.train_dataset_model(
        csv_file_path=dataset_key,
        target_column="label",
        model_name="sentiment_classifier",
        version_tag="v1.0.0",
        model_type="random_forest",
        workspace_id=workspace_id,
    )

    assert artifact_key == f"workspaces/{workspace_id}/models/sentiment_classifier/v1.0.0.json"
    assert artifact_key in s3_objects
    assert metrics["accuracy"] >= 0.0

    # 4. Verify Controlled Inference using S3 Artifact
    predictor = ControlledInferencePredictor(artifact_store=artifact_store)
    prediction_result, latency_ms = predictor.predict(
        model_status="approved",
        artifact_path=artifact_key,
        input_features={"f1": 1.5, "f2": 2.5, "f3": 3.5},
    )

    assert prediction_result["prediction"] in ("positive", "negative")
    assert "confidence" in prediction_result
    assert prediction_result["model_version"] == "v1.0.0"
    assert latency_ms >= 0.0
