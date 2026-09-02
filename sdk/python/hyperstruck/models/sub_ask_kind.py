from enum import Enum


class SubAskKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    DESCRIBE = "describe"
    SELECT = "select"
