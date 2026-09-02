from enum import Enum


class FindingKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    DONE_OR_WORKING = "done_or_working"
    IN_PROGRESS_OR_PENDING = "in_progress_or_pending"
    MISSING_OR_BLOCKING = "missing_or_blocking"
    PLANNED = "planned"
    DECISION = "decision"
    UNKNOWN = "unknown"
    OTHER = "other"
    OBLIGATION = "obligation"
