from enum import Enum


class PassageAbsence(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NO_POINTER = "no_pointer"
    ERASED = "erased"
    UNREADABLE = "unreadable"
    NOT_RESOLVED = "not_resolved"
    TRUNCATED = "truncated"
    HELD_SOURCE = "held_source"
