from enum import Enum


class HitlPolicyPreset(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    AUTONOMY = "autonomy"
    MILESTONE_ONLY = "milestone_only"
