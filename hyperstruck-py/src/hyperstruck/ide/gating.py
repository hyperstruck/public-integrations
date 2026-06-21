"""Decide whether a finished turn is worth observing, and classify tool calls.

The server-side critic is the precision backstop and the spend-cap is the hard
budget, so this client gate is a cost/recall optimiser: it skips the turns that
cannot teach anything (pure reading, trivial chat) and always keeps the highest
signal one (a turn that recovered from a failure).

Classification is best-effort by tool name, refined by the editor hook that fired
(a Cursor file-edit or shell hook already tells us the kind). An unrecognised
tool is treated as read-only, the conservative choice: it never forces a spurious
observe, and a genuinely material unknown tool still rides in alongside the known
material steps of the same turn.
"""

from __future__ import annotations

from typing import Any

from hyperstruck.ide.constants import (
    MATERIAL_KINDS,
    MIN_MATERIAL_STEPS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STEP_KIND_COMMAND,
    STEP_KIND_EDIT,
    STEP_KIND_OTHER,
    STEP_KIND_READ,
)

# Substrings (lowercased) that mark a tool as an edit or a command across Claude
# Code and Cursor tool names. Read-only is the default for anything unmatched.
_EDIT_HINTS = (
    "edit",
    "write",
    "create_file",
    "apply_patch",
    "str_replace",
    "notebook",
    "patch",
)
_COMMAND_HINTS = (
    "bash",
    "shell",
    "terminal",
    "run_command",
    "exec",
    "pytest",
    "npm",
    "make",
)
_READ_HINTS = (
    "read",
    "grep",
    "glob",
    "search",
    "list_dir",
    "ls",
    "fetch",
    "view",
    "cat",
    "find",
)


def classify_tool(name: str | None) -> str:
    """Map a tool name to a step kind (edit / command / read / other)."""
    lowered = (name or "").lower()
    if not lowered:
        return STEP_KIND_OTHER
    if any(hint in lowered for hint in _EDIT_HINTS):
        return STEP_KIND_EDIT
    if any(hint in lowered for hint in _COMMAND_HINTS):
        return STEP_KIND_COMMAND
    if any(hint in lowered for hint in _READ_HINTS):
        return STEP_KIND_READ
    return STEP_KIND_OTHER


def is_material(step: dict[str, Any]) -> bool:
    """Whether a captured step changed or executed something."""
    return step.get("kind") in MATERIAL_KINDS


def recovered_from_failure(steps: list[dict[str, Any]]) -> bool:
    """A failed step followed by any later successful step: the prime learning."""
    seen_failure = False
    for step in steps:
        if step.get("status") == STATUS_FAILED:
            seen_failure = True
        elif seen_failure and step.get("status") == STATUS_COMPLETED:
            return True
    return False


def should_observe(steps: list[dict[str, Any]]) -> bool:
    """Whether a turn's episode is worth shipping to observe.

    Always for a failure-recovery turn; otherwise only when the turn has at least
    :data:`MIN_MATERIAL_STEPS` material steps. Pure read/search/chat turns, and
    rapid sub-threshold turns, fall through to ``False`` (the debounce is
    subsumed: a tiny rapid turn cannot clear the material threshold).
    """
    if not steps:
        return False
    if recovered_from_failure(steps):
        return True
    material = sum(1 for step in steps if is_material(step))
    return material >= MIN_MATERIAL_STEPS
