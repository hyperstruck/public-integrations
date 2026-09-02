from enum import Enum


class AgentStatus(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
