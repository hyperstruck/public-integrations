from enum import Enum


class DocumentRead(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    MAIN = "main"
    EARLIER_HISTORY = "earlier_history"
    NOT_READ = "not_read"
