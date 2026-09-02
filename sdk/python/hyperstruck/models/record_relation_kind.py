from enum import Enum


class RecordRelationKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    IN_REPLY_TO = "in_reply_to"
    REFERENCES = "references"
    VERSION_OF = "version_of"
    SUPERSEDES = "supersedes"
    ATTACHMENT_OF = "attachment_of"
    THREAD = "thread"
