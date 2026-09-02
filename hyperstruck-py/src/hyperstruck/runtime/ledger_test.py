"""What the ledger must refuse, which is most of what it is for."""

from __future__ import annotations

import pytest

from hyperstruck.runtime.ledger import (
    LedgerClosedError,
    RunLedger,
    render_confirmed_shelf,
)


def _ledger() -> RunLedger:
    ledger = RunLedger(run_id="r1", goal="g")
    ledger.record_offer(
        advice=render_confirmed_shelf("advice", "A", ["l1", "l2"]),
        facts=render_confirmed_shelf("facts", "F", ["c1"]),
    )
    return ledger


def test_only_calls_present_in_both_streams_become_steps() -> None:
    """A planned call the runtime never ran is not evidence about anything.

    Recording it would teach the corpus from an obligation rather than from an outcome,
    which is the failure this join exists to prevent.
    """
    ledger = _ledger()
    ledger.record_planned_calls([("t1", "search", {"q": "x"}), ("t2", "write", {})])
    ledger.record_outcome("t1", "search", result={"hits": 1})

    assert [step["id"] for step in ledger.steps] == ["t1"]


def test_an_outcome_for_a_call_nobody_planned_is_dropped() -> None:
    """The same defect from the other side: two streams from different runs."""
    ledger = _ledger()
    ledger.record_planned_calls([("t1", "search", {})])
    ledger.record_outcome("t1", "search", result=1)
    ledger.record_outcome("stray", "other", result=1)

    assert [step["id"] for step in ledger.steps] == ["t1"]


def test_a_failed_outcome_is_recorded_as_failed_not_dropped() -> None:
    """A failure is the highest-signal step there is; losing it loses the lesson."""
    ledger = _ledger()
    ledger.record_planned_calls([("t1", "write", {})])
    ledger.record_outcome("t1", "write", error="permission denied")

    assert ledger.steps[0]["status"] == "failed"
    assert ledger.steps[0]["error"] == "permission denied"


def test_the_ledger_holds_the_two_shelves_the_boundary_returns() -> None:
    """Open obligations ride the facts shelf as owed claims, so there is no third shelf."""
    ledger = _ledger()

    assert [ledger.advice.offered_ids, ledger.facts.offered_ids] == [
        ("l1", "l2"),
        ("c1",),
    ]
    assert not hasattr(ledger, "obligations")
    assert ledger.offered_any is True


def test_recording_after_close_is_refused_rather_than_ignored() -> None:
    """Ignoring it would report a smaller episode than the one that happened."""
    ledger = _ledger()
    ledger.close()

    with pytest.raises(LedgerClosedError):
        ledger.record_outcome("t1", "write", result=1)
    with pytest.raises(LedgerClosedError):
        ledger.record_planned_calls([("t1", "write", {})])


def test_a_second_close_is_refused() -> None:
    """A no-op would hide a double close in a retry, and the second sends a duplicate."""
    ledger = _ledger()
    ledger.close()

    with pytest.raises(LedgerClosedError, match="already closed"):
        ledger.close()


def test_a_resolve_that_raised_is_distinguishable_from_one_that_returned_nothing() -> (
    None
):
    """Collapsing these makes a broken deployment look exactly like a cold corpus."""
    ledger = RunLedger(run_id="r2", goal="g")
    ledger.record_resolve_failed()

    assert ledger.is_resolved is True
    assert ledger.is_resolve_failed is True
    assert ledger.offered_any is False


def test_an_empty_offer_is_resolved_but_offers_nothing() -> None:
    ledger = RunLedger(run_id="r3", goal="g")
    ledger.record_offer(
        advice=render_confirmed_shelf("advice", None, []),
        facts=render_confirmed_shelf("facts", None, []),
    )

    assert ledger.is_resolved is True
    assert ledger.is_resolve_failed is False
    assert ledger.offered_any is False
