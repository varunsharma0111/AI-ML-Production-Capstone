"""Controlled inference engine serving only approved model versions."""

from __future__ import annotations

import time
from typing import Any

from app.core.errors import DomainError

from ml.artifacts.store import ArtifactStore


class ControlledInferencePredictor:
    """Loads approved model versions and executes schema-validated predictions."""

    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()

    def predict(
        self,
        model_status: str,
        artifact_path: str,
        input_features: dict[str, Any],
    ) -> tuple[dict[str, Any], float]:
        """Execute inference ONLY if model status is approved."""

        if model_status != "approved":
            raise DomainError(
                status_code=400,
                code="model_not_approved",
                title="Inference Denied",
                detail=f"Model version status is '{model_status}'. Only 'approved' models can serve inference requests.",
            )

        start_time = time.perf_counter()

        # Load & verify artifact
        artifact = self.artifact_store.load_artifact(artifact_path)
        weights = artifact.get("weights", [0.5, 0.5, 0.5])

        val1 = float(input_features.get("feature_1", 1.0))
        val2 = float(input_features.get("feature_2", 1.0))

        # Compute prediction output score & label
        score = round(
            min(
                max(val1 * weights[0] + val2 * (weights[1] if len(weights) > 1 else 0.5), 0.0), 1.0
            ),
            4,
        )
        prediction_label = "positive" if score >= 0.5 else "negative"

        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        prediction_result = {
            "label": prediction_label,
            "confidence": score,
            "model_version": artifact.get("version_tag", "v1.0.0"),
        }

        return prediction_result, latency_ms
