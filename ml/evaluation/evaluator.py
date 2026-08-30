"""Model quality evaluation engine and gate checker."""

from __future__ import annotations

from typing import Any
from app.domains.ml.types import MIN_ACCURACY_THRESHOLD, MIN_F1_SCORE_THRESHOLD


class ModelEvaluator:
    """Evaluates model performance metrics against mandatory promotion quality gates."""

    def evaluate(
        self, accuracy: float, f1_score: float, latency_ms: float
    ) -> tuple[bool, dict[str, Any]]:
        passed_accuracy = accuracy >= MIN_ACCURACY_THRESHOLD
        passed_f1 = f1_score >= MIN_F1_SCORE_THRESHOLD
        passed_gate = passed_accuracy and passed_f1

        metadata = {
            "min_accuracy_required": MIN_ACCURACY_THRESHOLD,
            "min_f1_score_required": MIN_F1_SCORE_THRESHOLD,
            "passed_accuracy_gate": passed_accuracy,
            "passed_f1_gate": passed_f1,
            "status": "APPROVED" if passed_gate else "REJECTED",
        }

        return passed_gate, metadata
