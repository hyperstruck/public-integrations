from enum import Enum


class LearningGraphEdgeType(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    HAS_INSTANCE = "HAS_INSTANCE"
    PRODUCED_LEARNING = "PRODUCED_LEARNING"
    USED_IN_PLAN = "USED_IN_PLAN"
    APPLIES_TO = "APPLIES_TO"
    APPLIES_TO_GOAL = "APPLIES_TO_GOAL"
    SUPERSEDES = "SUPERSEDES"
    CONTRADICTS = "CONTRADICTS"
    REFINES = "REFINES"
    ORG_PROMOTION_OF = "ORG_PROMOTION_OF"
