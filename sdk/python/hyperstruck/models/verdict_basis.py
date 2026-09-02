from enum import Enum


class VerdictBasis(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    DECLARED = "declared"
    READ = "read"
