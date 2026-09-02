from enum import Enum


class DocumentTextAbsenceReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NO_HEAD = "no_head"
    ERASED = "erased"
    KEY_UNAVAILABLE = "key_unavailable"
    UNREADABLE = "unreadable"
    TOO_LONG = "too_long"
    HELD_SOURCE = "held_source"
