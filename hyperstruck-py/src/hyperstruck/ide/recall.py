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

from dataclasses import dataclass
from enum import StrEnum


class RecallOutcome(StrEnum):
    """What became of this turn's recall, from resolve through to the receipt."""

    DELIVERED = "delivered"

    # The recall never reached the model. Nothing was shown, so nothing is owed.
    # RESOLVE_NO_GOAL is kept apart from RESOLVE_EMPTY because they have different
    # owners: an empty goal means the host handed the hook no prompt, which is a wiring
    # defect, while an empty answer means the corpus had nothing for a real goal, which
    # is an ordinary cold start. RECALL_UNRECOGNISED is the honest answer when the
    # stored verdict cannot be read back at all, rather than naming a cause nobody saw.
    RESOLVE_TIMED_OUT = "resolve_timed_out"
    RESOLVE_FAILED = "resolve_failed"
    RESOLVE_EMPTY = "resolve_empty"
    RESOLVE_NO_GOAL = "resolve_no_goal"
    RESOLVE_SUPERSEDED = "resolve_superseded"
    RECALL_UNCLAIMED = "recall_unclaimed"
    RECALL_MISSING = "recall_missing"
    RECALL_UNRECOGNISED = "recall_unrecognised"

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
        RecallOutcome.RESOLVE_NO_GOAL,
        RecallOutcome.RESOLVE_SUPERSEDED,
        RecallOutcome.RECALL_UNCLAIMED,
        RecallOutcome.RECALL_MISSING,
        RecallOutcome.RECALL_UNRECOGNISED,
    }
)


@dataclass(frozen=True)
class RecallResult:
    """A turn's receipt and the reason it has none, which are one answer.

    Threaded together rather than as a bare pair, because the two are read at three call
    sites and by position: an anonymous tuple makes ``recall[0]`` the receipt at every
    one of them and nothing catches the day someone swaps them.
    """

    receipt: str
    outcome: RecallOutcome

    @property
    def is_delivered(self) -> bool:
        return self.outcome.is_delivered
