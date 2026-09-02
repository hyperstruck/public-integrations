from enum import Enum


class SilenceReason(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    TERM_DID_NOT_PARTICIPATE = "term_did_not_participate"
    NO_SURFACE_MATCHED = "no_surface_matched"
    ENTITY_BOUND_NO_CLAIMS = "entity_bound_no_claims"
    HELD_BACK = "held_back"
    OUTSIDE_AS_OF = "outside_as_of"
    ARM_UNAVAILABLE = "arm_unavailable"
    SHELF_UNAVAILABLE = "shelf_unavailable"
    SHELF_TRUNCATED = "shelf_truncated"
    READ_DEADLINE = "read_deadline"
