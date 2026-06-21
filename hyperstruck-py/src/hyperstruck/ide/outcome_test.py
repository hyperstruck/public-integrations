"""Outcome resolution: provisional cascade and structural rework."""

from __future__ import annotations

from hyperstruck.ide.outcome import (
    edited_paths,
    provisional_outcome,
    resolve_prior_outcome,
    reworked,
)


def _edit(path: str, status: str = "completed") -> dict:
    return {"kind": "edit", "status": status, "args": {"path": path}}


def _cmd(status: str) -> dict:
    return {"kind": "command", "status": status, "args": {"command": "pytest"}}


def test_provisional_execution_oracle_wins() -> None:
    assert provisional_outcome([_edit("a.py"), _cmd("completed")]) is True
    assert provisional_outcome([_edit("a.py"), _cmd("failed")]) is False


def test_provisional_native_then_optimistic() -> None:
    assert provisional_outcome([_edit("a.py")], native_status="aborted") is False
    assert provisional_outcome([_edit("a.py")], native_status="completed") is True
    assert provisional_outcome([_edit("a.py")]) is True  # optimistic default


def test_edited_paths_and_rework() -> None:
    prior = [_edit("client.py"), _cmd("completed")]
    same = [_edit("client.py")]
    other = [_edit("server.py")]
    assert edited_paths(prior) == {"client.py"}
    assert reworked(prior, same) is True
    assert reworked(prior, other) is False
    assert reworked([_cmd("completed")], same) is False  # no prior paths


def test_resolve_prior_outcome() -> None:
    # Rework marks the prior turn failed, even when it had passed (false-green).
    assert resolve_prior_outcome(True, reworked=True) is False
    assert resolve_prior_outcome(False, reworked=True) is False
    # No rework: the objective provisional label stands.
    assert resolve_prior_outcome(True, reworked=False) is True
    assert resolve_prior_outcome(False, reworked=False) is False
