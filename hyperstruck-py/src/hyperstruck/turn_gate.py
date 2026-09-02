"""Whether a finished turn is worth observing, and why it was declined if not.

Lifted out of ``hyperstruck.ide`` rather than copied. It was the only implementation of
this decision in the package: the LangGraph seat never declines at all, so a second host
either inherited nothing or grew a second table beside this one. Two tables deciding what
the corpus learns from is not a duplication that shows up as a merge conflict; it shows up
months later as two hosts disagreeing about which turns taught anything, with no single
place to read the rule.

It lives at the neutral layer because ``no_engine_import_test`` forbids the neutral half
importing ``hyperstruck.ide``, and every host needs it. The IDE seat re-exports these
names, so its own callers and tests are unchanged.

The server-side critic is the precision backstop and the spend cap is the hard budget, so
this gate is a cost and recall optimiser rather than a correctness boundary: it skips
turns that cannot teach anything and always keeps the highest-signal one, a turn that
recovered from a failure.
"""

from __future__ import annotations

from typing import Any

from hyperstruck._wire import (
    REASON_BELOW_MATERIAL_THRESHOLD,
    REASON_EMPTY_OFFER,
    REASON_NO_GOAL,
    REASON_NO_TOOL_CALLS,
    REASON_UNEVIDENCED_OUTCOME,
)

# The step statuses and the material-kind set the gate reads. Duplicated from the IDE
# constants deliberately rather than imported from them, because importing would put the
# neutral layer back under the adapter this module exists to climb out of. The IDE module
# now imports these instead of defining its own, so there is still exactly one definition.
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Two, not one. One material step is a turn that did a single thing, which the corpus
# cannot contrast against anything; two is the minimum from which a lesson can be drawn.
MIN_MATERIAL_STEPS = 2

# The reasons themselves already live at the neutral layer and are imported above rather
# than restated here. ``REASON_NO_GOAL`` is not in the server's closed set and must be
# sent only when the vendored contract says the boundary recognises it, exactly as the
# IDE seat already gates it: a decline carrying an unknown reason is refused, and a
# refused decline leaves the run open holding its resolve reservation, which is worse
# than saying less.


def is_material(step: dict[str, Any], material_kinds: frozenset[str]) -> bool:
    """Whether a captured step changed or executed something.

    The kind set is passed in rather than read from a constant, because what counts as
    material is the host's judgement about its own tools and the two hosts do not share a
    vocabulary. The rule over the set is what is shared.
    """
    return step.get("kind") in material_kinds


def recovered_from_failure(steps: list[dict[str, Any]]) -> bool:
    """A failed step followed by any later successful step: the prime learning."""
    seen_failure = False
    for step in steps:
        if step.get("status") == STATUS_FAILED:
            seen_failure = True
        elif seen_failure and step.get("status") == STATUS_COMPLETED:
            return True
    return False


def should_observe(
    steps: list[dict[str, Any]],
    material_kinds: frozenset[str],
    *,
    is_answer_present: bool = False,
) -> bool:
    """Whether a turn's episode is worth shipping to observe.

    Always for a failure-recovery turn, and always for a turn that composed an answer; otherwise
    only when the turn has at least :data:`MIN_MATERIAL_STEPS` material steps. Rapid sub-threshold
    turns fall through to ``False``, and the debounce is subsumed, since a tiny rapid turn cannot
    clear the material threshold anyway.

    ``is_answer_present`` exists because the material threshold answers a question about the
    LEARNING corpus, that one step cannot be contrasted against anything, and was silently also
    deciding a different question over the same turn: whether a commitment the agent SPOKE is ever
    seen. Those come apart exactly where it matters. "I will confirm the volumes with the depot and
    send them over by Friday", said after a read and no edit, is one material step at most and is
    the whole shape the own-output obligation lane exists for; under the threshold alone it went to
    reinforce, which does not harvest, or to decline, which carries no episode, and the promise was
    lost as completely as before the lane was built.

    The learning half is not harmed by the widening: a thin episode simply yields no learning and
    is reported with a zero-yield reason, which is the same outcome it would have had unsent. The
    cost is real and is the reason this is a separate flag rather than a lowered threshold: it
    ships more episodes on the observe leg, so it is spent only where an answer actually exists.
    """
    if not steps:
        return False
    if recovered_from_failure(steps):
        return True
    if is_answer_present:
        return True
    material = sum(1 for step in steps if is_material(step, material_kinds))
    return material >= MIN_MATERIAL_STEPS


def decline_reason(
    steps: list[dict[str, Any]],
    is_worth_learning_from: bool,
    *,
    is_goalless: bool,
    is_offer_empty: bool = False,
) -> str:
    """Why this turn was declined, from the gate that actually decided it.

    The goalless case is reported first because it is the only one that is not a
    judgement about the turn's steps: a goalless turn can be entirely material and is
    still declined, so reporting it by its step count would name a gate that never ran.

    Derived rather than invented, so the reported cause and the gate can never disagree.
    This is what makes the gate measurable: before it was derived, it fired silently and
    how often it skipped a turn, and why, was invisible.

    The missing outcome is reported only for a turn the step gates would have let
    through, because that is the only case where it decided anything. A turn that wrote
    nothing is below the material threshold whatever its evidence says, and naming the
    outcome there would report a gate that never got to run.

    The order below is exactly the order the code tests, and the two must be read together:
    goalless first, then the missing outcome, then no steps at all, then the empty offer,
    then the step count. An earlier draft of this docstring described the empty offer as
    ordered after "the step gates" in a way that read as though it came last of all.

    ``empty_offer`` is unreachable from the IDE seat and reachable here, which is why the
    parameter exists: a host whose recall returned nothing and whose turn had nothing
    material is better described by the empty offer than by the step count, because the
    repair is different. One says the corpus had nothing to give, the other says the turn
    had nothing to give back. It is still ordered after the step gates, so a turn with
    material steps is never explained away by its offer.

    "Read-only" is deliberately avoided here, though it once appeared. The word names a
    different thing elsewhere: ``readonly_close`` is what a throwaway recall closes itself
    with, and such a run never reaches this function. One is a turn that made no writes,
    the other a recall that had no turn. Reusing the word for both is how those two
    populations became indistinguishable in the first place.
    """
    if is_goalless:
        return REASON_NO_GOAL
    if is_worth_learning_from:
        return REASON_UNEVIDENCED_OUTCOME
    if not steps:
        return REASON_NO_TOOL_CALLS
    if is_offer_empty:
        return REASON_EMPTY_OFFER
    return REASON_BELOW_MATERIAL_THRESHOLD
