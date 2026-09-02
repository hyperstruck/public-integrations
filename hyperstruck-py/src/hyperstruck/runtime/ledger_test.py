"""What the ledger must refuse, which is most of what it is for."""

from __future__ import annotations

import pytest

from hyperstruck.runtime.ledger import (
    LedgerClosedError,
    RunLedger,
    Shelf,
    offered_and_delivered_shelf,
    render_confirmed_shelf,
)


def _ledger(*, delivered: list[str] | None = None) -> RunLedger:
    ledger = RunLedger(run_id="r1", goal="g")
    ledger.record_offer(
        advice=render_confirmed_shelf("advice", "A", ["l1", "l2"]),
        facts=render_confirmed_shelf("facts", "F", ["c1"]),
        obligations=offered_and_delivered_shelf(
            "obligations", "O", ["o1", "o2"], delivered
        ),
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


def test_the_obligation_shelf_keeps_offered_and_delivered_apart() -> None:
    """The whole reason this ledger has three shelves rather than two id sets.

    ``offered_obligation_ids`` names everything selection admitted, including one the
    token budget then cut. The shelf escalates on deliveries, so reporting the offered
    set as delivered would escalate an obligation no model was ever shown.
    """
    ledger = _ledger(delivered=["o1"])

    assert ledger.obligations is not None
    assert ledger.obligations.offered_ids == ("o1", "o2")
    assert ledger.obligations.delivered_ids == ("o1",)
    assert ledger.offered_any is True
    assert ledger.delivered_any is True


def test_a_boundary_reporting_no_delivered_set_reads_as_nothing_delivered() -> None:
    """Under-reporting forgoes credit; over-reporting escalates against a real person.

    An older deployment sends no delivered set at all. Reading its silence as "all of
    them" is the one direction with a cost outside our own numbers.
    """
    ledger = _ledger(delivered=None)

    assert ledger.obligations is not None
    assert ledger.obligations.offered_ids == ("o1", "o2")
    assert ledger.obligations.delivered_ids == ()


def test_a_render_confirmed_shelf_whose_sets_disagree_is_refused() -> None:
    """Either the boundary changed its promise or the flag is wrong. Both need a person."""
    with pytest.raises(ValueError, match="render-confirmed"):
        Shelf(
            name="advice",
            text=None,
            offered_ids=("a",),
            delivered_ids=(),
            is_render_confirmed=True,
        )


def test_delivering_an_id_that_was_never_offered_is_refused() -> None:
    """A difference here means the two sets were read from different responses."""
    with pytest.raises(ValueError, match="never offered"):
        Shelf(
            name="obligations",
            text=None,
            offered_ids=("a",),
            delivered_ids=("b",),
            is_render_confirmed=False,
        )


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
        obligations=offered_and_delivered_shelf("obligations", None, [], None),
    )

    assert ledger.is_resolved is True
    assert ledger.is_resolve_failed is False
    assert ledger.offered_any is False
