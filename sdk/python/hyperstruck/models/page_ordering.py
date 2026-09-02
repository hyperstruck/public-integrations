from enum import Enum


class PageOrdering(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    FUSED = "fused"
    KEYSET = "keyset"
