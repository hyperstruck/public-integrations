from enum import Enum


class FlagKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    NUMBER = "number"
    NAME = "name"
    STATUS = "status"
    RELATION = "relation"
    INVENTED = "invented"
