"""Client-side redaction, applied before any payload leaves the process.

Traces leave the customer's environment, so redaction happens here, not on our
side. Two layers:

1. **Declared-field strip.** Tool arguments the customer declared sensitive are
   replaced with a redaction marker, so their values never reach the platform.
2. **Known-value scrub.** Because the declared values are known exactly, every
   one is scrubbed from the entire outbound payload (including tool results and
   any model/AI text that echoed a literal secret), at any nesting depth. The
   scrub matches each value only as a whole token (non-word lookarounds), and
   skips values shorter than ``MIN_SCRUB_LENGTH``, so a short or common declared
   value does not corrupt unrelated content. The tradeoff of whole-token matching
   is in the catch-the-echo direction: a declared value the *declared argument
   already strips* is also caught wherever it appears as a standalone token, but
   an echo that concatenates the value to other word characters (e.g. the secret
   glued inside a larger identifier) is left intact rather than corrupting it. The
   declared argument itself is always stripped regardless.

What is and is not redacted here, for integrators: only *declared* sensitive
argument values are stripped, and only those exact values are scrubbed elsewhere.
Tool **results** and **errors** (and the free-text goal) are NOT scanned for
undeclared PII a tool may have fetched (e.g. a lookup tool returning an SSN it
was never passed); such content is sent to the platform, which applies a
heuristic redaction floor to undeclared fields server-side. General
data-loss-prevention scanning of undeclared secrets is out of scope client-side.
To keep a value off the platform entirely, declare the argument carrying it.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

REDACTION_MARKER = "[REDACTED]"

# Minimum length for a declared value to be scrubbed across the whole payload. A
# one-character value (``"1"``, ``"a"``) scrubbed everywhere corrupts unrelated
# content, so values shorter than this are still stripped from their own declared
# argument but never scrubbed elsewhere. Mirrors Core's server-side floor.
MIN_SCRUB_LENGTH = 2


def _labelled_marker(label: str) -> str:
    label = (label or "").strip()
    return f"[REDACTED:{label}]" if label else REDACTION_MARKER


def _collect_declared_values(steps: list[dict[str, Any]]) -> set[str]:
    """Gather declared-sensitive argument values long enough to scrub elsewhere.

    Values shorter than :data:`MIN_SCRUB_LENGTH` are excluded: they are still
    stripped from their own declared argument, but scrubbing a one-character value
    across the whole payload would corrupt unrelated content.
    """
    values: set[str] = set()
    for step in steps:
        declared = (step.get("declared_sensitivity") or {}).get("args") or {}
        args = step.get("args") or {}
        for arg_name in declared:
            if arg_name in args and args[arg_name] is not None:
                rendered = str(args[arg_name])
                if len(rendered) >= MIN_SCRUB_LENGTH:
                    values.add(rendered)
    return values


def _strip_declared_args(steps: list[dict[str, Any]]) -> None:
    """Replace each declared-sensitive argument value with its marker, in place."""
    for step in steps:
        declared = (step.get("declared_sensitivity") or {}).get("args") or {}
        args = step.get("args")
        if not isinstance(args, dict):
            continue
        for arg_name, label in declared.items():
            if arg_name in args and args[arg_name] is not None:
                args[arg_name] = _labelled_marker(label)


def scrub_strings(value: Any, replace: Callable[[str], str]) -> Any:
    """Apply ``replace`` to every string in a payload, at any depth.

    The traversal is iterative (an explicit work stack), not recursive, so an
    arbitrarily deep payload is fully processed without a depth cap and cannot
    raise ``RecursionError`` into the host's run. Tuples become lists, matching
    JSON serialisation. ``replace`` runs only on strings; other scalars pass
    through untouched.

    Exposed so other adapters can layer their own string scrub (e.g. the IDE
    adapter's secret-pattern pass) over the same safe traversal rather than
    reinventing it.
    """
    if isinstance(value, str):
        return replace(value)
    if not isinstance(value, (dict, list, tuple)):
        return value

    def _scalar(item: Any) -> Any:
        return replace(item) if isinstance(item, str) else item

    root: Any = {} if isinstance(value, dict) else []
    # Each work item rebuilds one container into its pre-created shell.
    stack: list[tuple[Any, Any]] = [(value, root)]
    while stack:
        source, target = stack.pop()
        pairs = source.items() if isinstance(source, dict) else enumerate(source)
        for key, item in pairs:
            if isinstance(item, dict):
                child: Any = {}
                stack.append((item, child))
            elif isinstance(item, (list, tuple)):
                child = []
                stack.append((item, child))
            else:
                child = _scalar(item)
            if isinstance(target, list):
                target.append(child)
            else:
                target[key] = child
    return root


def _scrub_value(value: Any, pattern: re.Pattern[str]) -> Any:
    """Replace every known secret with the marker in any string, at any depth.

    Uses a single precompiled alternation so each string is scanned once,
    regardless of how many distinct secrets there are.
    """
    return scrub_strings(value, lambda s: pattern.sub(REDACTION_MARKER, s))


def redact_episode_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted copy of an episode payload, safe to send.

    Declared-sensitive arguments are stripped to markers, then their exact values
    are scrubbed everywhere else in the payload. The input is not mutated.
    """
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    # Work on a deep-ish copy of steps so the caller's episode is untouched.
    steps_copy = [dict(step) for step in steps]
    for step in steps_copy:
        if isinstance(step.get("args"), dict):
            step["args"] = dict(step["args"])

    secrets = sorted(_collect_declared_values(steps_copy), key=len, reverse=True)
    _strip_declared_args(steps_copy)

    redacted = dict(payload)
    redacted["steps"] = steps_copy
    if secrets:
        # Longest-first alternation so a longer secret wins over a shorter prefix.
        # Each secret is fenced by non-word lookarounds so it matches only as a
        # whole token: a value like "25" does not corrupt "1250".
        alternation = "|".join(re.escape(secret) for secret in secrets)
        pattern = re.compile(rf"(?<!\w)(?:{alternation})(?!\w)")
        redacted = _scrub_value(redacted, pattern)
    return redacted
