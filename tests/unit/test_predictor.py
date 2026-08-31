"""Unit tests for ControlledInferencePredictor feature validation and prediction execution."""

import json
from uuid import uuid4

import pytest
from app.core.errors import DomainError, ValidationError

from ml.artifacts.store import ArtifactStore
from services.ml_inference.predictor import ControlledInferencePredictor


def create_test_artifact(
    tmp_path, model_name: str, version_tag: str, model_type: str = "random_forest"
):
    store = ArtifactStore(base_dir=tmp_path)
    payload = {
        "model_name": model_name,
        "version_tag": version_tag,
        "model_type": model_type,
        "target_column": "target",
        "target_classes": ["no", "yes"],
        "feature_names": ["age", "income", "tenure"],
        "weights": [0.05, 0.0001, 0.2],
        "hyperparameters": {"n_estimators": 50},
        "metrics": {"accuracy": 0.95, "f1_score": 0.92},
    }
    key = store.save_artifact(model_name, version_tag, payload)
    return store, key


def test_predictor_success_production_model(tmp_path):
    store, key = create_test_artifact(tmp_path, "churn-model", "v1.0.0")
    predictor = ControlledInferencePredictor(artifact_store=store)

    features = {"age": 35, "income": 50000, "tenure": 3}
    result, latency_ms = predictor.predict("production", key, features)

    assert "prediction" in result
    assert result["prediction"] in ["yes", "no"]
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["model_version"] == "v1.0.0"
    assert latency_ms > 0.0


def test_predictor_blocked_candidate_or_rejected(tmp_path):
    store, key = create_test_artifact(tmp_path, "churn-model", "v1.0.0")
    predictor = ControlledInferencePredictor(artifact_store=store)

    features = {"age": 35, "income": 50000, "tenure": 3}

    with pytest.raises(DomainError) as exc_info_candidate:
        predictor.predict("candidate", key, features)
    assert exc_info_candidate.value.status_code == 400

    with pytest.raises(DomainError) as exc_info_rejected:
        predictor.predict("rejected", key, features)
    assert exc_info_rejected.value.status_code == 400


def test_predictor_missing_required_feature(tmp_path):
    store, key = create_test_artifact(tmp_path, "churn-model", "v1.0.0")
    predictor = ControlledInferencePredictor(artifact_store=store)

    incomplete_features = {"age": 35, "income": 50000}  # Missing 'tenure'

    with pytest.raises(ValidationError) as exc_info:
        predictor.predict("approved", key, incomplete_features)
    assert "Missing required input feature: 'tenure'" in str(exc_info.value)


def test_predictor_invalid_feature_type(tmp_path):
    store, key = create_test_artifact(tmp_path, "churn-model", "v1.0.0")
    predictor = ControlledInferencePredictor(artifact_store=store)

    invalid_type_features = {"age": "invalid_string", "income": 50000, "tenure": 3}

    with pytest.raises(ValidationError) as exc_info:
        predictor.predict("approved", key, invalid_type_features)
    assert "Invalid non-numeric value for feature 'age'" in str(exc_info.value)


def test_predictor_target_column_rejected(tmp_path):
    store, key = create_test_artifact(tmp_path, "churn-model", "v1.0.0")
    predictor = ControlledInferencePredictor(artifact_store=store)

    target_included_features = {
        "age": 35,
        "income": 50000,
        "tenure": 3,
        "target": "yes",  # Forbidden target column!
    }

    with pytest.raises(ValidationError) as exc_info:
        predictor.predict("approved", key, target_included_features)
    assert "Target column 'target' cannot be passed as an input feature" in str(exc_info.value)


def test_predictor_corrupted_sha256_artifact(tmp_path):
    store, key = create_test_artifact(tmp_path, "churn-model", "v1.0.0")
    predictor = ControlledInferencePredictor(artifact_store=store)

    # Tamper with saved artifact content on disk
    full_path = store.base_dir / key
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["payload"]["model_name"] = "tampered-name"
    full_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(DomainError) as exc_info:
        predictor.predict("approved", key, {"age": 35, "income": 50000, "tenure": 3})
    assert exc_info.value.status_code == 400
    assert "failed SHA-256 integrity check" in exc_info.value.detail
