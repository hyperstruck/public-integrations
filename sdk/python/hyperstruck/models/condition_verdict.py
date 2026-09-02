from enum import Enum


class ConditionVerdict(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    MET = "met"
    NOT_MET = "not_met"
    NOT_STATED = "not_stated"
    CONFLICT = "conflict"
    CLOSE = "close"
