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
from pathlib import Path

from hyperstruck.contracts import published_names


class RecallOutcome(StrEnum):
    """What became of this turn's recall, from resolve through to the receipt."""

    DELIVERED = "delivered"

    # The recall never reached the model. Nothing was shown, so nothing is owed.
    # RESOLVE_NO_GOAL is kept apart from RESOLVE_EMPTY because they have different
    # owners: an empty goal means the host handed the hook no prompt, which is a wiring
    # defect, while an empty answer means the corpus had nothing for a real goal, which
    # is an ordinary cold start. RECALL_UNRECOGNISED covers both ways the stored verdict
    # cannot be believed, a value this release cannot parse and one that contradicts the
    # turn it is read for, rather than naming a cause nobody observed.
    RESOLVE_TIMED_OUT = "resolve_timed_out"
    RESOLVE_FAILED = "resolve_failed"
    RESOLVE_EMPTY = "resolve_empty"
    RESOLVE_NO_GOAL = "resolve_no_goal"
    RESOLVE_SUPERSEDED = "resolve_superseded"
    RECALL_UNCLAIMED = "recall_unclaimed"
    RECALL_MISSING = "recall_missing"
    RECALL_UNRECOGNISED = "recall_unrecognised"
    # RECALL_UNCLAIMED used to carry two answers at once. A stash the host had every
    # chance to show and did not is a defect; a stash the host was never able to show,
    # because injection rides a tool event and the turn called no tool, is the shape of
    # the host. Reported together they read as one drop rate, so the structural half was
    # being counted against the client as though a fix existed for it.
    RECALL_NO_INJECTION_POINT = "recall_no_injection_point"
    # A warm stash from an earlier turn of this project, emitted at prompt time. It was
    # shown, so it is not a drop, and it is deliberately uncreditable: it was resolved
    # against a different goal and carries no run marker, so no receipt can ever redeem
    # it. Crediting this turn for it would inflate the very rate the split above exists
    # to make honest.
    STASH_EMITTED = "stash_emitted"

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
        RecallOutcome.RECALL_NO_INJECTION_POINT,
        RecallOutcome.STASH_EMITTED,
    }
)


_CONTRACT = Path(__file__).parent / "published_recall_outcomes.json"

# Where an outcome the boundary has not published yet degrades to. The boundary validates
# this field against a closed enum behind ``extra="forbid"``, so a member it does not know
# costs the run its whole episode rather than one diagnostic field, and this client mirrors
# to its public repo on merge while the API ships on a separate dispatch. RECALL_UNCLAIMED
# is what every one of these reported before the split, so degrading to it is this client's
# own previous answer rather than a new claim, and it never reports credit that was not
# earned.
_DEGRADES_TO = RecallOutcome.RECALL_UNCLAIMED


def published_outcomes() -> frozenset[str]:
    """The outcome names the boundary accepts, as published by it."""
    return published_names(_CONTRACT, "outcomes")


def wire_value(outcome: RecallOutcome) -> str:
    """The name to send for an outcome, degraded when the boundary cannot parse it.

    An *unreadable* contract is not an empty one. Degrading on an empty set would send
    ``recall_unclaimed`` for every member including the long-published ones, so a truncated
    file in a wheel build would report delivered recall as undelivered on every turn of every
    affected install, take fleet-wide credit attribution to zero, and surface nowhere because
    the hook fails open. That turns a loud packaging fault into a silent data-integrity one.
    An empty set therefore means "nothing is known about the boundary", and the honest answer
    then is what this client's own enum says.
    """
    published = published_outcomes()
    if not published or str(outcome) in published:
        return str(outcome)
    return str(_DEGRADES_TO)


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
