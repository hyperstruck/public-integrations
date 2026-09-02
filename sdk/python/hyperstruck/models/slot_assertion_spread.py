from enum import Enum


class SlotAssertionSpread(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    SAME_DOCUMENT = "same_document"
    DIFFERENT_DOCUMENTS = "different_documents"
    UNKNOWN = "unknown"
