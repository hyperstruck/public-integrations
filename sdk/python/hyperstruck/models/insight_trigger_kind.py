from enum import Enum


class InsightTriggerKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    MANUAL = "manual"
    API = "api"
