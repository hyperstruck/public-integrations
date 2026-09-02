from enum import Enum


class ValueKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    MEASURED = "measured"
    ESTIMATED = "estimated"
