from enum import Enum


class BillingSummaryStatus(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    UNLIMITED = "unlimited"
    OK = "ok"
    SOFT_EXCEEDED = "soft_exceeded"
    HARD_EXCEEDED = "hard_exceeded"
