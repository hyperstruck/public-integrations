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

from hyperstruck import turn_gate
from hyperstruck.ide.constants import (
    MATERIAL_KINDS,
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


# The rule lives in hyperstruck.turn_gate, which every host shares. What stays here is
# this host's vocabulary: which step kinds it calls material. Binding the two in one
# place is what stops the seats disagreeing about which turns taught anything.
recovered_from_failure = turn_gate.recovered_from_failure


def is_material(step: dict[str, Any]) -> bool:
    """Whether a captured step changed or executed something."""
    return turn_gate.is_material(step, MATERIAL_KINDS)


def should_observe(
    steps: list[dict[str, Any]], *, is_answer_present: bool = False
) -> bool:
    """Whether a turn's episode is worth shipping to observe.

    Always for a failure-recovery turn, and always for a turn that composed an answer; otherwise
    only when the turn has at least :data:`MIN_MATERIAL_STEPS` material steps. Rapid sub-threshold
    turns fall through to ``False`` (the debounce is subsumed: a tiny rapid turn cannot clear the
    material threshold). See ``turn_gate.should_observe`` for why an answer is its own reason.
    """
    return turn_gate.should_observe(
        steps, MATERIAL_KINDS, is_answer_present=is_answer_present
    )
