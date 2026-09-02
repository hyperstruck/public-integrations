from enum import Enum


class ValueBasis(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    RATE_CARD = "rate_card"
    STATED = "stated"
    TIME_DERIVED = "time_derived"
    DEFAULT_ESTIMATE = "default_estimate"
    REVERSAL = "reversal"
