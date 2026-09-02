from enum import Enum


class SupersessionReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    WORLD_CHANGE = "world_change"
    CORRECTION = "correction"
    RETRACTION = "retraction"
    REFINEMENT = "refinement"
    ATTRIBUTE_MERGE = "attribute_merge"
    RETROACTIVE_KEY = "retroactive_key"
    RETROACTIVE_CORROBORATION = "retroactive_corroboration"
