from enum import Enum


class InsightFeasibility(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    UNLIKELY = "unlikely"
