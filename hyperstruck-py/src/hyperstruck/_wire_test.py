"""The closed sets this client sends, held against what the boundary publishes."""

from __future__ import annotations

import pytest

from hyperstruck._wire import (
    DECLINE_REASONS,
    EvidenceItem,
    OBLIGATION_OUTCOMES,
    Obligation,
    ObligationClosure,
    ObligationDue,
    ObligationOutcome,
    ObligationParty,
    is_unpublished_decline_reason,
    REASON_NO_GOAL,
    REASON_READONLY_CLOSE,
    _evidence_payload,
    combine_injection_blocks,
    published_decline_reasons,
)


def test_every_published_reason_is_one_this_client_knows() -> None:
    """The vendored list is the boundary's own. A reason on it that this client cannot
    name is a decline it can never send, which is a silent gap rather than an error."""
    assert published_decline_reasons() <= DECLINE_REASONS


def test_a_reason_the_boundary_already_accepts_is_published() -> None:
    assert REASON_READONLY_CLOSE in published_decline_reasons()


def test_a_reason_can_be_defined_here_before_the_boundary_takes_it() -> None:
    """This is the whole point of publishing separately from defining.

    A refused decline is not a degraded diagnostic: it leaves the run open holding its
    resolve reservation until the retention sweep, and this client reaches a user's
    machine on a different schedule from the API it talks to. So the code names the
    reason, and the caller checks whether it may send it yet.

    Asserted against a SYNTHETIC unpublished reason rather than against a real one.
    This test read ``published_decline_reasons() < DECLINE_REASONS``, a strict subset,
    which held only while some reason was still unpublished: no_goal was the last one,
    so publishing it turned a guard on the mechanism into a guard on the backlog and
    the mechanism would have gone untested at the moment it started mattering.
    """
    assert REASON_NO_GOAL in DECLINE_REASONS
    assert REASON_NO_GOAL not in published_decline_reasons()
    # Drives the gate rather than asserting a set membership. The first rewrite of this
    # test read `assert "a_made_up_name" not in published`, which is true of any string
    # nobody wrote into the JSON file: it cannot fail and it exercises no code path, so
    # it read as coverage while testing nothing. The predicate is the mechanism.
    assert is_unpublished_decline_reason(REASON_NO_GOAL) is True
    assert is_unpublished_decline_reason(REASON_READONLY_CLOSE) is False
    assert published_decline_reasons() <= DECLINE_REASONS


def test_an_unreadable_contract_withholds_nothing_rather_than_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty published set means the file could not be read, not that nothing is sendable.

    `published_names` degrades a missing, truncated or wrong-shaped contract to an empty
    set by design. Under the old per-reason key that cost one reason; under this
    property key, without the escape hatch, it would withhold every decline and leave
    every run open holding its reservation, fleet-wide and silently.
    """
    monkeypatch.setattr("hyperstruck._wire.published_decline_reasons", frozenset)
    for reason in DECLINE_REASONS:
        assert is_unpublished_decline_reason(reason) is False


def test_combine_injection_blocks_places_the_halves_adjacently() -> None:
    assert combine_injection_blocks("RULES", "FACTS") == "RULES\n\nFACTS"
    assert combine_injection_blocks("RULES", None) == "RULES"
    assert combine_injection_blocks(None, "FACTS") == "FACTS"
    assert combine_injection_blocks(None, None) is None
    # An empty string is nothing to show, not a block to join a separator onto.
    assert combine_injection_blocks("", "FACTS") == "FACTS"
    assert combine_injection_blocks("", "") is None


def test_an_obligation_serialises_only_what_the_caller_set() -> None:
    obligation = Obligation(
        statement="Send the SOC 2 report to Meridian Books",
        owed_by=ObligationParty(role="AE"),
        owed_to=ObligationParty(entity="Meridian Books"),
        due=ObligationDue(at="2026-08-29T00:00:00+10:00", tz="Australia/Sydney"),
    )
    assert obligation.to_payload() == {
        "statement": "Send the SOC 2 report to Meridian Books",
        "owed_by": {"role": "AE"},
        "owed_to": {"entity": "Meridian Books"},
        "due": {
            "at": "2026-08-29T00:00:00+10:00",
            "precision": "date",
            "tz": "Australia/Sydney",
        },
    }


def test_an_obligation_outcome_reads_the_typed_result() -> None:
    held = ObligationOutcome.from_response({"id": "abc", "outcome": "deduped"})
    assert held.is_held and held.id == "abc"
    refused = ObligationOutcome.from_response(
        {"outcome": "refused_capacity", "reason": "hard ceiling 1000 reached"}
    )
    assert not refused.is_held and refused.reason
    assert {held.outcome, refused.outcome} <= OBLIGATION_OUTCOMES


def test_a_closure_refuses_an_outcome_the_shelf_would_reject_anyway():
    """Refused here rather than at the server, so a caller gets the field name and not a 422 from
    two layers down."""
    with pytest.raises(ValueError, match="kept_basis"):
        ObligationClosure(outcome="kept")
    with pytest.raises(ValueError, match="dropped_reason"):
        ObligationClosure(outcome="dropped")
    with pytest.raises(ValueError, match="cancel"):
        ObligationClosure(outcome="cancelled")


def test_a_closure_drops_its_version_token_on_the_loop_level_path():
    """The run lock serialises the loop-level path, so there is no race for a token to guard and
    the server does not accept one."""
    closure = ObligationClosure(
        outcome="dropped", dropped_reason="not_an_obligation", expected_version=4
    )
    assert closure.to_payload()["expected_version"] == 4
    assert "expected_version" not in closure.to_outcome_payload("ob-1")
    assert closure.to_outcome_payload("ob-1")["id"] == "ob-1"


def test_a_closure_omits_what_the_caller_did_not_say():
    """An absent expected_version means the shelf's own open-status guard is the only one that
    applies, which is not the same as sending null."""
    assert ObligationClosure(outcome="kept", kept_basis="declared").to_payload() == {
        "outcome": "kept",
        "kept_basis": "declared",
    }
def test_an_evidence_item_omits_obligations_when_none_are_set() -> None:
    item = EvidenceItem(id="e1", content="a note with no typed obligations")
    payload = _evidence_payload(item)
    assert "obligations" not in payload


def test_an_evidence_item_serialises_each_typed_obligation_with_defaults_dropped() -> None:
    item = EvidenceItem(
        id="e1",
        content="Kris said she'd send the SOC 2 report by Friday.",
        obligations=(
            Obligation(
                statement="Send the SOC 2 report to Meridian Books",
                owed_by=ObligationParty(entity="Kris"),
                owed_to=ObligationParty(entity="Meridian Books"),
                due=ObligationDue(at="2026-08-29T00:00:00+10:00", tz="Australia/Sydney"),
            ),
        ),
    )
    payload = _evidence_payload(item)
    assert payload["obligations"] == [
        {
            "statement": "Send the SOC 2 report to Meridian Books",
            "owed_by": {"entity": "Kris"},
            "owed_to": {"entity": "Meridian Books"},
            "due": {
                "at": "2026-08-29T00:00:00+10:00",
                "precision": "date",
                "tz": "Australia/Sydney",
            },
        }
    ]
