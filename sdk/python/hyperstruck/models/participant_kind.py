from enum import Enum


class ParticipantKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    INDIVIDUAL = "individual"
    GROUP = "group"
    RESOURCE = "resource"
    ROOM = "room"
    BOT = "bot"
    UNKNOWN = "unknown"
