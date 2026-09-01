"""Unit tests for ML model trainer, artifact creation, and integrity."""

import tempfile
from pathlib import Path

import pytest

from ml.artifacts.store import ArtifactStore
from ml.training.trainer import ModelTrainer


def test_train_dataset_model_all_algorithms() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "sample_data.csv"
        content = (
            "feature1,feature2,feature3,target\n"
            "1.0,2.0,3.0,yes\n"
            "2.0,1.0,4.0,no\n"
            "1.5,2.5,3.5,yes\n"
            "3.0,0.5,5.0,no\n"
            "2.5,1.5,4.5,yes\n"
            "4.0,0.2,6.0,no\n"
            "3.5,1.2,5.5,yes\n"
            "5.0,0.1,7.0,no\n"
        )
        csv_path.write_text(content, encoding="utf-8")

        artifact_store = ArtifactStore(base_dir=Path(tmp_dir) / "artifacts")
        trainer = ModelTrainer(artifact_store=artifact_store)

        for model_type in ["random_forest", "decision_tree", "logistic_regression"]:
            metrics, artifact_path = trainer.train_dataset_model(
                csv_file_path=csv_path,
                target_column="target",
                model_name=f"test_{model_type}",
                version_tag="v1.0.0",
                model_type=model_type,
                hyperparameters={"n_estimators": 50, "max_depth": 3, "random_state": 42},
            )

            assert "accuracy" in metrics
            assert "precision" in metrics
            assert "recall" in metrics
            assert "f1_score" in metrics
            assert "training_duration_ms" in metrics
            assert metrics["target_column"] == "target"
            assert set(metrics["target_classes"]) == {"no", "yes"}

            assert artifact_path == f"models/test_{model_type}/v1.0.0.json"
            loaded = artifact_store.load_artifact(artifact_path)
            assert loaded["model_name"] == f"test_{model_type}"
            assert loaded["version_tag"] == "v1.0.0"
            assert loaded["model_type"] == model_type


def test_artifact_sha256_integrity_tamper_detection() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir) / "artifacts"
        artifact_store = ArtifactStore(base_dir=base_dir)

        ref_key = artifact_store.save_artifact("clf", "v1.0.0", {"weights": [0.1, 0.2, 0.3]})
        # Valid load
        loaded = artifact_store.load_artifact(ref_key)
        assert loaded["weights"] == [0.1, 0.2, 0.3]

        # Tamper content
        file_path = base_dir / ref_key
        content = file_path.read_text(encoding="utf-8")
        tampered_content = content.replace("0.1", "0.9")
        file_path.write_text(tampered_content, encoding="utf-8")

        with pytest.raises(ValueError, match="integrity check failed"):
            artifact_store.load_artifact(ref_key)


def test_train_dataset_model_missing_target_column() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "sample_data.csv"
        csv_path.write_text("feature1,feature2\n1,2\n3,4\n", encoding="utf-8")

        trainer = ModelTrainer(artifact_store=ArtifactStore(base_dir=Path(tmp_dir) / "artifacts"))
        with pytest.raises(ValueError, match="Target column 'non_existent' not found"):
            trainer.train_dataset_model(
                csv_file_path=csv_path,
                target_column="non_existent",
                model_name="test_model",
                version_tag="v1.0.0",
            )


def test_train_dataset_model_insufficient_rows() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "sample_data.csv"
        csv_path.write_text("feature1,target\n1,yes\n", encoding="utf-8")

        trainer = ModelTrainer(artifact_store=ArtifactStore(base_dir=Path(tmp_dir) / "artifacts"))
        with pytest.raises(ValueError, match="fewer than 2 valid rows"):
            trainer.train_dataset_model(
                csv_file_path=csv_path,
                target_column="target",
                model_name="test_model",
                version_tag="v1.0.0",
            )


def test_train_dataset_model_file_not_found() -> None:
    trainer = ModelTrainer()
    with pytest.raises(FileNotFoundError):
        trainer.train_dataset_model(
            csv_file_path="non_existent_file.csv",
            target_column="target",
            model_name="test_model",
            version_tag="v1.0.0",
        )
