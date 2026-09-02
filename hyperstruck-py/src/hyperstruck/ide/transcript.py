"""Reading the editor's own transcript, under one set of bounds.

Two callers read this file and they were reading it two ways. ``receipt`` looks for the lines
carrying a run's marker, anywhere in the session; ``final_output`` wants the closing prose of the
last assistant message, which is at the end by construction. What they share is the part that has to
be got right once: a transcript is append-only for the life of a session, it is read on the turn's
own stop hook, and it can be tens of megabytes, so it is refused above a ceiling, streamed rather
than materialised, and decoded as utf-8 explicitly because the platform locale would mangle a
non-ASCII line into a mismatch.

That was duplicated down to a re-declared 64MB constant, which is how the two come to disagree about
what "too large" means and then behave differently on the same file.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from hyperstruck.ide.debug import debug

# A transcript grows for the life of a session and is read on the turn's own stop hook, so the read
# refuses an implausible file rather than trusting it. One declaration, because two readers with two
# ceilings is a file one of them will read and the other will not.
MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024

# How much of the end of the file a tail read looks at.
#
# Bounded in BYTES, not in records. A per-record bound says nothing about the work: a turn's last
# fifty records can be fifty tool results of a megabyte each, and a reader that promised to look at
# a bounded number of them still read fifty megabytes. This is the number that actually bounds it.
#
# 4 MiB against a composed answer clipped at 32,000 characters is roughly two orders of magnitude of
# slack, so the closing message is inside it on any ordinary turn. When it is not, the caller falls
# back to a full scan rather than answering wrong: cheap in the common case, never less correct than
# reading everything.
TAIL_BYTES = 4 * 1024 * 1024


class TranscriptMissing(Exception):
    """There is no file at that path."""


class TranscriptUnreadable(Exception):
    """There is a file and it could not be read: too large, or the read itself failed."""


def iter_lines(
    transcript_path: str | Path, *, what: str, tail_bytes: int | None = None, max_bytes: int | None = None
) -> Iterator[str]:
    """Yield the transcript's lines, streamed.

    ``tail_bytes`` reads only the end of the file, dropping the first line it lands in because a
    byte offset lands mid-record and half a JSON object is not a record. Omitted, the whole file is
    streamed, which is what a caller looking for something that can be anywhere in the session
    needs.

    **Failure is raised, not swallowed, and that is not the callers' posture being ignored.** Both
    of them fail open and neither may cost a turn its episode, but they answer differently and one
    of those answers is load-bearing: ``receipt`` must report TRANSCRIPT_UNREADABLE rather than
    NO_MATCHING_RECORD, because the second writes a claim that the recall was never delivered and
    the boundary's delivery latch only moves one way. A reader that returned an empty iterator for
    both would have made "unreadable" indistinguishable from "nothing matched", silently. Since it
    is a generator, these surface on the first iteration, inside the caller's own guard.
    """
    path = Path(transcript_path)
    if not path.is_file():
        debug(f"{what}: no transcript at {transcript_path}")
        raise TranscriptMissing(str(transcript_path))
    try:
        # ``max_bytes`` is the caller's own ceiling where it has one, so a caller that lowers its
        # limit (a test, or a host that knows its transcripts are small) still gets the refusal.
        # Defaulted rather than fixed, because a single module-level constant read here would make
        # every caller's ceiling unpatchable and silently ignored.
        ceiling = MAX_TRANSCRIPT_BYTES if max_bytes is None else max_bytes
        size = path.stat().st_size
        if size > ceiling:
            debug(f"{what}: transcript too large to read ({size} bytes)")
            raise TranscriptUnreadable(f"{size} bytes")
        # Opened in BINARY and decoded per line. A text handle's ``seek`` takes an opaque cookie
        # encoding decoder state, not a byte offset, so seeking to one on a text stream is not the
        # operation it looks like. Decoding each line here keeps the explicit utf-8 and the
        # replacement behaviour the text handle gave, with an offset that means what it says.
        with path.open("rb") as handle:
            if tail_bytes is not None and size > tail_bytes:
                handle.seek(size - tail_bytes)
                handle.readline()  # the record this offset landed inside, necessarily partial
            for line in handle:
                yield line.decode("utf-8", errors="replace")
    except OSError as exc:
        debug(f"{what}: transcript unreadable ({type(exc).__name__}): {exc}")
        raise TranscriptUnreadable(str(exc)) from exc
