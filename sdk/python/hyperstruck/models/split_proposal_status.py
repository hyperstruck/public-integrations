from enum import Enum


class SplitProposalStatus(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
