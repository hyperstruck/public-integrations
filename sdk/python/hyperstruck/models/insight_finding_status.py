from enum import Enum


class InsightFindingStatus(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NEW = "new"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"
    REPLACED = "replaced"
