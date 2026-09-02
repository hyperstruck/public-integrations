from enum import Enum


class RunStatus(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    QUEUED = "queued"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
