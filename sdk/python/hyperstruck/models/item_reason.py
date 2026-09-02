from enum import Enum


class ItemReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    CONTRAST_NOT_FOUND = "contrast_not_found"
    PASS_FAILED = "pass_failed"
    OVER_BUDGET = "over_budget"
    NO_MAP_SEAT = "no_map_seat"
