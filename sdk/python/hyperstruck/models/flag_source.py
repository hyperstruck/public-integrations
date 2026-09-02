from enum import Enum


class FlagSource(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    MODEL = "model"
    CODE = "code"
