from enum import Enum


class ContainerKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ORGANISATION = "organisation"
    PLACE = "place"
    THING = "thing"
