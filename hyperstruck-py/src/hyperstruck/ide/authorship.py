"""Who started a turn, read from the host's own record of the prompt.

A host puts more into the user's turn than the user typed: a subagent's report, a background
task's notification. The wrapper list in ``host_vocabularies`` recognises those by their markup,
and markup drifts. Where the host also *records* who started the turn, that record is the better
witness, and this is where it is read.

It is read at the end of the turn, when the record is certainly written, and found by text: the
prompt hook stores the goal scrubbed, clipped and stripped of some envelopes, so each candidate
record is put through the same transform before it is compared.

**Every miss abstains.** A reading that cannot be made leaves the turn to the wrapper list exactly
as before, under a reason the debug trace names, because a wrong "nobody started this" silently
deletes a person's words from the corpus.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from hyperstruck.ide.constants import TRUNCATION_MARKER
from hyperstruck.ide.debug import debug
from hyperstruck.ide.host_vocabularies import (
    is_turn_origin_a_principal,
    prompt_envelope,
    turn_origins,
)
from hyperstruck.ide.prompt_spans import (
    principal_prose,
    prompt_spans,
    strip_harness_envelopes,
)
from hyperstruck.ide.redaction import clip_goal, scrub_secrets
from hyperstruck.ide.transcript import (
    TAIL_BYTES,
    TranscriptMissing,
    TranscriptUnreadable,
    iter_lines,
)

ORIGIN_FIELD = "turnOrigin"

REASON_NO_TABLE = "no_table"
REASON_UNREADABLE = "unreadable"
REASON_NO_RECORD = "no_record"
REASON_NO_FIELD = "no_field"
REASON_UNKNOWN_ORIGIN = "unknown_origin"


def _normalised(text: str) -> str:
    return " ".join(text.split())


@dataclass(frozen=True)
class TurnAuthorship:
    """What the host's record says about one turn.

    ``reason`` is the declared origin when one was read, and otherwise why the reading abstained
    or, for ``unknown_origin``, why nobody is credited.
    """

    is_without_principal: bool
    reason: str


def _abstain(reason: str) -> TurnAuthorship:
    debug(f"authorship: abstained ({reason}); the wrapper list decides this turn")
    return TurnAuthorship(is_without_principal=False, reason=reason)


def turn_authorship(transcript_path: str, goal: str, source: str) -> TurnAuthorship:
    """Who the host says started the turn whose stored goal is ``goal``."""
    if not turn_origins(source):
        return _abstain(REASON_NO_TABLE)
    if not transcript_path:
        return _abstain(REASON_UNREADABLE)
    wanted = _normalised(goal)
    try:
        record = _last_matching(
            iter_lines(transcript_path, what="authorship", tail_bytes=TAIL_BYTES),
            wanted,
            source,
        )
        if record is None:
            # The prompt opens the turn, so on a long turn it sits before the tail.
            record = _last_matching(
                iter_lines(transcript_path, what="authorship"), wanted, source
            )
    except (TranscriptMissing, TranscriptUnreadable):
        return _abstain(REASON_UNREADABLE)
    if record is None:
        return _abstain(REASON_NO_RECORD)
    origin = _recorded_origin(record)
    if not origin:
        return _abstain(REASON_NO_FIELD)
    is_principal = bool(is_turn_origin_a_principal(source, origin))
    if origin not in turn_origins(source):
        debug(f"authorship: undeclared turn origin {origin!r}; read as nobody")
        return TurnAuthorship(is_without_principal=True, reason=REASON_UNKNOWN_ORIGIN)
    return TurnAuthorship(is_without_principal=not is_principal, reason=origin)


def _last_matching(
    lines: Iterable[str], wanted: str, source: str
) -> dict[str, Any] | None:
    """The last prompt record that is this turn's prompt, an equal one before a wrapping one.

    A host does not always record the text it handed the prompt hook. Claude Code queues a
    subagent's report as a bare ``<agent-message>`` block, hands the hook that, and writes the
    record as the block inside a lead-in line and a closing paragraph, so the two are never equal.
    A record that wraps the goal in host text is therefore the same prompt. One equal to the goal
    is the surer match and wins wherever it sits, so a relayed message that quotes a typed prompt
    cannot claim that prompt's turn.
    """
    equal: dict[str, Any] | None = None
    wrapping: dict[str, Any] | None = None
    for line in lines:
        if '"user"' not in line and _ABSORBED_ATTACHMENT not in line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        text = _prompt_text(record)
        if text is None:
            continue
        unclipped = scrub_secrets(strip_harness_envelopes(text.strip(), source))
        if _normalised(clip_goal(unclipped)) == wanted:
            equal = record
        elif _is_wrapped_in_host_text(wanted, _normalised(unclipped), source):
            wrapping = record
    return equal or wrapping


# Shorter than this, a goal found inside another record is a coincidence, not the same prompt.
_MIN_WRAPPED_GOAL_CHARS = 40
_CLIP_SUFFIX = _normalised(TRUNCATION_MARKER)


def _lead_ins(source: str) -> frozenset[str]:
    """What may stand before a queued block in its record: nothing, or one declared opener."""
    return frozenset({""} | {_normalised(opener) for opener, _closer, _runs in prompt_envelope(source)})


def _is_wrapped_in_host_text(wanted: str, record_text: str, source: str) -> bool:
    """Whether ``record_text`` is the goal with nothing but host markup around it.

    Both arrive whitespace-normalised and the record unclipped: the goal was clipped at the
    boundary's bound before the host's lead-in was ever added, so the two are cut at different
    places and a clipped goal is compared as a prefix of what follows it in the record.
    """
    is_clipped = wanted.endswith(_CLIP_SUFFIX)
    goal = wanted[: -len(_CLIP_SUFFIX)].rstrip() if is_clipped else wanted
    if len(goal) < _MIN_WRAPPED_GOAL_CHARS:
        return False
    at = record_text.find(goal)
    if at < 0:
        return False
    # Only the host's own lead-in precedes a queued block; anything else is a record quoting the goal.
    if record_text[:at].strip() not in _lead_ins(source):
        return False
    around = record_text[:at] + ("" if is_clipped else record_text[at + len(goal) :])
    return principal_prose(prompt_spans(around, source)) is None


# A prompt the host took in while a turn was running: an attachment, never a ``user`` record.
_ABSORBED_ATTACHMENT = "queued_command"


def _absorbed(record: dict[str, Any]) -> dict[str, Any] | None:
    """The queued prompt this record carries, when it is one the host absorbed mid-turn."""
    attachment = record.get("attachment")
    if (
        record.get("type") == "attachment"
        and isinstance(attachment, dict)
        and attachment.get("type") == _ABSORBED_ATTACHMENT
    ):
        return attachment
    return None


def _recorded_origin(record: dict[str, Any]) -> str | None:
    """Who the host says started this prompt, in the spelling the origin table uses.

    A ``user`` record names it in ``turnOrigin``. An absorbed prompt names it in ``origin.kind``
    and spells the same value with a hyphen (``task-notification``), so it is read into one form.
    """
    absorbed = _absorbed(record)
    if absorbed is None:
        origin = record.get(ORIGIN_FIELD)
    else:
        declared = absorbed.get("origin")
        origin = declared.get("kind") if isinstance(declared, dict) else None
    return origin.replace("-", "_") if isinstance(origin, str) and origin else None


def _prompt_text(record: dict[str, Any]) -> str | None:
    """The text of a prompt the main conversation received, or ``None`` for anything else.

    A ``user`` record is also where the host writes a tool result, and a sidechain record is a
    subagent's own conversation. Neither opened a turn of this session.
    """
    if record.get("isSidechain"):
        return None
    absorbed = _absorbed(record)
    if absorbed is not None:
        prompt = absorbed.get("prompt")
        return prompt if isinstance(prompt, str) else None
    if record.get("type") != "user":
        return None
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    blocks = [block for block in content if isinstance(block, dict)]
    if any(block.get("type") == "tool_result" for block in blocks):
        return None
    texts = [
        block["text"]
        for block in blocks
        if block.get("type") == "text" and isinstance(block.get("text"), str)
    ]
    return "\n".join(texts) if texts else None
