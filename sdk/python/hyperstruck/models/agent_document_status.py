from enum import Enum


class AgentDocumentStatus(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    READING = "reading"
    PAUSED = "paused"
    FAILED = "failed"
    UP_TO_DATE = "up_to_date"
    EMPTY = "empty"
