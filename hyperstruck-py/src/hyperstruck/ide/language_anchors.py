"""Grammars that say a language runtime authored a line, before anything is read out of it.

A host framing says "an error is reported somewhere in here". It does not say who wrote the
text, and every rule built on position rather than authorship shipped a username, an internal
hostname and an environment variable name for ordinary input. What licenses a read is a
recognizer for a published error format: accept only what a recognizer for the known language
accepts, and never salvage the remainder heuristically (Sassaman, Patterson, Bratus & Locasto,
"Security Applications of Formal Language Theory", IEEE Systems Journal, 2013).

**A block is recognised, never a line.** The licence is a banner, and what it licenses is the
contiguous run of frames beneath it plus the one unindented line that ends the run. Reading
"below the last frame in the text" is not the same thing and leaks: a genuine traceback
followed by unrelated indented output handed the read to whatever came after it, which
returned an internal hostname when it was executed. Indentation delimits the block because
CPython indents a frame and its echoed source and never indents the exception line.

**Why only CPython is here.** V8 was declared and has been withdrawn. Its published format
opens with ``${name}: ${message}`` and *has no banner*, so the only licence available was the
presence of an indented ``at `` line somewhere below. That licenses nothing: a Java stack
trace satisfies it, and the line above a frame is as likely to be ``tlynch: permission
denied`` as ``ReferenceError: x is not defined``. Executed against the real client, all three
of the named leak classes came back through it. A language with no banner has no recognizer,
and the honest consequence is that it does not get an entry rather than getting a positional
rule wearing a grammar's name. That is why :class:`LanguageAnchor` requires a banner.

**What this claims, and what it does not.** It does not claim the interpreter wrote the text.
``traceback.print_exc()`` on a caught exception is byte-identical to an uncaught one, a
combined result stream has no stdout and stderr split to appeal to, and a program may print
traceback-shaped text for its own reasons. The licence is narrower and survives all three:
whoever printed it, what is read out is a **class-name-shaped identifier and never the
message**, so ``KeyError: 'secret-tenant-id'`` yields ``KeyError``. A program printing a
fabricated traceback contributes an application-specific class name, which is the same
category as a genuine user-defined exception class, and which the boundary's cross-tenant
floor keeps agent-specific.

This is not a lexicon. The entry is a structural pattern over a published format rather than a
vocabulary of words, membership decides nothing about meaning, and a language absent from the
table costs coverage on that language rather than flipping any verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageAnchor:
    """One language's error format: what licenses a read, and where the name sits.

    ``banner_re`` is the line that licenses a block, and it is **not optional**. A language
    whose published format has no banner has nothing to license a read with, and is not
    representable here on purpose; see the module docstring.

    ``frame_re`` matches a *real* frame line, not merely an indented one. The distinction is
    load-bearing: a block's frame run is delimited by indentation, but a run made entirely of
    elision markers or source echoes is not a stack and licenses nothing.
    """

    banner_re: re.Pattern[str]
    frame_re: re.Pattern[str]
    name_re: re.Pattern[str]


# CPython prints a banner, then an indented run of frames and their source echoes, then the
# exception line at column zero. https://docs.python.org/3/library/traceback.html
_CPYTHON = LanguageAnchor(
    banner_re=re.compile(r"^Traceback \(most recent call last\):$"),
    frame_re=re.compile(r'^\s+File "'),
    name_re=re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)(?::|$)"),
)

_ANCHORS = (_CPYTHON,)


def anchored_name(lines: list[str]) -> str | None:
    """The failure's name, if a declared language grammar licenses reading one."""
    for anchor in _ANCHORS:
        name = _name_in_last_block(anchor, lines)
        if name is not None:
            return name
    return None


def _name_in_last_block(anchor: LanguageAnchor, lines: list[str]) -> str | None:
    """The exception line of the last licensed block, or nothing.

    **The block is what is read, never the window.** An earlier version collected every frame
    line anywhere in the scanned text and read below the last one, which let any indented
    ``File "`` line appearing after a traceback move the anchor out of the block entirely and
    hand the read to whatever followed. Executed against the real client, a genuine traceback
    followed by unrelated indented text and a hostname returned the hostname.

    The last block is the right one: chained exceptions print the handling exception last, and
    ``raise X from Y`` puts the one that actually stopped the program at the end.
    """
    banners = [index for index, line in enumerate(lines) if anchor.banner_re.match(line.rstrip())]
    if not banners:
        return None
    start = banners[-1] + 1
    end = start
    has_frame = False
    while end < len(lines) and lines[end][:1].isspace():
        has_frame = has_frame or bool(anchor.frame_re.match(lines[end]))
        end += 1
    # A run of elision markers or echoed source is not a stack. Requiring a real frame is what
    # stops ``Traceback ...\n  ...\n<anything>`` licensing a read of that last line.
    if not has_frame or end >= len(lines):
        return None
    match = anchor.name_re.match(lines[end].strip())
    return match.group(1) if match else None
