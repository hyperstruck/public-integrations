from enum import Enum


class ResolvePurpose(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    AGENT_LOOP = "agent_loop"
    EXPLICIT_RECALL = "explicit_recall"
