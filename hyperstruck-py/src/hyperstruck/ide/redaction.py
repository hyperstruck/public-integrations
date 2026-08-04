"""Privacy-forward redaction for IDE turns, before any episode leaves the machine.

Two protections, in order of importance:

1. **No raw file contents or diffs are shipped.** The hook never captures a file
   body or a diff into a step; it captures the tool name, the path, the status,
   the error, and a clipped result. The pattern, not the literal code, is what the
   producer needs. :func:`clip_result` enforces the size ceiling at capture.
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

from typing import Any

from hyperstruck.ide.constants import (
    MAX_BOUNDARY_GOAL_CHARS,
    MAX_RESULT_CHARS,
    TRUNCATION_MARKER,
)
from hyperstruck.redaction import (
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


def _clip(text: str, limit: int) -> str:
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
    return _clip(value if isinstance(value, str) else str(value), MAX_RESULT_CHARS)


def clip_goal(text: str) -> str:
    """Hold the goal inside the platform's bound, which resolve and observe share.

    Applied at capture and again after the secret scrub: scrubbing substitutes a
    placeholder that can be longer than the token it replaces, so a goal that fit
    before the scrub can exceed the bound after it.
    """
    return _clip(text, MAX_BOUNDARY_GOAL_CHARS)


def redact_ide_episode(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a send-safe copy of an episode payload.

    Declared-sensitive args are stripped first (package redaction), then the
    secret scrub is applied ONLY to the free-text fields (goal, the principal's utterance,
    and steps), never to identifiers. Scrubbing the whole dict would corrupt ``run_id`` (its uuid
    tail clears the high-entropy gate), which the server keys its offer log and
    dedup on, silently breaking reinforce. ``run_id``/``thread_id``/
    ``source_framework``/``outcome`` are preserved verbatim. The input is not
    mutated.
    """
    redacted = dict(redact_episode_payload(payload))
    goal = redacted.get("goal")
    if isinstance(goal, str):
        redacted["goal"] = clip_goal(scrub_secrets(goal))
    utterance = redacted.get("principal_utterance")
    if isinstance(utterance, str):
        # Scrubbed but never clipped. A clipped goal costs some retrieval quality; a clipped
        # utterance becomes a frozen rule whose meaning a cut qualifier can reverse, so the
        # length decision is made at admission where it can refuse rather than truncate.
        redacted["principal_utterance"] = scrub_secrets(utterance)
    if isinstance(redacted.get("steps"), list):
        redacted["steps"] = scrub_strings(redacted["steps"], scrub_secrets)
    return redacted
