"""Per-turn state shared across the three hook processes via the session dir.

The prompt-submit hook, the per-tool hooks, and the stop hook are separate OS
processes, so disk is the only channel between them. State is keyed by the
editor's session id under ``~/.hyperstruck/sessions/<session_id>/``.

The single-process turn-start and turn-end hooks own the small top-level files
(``active.json``, ``pending.json``) and write them atomically (temp + rename).
The per-tool hooks fire in parallel, so they never share a mutable file: each
writes its own append-only per-step file under ``active/steps/``, and the stop
hook merges them in order. No process ever rewrites another's file, so parallel
tool calls cannot drop a step. Every read tolerates a missing or partial file and
returns ``None`` (the loop fails open).
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
    FLUSHING_SUBDIR,
    PENDING_FILE,
    STEPS_SUBDIR,
    sessions_dir,
)


@dataclass(frozen=True)
class ActiveTurn:
    """The turn in progress: written at turn start, before any tool runs."""

    run_id: str
    agent_id: str
    goal: str
    source_framework: str
    started_at: float
    # Learnings resolve offered for this turn, carried to the pending turn so the
    # deferred reinforce can credit them.
    offered_learning_ids: tuple[str, ...] = field(default_factory=tuple)
    # Cursor cannot inject at prompt time, so the prompt hook stashes the resolved
    # injection text here and the first postToolUse hook emits it, then flips
    # is_injected so later tool hooks in the same turn do not re-inject.
    injected_text: str | None = None
    is_injected: bool = False


@dataclass(frozen=True)
class PendingTurn:
    """A finished turn awaiting outcome ground truth from the next prompt.

    ``is_success`` is the *provisional* label computed at turn end; the next
    prompt may override it before the episode is written.
    """

    run_id: str
    agent_id: str
    goal: str
    steps: tuple[dict[str, Any], ...]
    is_success: bool
    source_framework: str
    ended_at: float
    offered_learning_ids: tuple[str, ...] = field(default_factory=tuple)


def session_dir(session_id: str) -> Path:
    return sessions_dir() / _safe_name(session_id)


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
        _reset_dir(steps_dir)
    else:
        ensure_private_dir(steps_dir)
    _write_json_atomic(sdir / ACTIVE_FILE, asdict(turn))


def read_active(session_id: str) -> ActiveTurn | None:
    data = _read_json(session_dir(session_id) / ACTIVE_FILE)
    if not data:
        return None
    try:
        return ActiveTurn(
            run_id=data["run_id"],
            agent_id=data.get("agent_id", ""),
            goal=data.get("goal", ""),
            source_framework=data.get("source_framework", ""),
            started_at=float(data.get("started_at", 0.0)),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
            injected_text=data.get("injected_text"),
            is_injected=bool(data.get("is_injected", False)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def clear_active(session_id: str) -> None:
    sdir = session_dir(session_id)
    _remove(sdir / ACTIVE_FILE)
    _remove_tree(sdir / ACTIVE_SUBDIR)


# -- per-step append files ---------------------------------------------------


def append_step(session_id: str, step: dict[str, Any]) -> None:
    """Write ONE append-only per-step file. Safe under parallel tool hooks.

    The filename is time-ordered and uuid-unique, so concurrent processes never
    collide and the stop hook can merge in execution order.
    """
    steps_dir = session_dir(session_id) / ACTIVE_SUBDIR / STEPS_SUBDIR
    ensure_private_dir(steps_dir)
    name = f"{time.time_ns():020d}-{uuid.uuid4().hex}.json"
    _write_json_atomic(steps_dir / name, step)


def read_steps(session_id: str) -> list[dict[str, Any]]:
    """Merge the per-step files in time order. Skips any unreadable file."""
    steps_dir = session_dir(session_id) / ACTIVE_SUBDIR / STEPS_SUBDIR
    if not steps_dir.is_dir():
        return []
    steps: list[dict[str, Any]] = []
    for path in sorted(steps_dir.iterdir(), key=lambda p: p.name):
        if path.suffix != ".json":
            continue
        data = _read_json(path)
        if isinstance(data, dict):
            steps.append(data)
    return steps


# -- pending turn ------------------------------------------------------------


def write_pending(session_id: str, pending: PendingTurn) -> None:
    """Move the finished turn into ``pending`` and retire its active state."""
    sdir = session_dir(session_id)
    _write_json_atomic(sdir / PENDING_FILE, _pending_to_dict(pending))
    clear_active(session_id)


def read_pending(session_id: str) -> PendingTurn | None:
    return _pending_from_dict(_read_json(session_dir(session_id) / PENDING_FILE))


def clear_pending(session_id: str) -> None:
    _remove(session_dir(session_id) / PENDING_FILE)


# -- flush handoff -----------------------------------------------------------


def stage_flush(session_id: str, run_id: str, episode_payload: dict[str, Any]) -> Path:
    """Hand a resolved episode to a detached flush, keyed by the real run id.

    Writing it under ``flushing/`` decouples delivery from the active/pending
    lifecycle, so the next turn can proceed while the flush runs in another
    process. The filename uses the caller's *un-redacted* run id (the redacted
    episode's run id would collapse to a constant and collide across turns,
    overwriting an undelivered episode), with a uuid fallback to keep the name
    unique even if the id is empty.
    """
    flush_dir = session_dir(session_id) / FLUSHING_SUBDIR
    ensure_private_dir(flush_dir)
    name = f"{_safe_name(run_id)}-{uuid.uuid4().hex}"
    path = flush_dir / f"{name}.json"
    _write_json_atomic(path, episode_payload)
    return path


def read_flush(path: str | os.PathLike[str]) -> dict[str, Any] | None:
    return _read_json(Path(path))


def remove_flush(path: str | os.PathLike[str]) -> None:
    _remove(Path(path))


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
    flush_dir = sdir / FLUSHING_SUBDIR
    if flush_dir.is_dir() and any(flush_dir.iterdir()):
        return
    _remove_tree(sdir)


# -- serialisation helpers ---------------------------------------------------


def _pending_to_dict(pending: PendingTurn) -> dict[str, Any]:
    data = asdict(pending)
    data["steps"] = list(pending.steps)
    data["offered_learning_ids"] = list(pending.offered_learning_ids)
    return data


def _pending_from_dict(data: dict[str, Any] | None) -> PendingTurn | None:
    if not data:
        return None
    try:
        return PendingTurn(
            run_id=data["run_id"],
            agent_id=data.get("agent_id", ""),
            goal=data.get("goal", ""),
            steps=tuple(data.get("steps") or ()),
            is_success=bool(data.get("is_success", True)),
            source_framework=data.get("source_framework", ""),
            ended_at=float(data.get("ended_at", 0.0)),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
        )
    except (KeyError, TypeError, ValueError):
        return None


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


def _write_json_atomic(path: Path, obj: Any) -> None:
    """Write JSON via a temp file + rename so a reader never sees a partial."""
    ensure_private_dir(path.parent)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle)
    try:
        os.chmod(tmp, 0o600)  # state files hold prompts/command output: owner-only
    except OSError:
        pass
    os.replace(tmp, path)


def _read_json(path: Path) -> Any | None:
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


def _safe_name(name: str) -> str:
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
