from enum import Enum


class InsightPriority(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
