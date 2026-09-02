from enum import Enum


class BillingWindowKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    SUBSCRIPTION_PERIOD = "subscription_period"
    CALENDAR_MONTH = "calendar_month"
