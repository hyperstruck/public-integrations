from enum import Enum


class UsageTimeWindow(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    CALENDAR_QUARTER = "calendar_quarter"
    CALENDAR_YEAR = "calendar_year"
