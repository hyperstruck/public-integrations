from enum import Enum


class LearningGraphNodeType(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    LEARNING = "learning"
    INSTANCE = "instance"
    PLAN = "plan"
    GOAL = "goal"
    TOOL = "tool"
    ORG_LEARNING = "org_learning"
    EVIDENCE_SOURCE = "evidence_source"
