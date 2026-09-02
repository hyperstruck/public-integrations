from enum import Enum


class ParticipantRole(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ORGANISER = "organiser"
    REQUIRED = "required"
    OPTIONAL = "optional"
    NON_PARTICIPANT = "non_participant"
    FROM = "from"
    TO = "to"
    CC = "cc"
    BCC = "bcc"
    AUTHOR = "author"
    REQUESTER = "requester"
    REPORTER = "reporter"
    ASSIGNEE = "assignee"
    WATCHER = "watcher"
    MENTIONED = "mentioned"
    UNKNOWN = "unknown"
