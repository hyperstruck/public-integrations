from enum import Enum


class SpaceKind(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    COMMONS = "commons"
    DEPARTMENT = "department"
    DOMAIN = "domain"
    PERSONAL = "personal"
