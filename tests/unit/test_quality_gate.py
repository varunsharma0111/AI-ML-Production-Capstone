"""Unit tests for ModelEvaluator quality gate and configurable thresholds."""

from ml.evaluation.evaluator import ModelEvaluator


def test_quality_gate_pass_default_thresholds():
    evaluator = ModelEvaluator()
    passed, metadata = evaluator.evaluate(accuracy=0.92, f1_score=0.88)

    assert passed is True
    assert metadata["status"] == "APPROVED"
    assert metadata["passed_accuracy_gate"] is True
    assert metadata["passed_f1_gate"] is True
    assert len(metadata["failure_reasons"]) == 0
    assert metadata["accuracy_threshold"] == 0.90
    assert metadata["f1_threshold"] == 0.85


def test_quality_gate_fail_accuracy_threshold():
    evaluator = ModelEvaluator()
    passed, metadata = evaluator.evaluate(accuracy=0.87, f1_score=0.89)

    assert passed is False
    assert metadata["status"] == "REJECTED"
    assert metadata["passed_accuracy_gate"] is False
    assert metadata["passed_f1_gate"] is True
    assert len(metadata["failure_reasons"]) == 1
    assert "Accuracy (87.0%) is below required threshold" in metadata["failure_reasons"][0]


def test_quality_gate_fail_f1_threshold():
    evaluator = ModelEvaluator()
    passed, metadata = evaluator.evaluate(accuracy=0.95, f1_score=0.81)

    assert passed is False
    assert metadata["status"] == "REJECTED"
    assert metadata["passed_accuracy_gate"] is True
    assert metadata["passed_f1_gate"] is False
    assert len(metadata["failure_reasons"]) == 1
    assert "F1 score (81.0%) is below required threshold" in metadata["failure_reasons"][0]


def test_quality_gate_fail_multiple_criteria():
    evaluator = ModelEvaluator()
    passed, metadata = evaluator.evaluate(accuracy=0.82, f1_score=0.75)

    assert passed is False
    assert metadata["status"] == "REJECTED"
    assert metadata["passed_accuracy_gate"] is False
    assert metadata["passed_f1_gate"] is False
    assert len(metadata["failure_reasons"]) == 2


def test_quality_gate_configurable_workspace_thresholds():
    evaluator = ModelEvaluator()
    # High strict thresholds
    passed, metadata = evaluator.evaluate(
        accuracy=0.91, f1_score=0.86, accuracy_threshold=0.95, f1_threshold=0.90
    )
    assert passed is False
    assert metadata["status"] == "REJECTED"

    # Relaxed thresholds
    passed_relaxed, metadata_relaxed = evaluator.evaluate(
        accuracy=0.82, f1_score=0.80, accuracy_threshold=0.80, f1_threshold=0.75
    )
    assert passed_relaxed is True
    assert metadata_relaxed["status"] == "APPROVED"
