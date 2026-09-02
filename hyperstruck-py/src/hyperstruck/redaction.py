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

import ipaddress
import logging
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Tiered free-text detector (secrets + validated structured PII)
# ---------------------------------------------------------------------------
#
# The declared-field model above needs the customer to mark which arguments are
# sensitive. A host that hands us free-form text (an MCP host's goal, a tool
# result) declares nothing, so free text gets a layered detector instead. The
# tiers, in order of how catastrophic a miss is:
#
#   Tier 1 (default ON, pure stdlib): secrets first (the catastrophic case),
#     then validated structured PII. Secrets use known credential shapes plus a
#     Shannon-entropy gate; PII is validated (Luhn, IBAN mod-97, parseable IP),
#     not bare regex, so precision stays high. Each detection becomes a tagged
#     placeholder (``<SECRET_1>``, ``<EMAIL_1>``) so the text shape the model
#     reasons over survives.
#   Tier 2 (opt-in): a NER pass for names/addresses/orgs (exactly what regex
#     cannot do). Lazy and graceful: an absent backend falls back to Tier 1 with
#     a warning, never a crash, so the ~500MB model stays a deliberate extra.
#   Tier 3 (a hook, not a dependency): a customer-supplied *local* model. We
#     never ship a tier that sends data to a third-party LLM to decide what not
#     to send.

# Credential-bearing key/name fragments, the single source of truth shared by the
# in-string ``key=value`` rule below and the structured sensitive-key detector, so
# the two cannot drift. ``_`` stands for an optional ``_``/``-`` separator.
_SECRET_KEY_WORDS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "secret_key",
    "client_secret",
    "token",
    "api_key",
    "access_key",
    "auth_token",
    "refresh_token",
    "session_token",
    "credential",
    "passphrase",
    "private_key",
    "authorization",
)

# Regex alternation form (``api_key`` -> ``api[_-]?key``) for the in-string rule.
_KEY_NAME_ALTERNATION = "|".join(w.replace("_", "[_-]?") for w in _SECRET_KEY_WORDS)

# Separator-stripped fragments for substring-matching a structured key name.
_NORMALISED_SECRET_FRAGMENTS = tuple(w.replace("_", "") for w in _SECRET_KEY_WORDS)


def _is_sensitive_key(key: str) -> bool:
    """Whether a structured key name designates a credential, by fragment match.

    Matches the sensitive word anywhere in a normalised (lowercased, separator-
    stripped) key, so namespaced spellings like ``db_password``, ``access_token``,
    ``client_secret``, and ``openai_api_key`` are caught, not only exact names. Over-
    matching (``tokenizer`` reads as sensitive) is the accepted privacy-forward trade.
    """
    collapsed = key.lower().replace("_", "").replace("-", "")
    return any(fragment in collapsed for fragment in _NORMALISED_SECRET_FRAGMENTS)


# Known credential shapes: the curated hot-path subset of the gitleaks /
# detect-secrets reference set. Shared, so the scrubber and the identifier-safe
# detector below cannot drift on what counts as a credential by construction.
#
# Two shapes are held apart because ordinary words produce their prefixes. Both
# key on a word ending in "sk" or "rk": "risk-", "task-" and "desk-" give
# sk-[A-Za-z0-9_-]{16,}, and "risk_live_monitoring_dashboard" and
# "desk_test_automation_pipeline" give [sr]k_(live|test)_[A-Za-z0-9]{10,} (the
# tail must reach 10 characters, so "desk_test_run" does not). Only these need a
# token boundary to stay usable on identifiers; the rest have prefixes no English
# word yields.
_PRIVATE_KEY_BLOCK = (
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z]*PRIVATE KEY-----"
)
_WORD_AMBIGUOUS_SHAPES = (
    r"sk-[A-Za-z0-9_\-]{16,}|[sr]k_(?:live|test)_[A-Za-z0-9]{10,}"
)
# Each length floor is the real credential's, not a round number: a shape loose
# enough to admit a descriptive identifier refuses legitimate work, which on the
# identifier path is the expensive direction. `SG.` additionally takes a token
# boundary, being the one added prefix short enough to end an ordinary word
# ("MSG.", "OSG."). `AIza` is open-ended rather than exactly 35 so a longer
# lookalike redacts whole instead of leaving its tail behind.
_DISTINCT_SHAPES = (
    r"AKIA[0-9A-Z]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{50,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|AIza[0-9A-Za-z_\-]{35,}"
    r"|ya29\.[0-9A-Za-z_\-]{20,}"
    r"|eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"
    r"|(?<![A-Za-z0-9])SG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{30,}"
    r"|hf_[A-Za-z0-9]{30,}"
    r"|npm_[A-Za-z0-9]{30,}"
    r"|(?i:bearer\s+[A-Za-z0-9._\-]{16,})"
)
_KNOWN_CREDENTIAL_SHAPES = (
    _PRIVATE_KEY_BLOCK + r"|" + _WORD_AMBIGUOUS_SHAPES + r"|" + _DISTINCT_SHAPES
)

# The key and the value may each be quoted, which is what a stringified JSON or
# YAML fragment in a tool error looks like. Without those alternatives the rule
# needed `[:=]` immediately after the key word and a value that started with a
# non-quote, so `password: "hunter2000"` and `{"password": "hunter2000"}` matched
# nothing here and, being short, nothing in the entropy arm either.
#
# The quoted value excludes newlines and its closing quote is optional. Both
# matter on a clipped stderr, which is what this hook ships. Without the newline
# bound a quoted value runs to the next quote lines away, taking the failure
# detail the step exists to carry; without the optional close, an unterminated
# quote (the shape clipping produces) matched nothing and leaked the value whole.
#
# TODO(ceiling): the optional close means a quoted literal ENDING in the separator
# ("token=", "api_key=") has its closing quote read as an opening one, so the
# redaction runs to end of line. Measured at 4 lines in 217,701, all of them this
# module's own comments and tests. Over-redaction only, and bounded to one line.
# Re-requiring the close is the only narrowing available and it reinstates the
# leak, so this stands until a value carries enough context to tell the two
# apart.
_KEY_VALUE_RULE = (
    r"(?P<kv>(?i:[\"']?(?:" + _KEY_NAME_ALTERNATION + r")[\"']?\s*[:=]\s*)"
    r"(?P<kvval>\"[^\"\r\n]{4,}\"?|'[^'\r\n]{4,}'?|[^\s'\"]{4,}))"
)

_SECRET_PATTERN = re.compile(
    r"(?P<known>" + _KNOWN_CREDENTIAL_SHAPES + r")"
    r"|" + _KEY_VALUE_RULE + r"|(?P<generic>[A-Za-z0-9+/=_\-]{32,})"
)

# The same shapes with no generic arm, for judging an identifier. Dropping the
# generic arm is what lets a known shape match at an inner offset at all: in the
# combined pattern above it swallows the whole token first, so an embedded
# credential is never reached.
#
# The token boundary is applied per shape rather than to the whole alternation,
# because a blanket boundary and no boundary are both wrong. A blanket one misses
# a credential glued to preceding characters; none refuses "risk-management-review"
# and every other ordinary word ending in "sk" or "rk".
#
# A key name also starts wherever it begins with a capital, not only after a
# delimiter. Requiring a delimiter alone would accept "myPassword=hunter2000",
# "DBPASSWORD=hunter2000" and "XPassword=hunter2000", all of which the scrubber
# catches; that is under-detection in the direction that egresses a secret.
# Keying on the capital rather than on a lowercase-to-uppercase hump is what
# covers the all-caps and uppercase-preceded spellings. Allowing any preceding
# character instead would refuse "notatoken=abcd" for merely containing "token".
#
# TODO(ceiling): the all-lowercase glued spelling ("mytoken=hunter2000",
# "thepassword=hunter2000") is therefore accepted, though the scrubber catches it.
# It is the price of not refusing "notatoken=abcd", and unlike the shape ceiling
# above it cannot be split by capitalisation. Revisit alongside a declared run-id
# format. Note the delimiter test is ASCII-only, so a non-ASCII letter reads as a
# delimiter: "cafétoken:abcd1234" is refused where "übertoken:abcd1234" is not.
_CREDENTIAL_KEY_START = r"(?:(?<![A-Za-z0-9])|(?=[A-Z]))"

# TODO(ceiling): a word-ambiguous credential glued directly to letters
# ("xxsk-AbCdEf0123456789", "myrk_live_ABCDEFGHIJ") is still accepted, because it
# is indistinguishable from "risk-management-review-2026-08" without knowing which
# is intended. The same ambiguity refuses a descriptive id that genuinely starts
# "sk-". Revisit if run ids ever carry a declared format, which settles it by
# construction.
_KNOWN_CREDENTIAL_PATTERN = re.compile(
    _PRIVATE_KEY_BLOCK
    + r"|" + _DISTINCT_SHAPES
    + r"|(?<![A-Za-z0-9])(?:" + _WORD_AMBIGUOUS_SHAPES + r")"
    + r"|" + _CREDENTIAL_KEY_START + r"(?:" + _KEY_VALUE_RULE + r")"
)

# Minimum bits-of-entropy per character for a generic long token to count as a
# secret. This does NOT separate keys from identifiers:
# "sk-proj-AbCdEf0123456789AbCdEf0123456789AbCdEf" measures 4.43 bits/char and
# "the quick brown fox jumps over the lazy dog" measures 4.39. Prose
# is spared only because the generic character class excludes whitespace, so prose
# is never one 32+ char token. A hyphen-joined identifier has no whitespace either
# and so is always caught, which is harmless when flattening free text and wrong
# for an identifier. Identifiers use known_credential_match instead.
_ENTROPY_THRESHOLD = 3.5


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


def scrub_secrets(
    text: str,
    replacement: Callable[[str], str] = lambda _: REDACTION_MARKER,
) -> str:
    """Redact known credential shapes and high-entropy tokens from one string.

    ``replacement`` maps a detected secret to the text that replaces it, so the
    same detector backs both the bare-marker adapters (the IDE) and the tagged-
    placeholder path (an MCP host), without duplicating the patterns.
    """
    if not text:
        return text

    def _sub(match: re.Match[str]) -> str:
        if match.group("known"):
            return replacement(match.group("known"))
        if match.group("kv"):
            # Keep the "password=" key prefix, redact only the value.
            value = match.group("kvval")
            return match.group("kv")[: -len(value)] + replacement(value)
        token = match.group("generic")
        return replacement(token) if _is_high_entropy(token) else token

    return _SECRET_PATTERN.sub(_sub, text)


def known_credential_match(text: str) -> str | None:
    """The credential of a *recognised shape* inside ``text``, or ``None``.

    Returns the matched substring rather than a bool so a caller refusing on it can
    say what it objected to. Callers must not echo the return value into a message
    or a log; it is the suspect text itself.

    The same detector as :func:`scrub_secrets` minus its generic entropy arm, for
    callers that must judge an **identifier** rather than free text. Scrubbing may
    flatten a false positive harmlessly; refusing one blocks legitimate work, and
    the entropy arm cannot tell an identifier from a key (see
    :data:`_ENTROPY_THRESHOLD`), so it is excluded here rather than re-tuned.

    Matches only a shape that is a credential by construction: a private key
    block, a provider-prefixed token, or a ``password=``-style key/value pair.

    Deliberately stricter than the scrubber on the key/value rule: here it must
    start at a token boundary, so ``notatoken=abcd`` is not a credential merely for
    containing "token". The scrubber keeps the looser rule on purpose, because
    over-redacting free text costs nothing while under-redacting leaks.
    """
    if not text:
        return None
    match = _KNOWN_CREDENTIAL_PATTERN.search(text)
    return match.group(0) if match else None


# Validated structured-PII detectors. Each regex is a candidate finder; a
# validator (Luhn, IBAN mod-97, a parseable IP) decides whether the candidate is
# real, so ordinary numbers and identifiers are not corrupted.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_CARD_RE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Za-z0-9]{11,30}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_IPV4_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_IPV6_RE = re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b")
# Dot is deliberately excluded as a phone separator: a dotted decimal is far more
# likely an invalid IP or a version string than a phone number, and matching it
# would corrupt those. The common phone separators (space, parens, dash) stay.
_PHONE_RE = re.compile(r"\+?\d(?:[\d()\- ]{5,})\d")


def _digits(text: str) -> str:
    return "".join(ch for ch in text if ch.isdigit())


def _luhn_ok(digits: str) -> bool:
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, ch in enumerate(reversed(digits)):
        value = int(ch)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _iban_ok(candidate: str) -> bool:
    rearranged = candidate[4:] + candidate[:4]
    numeric = "".join(str(int(ch, 36)) if ch.isalpha() else ch for ch in rearranged)
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def _is_ip(candidate: str) -> bool:
    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False


def _phone_ok(candidate: str) -> bool:
    digits = _digits(candidate)
    if not 7 <= len(digits) <= 15:
        return False
    # A bare run of digits is ambiguous (an id, a quantity), so require a leading
    # ``+``, an internal separator, or enough digits to read unambiguously as a
    # number, keeping precision high on free text.
    return (
        candidate.lstrip().startswith("+")
        or any(sep in candidate for sep in " ().-")
        or len(digits) >= 10
    )


def _redact_structured_pii(text: str, allocator: _PlaceholderAllocator) -> str:
    """Replace validated structured PII with tagged placeholders.

    Order matters: the denser, validator-gated kinds (IBAN, card, SSN, IP) run
    before the looser ones (email, phone), and each replacement leaves an
    angle-bracketed placeholder a later pass cannot re-match, so the kinds do not
    fight over the same span.
    """

    def _gate(kind: str, ok: Callable[[str], bool]) -> Callable[[re.Match[str]], str]:
        def _sub(match: re.Match[str]) -> str:
            token = match.group()
            return allocator.placeholder(kind, token) if ok(token) else token

        return _sub

    text = _IBAN_RE.sub(_gate("IBAN", _iban_ok), text)
    text = _CARD_RE.sub(_gate("CARD", lambda t: _luhn_ok(_digits(t))), text)
    text = _SSN_RE.sub(_gate("SSN", lambda _t: True), text)
    text = _IPV6_RE.sub(_gate("IP", _is_ip), text)
    text = _IPV4_RE.sub(_gate("IP", _is_ip), text)
    text = _EMAIL_RE.sub(_gate("EMAIL", lambda _t: True), text)
    text = _PHONE_RE.sub(_gate("PHONE", _phone_ok), text)
    return text


class _PlaceholderAllocator:
    """Allocates stable, numbered placeholders per kind within one redaction.

    The same value maps to the same placeholder, so a secret echoed twice reads
    as one entity to the model rather than two, and the text shape survives.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._seen: dict[tuple[str, str], str] = {}

    def placeholder(self, kind: str, value: str) -> str:
        cached = self._seen.get((kind, value))
        if cached is not None:
            return cached
        count = self._counts.get(kind, 0) + 1
        self._counts[kind] = count
        tag = f"<{kind}_{count}>"
        self._seen[(kind, value)] = tag
        return tag


@dataclass(frozen=True)
class RedactionPolicy:
    """How aggressively to scrub free text before it leaves the process.

    Tier 1 (secrets + structured PII) is always on. ``is_ner_enabled`` turns on
    the optional Tier-2 names/addresses pass; ``ner_hook`` and
    ``local_model_hook`` let a customer plug their own Tier-2 backend or a Tier-3
    *local* model. ``is_transmission_disabled`` is the deployment-level "do not
    learn" switch the caller honours before any egress.
    """

    is_ner_enabled: bool = False
    ner_hook: Callable[[str], str] | None = None
    local_model_hook: Callable[[str], str] | None = None
    is_transmission_disabled: bool = False


_NER_WARNED = False


def _apply_ner(text: str, policy: RedactionPolicy) -> str:
    """Apply the optional Tier-2 NER pass via a customer-supplied hook.

    The package ships no NER backend: the names/addresses tier is a hosted,
    entitlement-gated feature, so the open SDK only honours a ``ner_hook`` a
    deployment supplies itself. Without one the text falls through Tier 1 unchanged
    with a one-time warning.
    """
    if policy.ner_hook is not None:
        return policy.ner_hook(text)
    global _NER_WARNED
    if not _NER_WARNED:
        logger.warning(
            "NER redaction requested but no ner_hook is set; falling back to the "
            "zero-dependency tier. The names/addresses tier is a hosted feature."
        )
        _NER_WARNED = True
    return text


def redact_text(
    text: str,
    *,
    policy: RedactionPolicy | None = None,
    allocator: _PlaceholderAllocator | None = None,
) -> str:
    """Scrub one free-text string: Tier 1, then optional Tier 2 and Tier 3.

    Secrets are scrubbed first (the catastrophic miss), then validated structured
    PII, both to tagged placeholders. The optional NER and local-model tiers run
    last so they refine, never replace, the zero-dependency floor.
    """
    if not text:
        return text
    policy = policy or RedactionPolicy()
    allocator = allocator or _PlaceholderAllocator()
    text = scrub_secrets(text, lambda value: allocator.placeholder("SECRET", value))
    text = _redact_structured_pii(text, allocator)
    if policy.is_ner_enabled:
        text = _apply_ner(text, policy)
    if policy.local_model_hook is not None:
        text = policy.local_model_hook(text)
    return text


# Keys whose string values are identifiers, not free text: scrubbing them would
# corrupt the correlation handles the boundary keys its offer log and idempotency
# on (a run id's uuid tail clears the entropy gate), so they pass through verbatim.
_IDENTIFIER_KEYS = frozenset(
    {"run_id", "thread_id", "source_framework", "id", "status"}
)


def redact_free_text(
    payload: Any,
    *,
    policy: RedactionPolicy | None = None,
    preserve_keys: frozenset[str] = _IDENTIFIER_KEYS,
    allocator: _PlaceholderAllocator | None = None,
) -> Any:
    """Scrub every free-text string in a payload, preserving identifier keys.

    A key-aware walk: an identifier key passes through verbatim; a value under a
    sensitive key name (``api_key``, ``db_password``, ...) is redacted whole, since a
    structured payload hides it from the in-string secret rule; every other string
    runs through :func:`redact_text`. Sensitivity propagates down the whole subtree
    under a sensitive key, through both dicts and lists, so a secret nested as
    ``{"credential": {"value": "..."}}`` is caught too. One allocator is shared so a
    value echoed in two places reads as one entity. The traversal is iterative (an
    explicit stack), not recursive, so an arbitrarily deep host payload cannot raise
    ``RecursionError`` on the write path. The input is not mutated.
    """
    policy = policy or RedactionPolicy()
    allocator = allocator or _PlaceholderAllocator()

    def _leaf(value: Any, key: str | None, sensitive: bool) -> Any:
        if not isinstance(value, str):
            return value
        if sensitive:
            return allocator.placeholder("SECRET", value)
        if key in preserve_keys:
            return value
        return redact_text(value, policy=policy, allocator=allocator)

    def _is_sensitive(key: Any, inherited: bool) -> bool:
        return inherited or (isinstance(key, str) and _is_sensitive_key(key))

    if not isinstance(payload, (dict, list, tuple)):
        return _leaf(payload, None, False)

    root: Any = {} if isinstance(payload, dict) else []
    # Each work item rebuilds one container; a list's children inherit the key (and
    # sensitivity) of the value the list itself sits under, and sensitivity carries
    # down into nested dicts as well, so a whole credential subtree is redacted.
    stack: list[tuple[Any, str | None, Any, bool]] = [(payload, None, root, False)]
    while stack:
        source, ctx_key, target, sensitive = stack.pop()
        pairs = (
            source.items()
            if isinstance(source, dict)
            else ((ctx_key, item) for item in source)
        )
        for key, item in pairs:
            child_sensitive = _is_sensitive(key, sensitive)
            if isinstance(item, dict):
                child: Any = {}
                stack.append((item, key, child, child_sensitive))
            elif isinstance(item, (list, tuple)):
                child = []
                stack.append((item, key, child, child_sensitive))
            else:
                child = _leaf(item, key, child_sensitive)
            if isinstance(target, dict):
                target[key] = child
            else:
                target.append(child)
    return root
