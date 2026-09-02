from enum import Enum


class ReviewState(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
