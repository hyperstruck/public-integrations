"""The answer the assistant actually gave, taken from the editor's own transcript.

The obligation shelf's own-output lane records the commitments an agent makes in its final answer
("I'll confirm the volumes by Friday") and offers them back when they come due. It needs the text
the person was shown, and nothing else this hook collects is that text: the steps are tool calls and
their results, which are what the assistant did rather than what it said, and a commitment lifted
out of them would be a promise nobody was ever made.

The transcript is the only place the composed answer exists at stop time, so it is read here, under
the same ceiling and through the same reader ``receipt`` uses. Read is all it is: no inference, no
reconstruction from steps. Where the last assistant message cannot be found the field is simply
absent, the boundary accepts the episode exactly as before, and the lane harvests nothing.

**The LAST assistant text block of the turn, and not a join of them.** An assistant emits text
between tool calls as well as at the end, and that mid-turn text is thinking out loud on the way to
an answer: "I'll check the depot schedule next" is a plan for the following ten seconds, not a
commitment to anybody. Joining them would feed the lane the largest false-positive class the
obligation manifesto names. The closing block is the one addressed to the reader.

**Bounded to THIS turn, which is the difference between a true record and a fabricated one.** A
transcript is one append-only file for the whole session, so "the newest assistant text in the file"
and "what this turn said" are the same thing only when this turn said something. A turn that composed
no prose at all (it ran tools and stopped, or it was interrupted, or it ended on a tool result) would
otherwise hand the previous turn's answer to this run's episode, and the lane would write that
turn's commitments onto the shelf a second time, dated to now, under this run. That is a promise
nobody made in this turn, recorded as though the agent had just made it.

The boundary is the transcript's own: the most recent record that is a genuine turn from the person,
meaning a ``user`` record carrying prose rather than one carrying a tool result. Everything after it
is this turn. Reading backwards from the end, the first assistant record with text wins and the first
genuine user record stops the search with nothing, so a turn that composed no prose answers empty
rather than answering with the turn before it.

**Where the boundary cannot be established the answer is nothing, deliberately.** The scan is bounded
(a bounded window over a bounded tail, then over the whole file), so it can run out of records having
found neither an answer nor a boundary. Guessing in that state is what the bug was; an empty answer
costs a commitment nobody may have made, and the lane writes nothing either way.

**The hook's own ``started_at`` was considered as the floor and rejected.** It is set to
``time.time()`` on the restage path in ``hook._restage_from_evidence``, which runs at the turn's
STOP, so a timestamp floor taken from it would reject the very answer it was meant to admit on
exactly the turns the backstop sweep exists to rescue. The transcript's own boundary needs no clock
and cannot be wrong about which turn a record belongs to.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from typing import Any

from hyperstruck.ide.constants import MAX_FINAL_OUTPUT_CHARS
from hyperstruck.ide.debug import debug
from hyperstruck.ide.transcript import TAIL_BYTES, TranscriptMissing, TranscriptUnreadable, iter_lines

__all__ = ["MAX_FINAL_OUTPUT_CHARS", "final_assistant_text"]

# How far back from the end of the transcript to look for the turn's composed answer, or for the
# turn boundary that proves there is none. The last assistant record is usually the answer; tool
# results and the turn's own opening prompt can sit between here and it, so this is slack rather
# than a search depth. It bounds PARSES; the bound on bytes is the tail read itself, which is the
# one that decides what this costs.
#
# Widened from 64 when the reader gained its turn boundary: a window that holds only assistant
# records needs to hold only the last few, but a window that must also reach back past this turn's
# tool results to the prompt that started it is measured in the turn's own step count, and a long
# turn runs hundreds of tools. Running out is not a wrong answer (it reads as an unestablished
# boundary and yields nothing), but it is a lost harvest, so the window is sized past any ordinary
# turn rather than against one.
_TAIL_CANDIDATES = 512


def _text_blocks(record: dict[str, Any]) -> list[str]:
    """The plain-text content of one assistant record, ignoring everything else in it.

    A message's content is a list of typed blocks and only the ``text`` ones were shown as prose.
    Tool-use blocks are the assistant acting rather than speaking, and thinking blocks are
    explicitly not addressed to anybody; including either would put the reasoning trace behind a
    provenance class that says the agent bound itself to the reader.
    """
    if record.get("type") != "assistant":
        return []
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    return [
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
        and block["text"].strip()
    ]


def _is_own_prose(record: dict[str, Any]) -> bool:
    """Whether this record is the assistant or the person speaking, rather than machinery.

    A sidechain record is a subagent's own conversation, which the person was never shown, and a
    meta record is the editor talking to itself. Neither is part of the turn this reader is bounding
    and neither may end it.
    """
    return not record.get("isSidechain") and not record.get("isMeta")


def _is_turn_boundary(record: dict[str, Any]) -> bool:
    """Whether this record is the person opening a turn, which is where this turn begins.

    A ``user`` record is two different things wearing one type. One is a prompt the person typed;
    the other is a tool result, which the editor writes back into the conversation under the user
    role because that is where the protocol puts it. Only the first ends a turn, so the content is
    what is read rather than the type: a string, or a block list carrying prose. A record whose
    blocks are all ``tool_result`` is the turn continuing, not a new one starting.
    """
    if record.get("type") != "user" or not _is_own_prose(record):
        return False
    message = record.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
        and block["text"].strip()
        for block in content
    )


def _latest_assistant_text(lines: Iterable[str]) -> tuple[list[str], bool]:
    """This turn's closing prose, and whether the turn boundary was established at all.

    Returns ``(blocks, is_bounded)``. ``is_bounded`` false means the scan ran out of records without
    settling the question, and the caller must widen the read or answer nothing; it never means the
    turn was silent. ``([], True)`` is the real and common answer for a turn that ran tools and
    composed nothing.

    Candidate LINES are kept and parsed backwards from the newest, so the ordinary turn costs one
    or two ``json.loads`` whatever the session's length. Walking backwards is also what makes the
    boundary cheap: the first assistant record with text is necessarily after any boundary further
    back, so it is this turn's by construction, and the first genuine user record reached before one
    proves this turn composed nothing.

    The prefilter takes user records as well as assistant ones now. It has to: a filter that saw
    only assistant records could find an answer but could never find the boundary that disqualifies
    it, which is the whole defect.
    """
    candidates: deque[str] = deque(maxlen=_TAIL_CANDIDATES)
    for line in lines:
        if '"assistant"' in line or '"user"' in line:
            candidates.append(line)
    while candidates:
        line = candidates.pop()
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if _is_turn_boundary(record):
            return [], True
        if record.get("type") != "assistant" or not _is_own_prose(record):
            continue
        blocks = _text_blocks(record)
        if blocks:
            return blocks, True
    # Nothing settled it: no prose from this turn and no boundary proving there was none. The
    # window may have dropped its oldest entries, or the read may have reached the start of a file
    # that holds no opening prompt at all. Both are the same answer to the caller, which is that the
    # turn could not be bounded, and the safe reading of an unbounded turn is that it said nothing.
    return [], False


def final_assistant_text(transcript_path: str | None) -> str:
    """The closing prose of the most recent assistant message, or an empty string.

    **The tail first, the whole file only if the tail held nothing.** This runs on the stop hook of
    every turn against a file that grows for the life of the session, so reading it end to end made
    the cost of a session quadratic in its own length: turn 200 re-read everything turns 1 to 199
    had written, to find something that is at the end by construction. The tail read is bounded in
    bytes, and the fallback is what stops that being a silent trade: a turn whose closing message
    sits further back than ``TAIL_BYTES`` (an answer followed by megabytes of tool results) is still
    found, at the cost this function used to pay unconditionally.

    Every failure answers with an empty string rather than raising or reporting a state of its own.
    Unlike the receipt, an absent value here costs nothing that can be told apart from a turn whose
    answer held no commitments: the lane writes nothing either way, and there is no credit rate for
    a missing one to distort. It is a best-effort read of an optional field, on the stop path of
    every turn, so it must never be able to cost a turn its episode.
    """
    if not transcript_path:
        return ""
    # Missing and unreadable are the same answer here, unlike in ``receipt``: this field is optional
    # and an absent one is indistinguishable from a turn whose answer held no commitments, so there
    # is no state worth reporting and nothing worth raising over.
    try:
        latest, is_bounded = _latest_assistant_text(
            iter_lines(transcript_path, what="final_output", tail_bytes=TAIL_BYTES)
        )
        # Widened only when the tail could not settle the question. An empty answer from a BOUNDED
        # tail is the real answer for a turn that composed nothing, and re-reading the whole file
        # for it would pay the unbounded cost on exactly the turns that have nothing to give.
        if not is_bounded:
            latest, is_bounded = _latest_assistant_text(
                iter_lines(transcript_path, what="final_output")
            )
    except (TranscriptMissing, TranscriptUnreadable, OSError, ValueError):
        return ""
    if not is_bounded:
        debug("final_output: this turn's boundary could not be found; reading nothing")
        return ""
    return "\n\n".join(latest).strip()[:MAX_FINAL_OUTPUT_CHARS]
