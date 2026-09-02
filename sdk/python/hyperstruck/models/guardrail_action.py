from enum import Enum


class GuardrailAction(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    ANONYMIZE = "anonymize"
    BLOCK = "block"
    LOG_ONLY = "log_only"
