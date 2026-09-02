from enum import Enum


class RunState(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    QUEUED = "queued"
    RUNNING = "running"
    FINISHED = "finished"
