"""Resolve a turn's terminal outcome, scoring on its FINAL state.

A transient failure on the way to a fix is normal in coding, so a turn is scored
on where it ended, not on whether any step failed. Resolving the *true* outcome is
a credit-assignment problem under delayed feedback: whether the work was accepted
is only knowable once the next turn happens. Two stages, both on objective or
behavioural signals only, with no language heuristics:

1. **Provisional label** at the turn's own stop: the execution oracle (trailing
   test/command result) -> native terminal status -> optimistic default.
2. **Final label** at the *next* turn's stop, when the successor turn's actions
   exist. The decisive signal is behavioural: did the next turn rework the same
   files this turn changed? Rework against the same artifacts is strong, language-
   agnostic evidence the turn did not land (the software-engineering revert/rework
   defect proxy, and the session-search "struggle" signal), and it catches a
   tests-passed-but-rejected false-green. Absent rework, the objective provisional
   label stands, because abstaining beats guessing.
"""

from __future__ import annotations

from typing import Any

from hyperstruck.ide.constants import (
    NATIVE_FAILURE_STATUSES,
    STATUS_COMPLETED,
    STEP_KIND_COMMAND,
    STEP_KIND_EDIT,
)


def provisional_outcome(
    steps: list[dict[str, Any]], native_status: str | None = None
) -> bool:
    """The turn-end label, from the execution oracle then native status then optimism."""
    last_command = _last_command_status(steps)
    if last_command is not None:
        return last_command == STATUS_COMPLETED
    if native_status:
        return native_status.strip().lower() not in NATIVE_FAILURE_STATUSES
    return True


def resolve_prior_outcome(provisional_is_success: bool, *, reworked: bool) -> bool:
    """The prior turn's final label: failed if the next turn reworked its files.

    Rework is the strong, language-agnostic signal that the prior turn did not
    land (even if its tests passed). With no rework, the objective provisional
    label stands.
    """
    if reworked:
        return False
    return provisional_is_success


def reworked(
    prior_steps: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    successor_steps: list[dict[str, Any]],
) -> bool:
    """Whether the successor turn edited any file the prior turn edited."""
    prior_paths = edited_paths(prior_steps)
    return bool(prior_paths) and bool(prior_paths & edited_paths(successor_steps))


def edited_paths(steps: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> set[str]:
    """The set of file paths a turn edited (from edit/command step args)."""
    paths: set[str] = set()
    for step in steps:
        if step.get("kind") not in (STEP_KIND_EDIT, STEP_KIND_COMMAND):
            continue
        args = step.get("args")
        path = args.get("path") if isinstance(args, dict) else None
        if path:
            paths.add(str(path).strip())
    return paths


def _last_command_status(steps: list[dict[str, Any]]) -> str | None:
    """The status of the last command/test step, or ``None`` if the turn ran none."""
    for step in reversed(steps):
        if step.get("kind") == STEP_KIND_COMMAND:
            return step.get("status")
    return None
