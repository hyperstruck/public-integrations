from enum import Enum


class LearningScope(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    AGENT = "agent"
    ORG = "org"
