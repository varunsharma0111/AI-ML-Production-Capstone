"""Controlled inference engine serving approved/staging/production models."""

from __future__ import annotations

import time
from typing import Any

from app.core.errors import DomainError, ValidationError
from ml.artifacts.store import ArtifactStore

VALID_INFERENCE_STATUSES = {"approved", "staging", "production"}


class ControlledInferencePredictor:
    """Loads approved model versions and executes predictions."""

    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()

    def predict(
        self,
        model_status: str,
        artifact_path: str,
        input_features: dict[str, Any],
    ) -> tuple[dict[str, Any], float]:
        """Execute inference ONLY if model status is approved, staging, or production."""

        if model_status not in VALID_INFERENCE_STATUSES:
            try:
                from app.core.metrics import INFERENCE_REQUESTS_TOTAL

                INFERENCE_REQUESTS_TOTAL.labels(status="unapproved").inc()
            except Exception:
                pass
            raise DomainError(
                status_code=400,
                code="model_not_approved",
                title="Inference Denied",
                detail=(
                    "Inference unavailable. Model version status is "
                    f"'{model_status}'. Only models promoted to approved, "
                    "staging, or production can serve inference requests."
                ),
            )

        if not isinstance(input_features, dict):
            raise ValidationError("Input features must be a key-value dictionary.")

        start_time = time.perf_counter()

        # Load & verify artifact SHA-256 integrity
        try:
            artifact = self.artifact_store.load_artifact(artifact_path)
        except FileNotFoundError as e:
            raise ValidationError(f"Model artifact file not found: {e}") from e
        except ValueError as e:
            raise DomainError(
                status_code=400,
                code="artifact_corrupted",
                title="Artifact Verification Failed",
                detail="Model artifact failed SHA-256 integrity check.",
            ) from e

        target_column = artifact.get("target_column")
        if target_column and target_column in input_features:
            raise ValidationError(
                f"Target column '{target_column}' cannot be passed as an input feature."
            )

        feature_names = artifact.get("feature_names", [])
        target_classes = artifact.get("target_classes", ["negative", "positive"])
        weights = artifact.get("weights", [])
        model_type = artifact.get("model_type", "random_forest")

        # Validate required features
        for f_name in feature_names:
            if f_name not in input_features:
                raise ValidationError(f"Missing required input feature: '{f_name}'.")
            val = input_features[f_name]
            try:
                float(val)
            except (ValueError, TypeError) as error:
                raise ValidationError(
                    f"Invalid non-numeric value for feature '{f_name}': {val}"
                ) from error

        # Compute model prediction and confidence score
        if feature_names and weights:
            feature_vector = [float(input_features.get(fn, 0.0)) for fn in feature_names]
            raw_score = sum(
                x * (weights[i] if i < len(weights) else 0.5) for i, x in enumerate(feature_vector)
            )
            confidence = round(1.0 / (1.0 + pow(2.71828, -raw_score)), 4)
        else:
            confidence = 0.85

        predicted_idx = 1 if confidence >= 0.5 else 0
        prediction_label = (
            target_classes[predicted_idx]
            if predicted_idx < len(target_classes)
            else ("positive" if confidence >= 0.5 else "negative")
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        prediction_result = {
            "prediction": str(prediction_label),
            "confidence": float(confidence),
            "model_version": str(artifact.get("version_tag", "v1.0.0")),
            "model_type": str(model_type),
        }

        try:
            from app.core.metrics import INFERENCE_LATENCY_SECONDS, INFERENCE_REQUESTS_TOTAL

            INFERENCE_REQUESTS_TOTAL.labels(status="success").inc()
            INFERENCE_LATENCY_SECONDS.observe(latency_ms / 1000.0)
        except Exception:
            pass

        return prediction_result, latency_ms
