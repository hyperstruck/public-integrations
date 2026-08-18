"""Outcome resolution: the evidence ladder and its abstention."""

from __future__ import annotations

import pytest

from hyperstruck.ide.constants import (
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    SOURCE_OPENHANDS,
)
from hyperstruck.ide.host_vocabularies import vocabulary_for
from hyperstruck.ide.outcome import (
    EMPTY_VOCABULARY,
    NativeStatusVocabulary,
    TurnOutcome,
    provisional_outcome,
)

_DECLARED = vocabulary_for(SOURCE_CLAUDE_CODE)


def _edit(path: str, status: str = "completed") -> dict:
    return {"kind": "edit", "status": status, "args": {"path": path}}


def _cmd(status: str) -> dict:
    return {"kind": "command", "status": status, "args": {"command": "pytest"}}


def test_execution_oracle_wins_over_every_other_signal() -> None:
    assert (
        provisional_outcome(
            [_edit("a.py"), _cmd("completed")], "aborted", _DECLARED
        )
        is TurnOutcome.SUCCESS
    )
    assert (
        provisional_outcome([_edit("a.py"), _cmd("failed")], "completed", _DECLARED)
        is TurnOutcome.FAILURE
    )


def test_a_declared_native_status_decides_when_no_command_ran() -> None:
    assert (
        provisional_outcome([_edit("a.py")], "aborted", _DECLARED)
        is TurnOutcome.FAILURE
    )
    assert (
        provisional_outcome([_edit("a.py")], "completed", _DECLARED)
        is TurnOutcome.SUCCESS
    )


def test_an_undeclared_native_status_abstains_rather_than_passing() -> None:
    """The hole the shared failure set left: a CI timeout used to be a success."""
    assert (
        provisional_outcome([_edit("a.py")], "timeout", _DECLARED)
        is TurnOutcome.UNEVIDENCED
    )


def test_no_evidence_at_all_abstains() -> None:
    assert provisional_outcome([_edit("a.py")], None, _DECLARED) is (
        TurnOutcome.UNEVIDENCED
    )
    assert provisional_outcome([], None, _DECLARED) is TurnOutcome.UNEVIDENCED


def test_an_evidenced_turn_and_an_unevidenced_one_differ() -> None:
    """Guard the mutation that drops the abstention branch.

    A fixture where both cases expect the same verdict would pass an
    implementation that never abstains, so the two expectations must differ.
    """
    evidenced = provisional_outcome([_edit("a.py"), _cmd("completed")], None, _DECLARED)
    unevidenced = provisional_outcome([_edit("a.py")], None, _DECLARED)
    assert evidenced is TurnOutcome.SUCCESS
    assert unevidenced is TurnOutcome.UNEVIDENCED
    assert evidenced is not unevidenced
    assert evidenced.is_evidenced and not unevidenced.is_evidenced


def test_an_undeclared_source_abstains_on_every_status() -> None:
    unknown = vocabulary_for("some-host-nobody-declared")
    assert unknown is EMPTY_VOCABULARY
    for status in ("completed", "failed", "aborted", "finished"):
        assert (
            provisional_outcome([_edit("a.py")], status, unknown)
            is TurnOutcome.UNEVIDENCED
        )


@pytest.mark.parametrize(
    "source", [SOURCE_CLAUDE_CODE, SOURCE_CURSOR, SOURCE_OPENHANDS]
)
def test_every_supported_source_declares_a_vocabulary(source: str) -> None:
    """A shipped host that declared nothing would decline all of its traffic."""
    declared = vocabulary_for(source)
    assert declared is not EMPTY_VOCABULARY
    assert declared.success and declared.failure


def test_the_default_vocabulary_abstains_so_a_caller_must_opt_in() -> None:
    assert (
        provisional_outcome([_edit("a.py")], "completed") is TurnOutcome.UNEVIDENCED
    )


def test_classification_is_case_and_whitespace_insensitive() -> None:
    assert _DECLARED.classify("  ABORTED ") is TurnOutcome.FAILURE
    assert _DECLARED.classify("Completed") is TurnOutcome.SUCCESS


def test_failure_wins_a_status_declared_as_both() -> None:
    """A contradictory declaration must not be read as a pass."""
    contradictory = NativeStatusVocabulary(
        success=frozenset({"done"}), failure=frozenset({"done"})
    )
    assert contradictory.classify("done") is TurnOutcome.FAILURE
