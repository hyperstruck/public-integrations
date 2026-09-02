from enum import Enum


class DecisionType(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    SKIP = "skip"
    PROVIDE_INPUT = "provide_input"
    PARTIAL_APPROVE = "partial_approve"
