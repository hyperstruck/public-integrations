from enum import Enum


class SupportVerdict(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    SUPPORTED = "supported"
    PARTLY_SUPPORTED = "partly_supported"
    UNSUPPORTED = "unsupported"
    UNCHECKED = "unchecked"
