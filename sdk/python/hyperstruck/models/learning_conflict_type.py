from enum import Enum


class LearningConflictType(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    CONTRADICTION = "contradiction"
    SUPERSESSION = "supersession"
    PARTIAL_OVERLAP = "partial_overlap"
