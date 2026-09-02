from enum import Enum


class DeclineReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NO_TOOL_CALLS = "no_tool_calls"
    BELOW_MATERIAL_THRESHOLD = "below_material_threshold"
    EMPTY_OFFER = "empty_offer"
    UNEVIDENCED_OUTCOME = "unevidenced_outcome"
    READONLY_CLOSE = "readonly_close"
