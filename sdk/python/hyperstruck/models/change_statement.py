from enum import Enum


class ChangeStatement(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NEVER_SUPERSEDED = "never_superseded"
    STALENESS_UNAVAILABLE = "staleness_unavailable"
    SUPERSEDED_NOT_SHOWN = "superseded_not_shown"
    CHANGE_UNMEASURED = "change_unmeasured"
