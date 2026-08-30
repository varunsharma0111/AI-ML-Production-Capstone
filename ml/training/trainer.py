"""Deterministic model trainer producing versioned ML artifacts."""

from __future__ import annotations

from typing import Any

from ml.artifacts.store import ArtifactStore


class ModelTrainer:
    """Trains reproducible model versions and persists artifacts."""

    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()

    def train_model(
        self,
        name: str,
        version_tag: str,
        hyperparameters: dict[str, Any] | None = None,
    ) -> str:
        """Simulate reproducible training and serialize model artifact."""
        params = hyperparameters or {"learning_rate": 0.01, "max_depth": 5, "seed": 42}

        # Deterministic weights generation
        weights = [round(0.42 + 0.1 * i, 4) for i in range(len(params))]

        artifact_data = {
            "model_name": name,
            "version_tag": version_tag,
            "hyperparameters": params,
            "weights": weights,
            "feature_names": ["feature_1", "feature_2", "feature_3"],
        }

        return self.artifact_store.save_artifact(name, version_tag, artifact_data)
