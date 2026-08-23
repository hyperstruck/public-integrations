"""Per-turn state shared across the three hook processes via the session dir.

The prompt-submit hook, the per-tool hooks, and the stop hook are separate OS
processes, so disk is the only channel between them. State is keyed by the
editor's session id under ``~/.hyperstruck/sessions/<session_id>/``.

The single-process turn-start and turn-end hooks own ``active.json`` and
``pending.json`` and write them atomically (temp + rename). The detached resolver
hands recall to the first tool hook through ``recall.json``; a hook validates a
non-destructive peek of the file, then atomically renames it to claim, so
parallel tools cannot inject twice and a failed validation leaves the stash for
a later hook. Tool steps remain append-only files under ``active/steps/`` so
concurrent captures cannot drop one another. Every read tolerates a missing or
partial file and returns ``None`` (the loop fails open).
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from hyperstruck.ide.constants import (
    ACTIVE_FILE,
    ACTIVE_SUBDIR,
    FLUSH_ATTEMPT_SUFFIX,
    FLUSHING_SUBDIR,
    INJECTION_POINT_FILE,
    PENDING_FILE,
    RECALL_FILE,
    RECALL_STATUS_FILE,
    STEPS_SUBDIR,
    dropped_flush_log,
    sessions_dir,
)


@dataclass(frozen=True)
class ActiveTurn:
    """The turn in progress: written at turn start, before any tool runs."""

    run_id: str
    agent_name: str
    goal: str
    source_framework: str
    started_at: float
    # Offered learnings are merged only when a tool hook successfully injects
    # their recall, then carried to pending so deferred reinforce can credit them.
    offered_learning_ids: tuple[str, ...] = field(default_factory=tuple)
    offered_claim_ids: tuple[str, ...] = field(default_factory=tuple)
    is_injected: bool = False
    # Where the editor keeps its own record of what it accepted. Stored at turn start
    # because the backstop sweep finalises an abandoned turn from another session, with
    # no payload of its own to read it from; without it those turns credit nothing.
    transcript_path: str = ""
    # The project this turn is working in, which is what the warm stash is keyed on. The
    # detached resolver publishes that stash and is handed only a session id, so the cwd
    # has to travel on the turn rather than being read from the resolver's own process.
    cwd: str = ""
    # Whether this turn showed the project's warm stash at prompt time. Carried so the
    # turn can report an exposure that is real and deliberately uncreditable, which is
    # otherwise indistinguishable from having been shown nothing at all.
    is_stash_emitted: bool = False
    # A digest of the warm stash this turn opened with, so its own recall can decline to
    # show an identical block a second time.
    stash_block_digest: str = ""


@dataclass(frozen=True)
class FinishedTurn:
    """A turn that has ended, carrying everything its delivery needs except its label.

    Built in memory at the turn's own stop and staged immediately. The label travels
    beside it rather than on it, because a record that carried one would have two
    sources of truth for the same verdict and only one of them read.
    """

    run_id: str
    agent_name: str
    goal: str
    steps: tuple[dict[str, Any], ...]
    source_framework: str
    ended_at: float
    offered_learning_ids: tuple[str, ...] = field(default_factory=tuple)
    offered_claim_ids: tuple[str, ...] = field(default_factory=tuple)
    # Carried from the active turn so a declined turn can still report whether the
    # recall reached the model: a turn can be shown its learnings and then do too
    # little to be worth learning from, and only the host knows which happened.
    is_injected: bool = False
    # What the editor recorded itself accepting for this turn, its own artefact rather
    # than this client's claim. Empty when the host produced none, which credits nothing.
    context_receipt: str = ""
    # Why that receipt is empty, from RecallOutcome. Carried to the boundary so an
    # undelivered recall stops being reported as a lost receipt.
    recall_outcome: str = ""


def session_dir(session_id: str) -> Path:
    return sessions_dir() / safe_name(session_id)


# -- active turn -------------------------------------------------------------


def write_active(
    session_id: str, turn: ActiveTurn, *, reset_steps: bool = True
) -> None:
    """Record the turn in progress.

    ``reset_steps`` clears leftover per-step files for a genuine turn start (the
    prompt hook). The lazy turn-start in the per-tool hook passes ``False``: there
    the steps dir may already hold a sibling tool call's step written by a
    parallel hook process, and resetting it would drop that step.
    """
    sdir = session_dir(session_id)
    steps_dir = sdir / ACTIVE_SUBDIR / STEPS_SUBDIR
    if reset_steps:
        clear_recall(session_id)
        _reset_dir(steps_dir)
    else:
        ensure_private_dir(steps_dir)
    write_json_atomic(sdir / ACTIVE_FILE, asdict(turn))


def read_active(session_id: str) -> ActiveTurn | None:
    data = read_json(session_dir(session_id) / ACTIVE_FILE)
    if not data:
        return None
    try:
        return ActiveTurn(
            run_id=data["run_id"],
            agent_name=data.get("agent_name") or data.get("agent_id", ""),
            goal=data.get("goal", ""),
            source_framework=data.get("source_framework", ""),
            started_at=float(data.get("started_at", 0.0)),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
            offered_claim_ids=tuple(data.get("offered_claim_ids") or ()),
            is_injected=bool(data.get("is_injected", False)),
            transcript_path=data.get("transcript_path", ""),
            cwd=data.get("cwd", ""),
            is_stash_emitted=bool(data.get("is_stash_emitted", False)),
            stash_block_digest=data.get("stash_block_digest", ""),
        )
    except (KeyError, TypeError, ValueError):
        return None


def clear_active(session_id: str) -> None:
    sdir = session_dir(session_id)
    _remove(sdir / ACTIVE_FILE)
    _remove_tree(sdir / ACTIVE_SUBDIR)


# -- detached recall handoff -------------------------------------------------


def write_recall(session_id: str, recall: dict[str, Any]) -> None:
    """Atomically publish one detached resolve result for the active turn."""
    write_json_atomic(session_dir(session_id) / RECALL_FILE, recall)


def peek_recall(session_id: str) -> dict[str, Any] | None:
    """Read the recall stash without consuming it, for pre-claim validation."""
    data = read_json(session_dir(session_id) / RECALL_FILE)
    return data if isinstance(data, dict) else None


def claim_recall(session_id: str) -> dict[str, Any] | None:
    """Atomically consume the recall stash so at most one parallel hook can emit it.

    Destructive on every path, including a claim the caller then discards: the
    stash is one-shot, so validate via ``peek_recall`` first and claim only when
    ready to emit.
    """
    sdir = session_dir(session_id)
    source = sdir / RECALL_FILE
    claimed = sdir / f".{RECALL_FILE}.{uuid.uuid4().hex}.processing"
    try:
        os.replace(source, claimed)
    except OSError:
        return None
    try:
        data = read_json(claimed)
        return data if isinstance(data, dict) else None
    finally:
        _remove(claimed)


def write_recall_status(session_id: str, run_id: str, outcome: str) -> None:
    """Record what the detached resolve did, for the stop hook to read back.

    The resolve runs in its own process whose only other channel is a stderr nobody
    reads, so a resolve that timed out, failed or arrived for a superseded turn left
    no trace at all. Written for the successful case too, because "the stash was
    published and no tool event ever claimed it" is a different answer from "no
    resolve ever landed", and the turn cannot tell them apart from an absent file.

    One slot per session, and the live turn owns it. A slow resolver for turn N returns
    after turn N+1 has started and published its own verdict; an unguarded write would
    replace it, and N+1's stop hook would then reject the mismatched run and report the
    least informative answer in the vocabulary. So a resolver whose run is no longer the
    active one may take a free slot or refresh its own, and never overwrites another
    run's. The active run always may, because a stale verdict cannot outrank the turn
    that is still running.
    """
    if not _may_take_status_slot(session_id, run_id):
        return
    write_json_atomic(
        session_dir(session_id) / RECALL_STATUS_FILE,
        {"run_id": run_id, "outcome": outcome},
    )


def _may_take_status_slot(session_id: str, run_id: str) -> bool:
    held = read_json(session_dir(session_id) / RECALL_STATUS_FILE)
    if not isinstance(held, dict) or held.get("run_id") in (None, run_id):
        return True
    active = read_active(session_id)
    return active is not None and active.run_id == run_id


def read_recall_status(session_id: str, run_id: str) -> str | None:
    """This run's resolve verdict, or ``None`` when the file is absent or another run's."""
    data = read_json(session_dir(session_id) / RECALL_STATUS_FILE)
    if not isinstance(data, dict) or data.get("run_id") != run_id:
        return None
    outcome = data.get("outcome")
    return str(outcome) if outcome else None


def clear_recall(session_id: str) -> None:
    """Drop published or in-flight recall state when its turn is retired."""
    sdir = session_dir(session_id)
    _remove(sdir / RECALL_FILE)
    _remove(sdir / RECALL_STATUS_FILE)
    if not sdir.is_dir():
        return
    for path in sdir.glob(f"{INJECTION_POINT_FILE}-*"):
        _remove(path)
    for path in sdir.glob(f".{RECALL_FILE}.*.processing"):
        _remove(path)


def _injection_point_path(session_id: str, run_id: str) -> Path:
    """One marker per run, so a turn can never inherit the previous turn's answer.

    Every other cross-process artefact here carries its ``run_id`` and is checked against
    the turn reading it. The marker held none, and ``write_active(reset_steps=False)`` (the
    lazy turn start in the per-tool hook) does not clear recall state, so a turn started
    that way after an unparsable ``active.json`` inherited the previous turn's marker and
    reported ``RECALL_UNCLAIMED`` -- the actionable half -- for a turn that never had
    anywhere to show anything. Naming the file after the run closes that by construction
    rather than by remembering to clear it, and creating a file stays atomic either way.
    """
    return session_dir(session_id) / f"{INJECTION_POINT_FILE}-{safe_name(run_id)}"


def mark_injection_point(session_id: str, run_id: str) -> bool:
    """Record that the host fired the hook that can show this turn's recall.

    A marker file rather than a field on the active turn. Tool hooks run as parallel
    processes with no lock, so a read-modify-write of ``active.json`` from one of them can
    clobber another's ``is_injected`` and offered ids between its read and its write, losing
    the credit for rules that were genuinely shown. Creating a file is atomic and carries no
    other state, so parallel hooks cannot destroy each other's work.

    Returns whether the mark landed. A silent failure here is not neutral: it reads back as
    "there was nowhere to show anything", which is the structural verdict with no remedy,
    so an unwritable session dir would quietly relabel every real drop as nothing to fix.
    """
    sdir = session_dir(session_id)
    try:
        ensure_private_dir(sdir)
        _injection_point_path(session_id, run_id).touch()
    except OSError:
        return False
    return True


def has_injection_point(session_id: str, run_id: str) -> bool:
    """Whether the injecting hook ever fired for this run."""
    return _injection_point_path(session_id, run_id).exists()


# -- per-step append files ---------------------------------------------------


def append_step(session_id: str, step: dict[str, Any]) -> None:
    """Write ONE append-only per-step file. Safe under parallel tool hooks.

    The filename is time-ordered and uuid-unique, so concurrent processes never
    collide and the stop hook can merge in execution order.
    """
    steps_dir = session_dir(session_id) / ACTIVE_SUBDIR / STEPS_SUBDIR
    ensure_private_dir(steps_dir)
    name = f"{time.time_ns():020d}-{uuid.uuid4().hex}.json"
    write_json_atomic(steps_dir / name, step)


def read_steps(session_id: str) -> list[dict[str, Any]]:
    """Merge the per-step files in time order. Skips any unreadable file."""
    steps_dir = session_dir(session_id) / ACTIVE_SUBDIR / STEPS_SUBDIR
    if not steps_dir.is_dir():
        return []
    steps: list[dict[str, Any]] = []
    for path in sorted(steps_dir.iterdir(), key=lambda p: p.name):
        if path.suffix != ".json":
            continue
        data = read_json(path)
        if isinstance(data, dict):
            steps.append(data)
    return steps


# -- turn retirement ---------------------------------------------------------


def retire_active(session_id: str) -> None:
    """Close out a turn once it has been staged for delivery."""
    clear_active(session_id)
    clear_recall(session_id)


def read_pending(session_id: str) -> tuple[FinishedTurn, bool] | None:
    """A turn an earlier release deferred to disk, with the label that file recorded.

    The label comes back alongside the turn rather than on it, because it is the older
    code's verdict travelling with older data, not something this release computed.
    """
    return _pending_from_dict(read_json(session_dir(session_id) / PENDING_FILE))


def clear_pending(session_id: str) -> None:
    _remove(session_dir(session_id) / PENDING_FILE)


# -- flush handoff -----------------------------------------------------------


def stage_flush(session_id: str, run_id: str, episode_payload: dict[str, Any]) -> Path:
    """Hand a resolved episode to a detached flush, keyed by the real run id.

    Writing it under ``flushing/`` decouples delivery from the turn lifecycle, so
    the next turn can proceed while the flush runs in another process. The filename
    uses the caller's *un-redacted* run id (the redacted episode's run id would
    collapse to a constant and collide across turns, overwriting an undelivered
    episode).

    That name is the single-delivery guard: one run id yields one path, so a second
    stage of the same turn atomically replaces the first file rather than adding a
    second one, and the run can be delivered at most once. Two writers can reach the
    same turn now that a stop and the sweep's orphan recovery both stage directly. A
    uuid is used only when there is no run id to key on, where there is no identity
    to collapse onto and losing one write would be worse than delivering two.
    """
    flush_dir = session_dir(session_id) / FLUSHING_SUBDIR
    ensure_private_dir(flush_dir)
    name = safe_name(run_id) if run_id else f"unkeyed-{uuid.uuid4().hex}"
    path = flush_dir / f"{name}.json"
    write_json_atomic(path, episode_payload)
    return path


def read_flush(path: str | os.PathLike[str]) -> dict[str, Any] | None:
    return read_json(Path(path))


def record_flush_attempt(path: str | os.PathLike[str]) -> int | None:
    """Record one failed delivery attempt and return the running total.

    Attempts live in a sidecar so retry metadata never corrupts the staged episode
    payload. The count is one atomic append per attempt (not a read-modify-write),
    so two flush processes racing on the same payload can never lose an increment
    and exceed the retry cap. ``None`` means another process already delivered and
    removed the payload, so there is nothing left to retry.
    """
    flush_path = Path(path)
    if not flush_path.is_file():
        return None
    attempt_path = _flush_attempt_path(flush_path)
    ensure_private_dir(attempt_path.parent)
    fd = os.open(attempt_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, b"x\n")
    finally:
        os.close(fd)
    if not flush_path.is_file():
        _remove(attempt_path)
        return None
    return read_flush_attempts(flush_path)


def read_flush_attempts(path: str | os.PathLike[str]) -> int:
    try:
        with _flush_attempt_path(Path(path)).open("rb") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return 0


def record_dropped_flush(
    path: str | os.PathLike[str],
    *,
    run_id: str,
    agent_name: str,
    attempts: int,
    cause: str | None,
) -> None:
    """Append a durable record of a flush dropped after exhausting its retry cap.

    A dropped flush is a learning lost for good, and the detached flush process's
    stderr is ``/dev/null``, so the loss is recorded as one JSON line under the
    loop root where an operator can see what was discarded and why. The cause is a
    coarse tag (e.g. ``HTTP 422``), never the payload, so no prompt content leaks.
    """
    record = {
        "at": time.time(),
        "run_id": run_id,
        "agent_name": agent_name,
        "attempts": attempts,
        "cause": cause,
        "path": str(path),
    }
    log_path = dropped_flush_log()
    ensure_private_dir(log_path.parent)
    line = (json.dumps(record) + "\n").encode("utf-8")
    fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def remove_flush(path: str | os.PathLike[str]) -> None:
    flush_path = Path(path)
    _remove(flush_path)
    _remove(_flush_attempt_path(flush_path))


def iter_flush_files(session_id: str) -> list[Path]:
    """Staged flush files for a session (orphans left by a killed flush process)."""
    flush_dir = session_dir(session_id) / FLUSHING_SUBDIR
    if not flush_dir.is_dir():
        return []
    return [p for p in flush_dir.iterdir() if p.suffix == ".json"]


# -- sweeping ----------------------------------------------------------------


def all_session_ids() -> list[str]:
    base = sessions_dir()
    if not base.is_dir():
        return []
    return [p.name for p in base.iterdir() if p.is_dir()]


def remove_session_if_empty(session_id: str) -> None:
    """Remove a session dir once it holds no active, pending, or flush state."""
    sdir = session_dir(session_id)
    if not sdir.is_dir():
        return
    if (sdir / ACTIVE_FILE).exists() or (sdir / PENDING_FILE).exists():
        return
    if (sdir / RECALL_FILE).exists():
        return
    if iter_flush_files(session_id):
        return
    _remove_tree(sdir)


# -- serialisation helpers ---------------------------------------------------


def _pending_from_dict(
    data: dict[str, Any] | None,
) -> tuple[FinishedTurn, bool] | None:
    if not data:
        return None
    try:
        turn = FinishedTurn(
            run_id=data["run_id"],
            agent_name=data.get("agent_name") or data.get("agent_id", ""),
            goal=data.get("goal", ""),
            steps=tuple(data.get("steps") or ()),
            source_framework=data.get("source_framework", ""),
            ended_at=float(data.get("ended_at", 0.0)),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
            offered_claim_ids=tuple(data.get("offered_claim_ids") or ()),
            # Every field written must be read back. is_injected was already missing here,
            # so a pending turn reloaded from disk always reported False and the decline
            # payload's is_delivered was permanently wrong.
            is_injected=bool(data.get("is_injected", False)),
            context_receipt=data.get("context_receipt", ""),
            recall_outcome=data.get("recall_outcome", ""),
        )
    except (KeyError, TypeError, ValueError):
        return None
    return turn, bool(data.get("is_success", True))


# -- filesystem primitives ---------------------------------------------------


def ensure_private_dir(path: Path) -> None:
    """Create a directory (and parents) restricted to the owner (0700).

    Turn state holds the user's prompts and command output, so it is kept private
    like the auth ``.env``. The owner-only mode also blocks another local user from
    entering the session dir to read its files.
    """
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def write_json_atomic(path: Path, obj: Any) -> None:
    """Write JSON via a temp file + rename so a reader never sees a partial.

    Public because the warm stash writes with it too. It lives outside the session dir
    but under the same root, holding the same kind of content, so it wants the same
    owner-only mode and the same guarantee that a concurrent reader never sees a partial
    file. A second implementation of either would be a second thing to get wrong.
    """
    ensure_private_dir(path.parent)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle)
    try:
        os.chmod(tmp, 0o600)  # state files hold prompts/command output: owner-only
    except OSError:
        pass
    os.replace(tmp, path)


def read_json(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _reset_dir(path: Path) -> None:
    _remove_tree(path)
    ensure_private_dir(path)


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    try:
        for child in path.iterdir():
            if child.is_dir():
                _remove_tree(child)
            else:
                _remove(child)
        path.rmdir()
    except OSError:
        pass


def _flush_attempt_path(path: Path) -> Path:
    return path.with_name(f"{path.name}{FLUSH_ATTEMPT_SUFFIX}")


def safe_name(name: str) -> str:
    """A filesystem-safe single path component for a session/run id.

    Slashes are already mapped to ``_``; dot-segments (``.``/``..``) are mapped to
    the fallback too, so an editor-supplied id cannot escape the session dir into
    ``~/.hyperstruck`` (next to the ``.env``).
    """
    cleaned = "".join(
        c if c.isalnum() or c in "-_." else "_" for c in (name or "").strip()
    )
    if cleaned in ("", ".", ".."):
        return "default"
    return cleaned
