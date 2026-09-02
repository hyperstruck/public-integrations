from enum import Enum


class SectionKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ANSWER = "answer"
    CHANGED = "changed"
    NOT_COVERED = "not_covered"
    VERDICT = "verdict"
    APPENDED = "appended"
    SELECTION = "selection"
