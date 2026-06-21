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

import math
import re
from typing import Any

from hyperstruck.ide.constants import MAX_RESULT_CHARS
from hyperstruck.redaction import (
    REDACTION_MARKER,
    redact_episode_payload,
    scrub_strings,
)

# Known credential shapes (the curated hot-path subset of the gitleaks /
# detect-secrets reference set), plus a generic long-token catch decided by
# entropy. One alternation, one pass per string.
#
# - ``known``: PEM private-key blocks, OpenAI ``sk-``/``sk_live_`` keys, Stripe
#   ``sk_/rk_ live|test`` keys, AWS ``AKIA`` keys, GitHub ``gh*_`` tokens, Slack
#   ``xox*`` tokens, and ``Bearer <token>`` headers.
# - ``kv``: a ``password=``/``token:``/``api_key=`` style assignment; the value is
#   redacted regardless of length or entropy, the key name is kept. This catches
#   short/structured secrets that the entropy gate would miss, e.g. in a shipped
#   command line or command output.
# - ``generic``: any 32+ char token of secret-shaped characters, redacted only
#   when its Shannon entropy clears the threshold (so ordinary identifiers and
#   prose survive, while random keys do not).
_SECRET_PATTERN = re.compile(
    r"(?P<known>"
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z]*PRIVATE KEY-----"
    r"|sk-[A-Za-z0-9_\-]{16,}"
    r"|[sr]k_(?:live|test)_[A-Za-z0-9]{10,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|(?i:bearer\s+[A-Za-z0-9._\-]{16,})"
    r")"
    r"|(?P<kv>(?i:(?:password|passwd|pwd|secret|secret[_-]?key|token|api[_-]?key|access[_-]?key|auth[_-]?token)\s*[:=]\s*)(?P<kvval>[^\s'\"]{4,}))"
    r"|(?P<generic>[A-Za-z0-9+/=_\-]{32,})"
)

# Minimum bits-of-entropy per character for a generic long token to count as a
# secret. Random base64/hex keys sit near their alphabet's ceiling; English prose
# and repetitive strings sit well below, so this lets identifiers through while
# catching keys. Hex hashes (e.g. commit SHAs) sit near 4.0 and are redacted;
# under the privacy-forward default that over-redaction is the accepted trade.
_ENTROPY_THRESHOLD = 3.5


def scrub_secrets(text: str) -> str:
    """Redact known credential shapes and high-entropy tokens from one string."""
    if not text:
        return text
    return _SECRET_PATTERN.sub(_replace, text)


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


def _replace(match: re.Match[str]) -> str:
    if match.group("known"):
        return REDACTION_MARKER
    if match.group("kv"):
        # Keep the "password=" key prefix, redact only the value.
        return match.group("kv")[: -len(match.group("kvval"))] + REDACTION_MARKER
    token = match.group("generic")
    return REDACTION_MARKER if _is_high_entropy(token) else token


def _is_high_entropy(token: str) -> bool:
    """Shannon entropy (bits/char) of a token, against the secret threshold."""
    if len(token) < 32:
        return False
    counts: dict[str, int] = {}
    for char in token:
        counts[char] = counts.get(char, 0) + 1
    length = len(token)
    entropy = -sum((c / length) * math.log2(c / length) for c in counts.values())
    return entropy >= _ENTROPY_THRESHOLD
