from enum import Enum


class ConditionKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    CHECKABLE = "checkable"
    GRADED = "graded"
