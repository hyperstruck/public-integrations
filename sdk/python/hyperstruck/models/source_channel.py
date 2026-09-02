from enum import Enum


class SourceChannel(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    UNKNOWN = "unknown"
    CHAT = "chat"
    EMAIL = "email"
    MEETING = "meeting"
    DOCUMENT_STORE = "document_store"
    SYSTEM_OF_RECORD = "system_of_record"
    API = "api"
