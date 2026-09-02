from enum import Enum


class ValueWindow(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ALL_TIME = "all_time"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_365_DAYS = "last_365_days"
