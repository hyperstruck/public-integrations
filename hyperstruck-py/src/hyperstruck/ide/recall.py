"""Why a turn carries no exposure receipt, in terms the turn itself can record.

A run that credits nothing has always looked the same from the boundary: offers were
made and no receipt arrived. Two very different things produce that. Either the recall
never reached the model at all, in which case there is nothing to vouch for and the
client is behaving correctly, or it was shown and the editor's record of it could not
be read back, which is a real loss. The boundary cannot tell them apart from a missing
field, so it reports the harsher one, and the difference only ever surfaced in a server
log nobody reads.

These are the states that distinguish them. They are recorded on the turn and travel
with it, so the answer is available where the failure happened rather than inferred a
day later from a credit rate.
"""

from __future__ import annotations

from enum import StrEnum


class RecallOutcome(StrEnum):
    """What became of this turn's recall, from resolve through to the receipt."""

    DELIVERED = "delivered"

    # The recall never reached the model. Nothing was shown, so nothing is owed.
    RESOLVE_TIMED_OUT = "resolve_timed_out"
    RESOLVE_FAILED = "resolve_failed"
    RESOLVE_EMPTY = "resolve_empty"
    RESOLVE_SUPERSEDED = "resolve_superseded"
    RECALL_UNCLAIMED = "recall_unclaimed"
    RECALL_MISSING = "recall_missing"

    # The recall was shown, and the editor's record of it could not be read back.
    # These four are what ``receipt.acceptance_record`` used to collapse into one
    # empty answer, which is why a changed transcript format would have looked
    # exactly like a corpus with nothing worth crediting.
    NO_TRANSCRIPT = "no_transcript"
    TRANSCRIPT_UNREADABLE = "transcript_unreadable"
    RECORD_SHAPE_CHANGED = "record_shape_changed"
    NO_MATCHING_RECORD = "no_matching_record"

    @property
    def is_delivered(self) -> bool:
        """Whether the model was shown the recall, whatever happened to the receipt.

        A receipt-side failure still means delivery happened, so it stays a defect
        worth alerting on; the delivery-side states do not.
        """
        return self not in _NEVER_DELIVERED


_NEVER_DELIVERED = frozenset(
    {
        RecallOutcome.RESOLVE_TIMED_OUT,
        RecallOutcome.RESOLVE_FAILED,
        RecallOutcome.RESOLVE_EMPTY,
        RecallOutcome.RESOLVE_SUPERSEDED,
        RecallOutcome.RECALL_UNCLAIMED,
        RecallOutcome.RECALL_MISSING,
    }
)
