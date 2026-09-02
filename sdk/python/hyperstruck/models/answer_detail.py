from enum import Enum


class AnswerDetail(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ANSWER = "answer"
    FINDINGS = "findings"
    CLAIMS = "claims"
    EVERYTHING = "everything"
