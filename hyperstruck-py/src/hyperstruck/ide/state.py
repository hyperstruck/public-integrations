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
    CHECKPOINT_CLAIM_FILE,
    FLUSH_ATTEMPT_SUFFIX,
    FLUSHING_SUBDIR,
    INJECTION_POINT_FILE,
    PENDING_FILE,
    RECALL_FILE,
    RECALL_STATUS_FILE,
    SHOWN_BLOCK_FILE,
    STEPS_SUBDIR,
    checkpoint_drift_log,
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
    # What the release that started this turn had already offered it. Nothing writes these
    # either: a turn started under this release carries its offers on the shown-block marker
    # of the block that made them, one marker per block, and ``_offered_this_turn`` reads
    # both so an upgrade mid-turn credits what the older file recorded. A third kind of
    # offer belongs on the marker beside those two, not here, where nothing would read it.
    offered_learning_ids: tuple[str, ...] = field(default_factory=tuple)
    offered_claim_ids: tuple[str, ...] = field(default_factory=tuple)
    # TODO(ceiling): a one-release carrier, like the pending drain in ``_sweep_stale``.
    # Remove it and the branch that reads it in ``_is_credited`` one release after this
    # ships, by which point no turn in flight can predate the shown-block marker.
    #
    # Whether the release that started this turn had already shown it a block, which is
    # the only thing that record can still tell us. That release kept the answer here, as
    # ``is_injected``; this one keeps it in a shown-block marker per block, so nothing
    # writes this field any more and a turn started under this release always reads False.
    #
    # It is not the live answer and must not be read as one. Blocks shown by this release
    # are counted from the markers, because a field on the active turn is read by each
    # parallel hook before the others write and a hook whose write lands last restores what
    # it read. That costs whatever the field was carrying, and the credit for a block that
    # genuinely reached the model is not something to lose that way.
    is_injected_by_previous_release: bool = False
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
    # show an identical block a second time. Written once, by the one prompt hook, and
    # never touched again; the blocks shown *during* the turn are recorded as marker files
    # instead, because the hooks that show them run in parallel.
    stash_block_digest: str = ""
    # The editor process that started this turn, so the backstop sweep can tell a session
    # that died from one merely sitting still. Idleness cannot: a turn blocked on a tool
    # permission prompt writes nothing while it waits and is indistinguishable from a
    # killed one by any clock, and declining it would delete the state the live turn still
    # needs. Zero means the client that wrote this record did not supply one, which reads
    # as unknown and falls back to the age gate.
    editor_pid: int = 0


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
    # The closing prose of the turn's last assistant message, read from the editor's transcript at
    # the turn's own stop. The obligation shelf's own-output lane reads it for the commitments the
    # assistant made in it; empty whenever it could not be read, which costs nothing.
    final_output: str = ""
    # The project this turn ran in; the detached flush reads it for a locator.
    cwd: str = ""


# Attempts a turn-start recall gets at the slot before giving up. Each pass either links,
# yields to a checkpoint of its own run, or clears an occupant it outranks, so more than one
# pass is needed only when another process moves the slot underneath this one.
_RECALL_PUBLISH_ATTEMPTS = 3


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
            # A client is upgraded in place while turns are in flight, so this file was
            # written by whichever release wrote it. An in-flight turn read as never
            # injected shows its block a second time and loses the credit for the first.
            is_injected_by_previous_release=bool(
                data.get("is_injected_by_previous_release") or data.get("is_injected")
            ),
            transcript_path=data.get("transcript_path", ""),
            cwd=data.get("cwd", ""),
            is_stash_emitted=bool(data.get("is_stash_emitted", False)),
            stash_block_digest=data.get("stash_block_digest", ""),
            # Absent from every record written before this field existed, and from any
            # host that cannot supply one. Both read as 0 and take the age gate.
            editor_pid=int(data.get("editor_pid") or 0),
        )
    except (KeyError, TypeError, ValueError):
        return None


def has_active(session_id: str) -> bool:
    """Whether this session holds an active turn at all, without reading it.

    Asked where the answer decides whether to delete state a live turn still needs, because
    ``read_active`` cannot tell "no turn here" from "this turn could not be read just now".
    It folds both into ``None``: ``read_json`` swallows ``OSError`` into it, and a hook that
    hits a descriptor limit against the parallel checkpoint subprocesses this loop now spawns
    gets that answer about a turn that is very much alive. Existence is the question actually
    being asked, and the file it asks about is written through ``os.replace``, so it is
    either the previous turn's or the current one's and never a partial write.
    """
    return (session_dir(session_id) / ACTIVE_FILE).exists()


def clear_active(session_id: str) -> None:
    sdir = session_dir(session_id)
    _remove(sdir / ACTIVE_FILE)
    _remove_tree(sdir / ACTIVE_SUBDIR)


# -- detached recall handoff -------------------------------------------------


def write_recall(
    session_id: str, recall: dict[str, Any], *, is_exclusive: bool = False
) -> bool:
    """Atomically publish one detached resolve result, returning whether it landed.

    ``is_exclusive`` refuses rather than overwrites when a stash is already waiting to be
    claimed, and every checkpoint resolve uses it. There is one slot per session and
    ``write_recall`` replaces it wholesale, so a checkpoint returning while an earlier
    stash is still unclaimed would destroy an injection that was about to happen. Losing
    the checkpoint costs one stale block; losing the slot could lose the injection.

    Both paths publish by linking, never by replacing. The link is what makes a refusal a
    decision rather than a hope: it fails outright when the target exists, so two resolvers
    racing cannot both believe the slot was free. A read of the slot followed by a write to
    it is not the same guarantee and cannot be substituted for one, because the write does
    not check what it lands on.

    ``is_exclusive`` is what a checkpoint sets, and it means "refuse an occupied slot" full
    stop: a checkpoint returning while an earlier stash is still unclaimed would destroy an
    injection that was about to happen, and losing the checkpoint costs one stale block
    where losing the slot could lose the injection.

    The turn-start resolve refuses only its own turn's checkpoint, and displaces anything
    else. Its own turn cleared this slot at the start, so an occupant arrived afterwards:
    if that is a checkpoint of this run, the turn-start answer is the older one and yields,
    since replacing it would discard a block already resolved, charged and recorded on the
    server. A leftover from any other run never outranked it and still does not.
    """
    path = session_dir(session_id) / RECALL_FILE
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.exclusive"
    try:
        ensure_private_dir(path.parent)
        write_json_atomic(tmp, recall)
        if is_exclusive:
            return _link_recall(tmp, path)
        return _link_recall_displacing(tmp, path, recall.get("run_id"))
    except OSError:
        return False
    finally:
        _remove(tmp)


def _link_recall(tmp: Path, path: Path) -> bool:
    try:
        os.link(tmp, path)
    except OSError:
        return False
    return True


def _link_recall_displacing(tmp: Path, path: Path, run_id: Any) -> bool:
    """Link into the slot, clearing an occupant this caller outranks, and never blind.

    Retried rather than done in one shot because clearing the slot and taking it are two
    operations, and a checkpoint of this run can land between them: the loop re-reads
    before every attempt, so that checkpoint is seen and yielded to on the next pass rather
    than overwritten. Bounded, and a caller that loses every attempt publishes nothing,
    which is the same fail-open answer as a refusal.
    """
    for _ in range(_RECALL_PUBLISH_ATTEMPTS):
        if _link_recall(tmp, path):
            return True
        if _holds_checkpoint_of(path, run_id):
            return False
        _remove(path)
    return False


def _holds_checkpoint_of(path: Path, run_id: Any) -> bool:
    held = read_json(path)
    if not isinstance(held, dict) or held.get("run_id") != run_id:
        return False
    return bool(held.get("checkpoint_ordinal"))


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


def recover_run_id(session_id: str) -> str:
    """This turn's run id from the recall artefacts, when its active record is gone.

    Read from the two files that carry the id as data rather than in their name: the
    status slot and the published recall. The marker files spell it through
    ``safe_name``, which is not reversible, so they are no use here.

    Both are removed by ``retire_active`` alongside the active record and the steps, so a
    turn that was already staged recovers nothing here. That is the desired direction: it
    means recovery cannot re-deliver a turn some other path has already closed.
    """
    sdir = session_dir(session_id)
    for name in (RECALL_STATUS_FILE, RECALL_FILE):
        run_id = _run_id_in(read_json(sdir / name))
        if run_id:
            return run_id
    # The recall files are consumed when a tool hook claims the block, so on any turn that
    # was actually shown something they are already gone by stop. The shown-block markers
    # are not: they carry the id as data beside the digest in their name, and they live
    # until ``clear_recall`` removes them with the rest of the turn.
    if sdir.is_dir():
        for path in sorted(sdir.glob(f"{SHOWN_BLOCK_FILE}-*")):
            run_id = _run_id_in(read_json(path))
            if run_id:
                return run_id
    return ""


def _run_id_in(data: Any) -> str:
    if isinstance(data, dict):
        run_id = data.get("run_id")
        if isinstance(run_id, str) and run_id:
            return run_id
    return ""


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
    for path in sdir.glob(f".{RECALL_FILE}.*.exclusive"):
        _remove(path)
    for path in sdir.glob(f"{CHECKPOINT_CLAIM_FILE}-*"):
        _remove(path)
    for path in sdir.glob(f"{SHOWN_BLOCK_FILE}-*"):
        _remove(path)
    for path in sdir.glob(f".{SHOWN_BLOCK_FILE}-*.claiming"):
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
    processes with no lock, so a read-modify-write of ``active.json`` from one of them is
    restored by whichever hook read before it and wrote after, losing whatever the first was
    recording. Creating a file is atomic and carries no other state, so parallel hooks cannot
    destroy each other's work.

    That argument is why the shown-block marker is a file too, and why nothing about an
    injection is written back to the turn any more: this hazard took the injection record
    itself once, and a turn that reads as never injected reports a block the model received
    as a recall that never arrived.

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


def _shown_block_path(session_id: str, run_id: str, digest: str) -> Path:
    name = f"{SHOWN_BLOCK_FILE}-{safe_name(run_id)}-{safe_name(digest)}"
    return session_dir(session_id) / name


def claim_shown_block(
    session_id: str,
    run_id: str,
    digest: str,
    *,
    learning_ids: tuple[str, ...] = (),
    claim_ids: tuple[str, ...] = (),
) -> bool | None:
    """Take the right to show this block to this run: True taken, False already shown.

    ``None`` is the third answer and is not the second: the claim could not be written at
    all, so whether this run has shown this block is unknown rather than known to be yes.
    A caller that collapses the two records a disk fault as a verdict about the block.

    Asking whether a block has been shown and recording that it is about to be are the same
    act here, which is what a field on the active turn could never make them. Once a turn
    can hold more than one stash at a time, two tool hooks can each claim their own and each
    read "nothing like this has been shown" before either has written, and the customer sees
    the same advice twice with a second marker stamped on it.

    The ids the block offered ride along, so they are never merged into ``active.json``. That
    merge is a read-modify-write, and the one this replaces could drop a whole injection's
    worth of offers when the other hook's write landed second, making rules that genuinely
    reached the model uncreditable.

    A claim that cannot be written withholds the block, which shows one block fewer rather
    than showing the same one twice against an unwritable session dir.
    """
    path = _shown_block_path(session_id, run_id, digest)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.claiming"
    try:
        ensure_private_dir(path.parent)
        write_json_atomic(
            tmp,
            {
                "run_id": run_id,
                "digest": digest,
                "learning_ids": list(learning_ids),
                "claim_ids": list(claim_ids),
            },
        )
        os.link(tmp, path)
    except FileExistsError:
        return False
    except OSError:
        return None
    finally:
        _remove(tmp)
    return True


def release_shown_block(session_id: str, run_id: str, digest: str) -> None:
    """Give back a claim whose block the host then refused to take.

    The claimer holds this one exclusively, so releasing it races with nobody, and a block
    the editor declined was never put in front of the model. Keeping the claim would let one
    refusal silence every later resolve that reached the same advice.
    """
    _remove(_shown_block_path(session_id, run_id, digest))


def read_shown_blocks(session_id: str, run_id: str) -> list[dict[str, Any]]:
    """Every block this run has shown, in no particular order. Skips unreadable files."""
    sdir = session_dir(session_id)
    if not sdir.is_dir():
        return []
    prefix = f"{SHOWN_BLOCK_FILE}-{safe_name(run_id)}-"
    shown = []
    for path in sdir.glob(f"{prefix}*"):
        data = read_json(path)
        if isinstance(data, dict):
            shown.append(data)
    return shown


def _checkpoint_claim_path(session_id: str, run_id: str, ordinal: int) -> Path:
    name = f"{CHECKPOINT_CLAIM_FILE}-{safe_name(run_id)}-{ordinal}"
    return session_dir(session_id) / name


def is_checkpoint_claimed(session_id: str, run_id: str, ordinal: int) -> bool:
    """Whether this run's checkpoint has already been taken.

    Separate from taking it, so the tool hook can answer "is there any work left to do"
    with a stat before it reads and parses a turn's worth of step files. It runs on every
    tool call, on the editor's synchronous path, and for most of a long turn the answer is
    no.
    """
    return _checkpoint_claim_path(session_id, run_id, ordinal).exists()


def claim_checkpoint(session_id: str, run_id: str, ordinal: int) -> bool:
    """Take one run's checkpoint, returning whether this caller got it.

    Exclusive creation, so of the parallel tool hooks that all observe the same threshold
    on the same steps directory exactly one spawns the resolve. Nothing releases a claim:
    a checkpoint fires once per run, which is what bounds a turn to two extra resolves
    however long it runs. Named after the run for the same reason the injection point is,
    so a lazily started turn cannot inherit the previous turn's claims.

    A claim that cannot be written is read as taken, which loses the checkpoint rather
    than letting every racing hook spawn a resolve against an unwritable session dir.
    """
    sdir = session_dir(session_id)
    try:
        ensure_private_dir(sdir)
        fd = os.open(
            _checkpoint_claim_path(session_id, run_id, ordinal),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
    except OSError:
        return False
    os.close(fd)
    return True


def record_checkpoint(
    *,
    run_id: str,
    ordinal: int,
    outcome: str | None = None,
    drift: float | None = None,
    is_block_changed: bool | None = None,
    is_injected: bool = False,
) -> None:
    """Append what one checkpoint did: its outcome, its drift, and what it changed.

    Append-only and keyed by nothing, which is the point. ``RECALL_STATUS_FILE`` holds one
    verdict per session and the live turn owns it, so a second checkpoint writing there
    would erase the first one's answer and a turn whose first checkpoint delivered and
    whose second timed out would record only the timeout. A checkpoint therefore never
    writes that slot at all: it belongs to the turn-start resolve, whose question is "why
    was this turn never shown its recall", and a checkpoint has no standing to answer it.
    Every checkpoint's own verdict lands here instead, where no checkpoint can overwrite
    another and a turn with two injections carries two of them.

    The drift and the changed-block verdict travel on the same line because either alone
    answers nothing: a distance with no outcome beside it, or an outcome with nothing that
    might explain it. Written for whoever is debugging this machine, not for anything
    downstream. Nothing collects the file and no transport off the machine exists.

    A checkpoint that never reached a block names the outcome that stopped it and carries
    no pair, which is honest: nothing was compared, so nothing was observed. A checkpoint
    that did reach one carries the pair and names an outcome only where the block was
    shown, because the two booleans already say which of the other endings it was and a
    borrowed name from the turn-level vocabulary would say it less accurately.
    """
    record = {
        "at": time.time(),
        "run_id": run_id,
        "ordinal": ordinal,
        "outcome": outcome,
        "drift": drift,
        "is_block_changed": is_block_changed,
        "is_injected": is_injected,
    }
    log_path = checkpoint_drift_log()
    ensure_private_dir(log_path.parent)
    line = (json.dumps(record) + "\n").encode("utf-8")
    fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


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


def count_steps(session_id: str) -> int:
    """How many steps this turn has captured, without opening any of them.

    An upper bound on the turn's material steps, which is what the checkpoint threshold is
    counted in, and the cheap half of that question: a directory listing rather than a JSON
    parse per tool call the turn has made. Under the count no threshold can have been
    crossed, so nothing is read at all.
    """
    steps_dir = session_dir(session_id) / ACTIVE_SUBDIR / STEPS_SUBDIR
    if not steps_dir.is_dir():
        return 0
    return sum(1 for path in steps_dir.iterdir() if path.suffix == ".json")


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


def write_flush(path: str | os.PathLike[str], payload: dict[str, Any]) -> None:
    """Persist the staged payload in place, e.g. once its locators are stamped.

    So a retry after a transient failure reuses what the first attempt stamped
    rather than recomputing it against whatever the working tree has become.
    """
    write_json_atomic(Path(path), payload)


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
            final_output=data.get("final_output", ""),
            cwd=data.get("cwd", ""),
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
