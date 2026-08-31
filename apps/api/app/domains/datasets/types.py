"""Dataset domain status and format enums."""

from enum import StrEnum


class DatasetStatus(StrEnum):
    UPLOADED = "uploaded"
    PROFILING = "profiling"
    READY = "ready"
    FAILED = "failed"


class DatasetFormat(StrEnum):
    CSV = "csv"
