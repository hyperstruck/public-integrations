from enum import Enum


class InsightEvidenceState(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    CURRENT = "current"
    CHANGED = "changed"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"
    UNCHECKED = "unchecked"
    NOT_CHECKED = "not_checked"
