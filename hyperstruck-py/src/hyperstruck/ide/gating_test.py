"""Informative-turn gating and tool classification."""

from __future__ import annotations

from hyperstruck.ide.gating import classify_tool, recovered_from_failure, should_observe
from hyperstruck.ide.constants import (
    STEP_KIND_COMMAND,
    STEP_KIND_EDIT,
    STEP_KIND_OTHER,
    STEP_KIND_READ,
)


def test_classify_tool() -> None:
    assert classify_tool("Edit") == STEP_KIND_EDIT
    assert classify_tool("Write") == STEP_KIND_EDIT
    assert classify_tool("Bash") == STEP_KIND_COMMAND
    assert classify_tool("run_terminal_cmd") == STEP_KIND_COMMAND
    assert classify_tool("Read") == STEP_KIND_READ
    assert classify_tool("Grep") == STEP_KIND_READ
    assert classify_tool("mystery_tool") == STEP_KIND_OTHER
    assert classify_tool(None) == STEP_KIND_OTHER


def _step(kind: str, status: str = "completed") -> dict:
    return {"kind": kind, "status": status}


def test_should_observe_material_threshold() -> None:
    assert should_observe([_step("edit"), _step("command")]) is True
    assert (
        should_observe([_step("edit")]) is False
    )  # one material step is below the gate
    assert should_observe([_step("read"), _step("read")]) is False
    assert should_observe([]) is False


def test_should_observe_failure_recovery_always() -> None:
    steps = [_step("command", "failed"), _step("command", "completed")]
    assert recovered_from_failure(steps) is True
    assert should_observe(steps) is True


def test_no_recovery_when_failure_is_last() -> None:
    steps = [_step("command", "completed"), _step("command", "failed")]
    assert recovered_from_failure(steps) is False
