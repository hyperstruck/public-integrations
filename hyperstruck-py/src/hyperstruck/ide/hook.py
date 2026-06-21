"""The IDE learning hooks: the editor-driven analogue of the LangGraph middleware.

Where the middleware runs the resolve/observe/reinforce loop inside one
``ainvoke``, these hooks run it across three separate OS processes fired by the
editor, sharing per-turn state on disk (see :mod:`hyperstruck.ide.state`):

* ``prompt`` (Claude Code ``UserPromptSubmit``; the Cursor skill calls it too):
  flushes the previous turn now that this prompt is its ground truth, sweeps
  stale sessions, mints a run id, resolves the goal's learnings, injects them, and
  records the new active turn.
* ``tool`` (``PostToolUse`` / Cursor tool hooks): appends one redacted step.
* ``stop`` (``Stop`` / Cursor ``stop``): finalises the turn with a provisional
  outcome and holds it as pending. No write to the platform yet.
* ``flush`` (internal, detached): delivers one turn's observe then reinforce.

Every command fails open: any error exits 0 with no output, so the learning loop
can never block or break the user's editing. The deferred write for turn N runs
at the *start* of turn N+1 (or at stale eviction), once the next prompt supplies
ground truth, and is handed to a detached ``flush`` process so it never delays the
prompt the user is waiting on.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os

# Used only for the fixed-argv detached flush in _spawn_flush; never a shell.
import subprocess  # nosec B404
import sys
import time
import uuid
from dataclasses import replace
from typing import Any

from hyperstruck.ide import outcome, state
from hyperstruck.ide.config import configured_agent_id, load_env
from hyperstruck.ide.constants import (
    EVICTION_WINDOW_SECONDS,
    FLUSH_STALE_SECONDS,
    NATIVE_FAILURE_STATUSES,
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from hyperstruck.ide.gating import classify_tool, should_observe
from hyperstruck.ide.redaction import (
    clip_result,
    redact_ide_episode,
    scrub_secrets,
)
from hyperstruck.ide.state import ActiveTurn, PendingTurn

# Wire fields of a step (the rest of a stored step, e.g. ``kind``, is client-only).
_WIRE_STEP_FIELDS = ("id", "name", "args", "status", "result", "error")


# -- command: prompt (turn start) --------------------------------------------


def cmd_prompt(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Turn start: resolve+inject for the new turn; recover any interrupted turn."""
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    goal = (args.goal or payload.get("prompt") or "").strip()
    agent_id = configured_agent_id()

    # Read-only recall (the hyper-learning skill): resolve and print for this goal,
    # without touching any turn state, so an explicit recall never disturbs the
    # automatic loop. A throwaway run id keeps the offer un-reinforced.
    if args.readonly:
        if agent_id:
            text, _ = _resolve(agent_id, _new_run_id(agent_id, session_id), goal)
            _emit_injection(text, args)
        return

    # 1. Orphan recovery: a turn interrupted before its stop hook fired never
    #    finalised. Treat it as a completed turn now (it really happened): it
    #    resolves the prior pending and becomes pending itself.
    orphan = state.read_active(session_id)
    if orphan is not None:
        _finalise(session_id, orphan, state.read_steps(session_id), native_status=None)
    # 2. Sweep stale sessions on their provisional label (backstop delivery).
    _sweep_stale(exclude=session_id)
    # 3. No configured agent means nothing to learn into: fail open, no injection.
    if not agent_id:
        return
    # 4. Begin the new turn and inject.
    run_id = _new_run_id(agent_id, session_id)
    injected_text, offered_ids = _resolve(agent_id, run_id, goal)
    state.write_active(
        session_id,
        ActiveTurn(
            run_id=run_id,
            agent_id=agent_id,
            goal=goal,
            source_framework=_source(args),
            started_at=time.time(),
            offered_learning_ids=offered_ids,
            injected_text=injected_text,
        ),
    )
    # Claude Code injects at prompt time (UserPromptSubmit additionalContext).
    # Cursor's prompt hook cannot inject, so the stash above is emitted later by
    # the first postToolUse hook (see cmd_tool --inject).
    if _source(args) == SOURCE_CLAUDE_CODE:
        _emit_injection(injected_text, args)


# -- command: tool (capture a step) ------------------------------------------


def cmd_tool(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Append one redacted step. Lazily starts a turn if none is active.

    The lazy start keeps the write path robust on Cursor, where the resolve skill
    may not have run for this turn: steps are still captured and the turn can be
    observed at stop even without an injection.
    """
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    if args.inject:
        # Cursor postToolUse: emit the prompt hook's stashed recall, once per turn.
        # This hook does not capture a step (afterFileEdit/afterShellExecution do),
        # so injection and capture never double-count the same tool call.
        _inject_pending(session_id)
        return
    if state.read_active(session_id) is None:
        agent_id = configured_agent_id()
        if not agent_id:
            return  # no agent configured: nothing to capture into, fail open
        run_id = _new_run_id(agent_id, session_id)
        # reset_steps=False: a parallel tool hook may already have written a step
        # for this turn; resetting the steps dir would drop it.
        state.write_active(
            session_id,
            ActiveTurn(
                run_id=run_id,
                agent_id=agent_id,
                goal="",
                source_framework=_source(args),
                started_at=time.time(),
            ),
            reset_steps=False,
        )
    state.append_step(session_id, _step_from_payload(payload, args))


# -- command: stop (finalise provisional) ------------------------------------


def cmd_stop(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Turn end: resolve the prior turn with this turn's evidence, hold this one."""
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    active = state.read_active(session_id)
    if active is None:
        return
    steps = state.read_steps(session_id)
    native_status = args.native_status or payload.get("status")
    _finalise(session_id, active, steps, native_status=native_status)


# -- command: flush (detached delivery) --------------------------------------


def cmd_flush(args: argparse.Namespace) -> None:
    """Deliver one staged turn: observe (if gated in) then reinforce.

    The staged file is removed ONLY when delivery succeeds. If the boundary is
    down or a write fails, the file is left in place so the next sweep re-spawns a
    flush for it (and eviction drops it after the retention window). This makes the
    staging dir a real outbox rather than a one-shot that loses the episode the
    moment delivery fails.
    """
    payload = state.read_flush(args.flush_path)
    if not payload:
        state.remove_flush(args.flush_path)
        return
    delivered = False
    try:
        delivered = asyncio.run(_deliver(payload))
    except Exception:  # noqa: BLE001 - fail open; leave the file for a later retry
        delivered = False
    if delivered:
        state.remove_flush(args.flush_path)


# -- turn finalisation / flush staging ---------------------------------------


def _finalise(
    session_id: str,
    current: ActiveTurn,
    current_steps: list[dict[str, Any]],
    *,
    native_status: str | None,
) -> None:
    """Resolve the prior turn using this turn's evidence, then hold this turn.

    The prior pending turn's outcome is decided here, now that this (its
    successor) turn's actions exist: rework against the prior turn's files marks it
    failed, otherwise its objective provisional label stands. This turn then
    becomes the pending turn, resolved when the *following* turn ends.
    """
    prior = state.read_pending(session_id)
    if prior is not None:
        final_is_success = outcome.resolve_prior_outcome(
            prior.is_success,
            reworked=outcome.reworked(prior.steps, current_steps),
        )
        _stage_and_flush(session_id, prior, final_is_success)
        state.clear_pending(session_id)
    state.write_pending(
        session_id,
        PendingTurn(
            run_id=current.run_id,
            agent_id=current.agent_id,
            goal=current.goal,
            steps=tuple(current_steps),
            is_success=outcome.provisional_outcome(current_steps, native_status),
            source_framework=current.source_framework,
            ended_at=time.time(),
            offered_learning_ids=current.offered_learning_ids,
        ),
    )


def _stage_and_flush(
    session_id: str, pending: PendingTurn, final_is_success: bool
) -> None:
    """Gate, stage the redacted episode with its final label, detach a flush."""
    if not pending.agent_id:
        return  # nothing to deliver to (turn captured before an agent was set)
    steps = list(pending.steps)
    do_observe = should_observe(steps)
    do_reinforce = bool(pending.offered_learning_ids)
    if not (do_observe or do_reinforce):
        return
    episode = _build_episode(pending, final_is_success)
    staged = {
        "agent_id": pending.agent_id,
        "episode": redact_ide_episode(episode),
        "do_observe": do_observe,
        "do_reinforce": do_reinforce,
    }
    path = state.stage_flush(session_id, pending.run_id, staged)
    _spawn_flush(path)


def _build_episode(pending: PendingTurn, is_success: bool) -> dict[str, Any]:
    """Project stored steps onto the wire episode shape (drops client-only fields)."""
    wire_steps = [
        {field: step.get(field) for field in _WIRE_STEP_FIELDS}
        for step in pending.steps
    ]
    completed = sum(
        1 for step in pending.steps if step.get("status") == STATUS_COMPLETED
    )
    failed = sum(1 for step in pending.steps if step.get("status") == STATUS_FAILED)
    return {
        "run_id": pending.run_id,
        "goal": pending.goal,
        "steps": wire_steps,
        "outcome": {
            "is_success": is_success,
            "total_steps": len(wire_steps),
            "completed_steps": completed,
            "failed_steps": failed,
        },
        "source_framework": pending.source_framework,
        "thread_id": None,
    }


def _sweep_stale(*, exclude: str) -> None:
    """Flush turns left longer than the eviction window, on their provisional label.

    A session abandoned with no successor turn never gets behavioural ground
    truth, so its pending (and any interrupted active) is delivered on the
    provisional label rather than lost.
    """
    now = time.time()
    for session_id in state.all_session_ids():
        if session_id == exclude:
            continue
        pending = state.read_pending(session_id)
        if pending is not None and now - pending.ended_at > EVICTION_WINDOW_SECONDS:
            _stage_and_flush(session_id, pending, pending.is_success)
            state.clear_pending(session_id)
        orphan = state.read_active(session_id)
        if orphan is not None and now - orphan.started_at > EVICTION_WINDOW_SECONDS:
            _finalise(
                session_id, orphan, state.read_steps(session_id), native_status=None
            )
        _recover_flushes(session_id, now)
        state.remove_session_if_empty(session_id)


def _recover_flushes(session_id: str, now: float) -> None:
    """Re-deliver or evict flush files orphaned by a killed flush process.

    A detached flush removes its file on completion; one left behind means its
    process died (sleep, OOM, reboot) before delivering. Re-spawn a flush for it
    (at-least-once is safe, the platform dedups by run id), but evict files past
    the eviction window so a permanently-failing delivery cannot pin the session.
    """
    for path in state.iter_flush_files(session_id):
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age > EVICTION_WINDOW_SECONDS:
            state.remove_flush(path)  # never delivered in time; drop it
        elif age > FLUSH_STALE_SECONDS:
            _spawn_flush(path)  # presumed orphaned; retry. Younger files are in flight.


# -- network (resolve / deliver) ---------------------------------------------


def _resolve(
    agent_id: str, run_id: str, goal: str
) -> tuple[str | None, tuple[str, ...]]:
    """Resolve the goal's learnings. Returns (injected_text, offered_ids); fails open."""
    if not goal:
        return None, ()
    try:
        return asyncio.run(_aresolve(agent_id, run_id, goal))
    except Exception:  # noqa: BLE001 - fail open, never block the prompt
        return None, ()


async def _aresolve(
    agent_id: str, run_id: str, goal: str
) -> tuple[str | None, tuple[str, ...]]:
    # Imported lazily: each hook is a short-lived subprocess, so deferring the
    # httpx-backed client import keeps startup latency off the no-network paths.
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    client = HostedLearningClient()
    try:
        context = await client.resolve(
            identity=AgentIdentity(agent_id=agent_id), run_id=run_id, goal=goal
        )
        return context.injected_text, tuple(context.offered_learning_ids)
    finally:
        await client.aclose()


async def _deliver(payload: dict[str, Any]) -> bool:
    """Observe (awaited to completion) then reinforce, so the wire order holds.

    Returns True when the staged episode is done with (delivered, or unrecoverable
    so not worth retrying) and False when delivery should be retried later.
    """
    from hyperstruck._wire import Episode, StepRecord, TerminalOutcome
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    agent_id = payload.get("agent_id")
    episode_data = payload.get("episode") or {}
    if not agent_id or not episode_data:
        return True  # malformed staged file: drop it, retrying cannot help
    identity = AgentIdentity(agent_id=agent_id)
    outcome_data = episode_data.get("outcome") or {}
    episode = Episode(
        run_id=episode_data.get("run_id", ""),
        goal=episode_data.get("goal", ""),
        steps=tuple(
            StepRecord(**_wire_step(step)) for step in episode_data.get("steps") or []
        ),
        outcome=TerminalOutcome(
            is_success=bool(outcome_data.get("is_success", True)),
            total_steps=int(outcome_data.get("total_steps", 0)),
            completed_steps=int(outcome_data.get("completed_steps", 0)),
            failed_steps=int(outcome_data.get("failed_steps", 0)),
        ),
        source_framework=episode_data.get("source_framework", SOURCE_CLAUDE_CODE),
    )
    try:
        client = HostedLearningClient()
    except ValueError:
        return True  # no API key configured: nothing to retry, drop it
    try:
        if payload.get("do_observe"):
            await client.observe(identity=identity, episode=episode)
            await client.drain()  # land observe before reinforce reads its offer log
        if payload.get("do_reinforce"):
            # IDE tool calls are undeclared, so an IDE turn never auto-promotes.
            await client.reinforce(
                identity=identity, episode=episode, is_org_promotion_allowed=False
            )
            await client.drain()
        # The client retries internally then drops with a counter rather than
        # raising; a non-zero failure count means the boundary did not accept it,
        # so keep the staged file for the next sweep to retry.
        return client.writes_failed == 0
    finally:
        await client.aclose()


def _wire_step(step: dict[str, Any]) -> dict[str, Any]:
    """Keep only StepRecord's fields, with a non-empty id (StepRecord requires it)."""
    wire = {field: step.get(field) for field in _WIRE_STEP_FIELDS}
    if not wire.get("id"):
        wire["id"] = uuid.uuid4().hex
    if not wire.get("name"):
        wire["name"] = "tool"
    if wire.get("status") not in (STATUS_COMPLETED, STATUS_FAILED):
        wire["status"] = STATUS_COMPLETED
    if not isinstance(wire.get("args"), dict):
        wire["args"] = {}
    return wire


# -- step capture ------------------------------------------------------------


def _step_from_payload(
    payload: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Build a redacted, no-raw-content step from a tool-hook payload.

    Spans Claude Code (``tool_name``/``tool_input``/``tool_response``) and Cursor
    (``command``/``file_path``/``exit_code``) shapes. Only safe-to-ship inputs go
    in ``args`` (path, command); no file body, diff, or tool output is ever
    captured. The result is always dropped (it would be source); only the tool
    name, path/command, status, and a clipped, scrubbed error survive.
    """
    name = (
        args.name
        or payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or "tool"
    )
    kind = args.kind or classify_tool(name)

    safe_args: dict[str, Any] = {}
    path = (
        payload.get("file_path")
        or payload.get("path")
        or (payload.get("tool_input") or {}).get("file_path")
    )
    if path:
        safe_args["path"] = scrub_secrets(str(path))
    command = payload.get("command") or (payload.get("tool_input") or {}).get("command")
    if command:
        safe_args["command"] = scrub_secrets(clip_result(command))

    is_error = _is_error(payload)
    # No tool result is ever shipped. A read or edit result is file contents or a
    # diff, and a command's stdout can be source too (git diff, grep, cat). The
    # only execution signal we need is pass/fail (the status); the failure detail
    # rides in `error`, clipped and scrubbed. So `result` is always dropped.
    raw_error = payload.get("error") or payload.get("stderr")
    response = payload.get("tool_response")
    if not raw_error and isinstance(response, dict):
        raw_error = response.get("stderr") or response.get("error")

    return {
        "id": payload.get("tool_call_id") or payload.get("id") or uuid.uuid4().hex,
        "name": str(name),
        "args": safe_args,
        "status": STATUS_FAILED if is_error else STATUS_COMPLETED,
        "result": None,
        "error": (
            scrub_secrets(clip_result(raw_error)) if (is_error and raw_error) else None
        ),
        "kind": kind,
    }


def _is_error(payload: dict[str, Any]) -> bool:
    """Whether a tool call failed, across Claude Code and Cursor payload shapes.

    Claude Code's ``Bash`` failures surface inside ``tool_response`` (stderr /
    interrupted / a nested exit code), not as a top-level field, so the nested
    dict is inspected as well as the top level.
    """
    if _failed_exit(payload.get("exit_code")):
        return True
    if payload.get("is_error") or payload.get("error") or payload.get("stderr"):
        return True
    if str(payload.get("status") or "").lower() in NATIVE_FAILURE_STATUSES:
        return True
    response = payload.get("tool_response")
    if isinstance(response, dict):
        if (
            response.get("error")
            or response.get("stderr")
            or response.get("interrupted")
        ):
            return True
        if _failed_exit(
            response.get("exit_code")
            or response.get("exitCode")
            or response.get("returnCode")
        ):
            return True
        if str(response.get("status") or "").lower() in NATIVE_FAILURE_STATUSES:
            return True
    return False


def _failed_exit(code: Any) -> bool:
    return isinstance(code, int) and code != 0


# -- process plumbing --------------------------------------------------------


def _new_run_id(agent_id: str, session_id: str) -> str:
    """Mint a run id namespaced by agent and session; the uuid tail is the unique part."""
    return f"{agent_id}:{session_id}:{uuid.uuid4().hex}"


def _spawn_flush(path: str | os.PathLike[str]) -> None:
    """Spawn a detached flush process so delivery never delays the prompt."""
    try:
        # Fixed argv from sys.executable, never a shell: not an injection surface.
        subprocess.Popen(  # nosec B603
            [sys.executable, "-m", "hyperstruck.ide.hook", "flush", str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except (OSError, ValueError):
        pass


def _emit_injection(injected_text: str | None, args: argparse.Namespace) -> None:
    """Emit the resolved learnings for the editor to inject before the model acts."""
    if not injected_text:
        return
    if args.emit == "text":
        sys.stdout.write(injected_text)
        return
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": injected_text,
            }
        },
        sys.stdout,
    )


def _emit_cursor_context(injected_text: str | None) -> None:
    """Cursor postToolUse injection: additional_context is added to the conversation."""
    if not injected_text:
        return
    json.dump({"additional_context": injected_text}, sys.stdout)


def _inject_pending(session_id: str) -> None:
    """Emit the prompt hook's stashed recall once, then mark the turn injected.

    Cursor's prompt hook cannot inject, so resolve stashes the text on the active
    turn and the first postToolUse hook delivers it. Subsequent tool hooks in the
    same turn see is_injected and do nothing, so the recall lands exactly once.
    """
    active = state.read_active(session_id)
    if active is None or active.is_injected or not active.injected_text:
        return
    _emit_cursor_context(active.injected_text)
    state.write_active(session_id, replace(active, is_injected=True), reset_steps=False)


def resolve_session_id(
    payload: dict[str, Any], cwd: str, args: argparse.Namespace
) -> str:
    """The editor's session id from argv or the hook payload, else a stable fallback.

    The fallback (terminal session leader + repo digest) is stable across the
    three hook processes of one turn when they share a terminal and repo, so they
    still rendezvous when the editor omits a session id.
    """
    explicit = args.session or _first(
        payload, ("session_id", "conversation_id", "sessionId", "threadId", "thread_id")
    )
    if explicit:
        return str(explicit)
    try:
        sid = os.getsid(0)
    except OSError:
        sid = 0
    digest = hashlib.sha1(
        cwd.encode("utf-8", "ignore"), usedforsecurity=False
    ).hexdigest()[:12]
    return f"derived-{sid}-{digest}"


def _source(args: argparse.Namespace) -> str:
    return args.source or SOURCE_CLAUDE_CODE


def _cwd(payload: dict[str, Any], args: argparse.Namespace) -> str:
    return args.cwd or payload.get("cwd") or os.getcwd()


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value:
            return value
    return None


def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hyperstruck.ide.hook", add_help=False)
    parser.add_argument("command", choices=["prompt", "tool", "stop", "flush"])
    parser.add_argument("flush_path", nargs="?", default=None)
    parser.add_argument(
        "--source", choices=[SOURCE_CLAUDE_CODE, SOURCE_CURSOR], default=None
    )
    parser.add_argument("--session", default=None)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--kind", default=None)
    parser.add_argument("--native-status", dest="native_status", default=None)
    parser.add_argument("--emit", choices=["json", "text"], default="json")
    parser.add_argument("--inject", action="store_true")
    parser.add_argument("--readonly", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Dispatch one hook command. Always returns 0: the loop must fail open."""
    try:
        args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 0
    try:
        load_env()  # bring ~/.hyperstruck/.env (auth + configured agent) into env
        if args.command == "flush":
            cmd_flush(args)
            return 0
        payload = _read_stdin()
        if args.command == "prompt":
            cmd_prompt(payload, args)
        elif args.command == "tool":
            cmd_tool(payload, args)
        elif args.command == "stop":
            cmd_stop(payload, args)
    except (
        BaseException
    ):  # noqa: BLE001 - the loop must never break the editor, even on cancellation/interrupt
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
