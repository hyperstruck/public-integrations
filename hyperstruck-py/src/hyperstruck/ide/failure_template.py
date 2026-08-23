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

What recurs is the failure's own **name**: the identifier a failing program leads with, after
the host's framing is removed.

    Error: Exit code 1
    ModuleNotFoundError: No module named 'pytest_asyncio'
    -> ModuleNotFoundError

Measured over 2,509 real failures this yields 71 distinct operands of which 94.7% recur, and
the population is genuinely discriminating: ``ModuleNotFoundError``, ``InputValidationError``,
``AttributeError``, ``KeyError``, ``TypeError``, ``json.decoder.JSONDecodeError``, ``ls``,
``sed``, ``fatal``.

**The token's shape is not what keeps it safe.** ``[A-Za-z0-9_.-]+`` is also the shape of a
username, a hostname and an environment variable name, so a rule that takes the leading
token of an arbitrary line ships those. Safety comes entirely from *where* the line is read
from: somewhere the host itself has said the failure is named. Everywhere else abstains.

**Why a single token rather than a masked phrase.** A Drain-style masked template (He, Zhu,
He & Lyu, "Drain: An Online Log Parsing Approach with Fixed Depth Tree", ICWS 2017) is
strictly more informative: measured on the same corpus it covers 100% of failures against
26.2% here, and ``ModuleNotFoundError: No module named <S>`` says more than
``ModuleNotFoundError``. It is not shippable yet. The boundary admits an operand only if it
matches ``^[A-Za-z0-9_.-]+$``, so a phrase is refused outright; and 72.7% of those richer
templates were singletons, which are simultaneously useless as gates and quasi-identifiers.
Both are answerable at the boundary, by widening the admissible shape and by admitting an
operand on how often it has been seen across the corpus. Until then the token is what this
end can send and have read.

This is not a lexicon and makes no judgement about meaning. It removes the host's own
declared framing, then takes the leading identifier by position. What survives is whatever
the failing program called itself.
"""

from __future__ import annotations

import re

# The boundary's own operand shape. An operand that does not match is refused there, so
# refusing it here keeps the two ends agreeing about what was sent.
_TOKEN = re.compile(r"^[A-Za-z0-9_.-]+$")

MAX_SIGNATURE_CHARS = 64

# The name leads the text it is in, so only the head of a result can hold it. This runs in a
# per-tool-call subprocess inside the editor, on unclipped raw output, so an unbounded scan
# would put a multi-megabyte ``cat`` between the user and their next keystroke.
MAX_SCANNED_CHARS = 4096
MAX_SCANNED_LINES = 20

# Enough to be a name rather than punctuation left over from stripping.
MIN_SIGNATURE_LETTERS = 2


def failure_signature(
    text: str, framing: tuple[str, ...] = (), *, is_host_labelled: bool = False
) -> str | None:
    """The identifier a failure leads with, or nothing usable.

    ``framing`` is the host's own generic prefixes, declared per host rather than guessed:
    Claude Code leads a failed result with ``Error:`` and an ``Exit code N`` line, and
    without removing them the operand is ``Error`` for 65% of all failures, which is the
    degenerate gate this module exists to avoid reached by a different route.

    **Where the operand is read from is a privacy control, not a parsing convenience.** On a
    host that reports failure by returning the whole result as a string, that string is
    stdout and stderr together, and only the framing says which part is the failure. An
    earlier version answered provenance ("was this framed anywhere?") and position ("take the
    last line") as separate questions, so on the one host this ships for the answer to the
    first was always yes and the second happily took a line of command output. It shipped a
    username, an internal hostname and a credential as gate operands in testing. The frame
    now decides *both*: the operand is read from the framed line, or the line straight after
    it, and nowhere else.

    ``is_host_labelled`` means the text arrived in a field that already means "this is the
    error" (``stderr``, ``error``), which needs no frame.
    """
    raw = text or ""
    is_whole_field_seen = len(raw) <= MAX_SCANNED_CHARS
    lines = [
        line
        for line in raw[:MAX_SCANNED_CHARS].splitlines()[:MAX_SCANNED_LINES]
        if line.strip()
    ]
    if not lines:
        return None
    if is_host_labelled:
        return _identifier_in_labelled_field(lines, is_whole_field_seen)
    return _identifier_at_frame(lines, framing)


def _identifier_in_labelled_field(
    lines: list[str], is_whole_field_seen: bool
) -> str | None:
    """The failure's name in a field that means "this is the error", if it holds only that.

    A field name is a claim about the field, not about each line inside it. ``stderr`` is a
    *stream*: on a host that runs shell commands it carries whatever the program sent to fd
    2, which is progress chatter, warnings and, for something like ``cat /etc/passwd``, the
    file. Reading the last line of that was the same positional guess the framed path was
    just corrected for, and it shipped a username, an internal hostname and an environment
    variable name in testing.

    One non-blank line is the case where the field name and the line coincide: there is
    nothing else in it for the operand to be. Anything longer is a stream and abstains,
    which costs coverage and is the only rule here that does not depend on guessing which
    line of a program's output was the failure.
    """
    if not is_whole_field_seen or len(lines) != 1:
        return None
    return _identifier(lines[0])


def _identifier_at_frame(lines: list[str], framing: tuple[str, ...]) -> str | None:
    """The failure's name at the host's frame, which is the only place it is known to be.

    The first line and nothing else. A host that concatenates stdout and stderr into one
    string gives no reliable position beyond its own frame: the line after the frame is the
    first line of the command's output, so a step like ``cat /etc/passwd; false`` would put
    a username there. Both of those were tried and both leaked, which is why this reads
    exactly one line and accepts the coverage that costs.

    Scanning *every* line for a frame reopens that by another door, because a tool's own
    output can contain the host's framing prefix: ``some output\nError: bastion.corp: down``
    would yield the hostname. The frame is part of the host's envelope, so it leads the
    result or it is not the envelope, and only three of the four routes that reach here have
    already had that checked elsewhere.
    """
    first = lines[0].strip()
    for prefix in framing:
        stripped = re.sub(prefix, "", first).strip()
        if stripped != first:
            return _identifier(stripped)
    return None


def _identifier(line: str) -> str | None:
    """The leading identifier of one line, if that line leads with one."""
    head = line.strip().split(":", 1)[0].split("(")[0].strip()
    if not head or len(head) > MAX_SIGNATURE_CHARS or not _TOKEN.match(head):
        return None
    letters = sum(1 for char in head if char.isalpha())
    return head if letters >= MIN_SIGNATURE_LETTERS else None
