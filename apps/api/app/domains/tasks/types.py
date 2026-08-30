"""Task domain constants."""

from enum import StrEnum


class TaskStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
