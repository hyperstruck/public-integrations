from enum import Enum


class ReadGuarantee(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    EXHAUSTIVE = "exhaustive"
    PARTIAL = "partial"
    BEST_EFFORT = "best_effort"
    UNAVAILABLE = "unavailable"
