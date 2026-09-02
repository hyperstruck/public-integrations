from enum import Enum


class EvidenceAvailability(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    AVAILABLE = "available"
    OMITTED = "omitted"
    ORG_STRIPPED = "org_stripped"
    TRUNCATED = "truncated"
