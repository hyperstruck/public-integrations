"""The shape of a failure, as an operand a rule can actually fire on.

A gate predicate is an equality test frozen onto a learned rule, so its operand has to be a
value that occurs again. Everything obvious fails that, and each fails it differently.

A **status** is true of every failure of a tool, so a gate on it never discriminates. An
**exit status** looked better and is not: measured over 1,181 real failures carrying one,
86.3% were ``1``, meaning no more than "something went wrong". Claude Code also puts an exit
status nowhere a hook can read (0 of 35,981 tool results carry one under any name), so on
that host it does not exist at all. The **raw error text** fails the other way: unbounded and
near-unique, it is a dead gate and a quasi-identifier at once, because an equality test can
never match a free-text string twice and the string carries paths and values.

**Position was the answer for a long time and was wrong every time.** The rule read an
identifier off the first line, or the last, or the line after the host's frame, and each
variant returned an internal hostname, a username and an environment variable name for
ordinary input. The reason is the same in every case: a host saying "an error is reported in
here" is not the host saying "the failing program's name is this token", and
``[A-Za-z0-9_.-]+`` is equally the shape of a username, a hostname and an environment
variable name. No content rule separates them either, because ``ModuleNotFoundError: No
module named x`` and ``tlynch: permission denied`` are the same string shape, and anything
that told them apart by meaning would be a lexicon.

**Provenance replaces position.** What licenses a read is a grammar that names the author of
the text before anything is read out of it, which is the recognizer discipline of Sassaman,
Patterson, Bratus & Locasto, "Security Applications of Formal Language Theory" (IEEE Systems
Journal, 2013): accept only what a recognizer for the known language accepts, and never
salvage the remainder heuristically. Three tiers follow from it.

    Exit code 1                              <- an envelope, not an author
    Traceback (most recent call last):       <- CPython's published banner
      File "app.py", line 1, in <module>
    ModuleNotFoundError: No module named 'x'
    -> ModuleNotFoundError                      (tier 2, a language runtime)

    <tool_use_error>File has not been read yet. Read it first before writing to it.
    -> File has not been read yet               (tier 1, the host's own message)

    Error: tlynch: permission denied
    -> nothing                                  (tier 3, the program's own output)

Tier 3 is the load-bearing one. When a frame consumes the whole line, the next line is the
program's own output, and the rule abstains rather than spilling into it. There is no lower
tier that takes a leading token from an unlicensed line: measured, spilling buys 15 points of
coverage whose discriminating operands are bare tool names, while a sibling variant sent a
line of the operator's own source as a gate operand.

**A host message is masked, a language name is not.** The host composes its messages from a
fixed vocabulary, so what varies inside one is a path or a value and is replaced by a mask;
what remains recurs across machines. A language runtime's error name is already the
class-name-shaped identifier, and never the message, so ``KeyError: 'secret-tenant-id'``
yields ``KeyError``.

**What this module does NOT do, stated because two rounds of review found it claiming
otherwise.** It does not sanitise. A username, an internal hostname and an environment
variable name are the same shape as an ordinary word and as an exception class name:
``tlynch`` against ``KeyError``, ``bastion`` against ``blocked``. Three rules were tried here
and each closed its cited cases and left the class open, because safety is not a property of
the string. It is a property of the population: ``KeyError`` appears across thousands of runs
and many tenants, ``tlynch`` appears in one operator's. A single observation does not carry
that difference, and a rule that separated them by meaning would be a lexicon.

**What bounds them is the boundary's support floors**, which are a k-anonymity mechanism
(Sweeney, "k-Anonymity: A Model for Protecting Privacy", IJUFKS 2002): an operand is frozen
onto a rule only after 5 distinct runs produce it, and the rule carrying it stays
agent-specific until 20 distinct **tenants** have produced it. A value belonging to one
operator never clears the second, so it is never shared.

**Tenants, and the distinction is load-bearing rather than pedantic.** Contract version 1
counted agents, and an agent-counted floor does not bound a single customer at all: delegation
mints a child agent id per delegation instance under the delegating agent's own organisation,
so one customer delegating to itself manufactures unbounded distinct agents and clears any
agent floor alone. Version 2 counts tenants for exactly that reason. Read the floor from the
vendored contract rather than from memory of which unit it used; the two versions read almost
identically and mean opposite things about one operator's data.

The number itself was calibrated when the unit was agents, so it is inherited rather than
measured for tenants. Counting tenants is strictly stricter, so it errs safe.

The residual is that these values are *stored* regardless, which is Core's to close and not
this module's.

Nothing here judges meaning. The tiers are structural patterns over published formats, and a
language absent from the table costs coverage on that language rather than flipping a verdict.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from enum import StrEnum
from math import log2

from hyperstruck.ide.language_anchors import anchored_name

# This runs in a per-tool-call subprocess on unclipped raw output, so an unbounded scan would
# put a multi-megabyte ``cat`` between the user and their next keystroke. The character bound
# is what prevents that, and it is the only bound needed.
#
# A separate 20-LINE cap used to sit here and was removed: a language block ends with its
# exception line, so capping lines amputated exactly the part that carries the name. A
# traceback of six frames or more runs past twenty lines, and every one of them abstained.
MAX_SCANNED_CHARS = 4096

# Enough to be a name rather than punctuation left over from stripping.
MIN_SIGNATURE_LETTERS = 2

# A period ending a sentence, rather than one inside a version, a filename or a dotted
# attribute path. The lookbehind is the whole trick: it keeps ``v1.2.3``, ``__init__.py``
# and ``Object.assign`` intact, because none of them puts a lowercase letter, a closing
# paren or a closing bracket immediately before a period that whitespace then follows.
# Abbreviations are out of scope: a host protocol message does not contain them.
_SENTENCE_END = re.compile(r"(?<=[a-z)\]])\.(?:\s|$)")

# What a word is replaced by when the vendored word pattern refuses it. Matches the mask
# shape the boundary's own phrase pattern admits.
_MASK = "<*>"

# A word of a host's own prose. A word carrying a dot or an underscore is an identifier, so a
# dotted hostname, a module path and an environment variable name are masked where the
# boundary's own word pattern would admit them.
#
# **This narrows the leak, it does not close it**, and no rule here can. An undotted bare
# token is the same shape as an ordinary word: ``bastion``, ``PGPASSWORD`` and ``tlynch`` are
# indistinguishable from ``blocked``, ``PERMISSION`` and ``missing`` by anything structural,
# and separating them by meaning would be a lexicon. See the module docstring for what
# actually bounds them.
#
# There is deliberately no alternative admitting an angle-bracketed token. One was tried and
# it passed ``<secret.txt>`` through untouched, because it was written to preserve the mask
# rather than to describe prose, and the mask is inserted after this test rather than read by
# it.
_IS_PROSE_WORD = re.compile(r"^(?:[A-Za-z][A-Za-z-]*|[0-9]+)$")


class ProvenanceTier(StrEnum):
    """Who authored the text a name would be read out of.

    The tier is decided before anything is read, and it is the tier rather than the shape of
    what was found that licenses an emit. A tier is withdrawn by removing the grammar that
    matches it, so an unlicensed result yields no candidate at all rather than a candidate
    someone downstream has to remember to refuse.
    """

    HOST_MESSAGE = "host_message"
    LANGUAGE_RUNTIME = "language_runtime"
    UNLICENSED = "unlicensed"


def failure_signature(
    text: str,
    host_framing: tuple[str, ...] = (),
    *,
    shape: Mapping[str, object] | None = None,
) -> tuple[ProvenanceTier, str | None]:
    """The failure's name and the provenance that licenses reading it.

    ``host_framing`` is the host's *own protocol* prefixes, which is a narrower set than the
    generic framing a host wraps any failed result in. ``Error:`` and ``Exit code N`` are
    envelopes around whatever the program printed, so what follows them is the program's own
    text and belongs to no tier; the two protocol frames introduce messages the host itself
    composed from a fixed vocabulary.

    Returns the tier alongside the candidate so the emit decision stays outside this module:
    a candidate under :attr:`ProvenanceTier.UNLICENSED` is never a value to send, and the
    caller refuses it rather than this function pretending it found nothing.
    """
    lines = _scanned(text)
    if not lines:
        return ProvenanceTier.UNLICENSED, None
    # The language tier is tried first because its grammar is the stronger claim: it names an
    # author, where a host frame only names an envelope. A host protocol message does not
    # carry a traceback banner and a frame run, so this costs nothing on the common path; what
    # it fixes is a host-framed traceback, which used to be cut and masked as prose and lose
    # the exception name the block was actually about.
    name = anchored_name(lines)
    if name is not None:
        return ProvenanceTier.LANGUAGE_RUNTIME, _admissible(name, shape)
    message = _host_message(lines[0], host_framing)
    if message is not None:
        return ProvenanceTier.HOST_MESSAGE, _phrase(message, shape)
    return ProvenanceTier.UNLICENSED, None


def _scanned(text: str) -> list[str]:
    return [
        line
        for line in (text or "")[:MAX_SCANNED_CHARS].splitlines()
        if line.strip()
    ]


def _host_message(first: str, host_framing: tuple[str, ...]) -> str | None:
    """What the host said after its own protocol frame, if it said anything.

    The frame leads the result or it is not the envelope, so this reads the first line and
    nothing else: scanning every line for a frame lets a tool's own output supply one, and
    ``some output\\nError: bastion.corp: down`` would then yield the hostname.

    **A frame consuming the whole line is not a match.** Claude Code leads a failed Bash
    result with ``Exit code 1`` as the entire first line, so stripping the frame leaves an
    empty string and the old rule returned ``None`` before ever reaching the error on line
    two. Requiring a non-empty remainder is what stops the empty case from being read as a
    host message, and what sends that result to the language tier instead, where its
    traceback is actually readable.
    """
    line = first.strip()
    for prefix in host_framing:
        try:
            remainder = re.sub(prefix, "", line).strip()
        except re.error:
            # A frame table is code rather than contract data, so a bad pattern here is a
            # packaging fault like any other. It still must not raise: this runs inside a hook
            # that fails open, so the exception would cost the episode and surface nowhere.
            continue
        if remainder != line and remainder:
            return remainder
    return None


def _phrase(message: str, shape: Mapping[str, object] | None) -> str | None:
    """A host message reduced to a template that recurs, or nothing usable.

    Cut at the first sentence, then mask by refusal: every word the boundary's own word
    pattern rejects becomes a mask. Deterministic, stateless and machine-independent, so the
    same failure yields a byte-identical operand on every machine, which is what the
    boundary's support floors need in order to accumulate at all.

    **A host protocol frame does not mean the host composed everything after it.** Claude
    Code's ``<tool_use_error>`` wraps its own messages and also messages that interpolate the
    user's verbatim command, and the two are not distinguishable by anything structural in the
    frame. The word rule is therefore tighter than the boundary's, and masks a word carrying a
    dot or an underscore.

    **That narrows the exposure and does not remove it.** ``Blocked: ssh bastion`` yields
    ``Blocked ssh bastion``, and ``bastion`` is a hostname; ``PGPASSWORD`` carries no
    underscore; ``tlynch`` is a word. Do not read this function as sanitising its input. What
    bounds those values is the boundary, not this rule; see the module docstring.

    Every bound is read from the vendored contract rather than reimplemented, so none can
    drift from the one the boundary validates against. An unreadable contract yields an empty
    shape and this abstains, because a missing bound read as "no bound" is the leak the bound
    exists to prevent.
    """
    separator = _pattern(shape, "word_separator_pattern")
    word = _pattern(shape, "word_pattern")
    phrase = _pattern(shape, "phrase_pattern")
    max_words = _bound(shape, "max_words")
    if separator is None or word is None or phrase is None or max_words is None:
        return None
    sentence = _SENTENCE_END.split(message, 1)[0].strip()
    words = [part for part in separator.split(sentence) if part]
    if not words or len(words) > max_words:
        return None
    masked = [
        part if word.match(part) and _IS_PROSE_WORD.match(part) else _MASK
        for part in words
    ]
    if all(part == _MASK for part in masked):
        return None
    return _admissible(" ".join(masked), shape)


def _admissible(value: str, shape: Mapping[str, object] | None) -> str | None:
    """Every bound the boundary publishes, applied here so it cannot refuse what we send.

    Mirroring three of ten was not a partial implementation, it was a silent one: an operand
    over the digit bound or the entropy bound was built, sent, and refused at the boundary
    with nothing anywhere to see, which reads as an empty lane rather than as a rejected
    value. Both tiers go through here, so neither can drift from what the boundary admits.

    Returns the value so a caller cannot forget to use the checked one.
    """
    phrase = _pattern(shape, "phrase_pattern")
    max_chars = _bound(shape, "max_chars")
    max_digits = _bound(shape, "max_digits")
    min_for_entropy = _bound(shape, "min_chars_for_entropy")
    max_entropy = _bound(shape, "max_entropy_bits")
    if phrase is None or max_chars is None or max_digits is None:
        return None
    if min_for_entropy is None or max_entropy is None:
        return None
    letters = sum(1 for char in value if char.isalpha())
    if not value or letters < MIN_SIGNATURE_LETTERS or not phrase.fullmatch(value):
        return None
    if len(value) > max_chars or sum(1 for c in value if c.isdigit()) > max_digits:
        return None
    if any(
        len(part) >= min_for_entropy and _entropy_bits(part) > max_entropy
        for part in value.split(" ")
    ):
        return None
    return value


def _entropy_bits(word: str) -> float:
    """Shannon entropy per character, which is how the boundary bounds a random-looking word."""
    counts = Counter(word)
    return -sum((n / len(word)) * log2(n / len(word)) for n in counts.values())


def _bound(shape: Mapping[str, object] | None, key: str) -> float | None:
    value = shape.get(key) if shape else None
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _pattern(shape: Mapping[str, object] | None, key: str) -> re.Pattern[str] | None:
    value = shape.get(key) if shape else None
    if not isinstance(value, str):
        return None
    try:
        return re.compile(value)
    except re.error:
        return None

