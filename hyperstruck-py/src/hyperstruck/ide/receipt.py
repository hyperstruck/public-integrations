"""Evidence that the editor accepted the recall, taken from the editor's own record.

The boundary credits a learning only once something confirms the model was shown it,
and this is the only part of the loop that can see anything of the sort. What it must
not do is answer with its own claim: echoing back the block this client emitted would
match every offered rule by construction and assert exactly the thing the receipt is
supposed to evidence. That failure is not hypothetical. Cursor's prompt hook cannot
inject at all, so the recall rides on a tool event; a Cursor turn that calls no tool
resolves learnings and never shows them, and a self-asserted receipt would credit every
one of those turns.

So the artefact is the editor's, not ours. Claude Code writes each accepted hook context
into its transcript as its own record, distinct from the record of what the hook printed,
and that record reflects the editor's decision: a denied, failed or dropped injection
leaves none. It is still one hop short of proof, because compaction and context eviction
happen downstream of it, and no editor exposes the prompt as sent. The boundary's states
carry that distinction rather than hiding it, and a run with no record credits nothing.

Which record belongs to which run is decided by an identifier this client mints and
stamps into the block, never by position in the file. The transcript is append-only
across every turn of a session, so counting records would let one denied hook shift every
later pairing and attribute a verdict to the wrong learnings, which is worse than sending
nothing at all. The marker leads the block so a truncated tail still resolves to the right
run, and the truncation then shows up honestly as the missing rules being absent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hyperstruck.ide.debug import debug

_MARKER_PREFIX = "hyperstruck-run"
_ACCEPTED_RECORD = "hook_additional_context"
# A transcript grows for the life of a session and is read on the turn's own stop hook,
# so the read is bounded by refusing an implausible file rather than by trusting it.
_MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024


def marker(run_id: str) -> str:
    return f"<!-- {_MARKER_PREFIX}: {run_id} -->"


def stamp(injected_text: str, run_id: str) -> str:
    """Lead the block with the identifier its receipt will be found by."""
    return f"{marker(run_id)}\n{injected_text}"


def _accepted_content(record: dict[str, Any], run_marker: str) -> str:
    """Only the entries of this record that carry our marker.

    A record's content is a list, and the editor is free to put other hooks' context
    beside ours. Joining the whole list would upload a sibling hook's output to the
    hosted API for no benefit: the matcher only ever looks for our own fragments.

    A record that carries the marker and does not match this shape is reported rather
    than skipped. It means the editor changed how it records an accepted hook context,
    which silently ends the whole credit path: every run would report nothing and the
    boundary would read it as a corpus with nothing worth crediting.
    """
    attachment = record.get("attachment")
    if not isinstance(attachment, dict):
        debug("receipt: a marked record has no attachment object; transcript format changed?")
        return ""
    if attachment.get("type") != _ACCEPTED_RECORD:
        debug(
            "receipt: a marked record is a "
            f"{attachment.get('type')!r} attachment, not {_ACCEPTED_RECORD!r}"
        )
        return ""
    content = attachment.get("content")
    entries = content if isinstance(content, list) else [content]
    return "\n".join(
        str(item) for item in entries if item and run_marker in str(item)
    )


def acceptance_record(transcript_path: str | None, run_id: str) -> str | None:
    """What the editor recorded itself accepting for this run, if anything.

    Every failure answers ``None``: no transcript, an unreadable or implausible file, a
    line that does not parse, or no record carrying this run's marker. That is the same
    answer as a host that never reported, which is the honest one, because in all of
    these cases nothing observed what the model was shown.

    Several records can carry one run's marker when the recall is injected on more than
    one tool event. They are joined rather than reduced to the first, because exposure is
    a disjunction over a learning's offers and a rule shown in the second block is shown.
    """
    if not transcript_path or not run_id:
        return None
    run_marker = marker(run_id)
    try:
        path = Path(transcript_path)
        if not path.is_file():
            debug(f"receipt: no transcript at {transcript_path}")
            return None
        size = path.stat().st_size
        if size > _MAX_TRANSCRIPT_BYTES:
            debug(f"receipt: transcript too large to read ({size} bytes)")
            return None
        # Streamed, not materialised: the file is read on the turn's own stop hook and
        # can be tens of megabytes, and only the handful of lines carrying this run's
        # marker are ever of interest. utf-8 explicitly, because decoding with the
        # platform locale would mangle a non-ASCII rule into a mismatch, which the
        # boundary then records as the model never having been shown it.
        accepted: list[str] = []
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if run_marker not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                content = _accepted_content(record, run_marker)
                if content:
                    accepted.append(content)
    except (OSError, ValueError) as exc:
        debug(f"receipt: transcript unreadable ({type(exc).__name__}): {exc}")
        return None

    if not accepted:
        debug(f"receipt: no acceptance record for run {run_id}")
        return None
    return "\n".join(accepted)
