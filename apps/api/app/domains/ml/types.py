"""ML domain status and quality gate constants."""

from enum import StrEnum


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    DRAFT = "draft"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    REJECTED = "rejected"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


# Default quality evaluation thresholds required for model promotion to APPROVED
DEFAULT_ACCURACY_THRESHOLD = 0.90
DEFAULT_F1_SCORE_THRESHOLD = 0.85
