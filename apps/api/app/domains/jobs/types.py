"""Job domain status and type enums."""

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    SAMPLE_ML_INGESTION = "sample_ml_ingestion"
    DATA_EXPORT = "data_export"
    MODEL_EVALUATION = "model_evaluation"
    DATASET_PROFILING = "dataset_profiling"
    MODEL_TRAINING = "model_training"
