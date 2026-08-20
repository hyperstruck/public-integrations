from __future__ import annotations

from hyperstruck.ide.recall import RecallOutcome


def test_the_two_families_of_failure_are_told_apart_by_whether_anything_was_shown() -> (
    None
):
    """The whole point of the vocabulary: one family is a defect, the other is not.

    A run that was never shown its recall owes no receipt and must not be reported as
    a client that lost one, which is what a single missing field forced the boundary
    to assume.
    """
    never_delivered = {
        RecallOutcome.RESOLVE_TIMED_OUT,
        RecallOutcome.RESOLVE_FAILED,
        RecallOutcome.RESOLVE_EMPTY,
        RecallOutcome.RESOLVE_NO_GOAL,
        RecallOutcome.RESOLVE_SUPERSEDED,
        RecallOutcome.RECALL_UNCLAIMED,
        RecallOutcome.RECALL_MISSING,
        RecallOutcome.RECALL_UNRECOGNISED,
    }

    assert {o for o in RecallOutcome if not o.is_delivered} == never_delivered
    assert RecallOutcome.DELIVERED.is_delivered


def test_a_receipt_side_failure_still_counts_as_delivered() -> None:
    """The model was shown the recall; only the evidence of it went missing.

    These four stay a defect worth alerting on, so folding them in with the
    never-delivered states would hide the only case that is genuinely broken.
    """
    for outcome in (
        RecallOutcome.NO_TRANSCRIPT,
        RecallOutcome.TRANSCRIPT_UNREADABLE,
        RecallOutcome.RECORD_SHAPE_CHANGED,
        RecallOutcome.NO_MATCHING_RECORD,
    ):
        assert outcome.is_delivered


def test_every_outcome_is_a_plain_string_on_the_wire() -> None:
    """The value is stored and queried server-side, so it travels as its own name."""
    assert str(RecallOutcome.RESOLVE_TIMED_OUT) == "resolve_timed_out"
    assert RecallOutcome("recall_unclaimed") is RecallOutcome.RECALL_UNCLAIMED
