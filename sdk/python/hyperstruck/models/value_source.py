from enum import Enum


class ValueSource(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    API = "api"
    MCP = "mcp"
    BOUNDARY = "boundary"
    AUTO = "auto"
    PORTAL = "portal"
