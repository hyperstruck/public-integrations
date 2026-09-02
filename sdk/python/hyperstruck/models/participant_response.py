from enum import Enum


class ParticipantResponse(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    NEEDS_ACTION = "needs_action"
    DELEGATED = "delegated"
    NONE = "none"
    UNKNOWN = "unknown"
