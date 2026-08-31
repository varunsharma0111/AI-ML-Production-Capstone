"""Model quality evaluation engine and configurable gate checker."""

from __future__ import annotations

from typing import Any

from app.domains.ml.types import DEFAULT_ACCURACY_THRESHOLD, DEFAULT_F1_SCORE_THRESHOLD


class ModelEvaluator:
    """Evaluates model performance metrics against configurable quality gate thresholds."""

    def evaluate(
        self,
        accuracy: float,
        f1_score: float,
        latency_ms: float = 0.0,
        accuracy_threshold: float = DEFAULT_ACCURACY_THRESHOLD,
        f1_threshold: float = DEFAULT_F1_SCORE_THRESHOLD,
    ) -> tuple[bool, dict[str, Any]]:
        passed_accuracy = accuracy >= accuracy_threshold
        passed_f1 = f1_score >= f1_threshold
        passed_gate = passed_accuracy and passed_f1

        failure_reasons: list[str] = []
        if not passed_accuracy:
            failure_reasons.append(
                f"Accuracy ({accuracy * 100:.1f}%) is below "
                f"required threshold ({accuracy_threshold * 100:.1f}%)."
            )
        if not passed_f1:
            failure_reasons.append(
                f"F1 score ({f1_score * 100:.1f}%) is below "
                f"required threshold ({f1_threshold * 100:.1f}%)."
            )

        metadata: dict[str, Any] = {
            "status": "APPROVED" if passed_gate else "REJECTED",
            "passed_gate": passed_gate,
            "accuracy": accuracy,
            "f1_score": f1_score,
            "accuracy_threshold": accuracy_threshold,
            "f1_threshold": f1_threshold,
            "passed_accuracy_gate": passed_accuracy,
            "passed_f1_gate": passed_f1,
            "failure_reasons": failure_reasons,
            "evaluator": "automated_quality_gate",
        }

        return passed_gate, metadata
