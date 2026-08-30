"""ML domain status and quality gate constants."""

from enum import StrEnum


class ModelStatus(StrEnum):
    DRAFT = "draft"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    ARCHIVED = "archived"


# Minimum quality evaluation thresholds required for model promotion to APPROVED
MIN_ACCURACY_THRESHOLD = 0.85
MIN_F1_SCORE_THRESHOLD = 0.80
