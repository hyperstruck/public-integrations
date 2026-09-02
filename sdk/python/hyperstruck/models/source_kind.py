from enum import Enum


class SourceKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    GROUNDING_REF = "grounding_ref"
    REGISTERED_DOCUMENT = "registered_document"
