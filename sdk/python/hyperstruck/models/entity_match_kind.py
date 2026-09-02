from enum import Enum


class EntityMatchKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NAME = "name"
    ALIAS = "alias"
    SURFACE = "surface"
