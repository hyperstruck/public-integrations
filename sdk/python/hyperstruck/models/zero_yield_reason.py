from enum import Enum


class ZeroYieldReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    WEAK_CONTRAST = "weak_contrast"
    DEDUP_ABSORBED = "dedup_absorbed"
    NO_ENTITY_RESOLVABLE = "no_entity_resolvable"
    GATE_REJECTED = "gate_rejected"
    NOTHING_EXTRACTED = "nothing_extracted"
    FAILED = "failed"
