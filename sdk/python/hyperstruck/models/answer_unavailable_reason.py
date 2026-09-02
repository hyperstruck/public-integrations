from enum import Enum


class AnswerUnavailableReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    READ_DEADLINE = "read_deadline"
    FINDINGS_UNAVAILABLE = "findings_unavailable"
    COMPOSER_DEADLINE = "composer_deadline"
    COMPOSER_FAILED = "composer_failed"
    COMPOSER_UNAVAILABLE = "composer_unavailable"
    NOTHING_READ = "nothing_read"
    INTERPRETATION_UNAVAILABLE = "interpretation_unavailable"
