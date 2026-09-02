"""Privacy-forward redaction for IDE turns, before any episode leaves the machine.

Two protections, in order of importance:

1. **No raw file contents or diffs are shipped.** The hook never captures a file
   body or a diff into a step, and it never captures a tool's output: a read or edit
   result *is* file contents and a command's stdout can be source. What it captures is
   the tool name, the path or command, the status, the error, and — for a failure that
   has one — the exit status alone, under the single field name the server derives a
   gate from (see :mod:`hyperstruck.ide.step_result`). The pattern, not the literal
   code, is what the producer needs. :func:`clip_result` enforces the size ceiling on
   the strings that do ship.
2. **Secrets are scrubbed** from whatever strings do ship (paths, commands, error
   text, clipped results, the goal). Known credential shapes are always redacted;
   long high-entropy tokens are redacted on the privacy-forward default that
   over-redaction is safer than a leak.

Layered over the package's declared-field redaction (:func:`redact_episode_payload`),
so a customer who *does* declare tool-arg sensitivity still gets that strip too.
The trade is recorded in the spec's decisions log: a richer "ship full results"
mode and a local-abstraction pass are available upgrades, not the default.

Separately from privacy, this module also holds strings inside the *boundary's*
bounds (:func:`clip_goal`). That ceiling is not ours to choose: over it the write
is rejected outright and the turn's learning is lost, so clipping to fit is what
keeps an oversized turn deliverable at all.
"""

from __future__ import annotations

import uuid
from typing import Any

from hyperstruck.ide.constants import (
    MAX_BOUNDARY_GOAL_CHARS,
    MAX_FINAL_OUTPUT_CHARS,
    MAX_RESULT_CHARS,
    TRUNCATION_MARKER,
)
from hyperstruck.redaction import (
    known_credential_match,
    redact_episode_payload,
    scrub_secrets,
    scrub_strings,
)

# ``scrub_secrets`` is owned by the shared redaction module and only used here; it
# is deliberately not re-exported (import it from ``hyperstruck.redaction``).
__all__ = [
    "clip_goal",
    "clip_result",
    "redact_ide_episode",
]


def clip_to(text: str, limit: int) -> str:
    """Truncate to ``limit`` characters in total, marker included."""
    if len(text) <= limit:
        return text
    if limit <= len(TRUNCATION_MARKER):
        return text[:limit]
    return text[: limit - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER


def clip_result(value: Any) -> Any:
    """Clip a tool result to the size ceiling so no large body is ever shipped.

    A string is truncated with an explicit marker; a non-string is rendered to a
    string first (its repr may carry detail, so it is clipped the same way). This
    is the last line against a raw file body sneaking through a tool result.
    """
    if value is None:
        return None
    return clip_to(value if isinstance(value, str) else str(value), MAX_RESULT_CHARS)


def clip_goal(text: str) -> str:
    """Hold the goal inside the platform's bound, which resolve and observe share.

    Applied at capture and again after the secret scrub: scrubbing substitutes a
    placeholder that can be longer than the token it replaces, so a goal that fit
    before the scrub can exceed the bound after it.
    """
    return clip_to(text, MAX_BOUNDARY_GOAL_CHARS)


def redact_ide_episode(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a send-safe copy of an episode payload.

    Declared-sensitive args are stripped first (package redaction), then the
    secret scrub is applied ONLY to the free-text fields (goal and a step's descriptive
    fields), never to identifiers. Scrubbing the whole dict would
    corrupt ``run_id`` (its uuid tail clears the high-entropy gate), which the
    server keys its offer log and dedup on, silently breaking reinforce.
    ``run_id``/``thread_id``/``source_framework`` are preserved verbatim, and so is
    each step's ``id``, and so is every counter on ``outcome``; ``outcome.final_output``
    is free text and is scrubbed and clipped like the goal. The input is not mutated.

    ``principal_utterance`` is dropped here even though the field still ships, and the two are not
    in tension: what replaced the old guard is a different SOURCE, not a check on this value. This
    host stopped populating the field when it stopped deferring a turn to its successor, so
    anything found here arrived from somewhere that never passed the admission rules that used to
    guard it, and the field authorises a rule rendered at primacy. What ships now is minted at
    delivery from the spans this client tagged as the principal's own prose
    (:func:`prompt_spans.principal_prose`), out of a goal already scrubbed and clipped above, and
    the boundary refuses any value it cannot place inside that tagged prose.
    """
    redacted = dict(redact_episode_payload(payload))
    goal = redacted.get("goal")
    if isinstance(goal, str):
        redacted["goal"] = clip_goal(scrub_secrets(goal))
    # Dropped for the reason in the docstring: the value now comes from the tagged spans.
    redacted.pop("principal_utterance", None)
    # The assistant's own closing prose, scrubbed and clipped rather than dropped.
    #
    # Dropped is what happens to ``principal_utterance`` above, and the reason does not carry: that
    # field authorises a rule frozen against outcomes, so an unaccounted-for value there is a
    # privilege escalation. This one is read for the commitments the assistant made in it, and it is
    # the assistant's own text rather than an unattributed one. What it CAN carry is a secret the
    # answer quoted back out of a tool result, so it goes through the same scrub the goal does, and
    # the same clip, because it is bounded at the boundary and a 4xx there costs the whole episode.
    #
    # An answer that scrubs down to nothing has the key REMOVED rather than sent empty, because the
    # API model forbids extra keys and the omission is what the whole rollout ordering rests on.
    outcome = redacted.get("outcome")
    if isinstance(outcome, dict) and isinstance(outcome.get("final_output"), str):
        scrubbed = clip_to(
            scrub_secrets(outcome["final_output"]), MAX_FINAL_OUTPUT_CHARS
        )
        outcome = {**outcome, "final_output": scrubbed}
        if not scrubbed:
            del outcome["final_output"]
        redacted["outcome"] = outcome
    if isinstance(redacted.get("steps"), list):
        redacted["steps"] = [_redact_step(step) for step in redacted["steps"]]
    return redacted


def _redact_step(step: Any) -> Any:
    """Scrub a step's descriptive fields while keeping its hook-minted provenance."""
    if not isinstance(step, dict):
        return scrub_strings(step, scrub_secrets)
    scrubbed = scrub_strings(step, scrub_secrets)
    if "id" in step:
        scrubbed["id"] = _safe_step_id(step["id"])
    return _restore_provenance_source_id(step, scrubbed)


# Restored verbatim: identifiers the client itself minted, never free text.
_HOOK_MINTED_PROVENANCE_KEYS = ("source_id", "_raw_path")


def _restore_provenance_source_id(
    original: Any, scrubbed: dict[str, Any]
) -> dict[str, Any]:
    """Put the hook-minted provenance keys back exactly as captured, never scrubbed.

    ``source_id`` is an identifier the client mints (a run id), not free text, the
    same reason a step's own ``id`` is restored above; the boundary parses it to
    name a turn, so a scrubbed segment collapses every session onto one.
    ``_raw_path`` is the tool's own unscrubbed path, carried through to the flush
    that relativises it; a real path can contain a high-entropy-looking segment
    (a temp directory name) this same scrub would otherwise corrupt.
    """
    provenance = (original.get("declared_sensitivity") or {}).get("provenance")
    if not isinstance(provenance, dict) or not any(
        key in provenance for key in _HOOK_MINTED_PROVENANCE_KEYS
    ):
        return scrubbed
    sensitivity = scrubbed.get("declared_sensitivity")
    if not isinstance(sensitivity, dict) or not isinstance(
        sensitivity.get("provenance"), dict
    ):
        return scrubbed
    restored = {
        key: provenance[key]
        for key in _HOOK_MINTED_PROVENANCE_KEYS
        if key in provenance
    }
    return {
        **scrubbed,
        "declared_sensitivity": {
            **sensitivity,
            "provenance": {**sensitivity["provenance"], **restored},
        },
    }


def _safe_step_id(original: Any) -> Any:
    """Preserve a step id, or re-mint it, but never flatten it to the marker.

    A step id joins a decision to its outcome and is documented unique within the
    episode, so replacing it with a shared marker collides every step onto one.
    That was live: a Cursor step id is a bare ``uuid4().hex``, which clears the
    entropy gate about 83% of the time, and a Claude Code ``toolu_`` id escapes
    only by being 30 characters against a 32-character rule.

    This path must fail open, so refusing (the distil answer for an identifier) is
    not available. Re-minting is the third option and the right one here: a fresh
    id drops the suspect text while staying unique, which a marker does not.
    """
    if not isinstance(original, str) or not original:
        return original
    return original if known_credential_match(original) is None else uuid.uuid4().hex
