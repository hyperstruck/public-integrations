from enum import Enum


class ReasoningTier(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    FULL = "full"
    BALANCED = "balanced"
    FAST = "fast"
