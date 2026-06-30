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
"""

from __future__ import annotations

from typing import Any

from hyperstruck.ide.constants import MAX_RESULT_CHARS
from hyperstruck.redaction import (
    redact_episode_payload,
    scrub_secrets,
    scrub_strings,
)

# ``scrub_secrets`` is owned by the shared redaction module and only used here; it
# is deliberately not re-exported (import it from ``hyperstruck.redaction``).
__all__ = [
    "clip_result",
    "redact_ide_episode",
]


def clip_result(value: Any) -> Any:
    """Clip a tool result to the size ceiling so no large body is ever shipped.

    A string is truncated with an explicit marker; a non-string is rendered to a
    string first (its repr may carry detail, so it is clipped the same way). This
    is the last line against a raw file body sneaking through a tool result.
    """
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    if len(text) <= MAX_RESULT_CHARS:
        return text
    return text[:MAX_RESULT_CHARS] + " [TRUNCATED]"


def redact_ide_episode(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a send-safe copy of an episode payload.

    Declared-sensitive args are stripped first (package redaction), then the
    secret scrub is applied ONLY to the free-text fields (goal and steps), never
    to identifiers. Scrubbing the whole dict would corrupt ``run_id`` (its uuid
    tail clears the high-entropy gate), which the server keys its offer log and
    dedup on, silently breaking reinforce. ``run_id``/``thread_id``/
    ``source_framework``/``outcome`` are preserved verbatim. The input is not
    mutated.
    """
    redacted = dict(redact_episode_payload(payload))
    goal = redacted.get("goal")
    if isinstance(goal, str):
        redacted["goal"] = scrub_secrets(goal)
    if isinstance(redacted.get("steps"), list):
        redacted["steps"] = scrub_strings(redacted["steps"], scrub_secrets)
    return redacted
