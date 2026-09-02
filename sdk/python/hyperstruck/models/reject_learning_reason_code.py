from enum import Enum


class RejectLearningReasonCode(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    MANUALLY_CURATED = "manually_curated"
    INCORRECT = "incorrect"
    OUTDATED = "outdated"
    TOO_SPECIFIC = "too_specific"
    DUPLICATE = "duplicate"
    OTHER = "other"
