from enum import Enum


class RecallOutcome(str, Enum):
    """The closed set of values this field may take."""

    __str__ = str.__str__

    DELIVERED = "delivered"
    RESOLVE_TIMED_OUT = "resolve_timed_out"
    RESOLVE_FAILED = "resolve_failed"
    RESOLVE_EMPTY = "resolve_empty"
    RESOLVE_NO_GOAL = "resolve_no_goal"
    RESOLVE_SUPERSEDED = "resolve_superseded"
    RECALL_UNCLAIMED = "recall_unclaimed"
    RECALL_MISSING = "recall_missing"
    RECALL_UNRECOGNISED = "recall_unrecognised"
    NO_TRANSCRIPT = "no_transcript"
    TRANSCRIPT_UNREADABLE = "transcript_unreadable"
    RECORD_SHAPE_CHANGED = "record_shape_changed"
    NO_MATCHING_RECORD = "no_matching_record"
