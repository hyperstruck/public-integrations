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

from collections.abc import Sequence

from hyperstruck._wire import EpisodeSpan
from hyperstruck.ide.debug import debug
from hyperstruck.ide.host_vocabularies import prompt_envelope
from hyperstruck.ide.receipt import MARKER_CLOSE, MARKER_OPEN

ORIGIN_USER_PROSE = "user_prose"
ORIGIN_HARNESS = "harness"

# Markup this client mints itself, whatever the host is, so it is declared apart from
# the per-host envelope rather than repeated in each.
_CLIENT_MARKUP: tuple[tuple[str, str, bool], ...] = ((MARKER_OPEN, MARKER_CLOSE, True),)


# A 4xx is terminal to the flush retry, so a cut past this drops the whole episode.
MAX_SPANS = 64


def prompt_spans(goal: str, source: str) -> tuple[EpisodeSpan, ...]:
    """The goal cut into prose and harness, or nothing when this host declares no envelope.

    Nothing rather than one prose span covering everything: an undeclared host has said
    nothing about its markup, and asserting the whole turn is prose would be a claim, not an
    abstention. The boundary's own closed set still reads it.

    Nothing again past ``MAX_SPANS``. A real 8,000-character Claude Code goal of repeated
    command blocks cuts into 255 spans, and sending them would 422 the episode away for good.
    Abstaining hands the boundary the same goal with no labelling, which its own closed set
    still reads, so the turn survives and only the client's labelling is lost.
    """
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
    envelope = envelope + _CLIENT_MARKUP

    closer_by_opener = {opener: closer for opener, closer, _ in envelope}
    runs_to_end_by_opener = {opener: runs_to_end for opener, _, runs_to_end in envelope}

    spans: list[EpisodeSpan] = []
    seen_at: dict[str, int] = {}
    cursor = 0
    while cursor < len(goal):
        opener, at = _next_opener(goal, cursor, closer_by_opener, seen_at)
        if opener is None:
            break
        closer = closer_by_opener[opener]
        found = goal.find(closer, at + len(opener))
        if found >= 0:
            end = found + len(closer)
        elif runs_to_end_by_opener[opener]:
            end = len(goal)
        else:
            end = at + len(opener)
        if at > cursor:
            spans.append(EpisodeSpan(text=goal[cursor:at], origin=ORIGIN_USER_PROSE))
        spans.append(EpisodeSpan(text=goal[at:end], origin=ORIGIN_HARNESS))
        cursor = end
    if cursor < len(goal):
        spans.append(EpisodeSpan(text=goal[cursor:], origin=ORIGIN_USER_PROSE))
    if len(spans) > MAX_SPANS:
        return ()
    return tuple(spans)


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
