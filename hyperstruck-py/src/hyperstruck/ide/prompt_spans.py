"""Cut the turn's goal into prose and machine markup, from what the host declares it emits.

The boundary decides provenance for every span of an episode, and it does so from a closed
set of markup it knows. A client that knows its host's own envelope can say so instead, and
this is where that is said. Only the goal is tagged: the boundary reads client spans for the
goal alone, and for a step result this client has no advantage over the boundary anyway, so
tagging one would be reconstructing provenance from appearance.

**Minted from the final goal string, never from the raw prompt.** The boundary matches a
client span to the text by content, and one span it cannot find discards the whole tagging
for that text and falls back, counted and silent to the caller. The goal is sent scrubbed and
clipped, so spans cut before either transform would miss on every episode carrying a secret
or a long prompt while the run read as fully tagged. :func:`prompt_spans` therefore takes the
goal that will be sent and cuts that, which makes the ordering a property of the signature
rather than a rule someone has to remember.

**Contiguous by construction.** The spans concatenate back to the goal exactly, so the
boundary records no gap. Text a client leaves between its spans is a gap the boundary labels
itself and counts, and a client that gapped on every turn would make that counter say nothing
about the turns where something really was missed.
"""

from __future__ import annotations

import re

from collections.abc import Sequence

from hyperstruck._wire import EpisodeSpan
from hyperstruck.ide.constants import TRUNCATION_MARKER
from hyperstruck.ide.debug import debug
from hyperstruck.ide.host_vocabularies import (
    line_start_openers,
    openers_kept_out_of_the_goal,
    prompt_envelope,
)
from hyperstruck.ide.receipt import MARKER_CLOSE, MARKER_OPEN

ORIGIN_USER_PROSE = "user_prose"
ORIGIN_HARNESS = "harness"

# Markup this client mints itself, whatever the host is, so it is declared apart from
# the per-host envelope rather than repeated in each.
_CLIENT_MARKUP: tuple[tuple[str, str, bool], ...] = ((MARKER_OPEN, MARKER_CLOSE, True),)


# A 4xx is terminal to the flush retry, so a cut past this drops the whole episode.
MAX_SPANS = 64


def prompt_spans(
    goal: str, source: str, *, is_without_principal: bool = False
) -> tuple[EpisodeSpan, ...]:
    """The goal cut into prose and harness, or nothing when this host declares no envelope.

    ``is_without_principal`` is the host's own record saying a machine started this turn
    (:mod:`hyperstruck.ide.authorship`). The whole goal is then one harness span whatever it looks
    like, because a relayed report carries no markup the wrapper list could be sure of.

    Nothing rather than one prose span covering everything: an undeclared host has said
    nothing about its markup, and asserting the whole turn is prose would be a claim, not an
    abstention. The boundary's own closed set still reads it.

    Nothing again past ``MAX_SPANS``. A real 8,000-character Claude Code goal of repeated
    command blocks cuts into 255 spans, and sending them would 422 the episode away for good.
    Abstaining hands the boundary the same goal with no labelling, which its own closed set
    still reads, so the turn survives and only the client's labelling is lost.
    """
    if goal and is_without_principal:
        return (EpisodeSpan(text=goal, origin=ORIGIN_HARNESS),)
    envelope = prompt_envelope(source)
    if not goal or not envelope:
        if goal and not envelope:
            # A host with no declared envelope mints no stated norms at all, and nothing else
            # distinguishes that from a principal who states none.
            debug(
                f"prompt_spans: {source!r} declares no prompt envelope, so this turn is untagged "
                "and its principal utterance will be dropped by the boundary"
            )
        return ()
    spans = _cut_spans(goal, envelope + _CLIENT_MARKUP, line_start_openers(source))
    if len(spans) > MAX_SPANS:
        return ()
    return tuple(spans)


def _cut_spans(
    goal: str,
    envelope: tuple[tuple[str, str, bool], ...],
    line_start: frozenset[str] = frozenset(),
) -> list[EpisodeSpan]:
    closer_by_opener = {opener: closer for opener, closer, _ in envelope}
    runs_to_end_by_opener = {opener: runs_to_end for opener, _, runs_to_end in envelope}

    spans: list[EpisodeSpan] = []
    seen_at: dict[str, int] = {}
    cursor = 0
    search_from = 0
    while cursor < len(goal):
        opener, at = _next_opener(goal, search_from, closer_by_opener, seen_at)
        if opener is None:
            break
        if _is_quoted_mention(goal, at, opener) or (
            opener in line_start and _is_mentioned_in_passing(goal, at, opener)
        ):
            search_from = at + len(opener)
            continue
        closer = closer_by_opener[opener]
        limit = len(goal)
        if not runs_to_end_by_opener[opener]:
            # A block that does not run to the end is one paragraph, so its closer is sought inside it.
            paragraph = _PARAGRAPH_BREAK.search(goal, at + len(opener))
            limit = paragraph.start() if paragraph is not None else len(goal)
        if runs_to_end_by_opener[opener]:
            found = goal.find(closer, at + len(opener), limit)
            end = found + len(closer) if found >= 0 else limit
        else:
            closing = _closer_pattern(closer).search(goal, at + len(opener), limit)
            end = closing.end() if closing is not None else limit
        if at > cursor:
            spans.append(EpisodeSpan(text=goal[cursor:at], origin=ORIGIN_USER_PROSE))
        spans.append(EpisodeSpan(text=goal[at:end], origin=ORIGIN_HARNESS))
        cursor = search_from = end
    if cursor < len(goal):
        clipped_at = _clipped_opener_start(goal, cursor, closer_by_opener)
        if clipped_at is None:
            spans.append(EpisodeSpan(text=goal[cursor:], origin=ORIGIN_USER_PROSE))
        else:
            if clipped_at > cursor:
                spans.append(
                    EpisodeSpan(text=goal[cursor:clipped_at], origin=ORIGIN_USER_PROSE)
                )
            spans.append(EpisodeSpan(text=goal[clipped_at:], origin=ORIGIN_HARNESS))
    return spans


# The least of a marker that must survive the clip before the tail is called the host's.
_MIN_CLIPPED_OPENER_CHARS = 16


def _clipped_opener_start(
    goal: str, cursor: int, closer_by_opener: dict[str, str]
) -> int | None:
    """Where a marker the goal clip cut through begins, or ``None`` when the tail is prose.

    The goal is clipped to the boundary's bound, and the cut can land inside a host marker: a
    long subagent report ends ``That "other Claude session" is an agent working in [TRUNCATED]``.
    No opener matches a marker with its end missing, so the fragment would ship as the person's
    words. Only a clipped goal is read this way, and only for a stretch too long to be chance.
    """
    if not goal.endswith(TRUNCATION_MARKER):
        return None
    tail = goal[cursor : len(goal) - len(TRUNCATION_MARKER)]
    for opener in closer_by_opener:
        for kept in range(len(opener) - 1, _MIN_CLIPPED_OPENER_CHARS - 1, -1):
            if tail.endswith(opener[:kept]):
                return cursor + len(tail) - kept
    return None


def _closer_pattern(closer: str) -> re.Pattern[str]:
    """The closer, matching any run of whitespace where it has a space, since a rewrap can split it."""
    return re.compile(r"\s+".join(re.escape(word) for word in closer.split(" ")))


_QUOTES = "\"'`"
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n")


def _is_quoted_mention(goal: str, at: int, opener: str) -> bool:
    """Whether the opener is a tag named inside quotes or backticks rather than one the host opened.

    A host opens an envelope bare, at the start of a line or of its text. A tag a command or a file
    read merely mentions (`rg "<tag>" src/`, a quoted fixture line) is wrapped, and the later closer
    that pairs with it is as much a mention as it is.
    """
    end = at + len(opener)
    return (
        at > 0 and end < len(goal) and goal[at - 1] in _QUOTES and goal[end] in _QUOTES
    )


def _is_mentioned_in_passing(goal: str, at: int, opener: str) -> bool:
    """Whether a line-start opener sits mid-line, or is only the start of a longer tag name.

    The host writes these on lines of their own, so ``why does <agent-message from=x> show up``
    is a person's sentence. A tag opener declared without its ``>`` must also end where the tag
    name does, or ``<agent-messages>`` would open a report.
    """
    if at > 0 and goal[at - 1] != "\n":
        return True
    following = goal[at + len(opener) : at + len(opener) + 1]
    return (
        opener.startswith("<")
        and not opener.endswith(">")
        and following not in ("", " ", ">", "\n", "\t")
    )


def _next_opener(
    goal: str,
    cursor: int,
    closer_by_opener: dict[str, str],
    seen_at: dict[str, int],
) -> tuple[str | None, int]:
    """The earliest declared opener at or after ``cursor``, and where it starts.

    Earliest by position and then by length, so a host declaring two markers that share a
    prefix cuts at the longer one rather than at whichever the dict happened to yield first.

    ``seen_at`` is the caller's memo of where each opener was last seen, kept across the walk.
    """
    best_opener: str | None = None
    best_at = len(goal)
    for opener in closer_by_opener:
        # The cursor only moves forward, so a remembered position at or after it still holds.
        # A remembered -1 holds too: an absent marker stays absent.
        at = seen_at.get(opener)
        if at is None or (at >= 0 and at < cursor):
            at = goal.find(opener, cursor)
            seen_at[opener] = at
        if at < 0:
            continue
        if at < best_at or (at == best_at and len(opener) > len(best_opener or "")):
            best_opener, best_at = opener, at
    return best_opener, best_at


def principal_prose(spans: Sequence[EpisodeSpan]) -> str | None:
    """The principal's own words on this turn: every user-prose span, in order.

    This is what fills ``principal_utterance``, and it is derived from the spans rather than from
    the goal for one reason: the field is the only evidence for a rule no tool result could have
    revealed, so a value that includes the host's own envelope would let machine text authorise a
    standing order. Cutting it from the spans means the two can never disagree about which half of
    the turn the principal wrote.

    ``None`` when the host declared no envelope, because :func:`prompt_spans` returns nothing there
    and an untagged turn is a turn this client cannot say anything about. The boundary refuses an
    utterance it cannot place inside tagged prose anyway, so sending the whole goal would be a
    claim this client has no basis for and would be dropped on arrival.
    """
    if not spans:
        return None
    prose = "".join(
        span.text for span in spans if span.origin == ORIGIN_USER_PROSE
    ).strip()
    return prose or None


def strip_harness_envelopes(text: str, source: str) -> str:
    """``text`` without the host's agent-message, task and reminder envelopes or our own marker.

    Removed rather than tagged: a background task id inside a notification was once read as a
    subject and became an entity. Other declared markup (the command blocks) stays, as does
    everything on a host that declares no envelope.
    """
    envelope = prompt_envelope(source)
    if not text or not envelope:
        return text
    markup = envelope + _CLIENT_MARKUP
    stripped_openers = (*openers_kept_out_of_the_goal(source), MARKER_OPEN)
    closer_by_opener = {opener: closer for opener, closer, _ in markup}
    spans = _cut_spans(text, markup, line_start_openers(source))
    is_stripped = [
        span.origin == ORIGIN_HARNESS
        and span.text.startswith(stripped_openers)
        and _is_balanced(span.text, closer_by_opener)
        for span in spans
    ]
    if not any(is_stripped):
        return text
    return "".join(
        span.text for span, gone in zip(spans, is_stripped, strict=True) if not gone
    ).strip()


def _is_balanced(span_text: str, closer_by_opener: dict[str, str]) -> bool:
    """Whether the span closes its own opener; an unmatched one is ordinary text, not an envelope."""
    # The longest, as the cut chose it: two declared openers can share a prefix.
    opener = max((o for o in closer_by_opener if span_text.startswith(o)), key=len)
    closer = closer_by_opener[opener]
    closing = _closer_pattern(closer).search(span_text, len(opener))
    return closing is not None and closing.end() == len(span_text)
