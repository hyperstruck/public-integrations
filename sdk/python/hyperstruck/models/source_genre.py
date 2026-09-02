from enum import Enum


class SourceGenre(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    UNKNOWN = "unknown"
    POLICY = "policy"
    PLAN = "plan"
    MINUTES = "minutes"
    REFERENCE = "reference"
    CORRESPONDENCE = "correspondence"
    NOTE = "note"
    ASIDE = "aside"
