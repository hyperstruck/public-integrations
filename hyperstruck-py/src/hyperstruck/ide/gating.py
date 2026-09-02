"""Decide whether a finished turn is worth observing, and classify tool calls.

The server-side critic is the precision backstop and the spend-cap is the hard
budget, so this client gate is a cost/recall optimiser: it skips the turns that
cannot teach anything (pure reading, trivial chat) and always keeps the highest
signal one (a turn that recovered from a failure).

Classification asks three questions in order and never guesses. The editor hook that
fired already knows the kind for its own events (a Cursor file-edit or shell hook), and
that wins. Otherwise the host's declaration for its own tools answers, then the stored
verdict from registration answers for everything a server contributed. A tool none of
them names is **material**.

That default is a deliberate reversal. It used to be read-only, on the reasoning that a
spurious observe costs more than a missed one, and it was backwards: those backstops
above exist for over-inclusion, *nothing* backstops over-exclusion, and a registration
gap is invisible. Under the old default every tool from every MCP server fell through to
a kind the gate refuses, so browser automation, API calls and messaging could not enter
the corpus at all, however much a run learned from them.
"""

from __future__ import annotations

from typing import Any

from hyperstruck.ide.constants import (
    MATERIAL_KINDS,
    MIN_MATERIAL_STEPS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STEP_KIND_ACT,
)
from hyperstruck.ide.host_vocabularies import declared_kind
from hyperstruck.ide.registration import registered_kind


def classify_tool(name: str | None, source: str = "") -> str:
    """Map a tool name to a step kind, from a declaration or from the material default.

    A lookup and nothing more. It is called once per tool call from inside the editor's
    hook, in a fresh subprocess, so a miss must never be the trigger for work: an
    unregistered tool takes the default rather than going and finding out.
    """
    if not name:
        return STEP_KIND_ACT
    return declared_kind(source, name) or registered_kind(source, name) or STEP_KIND_ACT


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
