from enum import Enum


class ValueRecorderType(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    AGENT = "agent"
    API_KEY = "api_key"
    USER = "user"
    PLATFORM = "platform"
