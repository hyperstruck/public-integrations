"""Finding our own block in the params as they were actually sent.

This is the artefact that makes a non-Claude-Code customer creditable at all, and the
whole of its value rests on one distinction. Remembering where we put the block and
handing that back is an echo: it asserts the very thing a receipt exists to prove, and it
would report a rendered learning just as confidently for a run whose trimming middleware
had emptied the block on the way to the model. Searching the sent params for our own lines
is an observation. The LangGraph seat sends no receipt precisely because, sitting above the
composition stack, an echo is the only artefact it could produce.

**The disclosure cost is zero, and that is enforced by construction rather than asserted.**
The receipt is assembled from the payload lines that matched lines *we authored*, and never
from the lines between them. An earlier version took the span from the first match to the
last and returned everything inside it, which is a different thing wearing the same
description: a model quoting one of our advice lines back, which is the ordinary case for an
agent restating guidance it was given, put a match early and our real block late, and the
span swallowed every message in between. A probe of that version produced a receipt carrying
a patient record, a card number and a password. Nothing between two matches is ours, so
nothing between two matches goes in.

**An echo is not an exposure.** For the same reason, a line is only counted as delivered
when it appears inside the region where our block actually sits. A tool result or a model
turn that quotes one of our lines elsewhere in the history is not evidence that the system
block survived; treating it as evidence would be a positive claim of exposure drawn from
the model's own output, which is the one assertion this lane must never make.

**What it can catch, and what it cannot.** The evidential value is full for the class the
receipt exists to catch: a downstream layer that dropped lines, emptied the block, or
truncated it partway. It cannot catch genuine rewording by a downstream summariser, and no
token-anchored matcher can; a reworded block reads here as missing lines, which is the
fail-safe direction.

**This does not re-implement the server's matcher and must not grow into one.** Core's
receipt module owns the judgement that decides credit, with a line-anchored rule for advice
and an anchored token window for facts, and a second copy of that would drift into two
answers about the same run. What lives here is a *local* fidelity report for the customer's
own eyes: it tells them their own trimming middleware emptied our block, without a support
ticket. Where the two disagree, the server's answer is the one that decides anything.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# Leading list markers a host may add, replace or renumber. Stripped as whole tokens and
# never as a character class: ``lstrip("-* ")`` eats the minus sign off a continuation
# line that a hard-wrapping host broke on ``range = -5 to -10``, and that line then never
# matches again. The rule is copied from Core's own stripper for exactly this reason.
_LIST_MARKER = re.compile(r"^([-*•–—]|\d+[.)]|[a-zA-Z][.)])$")

# How many unrelated lines may sit between two of ours before we stop believing they are
# the same block. Our block is contiguous when we send it, so any gap at all is the host's
# doing: a few lines of its own framing is ordinary, and a hundred means the second match
# is somewhere else in the conversation and belongs to a different region.
MAX_INTERLEAVE_LINES = 8

# What a run's block fidelity can be, per line and rolled up per shelf.
DELIVERED_VERBATIM = "delivered_verbatim"
DELIVERED_REFORMATTED = "delivered_reformatted"
UNRESOLVED = "unresolved"

FIDELITY_OUTCOMES = frozenset({DELIVERED_VERBATIM, DELIVERED_REFORMATTED, UNRESOLVED})


def _normalise(text: str) -> str:
    """Collapse whitespace, so a host that re-wraps or re-indents still matches.

    A host that reflows our block to its own column width still showed the model the
    learning. Reading that as a drop would be a positive claim of non-exposure drawn from
    formatting alone, which is the one thing this lane must never assert.
    """
    return " ".join(text.split())


def _strip_markers(line: str) -> str:
    """One line, normalised and stripped of the markers a rendered block begins with."""
    tokens = _normalise(line).split()
    index = 0
    while index < len(tokens) and _LIST_MARKER.match(tokens[index]):
        index += 1
    return " ".join(tokens[index:])


def _significant_lines(text: str | None) -> list[str]:
    """The lines of a block that carry content, in order, marker-stripped."""
    if not text:
        return []
    return [stripped for line in text.splitlines() if (stripped := _strip_markers(line))]


@dataclass(frozen=True)
class ShelfFidelity:
    """How much of one shelf's block survived the journey to the model.

    ``outcome`` is stated per shelf rather than per offered id, and the field name says so
    on purpose. The rendered block carries no id markers: the boundary returns the text and
    the offered id sets as two separate things, and nothing in the render says which line
    came from which learning. A per-id verdict derived from a per-shelf observation would be
    a precision this seat does not have, presented as one it does, so the ids are listed
    beside the verdict they share instead of each being handed a verdict of its own.
    Recovering true per-id fidelity needs id markers in the render, which is a boundary
    change and not this seat's to make.
    """

    name: str
    outcome: str
    offered_ids: tuple[str, ...]
    lines_expected: int
    lines_found: int
    missing_lines: tuple[str, ...]

    @property
    def is_delivered(self) -> bool:
        return self.outcome != UNRESOLVED


@dataclass(frozen=True)
class ReceiptLocation:
    """Our block as it was found in the sent params, and how intact it was.

    ``text`` holds the payload's own rendering of the lines we authored, in payload order,
    and nothing else. It is therefore evidence about what the host did to our block (a line
    dropped, a bullet renumbered, a block reflowed or emptied) while being incapable of
    carrying content we did not write.

    ``None`` means not one line of ours was found in a plausible block region, which is the
    honest artefact for a block that never reached the model: an empty receipt is not the
    same as no receipt, and sending an empty string would be read as an exposure that
    matched nothing.
    """

    text: str | None
    shelves: tuple[ShelfFidelity, ...]

    @property
    def is_present(self) -> bool:
        return self.text is not None

    @property
    def outcome(self) -> str:
        """The run's fidelity, taken as the worst any shelf reported.

        Worst rather than best, and rather than an average. The reader's question is
        whether anything went wrong on the way to the model, and a run that delivered its
        advice verbatim while its facts vanished has something wrong with it.
        """
        outcomes = {shelf.outcome for shelf in self.shelves if shelf.lines_expected}
        if not outcomes:
            return UNRESOLVED
        for candidate in (UNRESOLVED, DELIVERED_REFORMATTED, DELIVERED_VERBATIM):
            if candidate in outcomes:
                return candidate
        return UNRESOLVED


def locate_receipt(
    sent_payload: str,
    shelves: Sequence[tuple[str, str | None, Iterable[str]]],
) -> ReceiptLocation:
    """Find where our blocks sit in ``sent_payload``, and grade each shelf.

    ``shelves`` is ``(name, rendered_text, offered_ids)`` per shelf, in the order they were
    injected. Matching is confined to the cluster of the payload where our lines actually
    congregate, so a stray echo elsewhere in the message history neither credits a shelf nor
    drags unrelated content into the receipt.
    """
    sent_lines = sent_payload.splitlines()
    stripped_sent = [_strip_markers(line) for line in sent_lines]

    expected_by_shelf = [
        (name, text, tuple(offered_ids), _significant_lines(text))
        for name, text, offered_ids in shelves
    ]
    ours = {line for _, _, _, expected in expected_by_shelf for line in expected}

    region = _block_region(stripped_sent, ours)
    # Only lines inside the region count, and only they may appear in the receipt. Both
    # restrictions come from the same rule: a match outside the block our own lines form is
    # somebody else repeating us, and neither credits a shelf nor belongs in the artefact.
    present = {line for index, line in region}
    receipt_lines = [sent_lines[index] for index, _ in region]

    graded: list[ShelfFidelity] = []
    for name, text, offered_ids, expected in expected_by_shelf:
        found = [line for line in expected if line in present]
        missing = tuple(line for line in expected if line not in present)
        if not expected or not found:
            outcome = UNRESOLVED
        elif missing:
            outcome = DELIVERED_REFORMATTED
        else:
            outcome = _verbatim_or_reformatted(sent_payload, text)
        graded.append(
            ShelfFidelity(
                name=name,
                outcome=outcome,
                offered_ids=offered_ids,
                lines_expected=len(expected),
                lines_found=len(found),
                missing_lines=missing,
            )
        )

    if not receipt_lines:
        return ReceiptLocation(text=None, shelves=tuple(graded))
    return ReceiptLocation(text="\n".join(receipt_lines), shelves=tuple(graded))


def _block_region(
    stripped_sent: list[str], ours: set[str]
) -> list[tuple[int, str]]:
    """The cluster of payload lines that is our block, as ``(index, stripped)`` pairs.

    Every payload line matching something we authored is a candidate. They are grouped into
    clusters separated by more than :data:`MAX_INTERLEAVE_LINES` unrelated lines, and the
    richest cluster wins, measured by how many *distinct* lines of ours it holds rather than
    by how many matches it has: a tool result repeating one line ten times must not outrank
    the block itself.

    Ties go to the earlier cluster, which is arbitrary and stated so rather than left to be
    discovered. A tie means two regions carry equally much of our block, and no evidence
    here distinguishes them.
    """
    candidates = [
        (index, line) for index, line in enumerate(stripped_sent) if line and line in ours
    ]
    if not candidates:
        return []
    clusters: list[list[tuple[int, str]]] = [[candidates[0]]]
    for index, line in candidates[1:]:
        if index - clusters[-1][-1][0] > MAX_INTERLEAVE_LINES + 1:
            clusters.append([])
        clusters[-1].append((index, line))
    return max(clusters, key=lambda cluster: len({line for _, line in cluster}))


def _verbatim_or_reformatted(sent_payload: str, text: str | None) -> str:
    """Whether every line survived unchanged, or survived only after normalising.

    Every line is present either way; the difference is whether the host reflowed,
    re-indented or renumbered on the way. Both are deliveries and neither costs credit, so
    the distinction exists to answer the customer's own question about their stack rather
    than to gate anything.
    """
    if text and text in sent_payload:
        return DELIVERED_VERBATIM
    return DELIVERED_REFORMATTED


def flatten_params(params: Any) -> str:
    """Best-effort flattening of a model SDK's params into searchable text.

    Model SDKs disagree about the shape of a message list and each of them changes it, so
    this walks strings, mappings and sequences rather than naming any provider's schema. It
    is deliberately generous: a shape it cannot read contributes nothing, which reads as a
    block that did not arrive, which is the fail-safe direction for a lane that must never
    assert an exposure it cannot evidence.
    """
    collected: list[str] = []
    _collect_text(params, collected, depth=0, seen=set())
    return "\n".join(collected)


# A model params object nests a few levels: messages, content parts, and the odd blob of
# provider metadata. Bounded so a cyclic or pathologically nested object cannot turn a
# diagnostic into a hang on the model-call hot path.
_MAX_FLATTEN_DEPTH = 8


def _collect_text(
    value: Any, into: list[str], *, depth: int, seen: set[int]
) -> None:
    if depth > _MAX_FLATTEN_DEPTH:
        return
    if isinstance(value, str):
        into.append(value)
        return
    # A depth cap alone still walks a shared subgraph once per path into it, so a params
    # object a host built by reference is exponential in its own nesting. The identity set
    # is what makes the bound hold, and it matches the TypeScript flattener, which has had
    # one from the start.
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_text(item, into, depth=depth + 1, seen=seen)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _collect_text(item, into, depth=depth + 1, seen=seen)
        return
    content = getattr(value, "content", None)
    if content is not None and content is not value:
        _collect_text(content, into, depth=depth + 1, seen=seen)
