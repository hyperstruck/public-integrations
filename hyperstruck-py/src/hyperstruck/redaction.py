"""Client-side redaction, applied before any payload leaves the process.

Traces leave the customer's environment, so redaction happens here, not on our
side. Two layers:

1. **Declared-field strip.** Tool arguments the customer declared sensitive are
   replaced with a redaction marker, so their values never reach the platform.
2. **Known-value scrub.** Because the declared values are known exactly, every
   one is scrubbed from the entire outbound payload (including tool results and
   any model/AI text that echoed a literal secret), with a plain string replace.
   This catches the common echo case cheaply and with near-zero false positives.

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
from typing import Any

REDACTION_MARKER = "[REDACTED]"


def _labelled_marker(label: str) -> str:
    label = (label or "").strip()
    return f"[REDACTED:{label}]" if label else REDACTION_MARKER


def _collect_declared_values(steps: list[dict[str, Any]]) -> set[str]:
    """Gather the original values of every declared-sensitive argument."""
    values: set[str] = set()
    for step in steps:
        declared = (step.get("declared_sensitivity") or {}).get("args") or {}
        args = step.get("args") or {}
        for arg_name in declared:
            if arg_name in args and args[arg_name] is not None:
                rendered = str(args[arg_name])
                if rendered:
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


def _scrub_value(value: Any, pattern: re.Pattern[str]) -> Any:
    """Recursively replace every known secret with the marker in any string.

    Uses a single precompiled alternation so each string is scanned once,
    regardless of how many distinct secrets there are.
    """
    if isinstance(value, str):
        return pattern.sub(REDACTION_MARKER, value)
    if isinstance(value, dict):
        return {key: _scrub_value(item, pattern) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_value(item, pattern) for item in value]
    return value


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
        pattern = re.compile("|".join(re.escape(secret) for secret in secrets))
        redacted = _scrub_value(redacted, pattern)
    return redacted
