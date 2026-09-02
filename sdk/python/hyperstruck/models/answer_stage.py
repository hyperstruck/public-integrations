from enum import Enum


class AnswerStage(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    READ = "read"
    INTERPRETATION = "interpretation"
    FINDINGS = "findings"
    DECISION = "decision"
    FINDING_CHECK = "finding_check"
    SUPERSESSION = "supersession"
    PROSE = "prose"
    CHECKS = "checks"
