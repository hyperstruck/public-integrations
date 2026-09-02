from enum import Enum


class RunType(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    GOAL = "goal"
    RESUME = "resume"
