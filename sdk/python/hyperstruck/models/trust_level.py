from enum import Enum


class TrustLevel(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    UNVERIFIED = "unverified"
    AGENT_VERIFIED = "agent_verified"
    SOURCE_VERIFIED = "source_verified"
    CORROBORATED = "corroborated"
    UNKNOWN = "unknown"
