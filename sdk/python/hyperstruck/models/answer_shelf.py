from enum import Enum


class AnswerShelf(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    OBLIGATIONS = "obligations"
    CITATIONS = "citations"
    CO_MENTIONS = "co_mentions"
    SET_COUNTS = "set_counts"
