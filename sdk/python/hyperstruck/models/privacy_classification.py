from enum import Enum


class PrivacyClassification(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    SHAREABLE = "shareable"
    AGENT_SPECIFIC = "agent_specific"
    SENSITIVE = "sensitive"
