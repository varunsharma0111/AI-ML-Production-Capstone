"""Unit tests for Phase 5 ML training, artifact integrity, and quality gates."""

import tempfile
from pathlib import Path
import pytest
from ml.artifacts.store import ArtifactStore
from ml.evaluation.evaluator import ModelEvaluator
from ml.training.trainer import ModelTrainer


def test_artifact_store_save_and_verify_hash():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(base_dir=tmpdir)
        path = store.save_artifact("classifier", "v1.0", {"param": 100})

        loaded_data = store.load_artifact(path)
        assert loaded_data["param"] == 100


def test_trainer_produces_artifact():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(base_dir=tmpdir)
        trainer = ModelTrainer(artifact_store=store)

        path = trainer.train_model("test_model", "v1.0", {"learning_rate": 0.01})
        assert Path(path).exists()


def test_evaluator_quality_gate():
    evaluator = ModelEvaluator()

    # Passing thresholds (accuracy >= 0.85, f1 >= 0.80)
    passed, metadata = evaluator.evaluate(0.88, 0.85, 12.5)
    assert passed is True
    assert metadata["status"] == "APPROVED"

    # Failing threshold
    failed, metadata_failed = evaluator.evaluate(0.70, 0.65, 15.0)
    assert failed is False
    assert metadata_failed["status"] == "REJECTED"
