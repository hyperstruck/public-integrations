from enum import Enum


class QuestionReadArm(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    DETERMINISTIC = "deterministic"
    RECALL = "recall"
    CONCERNS = "concerns"
