from __future__ import annotations

from hyperstruck.ide.recall import RecallOutcome, published_outcomes, wire_value


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
        RecallOutcome.NO_MATCHING_RECORD,
        RecallOutcome.RECALL_NO_INJECTION_POINT,
        RecallOutcome.STASH_EMITTED,
    }

    assert {o for o in RecallOutcome if not o.is_delivered} == never_delivered
    assert RecallOutcome.DELIVERED.is_delivered


def test_a_failed_read_of_the_receipt_still_counts_as_delivered() -> None:
    """The model was shown the recall; only the evidence of it went missing.

    These three stay a defect worth alerting on, so folding them in with the
    never-delivered states would hide the only case that is genuinely broken.
    """
    for outcome in (
        RecallOutcome.NO_TRANSCRIPT,
        RecallOutcome.TRANSCRIPT_UNREADABLE,
        RecallOutcome.RECORD_SHAPE_CHANGED,
    ):
        assert outcome.is_delivered


def test_an_absent_record_is_the_editors_refusal_not_a_failed_read() -> None:
    """The one receipt-side answer that is evidence of a decision, not of a fault.

    ``receipt`` states that a denied, failed or dropped injection leaves no record at
    all, so an absent one means the recall never reached the model. Counting it as
    delivered charged the caller for recall it never saw and filed the run under a
    remedy nobody could apply.
    """
    assert not RecallOutcome.NO_MATCHING_RECORD.is_delivered


def test_every_outcome_is_a_plain_string_on_the_wire() -> None:
    """The value is stored and queried server-side, so it travels as its own name."""
    assert str(RecallOutcome.RESOLVE_TIMED_OUT) == "resolve_timed_out"
    assert RecallOutcome("recall_unclaimed") is RecallOutcome.RECALL_UNCLAIMED


def test_an_outcome_the_boundary_has_not_published_degrades_instead_of_422ing() -> None:
    """The field is a closed enum behind ``extra="forbid"`` on the receiving side.

    A member this client sends and the deployed boundary cannot parse costs that run
    its whole episode, not one diagnostic field, and this client reaches users on a
    different schedule from the API. So an unpublished member travels as the answer
    this client gave before the member existed, which is never one that claims credit.
    """
    published = published_outcomes()

    assert str(RecallOutcome.RECALL_UNCLAIMED) in published
    assert wire_value(RecallOutcome.RESOLVE_TIMED_OUT) == "resolve_timed_out"
    for pending in (
        RecallOutcome.RECALL_NO_INJECTION_POINT,
        RecallOutcome.STASH_EMITTED,
    ):
        if str(pending) in published:
            assert wire_value(pending) == str(pending)
        else:
            assert wire_value(pending) == str(RecallOutcome.RECALL_UNCLAIMED)
            assert not RecallOutcome(wire_value(pending)).is_delivered


def test_every_published_outcome_is_a_member_this_client_knows() -> None:
    """The vendored list is the boundary's, so a name absent here means a silent drop."""
    assert published_outcomes() <= {str(outcome) for outcome in RecallOutcome}
