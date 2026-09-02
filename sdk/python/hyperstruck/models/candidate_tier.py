from enum import Enum


class CandidateTier(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    QUALIFIES = "qualifies"
    RULED_OUT = "ruled_out"
    UNPROVEN = "unproven"
    NOT_EXAMINED = "not_examined"
    EVIDENCED = "evidenced"
