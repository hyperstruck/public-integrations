"""End-to-end turn lifecycle: capture, deferral, structural-rework resolution."""

from __future__ import annotations

import argparse
import asyncio
import subprocess

import httpx
import contextlib
import time
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from hyperstruck._wire import (
    REASON_BELOW_MATERIAL_THRESHOLD,
    REASON_NO_TOOL_CALLS,
    Episode,
    StepRecord,
    TerminalOutcome,
)
from hyperstruck import client
from hyperstruck.ide import receipt
from hyperstruck.identity import AgentIdentity
from hyperstruck.ide import hook, registration, stash, state, step_result
from hyperstruck.ide.recall import RecallOutcome
from hyperstruck.ide import constants
from hyperstruck.ide.constants import (
    CREDENTIAL_HEAD_CHARS,
    LIVENESS_FLOOR_SECONDS,
    PENDING_FILE,
)
from hyperstruck.ide.redaction import redact_ide_episode
from hyperstruck.ide.constants import (
    MAX_BOUNDARY_GOAL_CHARS,
    MAX_EPISODE_STEPS,
    MAX_STEP_FIELD_CHARS,
)

# Captured before the autouse fixture patches it, so the resolve breadcrumb tests
# can exercise the real _resolve rather than the fixture's readonly stub.
_REAL_RESOLVE = hook._resolve
_REAL_SPAWN_RESOLVE = hook._spawn_resolve

# The boundary's own CONTEXT_RECEIPT_MAX_CHARS, restated because this is a separate
# distribution that cannot import the server. The real ordering between the two is
# enforced against the actual server constant by the platform's
# api/boundary_exposure_receipt_guard_test.py; this copy only lets the clip test state
# what the clip is FOR.
_BOUNDARY_RECEIPT_CEILING = 200_000


# Captured before the autouse fixture below stubs it out, following the
# _REAL_ENSURE_DURABLE_VENV precedent in install_test.py. Without this, a test of the real
# function asserts against a no-op and passes whatever the function does.
_REAL_CLOSE_READONLY_RUN = hook._close_readonly_run


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))
    monkeypatch.setenv("HYPER_AGENT_NAME", "agent-x")
    # Readonly resolve always offers one learning. Detached resolve is modelled as
    # immediately ready so lifecycle tests can exercise the tool-time handoff.
    monkeypatch.setattr(
        hook,
        "_resolve",
        lambda agent_id, run_id, goal, source_framework, **_kwargs: hook.ResolvedContext(
            injected_text="INJECTED", offered_learning_ids=("L1",)
        ),
    )
    monkeypatch.setattr(hook, "_close_readonly_run", lambda *_args, **_kwargs: None)

    def resolve_now(session_id: str) -> None:
        active = state.read_active(session_id)
        assert active is not None
        state.write_recall(
            session_id,
            {
                "run_id": active.run_id,
                "injected_text": "INJECTED",
                "offered_learning_ids": ["L1"],
            },
        )

    monkeypatch.setattr(hook, "_spawn_resolve", resolve_now)
    staged: list = []
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: staged.append(path))
    return staged


def _args(command: str, **extra):
    argv = [command]
    for key, value in extra.items():
        argv += [f"--{key.replace('_', '-')}", value]
    return hook._parse_args(argv)


def _run_turn(session: str, prompt: str, steps: list[dict]) -> None:
    hook.cmd_prompt(
        {"session_id": session, "prompt": prompt, "cwd": "/repo"}, _args("prompt")
    )
    for step in steps:
        hook.cmd_tool({"session_id": session, "cwd": "/repo", **step}, _args("tool"))
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))


def _last_staged(staged: list) -> dict:
    return state.read_flush(staged[-1])


@contextlib.contextmanager
def _capturing_delivered_turns():
    """Collect the turn records handed to delivery, which no longer land on disk.

    A turn used to be readable from ``pending.json`` after its finalise. It is now
    staged and gone, so a test that needs the record itself, rather than the wire
    payload built from it, has to watch it go past.
    """
    delivered: list[state.FinishedTurn] = []
    real_stage_and_flush = hook._stage_and_flush

    def capture(session_id, turn, turn_outcome):
        delivered.append(turn)
        real_stage_and_flush(session_id, turn, turn_outcome)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(hook, "_stage_and_flush", capture)
        yield delivered


def test_a_single_turn_closes_its_loop_at_its_own_stop(_env) -> None:
    """The headless one-shot case: no successor turn, no session end, still delivered."""
    staged = _env
    _run_turn(
        "s1",
        "add a feature to client.py",
        [
            {"tool_name": "Edit", "file_path": "client.py", "tool_response": "updated"},
            {
                "tool_name": "Bash",
                "command": "pytest",
                "tool_response": "2 passed",
                "exit_code": 0,
            },
        ],
    )
    assert len(staged) == 1
    flushed = _last_staged(staged)
    assert "decline" not in flushed
    assert flushed["episode"]["outcome"]["is_success"] is True
    assert flushed["do_observe"] is True
    assert flushed["do_reinforce"] is True
    assert state.read_active("s1") is None


def test_a_turn_with_nothing_to_show_for_itself_declines(_env) -> None:
    """The optimistic default is gone: no oracle and no declared status credits nothing."""
    staged = _env
    _run_turn(
        "s-unevidenced",
        "read through the module",
        [
            {"tool_name": "Edit", "file_path": "client.py", "tool_response": "updated"},
            {"tool_name": "Edit", "file_path": "server.py", "tool_response": "updated"},
        ],
    )
    assert len(staged) == 1
    flushed = _last_staged(staged)
    assert flushed["decline"]["reason"] == "unevidenced_outcome"
    assert flushed["decline"]["is_delivered"] is True
    assert "episode" not in flushed


def test_a_status_no_host_declares_is_declined_not_credited(_env) -> None:
    """A CI run killed by a timeout used to be credited as a success."""
    staged = _env
    hook.cmd_prompt(
        {"session_id": "s-timeout", "prompt": "run the suite", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": "s-timeout",
            "tool_name": "Edit",
            "file_path": "client.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_stop(
        {"session_id": "s-timeout", "cwd": "/repo", "status": "timeout"}, _args("stop")
    )

    assert _last_staged(staged)["decline"]["reason"] == "unevidenced_outcome"


def test_a_declared_failure_status_still_lands_as_a_failed_episode(_env) -> None:
    """Abstention must not swallow the statuses a host does declare."""
    staged = _env
    hook.cmd_prompt(
        {"session_id": "s-aborted", "prompt": "run the suite", "cwd": "/repo"},
        _args("prompt"),
    )
    for path in ("client.py", "server.py"):
        hook.cmd_tool(
            {
                "session_id": "s-aborted",
                "tool_name": "Edit",
                "file_path": path,
                "tool_response": "ok",
            },
            _args("tool"),
        )
    hook.cmd_stop(
        {"session_id": "s-aborted", "cwd": "/repo", "status": "aborted"}, _args("stop")
    )

    flushed = _last_staged(staged)
    assert "decline" not in flushed
    assert flushed["episode"]["outcome"]["is_success"] is False


def test_each_turn_is_delivered_once_on_its_own_evidence(_env) -> None:
    """The accepted cost, pinned: a later turn no longer retracts an earlier one.

    Turn one passes its tests and is credited at its own stop. Turn two reworks the
    same file, which the retired deferral would have read as turn one having been
    rejected. Turn one keeps its credit, and turn two is delivered separately rather
    than as a correction to it.
    """
    staged = _env
    session = "s1"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "add feature to client.py", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "client.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "2 passed",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))

    assert len(staged) == 1
    first = _last_staged(staged)
    assert first["agent_name"] == "agent-x"
    assert first["episode"]["outcome"]["is_success"] is True
    assert first["do_observe"] is True  # 2 material steps
    assert first["do_reinforce"] is True  # L1 was offered
    # Steps validate against the wire StepModel shape (no client-only fields).
    for step in first["episode"]["steps"]:
        assert set(step) <= {
            "id",
            "name",
            "args",
            "status",
            "result",
            "error",
            "declared_sensitivity",
        }
        assert step["id"]
        StepRecord(**step)

    hook.cmd_prompt(
        {"session_id": session, "prompt": "that's broken", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "client.py",
            "tool_response": "fix",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "1 failed",
            "exit_code": 1,
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))

    assert len(staged) == 2
    assert state.read_flush(staged[0])["episode"]["outcome"]["is_success"] is True
    second = _last_staged(staged)
    assert second["episode"]["outcome"]["is_success"] is False
    assert (
        second["episode"]["run_id"] != state.read_flush(staged[0])["episode"]["run_id"]
    )


def test_observed_empty_offer_turn_reinforces(_env, monkeypatch) -> None:
    """A material turn that offered no learnings still reinforces (closes the loop)."""
    staged = _env
    monkeypatch.setattr(hook, "_spawn_resolve", lambda session_id: None)  # no offer
    session = "s-empty"
    _run_turn(
        session,
        "do work",
        [
            {"tool_name": "Edit", "file_path": "a.py", "tool_response": "ok"},
            {
                "tool_name": "Bash",
                "command": "pytest",
                "tool_response": "2 passed",
                "exit_code": 0,
            },
        ],
    )
    flushed = state.read_flush(staged[0])
    assert flushed["do_observe"] is True
    assert flushed["do_reinforce"] is True  # empty offer still closes the loop


@pytest.mark.parametrize(
    ("steps", "native_status"),
    [
        ([{"tool_name": "Read", "file_path": "a.py"}], None),
        ([{"tool_name": "Edit", "file_path": "a.py", "tool_response": "ok"}], None),
        (
            [
                {"tool_name": "Edit", "file_path": "a.py", "tool_response": "ok"},
                {"tool_name": "Edit", "file_path": "b.py", "tool_response": "ok"},
            ],
            "completed",
        ),
        (
            [
                {"tool_name": "Edit", "file_path": "a.py", "tool_response": "ok"},
                {
                    "tool_name": "Bash",
                    "command": "pytest",
                    "tool_response": "ok",
                    "exit_code": 0,
                },
            ],
            None,
        ),
    ],
)
def test_reinforcing_and_closing_the_loop_cannot_be_moved_apart(
    _env, steps, native_status
) -> None:
    """No lever moves credited turns without moving half-open ones the other way.

    A turn either observes and reinforces together, or declines. No shape closes a
    run without crediting it or credits one without closing it, which is what makes a
    rise in reinforce and a fall in half-open the same event rather than two.
    """
    staged = _env
    session = f"s-coupled-{len(steps)}-{native_status}"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "work", "cwd": "/repo"}, _args("prompt")
    )
    for step in steps:
        hook.cmd_tool({"session_id": session, "cwd": "/repo", **step}, _args("tool"))
    payload = {"session_id": session, "cwd": "/repo"}
    if native_status:
        payload["status"] = native_status
    hook.cmd_stop(payload, _args("stop"))

    assert len(staged) == 1  # every turn closes its run, exactly once
    flushed = _last_staged(staged)
    if "decline" in flushed:
        assert "episode" not in flushed
    else:
        assert flushed["do_observe"] is True and flushed["do_reinforce"] is True


def test_trivial_turn_without_offer_declines(_env, monkeypatch) -> None:
    """A read-only turn with nothing offered closes its run instead of going quiet.

    The run was opened at resolve, so staying silent would leave it open forever and
    make a deliberate skip look exactly like a host that stopped writing back. The
    episode is still withheld: declining closes the loop without feeding a trivial
    turn to the corpus.
    """
    staged = _env
    monkeypatch.setattr(hook, "_spawn_resolve", lambda session_id: None)  # no offer
    session = "s-trivial"
    _run_turn(session, "just read", [{"tool_name": "Read", "file_path": "a.py"}])

    assert len(staged) == 1
    flushed = state.read_flush(staged[0])
    assert "episode" not in flushed
    assert flushed["decline"]["reason"] == REASON_BELOW_MATERIAL_THRESHOLD
    assert flushed["decline"]["is_delivered"] is False


def test_turn_with_no_tool_calls_declines_as_no_tool_calls(_env, monkeypatch) -> None:
    """A pure conversational turn is the common case, and it must still close."""
    staged = _env
    monkeypatch.setattr(hook, "_spawn_resolve", lambda session_id: None)
    session = "s-chat"
    _run_turn(session, "what does this do?", [])

    assert len(staged) == 1
    flushed = state.read_flush(staged[0])
    assert flushed["decline"]["reason"] == REASON_NO_TOOL_CALLS


def test_new_task_keeps_green(_env) -> None:
    staged = _env
    session = "s1"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "edit a.py", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "a.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "ok",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    assert _last_staged(staged)["episode"]["outcome"]["is_success"] is True


def test_secret_scrubbed_from_shipped_episode(_env) -> None:
    staged = _env
    session = "s1"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "set the key", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "export K=sk-ABCDEFGHIJKLMNOPQRSTUV",
            "tool_response": "ok",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "x.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    hook.cmd_prompt(
        {"session_id": session, "prompt": "next thing", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    assert "sk-ABCDEFGHIJKLMNOPQRSTUV" not in str(_last_staged(staged))


def test_no_agent_no_capture(_env, monkeypatch) -> None:
    monkeypatch.delenv("HYPER_AGENT_NAME", raising=False)
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do a thing", "cwd": "/repo"}, _args("prompt")
    )
    assert state.read_active("s1") is None  # nothing recorded without an agent


def test_interrupted_turn_is_recovered(_env) -> None:
    staged = _env
    session = "s1"
    # Turn 1 starts and acts but is never stopped (interrupted).
    hook.cmd_prompt(
        {"session_id": session, "prompt": "edit a.py", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "a.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "ok",
            "exit_code": 0,
        },
        _args("tool"),
    )
    # No cmd_stop. Turn 2 begins: the orphan is delivered now, not discarded, and it
    # keeps its own evidence (the passing test run) rather than an optimistic default.
    hook.cmd_prompt(
        {"session_id": session, "prompt": "now edit b.py", "cwd": "/repo"},
        _args("prompt"),
    )

    assert len(staged) == 1
    recovered = _last_staged(staged)
    assert recovered["episode"]["goal"] == "edit a.py"
    assert recovered["episode"]["outcome"]["is_success"] is True
    assert state.read_active(session) is not None  # turn 2 is under way


def test_an_orphan_with_no_evidence_is_declined_not_credited(_env) -> None:
    """A session that died mid-turn has no stop payload, so it has nothing to credit."""
    staged = _env
    session = "s-crashed"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "edit a.py", "cwd": "/repo"}, _args("prompt")
    )
    for path in ("a.py", "b.py"):
        hook.cmd_tool(
            {
                "session_id": session,
                "tool_name": "Edit",
                "file_path": path,
                "tool_response": "ok",
            },
            _args("tool"),
        )
    hook.cmd_prompt(
        {"session_id": session, "prompt": "carry on", "cwd": "/repo"}, _args("prompt")
    )

    assert len(staged) == 1
    assert _last_staged(staged)["decline"]["reason"] == "unevidenced_outcome"


def test_a_stop_racing_the_sweep_delivers_the_turn_once(_env) -> None:
    """The two writers that can now reach one turn, interleaved rather than in sequence.

    The sweep's orphan recovery and the turn's own stop both stage directly, with no
    pending file to serialise them. The guard is ``stage_flush`` keying the staged
    filename on the run id, so the loser overwrites the winner instead of adding a
    second delivery for the same run.
    """
    staged = _env
    session = "s-race"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "work", "cwd": "/repo"}, _args("prompt")
    )
    for path in ("a.py", "b.py"):
        hook.cmd_tool(
            {
                "session_id": session,
                "tool_name": "Edit",
                "file_path": path,
                "tool_response": "ok",
            },
            _args("tool"),
        )
    active = state.read_active(session)
    assert active is not None
    aged = replace(active, started_at=0.0)
    state.write_active(session, aged, reset_steps=False)

    # Both writers read the turn before either retires it, which is the whole race: the
    # sweep judges the session abandoned and stages it, while the stop hook is already
    # holding the copy it read. Restoring the active turn between them reproduces that
    # interleaving. Running them in plain sequence would not: the sweep's retire makes
    # the stop a no-op, only one write happens, and the guard is never reached.
    hook._sweep_stale(exclude="other-session")
    state.write_active(session, aged, reset_steps=False)
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))

    assert len(staged) == 2, "both writers must stage, or this proves nothing"
    assert staged[0] == staged[1]  # the second write replaced the first in place
    flush_dir = state.session_dir(session) / "flushing"
    staged_files = list(flush_dir.glob("*.json"))
    assert len(staged_files) == 1, "one run id must never yield two staged deliveries"
    assert state.read_flush(staged_files[0])["decline"]["run_id"] == active.run_id


def test_the_sweep_declines_an_orphan_from_a_session_that_never_stopped(
    _env, monkeypatch
) -> None:
    """The sweep's second job: a session abandoned before Stop still closes its run."""
    staged = _env
    hook.cmd_prompt(
        {"session_id": "s-dead", "prompt": "edit a.py", "cwd": "/repo"}, _args("prompt")
    )
    for path in ("a.py", "b.py"):
        hook.cmd_tool(
            {
                "session_id": "s-dead",
                "tool_name": "Edit",
                "file_path": path,
                "tool_response": "ok",
            },
            _args("tool"),
        )
    orphan = state.read_active("s-dead")
    assert orphan is not None
    state.write_active("s-dead", replace(orphan, started_at=0.0), reset_steps=False)

    hook._sweep_stale(exclude="other-session")

    assert len(staged) == 1
    assert _last_staged(staged)["decline"]["reason"] == "unevidenced_outcome"


def test_read_and_edit_results_not_shipped(_env) -> None:
    staged = _env
    session = "s1"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "look then change", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Read",
            "file_path": "secret.py",
            "tool_response": "RAW_FILE_BODY_LINE",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "secret.py",
            "tool_response": "RAW_DIFF_BODY",
        },
        _args("tool"),
    )
    # A command step, so the turn is evidenced and reaches the episode path at all.
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "ok",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    flushed = _last_staged(staged)
    blob = str(flushed)
    assert "RAW_FILE_BODY_LINE" not in blob  # read content never ships
    assert "RAW_DIFF_BODY" not in blob  # edit diff never ships
    for step in flushed["episode"]["steps"]:
        if step["name"] != "Bash":
            assert step["result"] is None  # no result body for read/edit steps


def test_run_id_preserved_end_to_end(_env, monkeypatch) -> None:
    staged = _env
    run_ids: list[str] = []

    def capture(session_id):
        active = state.read_active(session_id)
        assert active is not None
        run_ids.append(active.run_id)
        state.write_recall(
            session_id,
            {
                "run_id": active.run_id,
                "injected_text": "INJECTED",
                "offered_learning_ids": ["L1"],
            },
        )

    monkeypatch.setattr(hook, "_spawn_resolve", capture)
    session = "s1"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "x", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "a.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "ok",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    flushed = _last_staged(staged)
    # The shipped run_id must equal this turn's resolve run_id (the server keys its
    # offer log on that id).
    assert flushed["episode"]["run_id"] == run_ids[0]
    assert "[REDACTED]" not in flushed["episode"]["run_id"]


def test_dump_command_output_dropped(_env) -> None:
    staged = _env
    session = "s1"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "show env", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "cat .env",
            "tool_response": "DBPASS=hunter2plain rawcontents",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "x.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    hook.cmd_prompt(
        {"session_id": session, "prompt": "next", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    blob = str(_last_staged(staged))
    assert "hunter2plain" not in blob  # cat output is content, not shipped
    assert "rawcontents" not in blob


def test_a_pending_file_from_the_previous_release_is_drained_not_stranded(
    _env,
) -> None:
    """On upgrade, a machine may hold turns this release's code no longer writes.

    Written here by hand, because nothing in the tree can produce one any more, which
    is exactly why the drain would go untested if this used a writer.
    """
    staged = _env
    session_dir = state.session_dir("oldsess")
    state.ensure_private_dir(session_dir)
    (session_dir / PENDING_FILE).write_text(
        json.dumps(
            {
                "run_id": "agent-x:oldsess:r1",
                "agent_name": "agent-x",
                "goal": "g",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": "a.py"},
                        "status": "completed",
                        "kind": "edit",
                    },
                    {
                        "id": "2",
                        "name": "Bash",
                        "args": {"command": "pytest"},
                        "status": "completed",
                        "kind": "command",
                    },
                ],
                "is_success": True,
                "source_framework": "claude-code",
                "ended_at": 0.0,
                "offered_learning_ids": ["L1"],
            }
        )
    )

    hook._sweep_stale(exclude="other")

    assert len(staged) == 1
    assert state.read_pending("oldsess") is None
    drained = _last_staged(staged)
    assert drained["episode"]["run_id"] == "agent-x:oldsess:r1"
    # Drained on the boolean label that file recorded, not re-derived from its steps.
    assert drained["episode"]["outcome"]["is_success"] is True


def test_the_drain_reaches_the_session_the_user_upgraded_inside(_env) -> None:
    """The commonest holder of a stale pending file is the session still being used.

    ``exclude`` exists to stop the sweep taking the caller's own live turn. Letting it
    cover the drain as well would strand exactly the case the drain is for, until the
    user happened to open some other session.
    """
    staged = _env
    session_dir = state.session_dir("s-upgraded")
    state.ensure_private_dir(session_dir)
    (session_dir / PENDING_FILE).write_text(
        json.dumps(
            {
                "run_id": "agent-x:s-upgraded:r1",
                "agent_name": "agent-x",
                "goal": "g",
                "steps": [
                    {"id": "1", "name": "Edit", "args": {}, "status": "completed"},
                    {"id": "2", "name": "Bash", "args": {}, "status": "completed"},
                ],
                "is_success": True,
                "source_framework": "claude-code",
                "ended_at": 0.0,
            }
        )
    )

    hook._sweep_stale(exclude="s-upgraded")

    assert len(staged) == 1
    assert state.read_pending("s-upgraded") is None


def test_sweep_removes_recall_without_an_active_turn(_env) -> None:
    state.write_recall(
        "oldsess",
        {
            "run_id": "ended-run",
            "injected_text": "TEXT",
            "offered_learning_ids": ["L1"],
        },
    )
    hook._sweep_stale(exclude="other")
    assert state.claim_recall("oldsess") is None
    assert not state.session_dir("oldsess").exists()


def test_main_fails_open_on_internal_error(_env, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_read_stdin", lambda: {})

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(hook, "cmd_prompt", boom)
    assert hook.main(["prompt"]) == 0  # never breaks the editor


def test_a_step_carries_its_source_provenance(_env) -> None:
    """Every step stamps who it happened for and when, in the shape Core admits.

    Mutation: drop the `declared_sensitivity` kwarg from the returned dict and this fails
    on `step["declared_sensitivity"] is None`.
    """
    step = hook._step_from_payload(
        {"tool_name": "Bash", "command": "pytest", "exit_code": 0},
        _args("tool"),
        run_id="dev-copilot:sess-1:run-1",
    )
    provenance = step["declared_sensitivity"]["provenance"]
    assert provenance["channel"] == "claude_code"
    assert provenance["genre"] == "coding_session"
    assert provenance["source_id"] == "dev-copilot:sess-1:run-1"
    assert provenance["source_time"]


def test_no_hook_version_is_stamped(_env) -> None:
    # Nothing reads it; a new-client episode is identified by its channel instead.
    step = hook._step_from_payload(
        {"tool_name": "Bash", "command": "pytest", "exit_code": 0},
        _args("tool"),
        run_id="dev-copilot:sess-1:run-1",
    )
    assert "hook_version" not in step["declared_sensitivity"]


def test_no_command_output_shipped(_env) -> None:
    # A command result is source-bearing (git diff, grep, test output), so no
    # result body ships for any step; only status survives.
    step = hook._step_from_payload(
        {
            "tool_name": "Bash",
            "command": "git diff",
            "tool_response": "diff --git a/x.py SECRETSRC",
            "exit_code": 0,
        },
        _args("tool"),
    )
    assert step["result"] is None
    assert step["status"] == "completed"


def test_the_gate_operand_field_reaches_the_wire(_env) -> None:
    """The one field of a step that carries a value lifted out of raw tool output.

    Everything about the operand was proved on ``gate_bearing_result`` in isolation, so
    nothing watched the field on the step this hook builds. Three things are asserted: the
    step carries the field, the wire projection keeps it rather than dropping it on the way
    out, and an unlicensed result still yields nothing.

    This asserted an always-empty field until the provenance tiers landed, with the licence
    monkeypatched on to stop that passing for the wrong reason. The patch is gone because
    the licence is real now, and a test that still forced it would be asserting the tiers
    work by assuming they do.
    """
    licensed = {
        "tool_name": "Bash",
        "command": "pytest",
        "tool_response": (
            "Exit code 1\n"
            "Traceback (most recent call last):\n"
            '  File "/app/run.py", line 3, in <module>\n'
            "    import missing\n"
            "ModuleNotFoundError: No module named 'missing'"
        ),
        "is_error": True,
    }

    step = hook._step_from_payload(licensed, _args("tool"))
    assert step["result"] == {step_result.GATE_FIELD: "ModuleNotFoundError"}
    assert hook._wire_step(step)["result"] == {
        step_result.GATE_FIELD: "ModuleNotFoundError"
    }

    unlicensed = licensed | {"tool_response": "Error: tlynch: permission denied"}
    assert hook._step_from_payload(unlicensed, _args("tool"))["result"] is None


def test_writing_to_stderr_is_not_failing(_env) -> None:
    """Corrected against production data; it used to assert the opposite.

    Treating a non-empty stderr as failure is what shipped, and it is wrong in both
    directions. Measured on a live machine, the client recorded 78 steps of which 11 were
    marked failed, and all 11 were successful commands whose stderr carried one benign line
    from a shell wrapper. Not one real failure was among them. ``git``, ``npm``, ``uv``,
    ``docker`` and ``pytest`` all write to stderr while succeeding, so stderr is output and
    an exit status is a verdict. It is still kept as the error text once something else has
    established that the step failed.
    """
    step = hook._step_from_payload(
        {
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": {"stdout": "2 passed", "stderr": "warning: deprecated"},
        },
        _args("tool"),
    )
    assert step["status"] == "completed"


def test_a_real_claude_code_failure_is_detected_from_the_shape_of_its_result(
    _env,
) -> None:
    """The defect that made the whole lane inert on its main host.

    Claude Code delivers a failed call's result as a plain string and a successful one as an
    object. Measured across 3,170 transcripts the separation is exact: all 2,509 failures
    were string-shaped, none was object-shaped. Every dict-reading branch missed them, so a
    real failure was recorded ``completed`` and ``recovered_from_failure``, the one turn
    class that is always observed, could never fire on a genuine recovery.
    """
    step = hook._step_from_payload(
        {
            "tool_name": "Bash",
            "command": "pytest -q",
            "tool_response": "Error: Exit code 1\nModuleNotFoundError: No module named 'x'",
        },
        _args("tool"),
    )
    assert step["status"] == "failed"
    # The message itself does NOT ship. It is the tool's output, and this client cannot tell
    # an error message from a file body by looking, so the shape of the failure reaches the
    # corpus masked and bounded as a gate operand instead of verbatim as prose.
    assert step["error"] is None

    # The 183 string-shaped results that were NOT failures were all JSON from MCP tools.
    mcp = hook._step_from_payload(
        {
            "tool_name": "mcp__cal__list",
            "tool_response": '{"success": true, "result": []}',
        },
        _args("tool"),
    )
    assert mcp["status"] == "completed"


def test_nested_bash_failure_detected(_env) -> None:
    # Claude Code Bash failures live inside tool_response, not top-level.
    step = hook._step_from_payload(
        {
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": {"error": "AssertionError boom", "interrupted": False},
        },
        _args("tool"),
    )
    assert step["status"] == "failed"
    assert step["error"] and "boom" in step["error"]
    interrupted = hook._step_from_payload(
        {
            "tool_name": "Bash",
            "command": "sleep 99",
            "tool_response": {"interrupted": True},
        },
        _args("tool"),
    )
    assert interrupted["status"] == "failed"


def test_git_turn_locator_reads_the_working_tree_once(_env, monkeypatch) -> None:
    """The turn-level remote/commit/tree, read by shelling to system git with a timeout.

    Mutation: make the second `git` call return a non-zero exit code and this fails on
    `commit == "deadbeef"`.
    """
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        assert kwargs["timeout"] == hook.GIT_LOCATOR_TIMEOUT_SECONDS
        by_subcommand = {"remote": "https://github.com/acme/api.git\n"}
        by_revision = {"HEAD": "deadbeef\n", "HEAD^{tree}": "cafefeed\n"}
        stdout = by_subcommand.get(argv[3]) or by_revision.get(argv[-1], "")
        return argparse.Namespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    remote, commit, tree = hook._git_turn_locator("/repo")
    assert (remote, commit, tree) == (
        "https://github.com/acme/api.git",
        "deadbeef",
        "cafefeed",
    )
    assert len(calls) == 3


def test_git_turn_locator_omits_on_any_failure(_env, monkeypatch) -> None:
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    assert hook._git_turn_locator("/not-a-repo") == (None, None, None)


def test_flush_fills_each_steps_locator_from_the_staged_cwd(_env, monkeypatch) -> None:
    """The detached flush, never the synchronous tool hook, fills the locator.

    Mutation: stop calling `_stamp_step_locators` before `_deliver` and this fails on
    `provenance["locator"] is None`.
    """
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    monkeypatch.setattr(
        hook,
        "_git_turn_locator",
        lambda cwd: ("https://github.com/acme/api.git", "a" * 40, "b" * 40),
    )
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": "/repo",
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": "src/x.py"},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )
    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert (
        provenance["locator"]
        == f"git:github.com/acme/api@{'a' * 40}^{{tree:{'b' * 40}}}:src/x.py"
    )
    assert provenance["basis"] == "observed"


def test_flush_retries_on_terminal_failure(_env, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)  # don't spawn
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def terminal(_payload):
        return hook.FlushOutcome.TERMINAL, "HTTP 422"

    monkeypatch.setattr(hook, "_deliver", terminal)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is not None  # kept for retry on failed delivery
    assert state.read_flush_attempts(path) == 1

    async def ok(_payload):
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", ok)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is None  # removed once delivered


def test_transient_failure_never_counts_or_drops(_env, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_FLUSH_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def transient(_payload):
        return hook.FlushOutcome.TRANSIENT, "ConnectError"

    monkeypatch.setattr(hook, "_deliver", transient)
    for _ in range(5):
        hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    # A transient outage must never count against the cap or drop the episode:
    # it retries until the eviction window, well past max attempts.
    assert state.read_flush(path) is not None
    assert state.read_flush_attempts(path) == 0


def test_dropped_decline_still_names_its_run(_env, monkeypatch, tmp_path) -> None:
    """A decline that cannot be delivered must still say which run it lost.

    The dropped record is the only trace that survives a failed write, so an
    unattributable one recreates the silent hole the decline exists to close. A
    decline nests its run id differently from an episode, so this pins that the
    drop path reads both shapes rather than only the episode one.
    """
    monkeypatch.setenv("HYPER_FLUSH_MAX_ATTEMPTS", "1")
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:declined",
        {
            "agent_name": "agent-x",
            "decline": {
                "run_id": "agent-x:s1:declined",
                "reason": REASON_NO_TOOL_CALLS,
                "is_delivered": False,
            },
        },
    )

    async def terminal(_payload):
        return hook.FlushOutcome.TERMINAL, "HTTP 422"

    monkeypatch.setattr(hook, "_deliver", terminal)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    record = json.loads((tmp_path / "dropped.jsonl").read_text().splitlines()[0])
    assert record["run_id"] == "agent-x:s1:declined"
    assert record["agent_name"] == "agent-x"


def test_flush_drops_after_max_terminal_attempts(_env, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HYPER_FLUSH_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)  # don't spawn
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def terminal(_payload):
        return hook.FlushOutcome.TERMINAL, "HTTP 422"

    monkeypatch.setattr(hook, "_deliver", terminal)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is not None
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is None
    # The drop leaves a durable, prompt-free trace with the run id and cause.
    dropped = (tmp_path / "dropped.jsonl").read_text().splitlines()
    assert len(dropped) == 1
    record = json.loads(dropped[0])
    assert record["run_id"] == "r"
    assert record["cause"] == "HTTP 422"
    assert record["attempts"] == 2


def test_unrecoverable_delivery_drops_without_counting(_env, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def unrecoverable(_payload):
        return hook.FlushOutcome.UNRECOVERABLE, "no API key configured"

    monkeypatch.setattr(hook, "_deliver", unrecoverable)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is None


def test_failed_flush_does_not_recreate_delivered_file(_env, monkeypatch) -> None:
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def fail_after_peer_delivered(_payload):
        state.remove_flush(path)
        return hook.FlushOutcome.TERMINAL, "HTTP 422"

    monkeypatch.setattr(hook, "_deliver", fail_after_peer_delivered)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is None


# -- detached recall + tool-time injection -----------------------------------


def test_prompt_spawns_resolve_without_inline_network(
    _env, capsys, monkeypatch
) -> None:
    spawned = []
    monkeypatch.setattr(hook, "_spawn_resolve", spawned.append)

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("prompt hook touched the resolve client")

    monkeypatch.setattr(hook, "_aresolve", forbidden)
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt"]),
    )
    assert capsys.readouterr().out == ""
    assert spawned == ["s1"]
    active = state.read_active("s1")
    assert active is not None
    assert active.offered_learning_ids == ()
    assert not hook._is_credited("s1", active)


def test_prompt_clips_an_oversized_goal_to_the_platform_bound(
    _env, monkeypatch
) -> None:
    monkeypatch.setattr(hook, "_spawn_resolve", lambda _session_id: None)
    hook.cmd_prompt(
        {
            "session_id": "s1",
            "prompt": "x" * (MAX_BOUNDARY_GOAL_CHARS + 500),
            "cwd": "/repo",
        },
        hook._parse_args(["prompt"]),
    )
    active = state.read_active("s1")
    assert active is not None
    assert len(active.goal) == MAX_BOUNDARY_GOAL_CHARS
    assert active.goal.endswith("[TRUNCATED]")


def test_prompt_scrubs_the_goal_before_it_can_reach_resolve(_env, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_spawn_resolve", lambda _session_id: None)
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "deploy with password=abcd", "cwd": "/repo"},
        hook._parse_args(["prompt"]),
    )
    active = state.read_active("s1")
    assert active is not None
    assert "abcd" not in active.goal


def test_episode_holds_the_step_cap_and_still_counts_the_whole_turn() -> None:
    steps = [
        {"id": f"s{n}", "name": "Bash", "args": {}, "status": "completed"}
        for n in range(MAX_EPISODE_STEPS + 20)
    ]
    pending = state.FinishedTurn(
        run_id="a:b:c",
        agent_name="agent-x",
        goal="g",
        steps=tuple(steps),
        source_framework="claude-code",
        ended_at=0.0,
    )
    episode = hook._build_episode(pending, is_success=True)
    assert len(episode["steps"]) == MAX_EPISODE_STEPS
    assert episode["steps"][-1]["id"] == steps[-1]["id"]  # the tail is what survives
    assert episode["outcome"]["total_steps"] == len(steps)
    assert episode["outcome"]["completed_steps"] == len(steps)


def test_wire_step_clips_an_overlong_tool_name() -> None:
    wire = hook._wire_step({"id": "x" * 400, "name": "y" * 400})
    assert len(wire["id"]) == MAX_STEP_FIELD_CHARS
    assert len(wire["name"]) == MAX_STEP_FIELD_CHARS


def test_prompt_spawns_fixed_argv_detached_resolver(_env, monkeypatch) -> None:
    calls = []

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))

    monkeypatch.setattr(hook, "_spawn_resolve", _REAL_SPAWN_RESOLVE)
    monkeypatch.setattr(hook.subprocess, "Popen", fake_popen)
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt"]),
    )
    argv, kwargs = calls[0]
    assert argv == [
        hook.sys.executable,
        "-m",
        "hyperstruck.ide.hook",
        "resolve",
        "s1",
    ]
    assert kwargs["start_new_session"] is True
    assert kwargs["stdin"] is hook.subprocess.DEVNULL
    assert kwargs["stdout"] is hook.subprocess.DEVNULL
    # The parent's -P does not reach a child: it is a fresh interpreter, and the
    # flag sets no environment. Without this the child dies on a project file
    # named after a stdlib module, which is what the wired flag fixes for the parent.
    assert kwargs["env"]["PYTHONSAFEPATH"] == "1"
    # A trail, not DEVNULL: a child dying before main's fail-open contract would
    # otherwise leave nothing behind at all.
    assert kwargs["stderr"] is not hook.subprocess.DEVNULL


@pytest.mark.parametrize("replacement", [None, "new-run"])
def test_resolver_drops_recall_when_turn_ended_or_changed(
    _env, monkeypatch, replacement
) -> None:
    state.write_active(
        "s1",
        state.ActiveTurn(
            run_id="old-run",
            agent_name="agent-x",
            goal="do x",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )

    async def resolve_then_change(*_args, **_kwargs):
        if replacement is None:
            state.clear_active("s1")
        else:
            state.write_active(
                "s1",
                state.ActiveTurn(
                    run_id=replacement,
                    agent_name="agent-x",
                    goal="next",
                    source_framework="claude-code",
                    started_at=2.0,
                ),
            )
        return hook.ResolvedContext(injected_text="TEXT", offered_learning_ids=("L1",))

    monkeypatch.setattr(hook, "_aresolve", resolve_then_change)
    hook.cmd_resolve("s1")
    assert state.claim_recall("s1") is None


def test_resolver_writes_matching_recall(_env, monkeypatch) -> None:
    state.write_active(
        "s1",
        state.ActiveTurn(
            run_id="run-1",
            agent_name="agent-x",
            goal="do x",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )

    async def resolved(*_args, **_kwargs):
        return hook.ResolvedContext(
            injected_text="TEXT",
            injected_facts_text="FACT",
            injected_obligations_text="OWED",
            offered_learning_ids=("L1", "L2"),
            offered_claim_ids=("C1",),
        )

    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s1")
    assert state.claim_recall("s1") == {
        "run_id": "run-1",
        "injected_text": "TEXT",
        "injected_facts_text": "FACT",
        # The third block travels with the other two, or the turn that injects reads a
        # record missing the half it was going to place.
        "injected_obligations_text": "OWED",
        "offered_learning_ids": ["L1", "L2"],
        "offered_claim_ids": ["C1"],
        "checkpoint_ordinal": 0,
        "drift": None,
    }


def test_the_resolver_records_why_it_published_nothing(_env, monkeypatch) -> None:
    """A detached process that fails silently is why an unposted receipt had no cause.

    Its stdout goes nowhere and its stderr is a diagnostic that is off by default, so
    the verdict is written where the stop hook can read it back. Each way of failing
    is named, because a hosted call that ran out of time is a capacity problem and a
    superseded turn is not a problem at all.
    """

    async def timed_out(*_args, **_kwargs):
        raise TimeoutError("hosted resolve did not answer")

    async def broke(*_args, **_kwargs):
        raise RuntimeError("connection reset")

    async def empty(*_args, **_kwargs):
        return hook.ResolvedContext()

    for session_id, resolver, expected in (
        ("s-timeout", timed_out, RecallOutcome.RESOLVE_TIMED_OUT),
        ("s-broken", broke, RecallOutcome.RESOLVE_FAILED),
        ("s-empty", empty, RecallOutcome.RESOLVE_EMPTY),
    ):
        _seeded_active(session_id)
        monkeypatch.setattr(hook, "_aresolve", resolver)
        hook.cmd_resolve(session_id)

        assert state.peek_recall(session_id) is None
        assert state.read_recall_status(session_id, "run-1") == expected


def test_a_published_stash_no_tool_event_claimed_reads_as_unclaimed(
    _env, monkeypatch
) -> None:
    """Published is not shown. The recall rides a tool event, and a turn may have none.

    Until the turn ends this is simply the normal state of a stash in flight, so the
    resolver records it on success too: an absent verdict then means the resolve had
    not returned at all, which is a different answer.
    """
    _seeded_active("s-unclaimed")

    async def resolved(*_args, **_kwargs):
        return hook.ResolvedContext(injected_text="TEXT", offered_learning_ids=("L1",))

    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s-unclaimed")

    assert state.read_recall_status("s-unclaimed", "run-1") == (
        RecallOutcome.RECALL_UNCLAIMED
    )


def test_a_superseded_resolve_is_not_reported_as_a_failure(_env, monkeypatch) -> None:
    """The turn moved on before the recall was ready; nothing broke."""
    _seeded_active("s-superseded")

    async def resolve_then_change(*_args, **_kwargs):
        state.write_active(
            "s-superseded",
            state.ActiveTurn(
                run_id="run-2",
                agent_name="agent-x",
                goal="next",
                source_framework="claude-code",
                started_at=2.0,
            ),
        )
        return hook.ResolvedContext(injected_text="TEXT", offered_learning_ids=("L1",))

    monkeypatch.setattr(hook, "_aresolve", resolve_then_change)
    hook.cmd_resolve("s-superseded")

    assert state.read_recall_status("s-superseded", "run-1") == (
        RecallOutcome.RESOLVE_SUPERSEDED
    )


def test_a_superseded_resolver_cannot_overwrite_the_live_turns_verdict(
    _env, monkeypatch
) -> None:
    """The slow resolver returns last, and the turn it is no longer about is running.

    Overwriting here costs the live turn its reason: its stop hook rejects the mismatched
    run and falls back to the least informative member of the vocabulary, which is the
    one answer this whole change exists to stop giving.
    """
    _seeded_active("s-race")
    state.write_recall_status("s-race", "run-1", RecallOutcome.RECALL_UNCLAIMED)

    state.write_recall_status("s-race", "run-0", RecallOutcome.RESOLVE_SUPERSEDED)

    assert state.read_recall_status("s-race", "run-1") == RecallOutcome.RECALL_UNCLAIMED
    assert state.read_recall_status("s-race", "run-0") is None


def test_a_verdict_from_another_run_is_never_read_as_this_ones(_env) -> None:
    """The status file outlives one turn, and the wrong cause is worse than none."""
    state.write_recall_status("s-stale", "run-0", RecallOutcome.RESOLVE_TIMED_OUT)

    assert state.read_recall_status("s-stale", "run-1") is None


def test_resolver_skips_publish_when_no_learnings(_env, monkeypatch) -> None:
    state.write_active(
        "s1",
        state.ActiveTurn(
            run_id="run-1",
            agent_name="agent-x",
            goal="do x",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )

    async def resolved(*_args, **_kwargs):
        return hook.ResolvedContext()

    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s1")
    assert state.peek_recall("s1") is None


# The slowest of 234 production resolves against api.hyperstruck.com over 24h on
# 2026-08-20 (p50 11.6s, p99 18.7s). The budget has to clear the tail, not the
# median, which is the property that actually failed: the previous constant was
# taken from a single 13.1s sample on 2026-08-10 and left the deadline sitting
# 0.9s above the slowest real resolve.
MEASURED_HOSTED_RESOLVE_SECONDS = 19.1


def test_recall_budget_clears_a_real_hosted_resolve() -> None:
    """With headroom on the detached seat, and no more than the tail on the awaited one.

    Nothing waits on the hook's resolver, so a budget close to the measured tail buys no
    latency there and loses recall every time the boundary has a slow day. The awaited
    seat is the opposite trade: the LangGraph middleware blocks its first model call on
    the same call, so headroom there is a stall a customer feels.
    """
    assert client.DEFAULT_DETACHED_RECALL_TIMEOUT > MEASURED_HOSTED_RESOLVE_SECONDS * 2
    assert client.DEFAULT_RECALL_TIMEOUT > MEASURED_HOSTED_RESOLVE_SECONDS
    assert client.DEFAULT_RECALL_TIMEOUT < MEASURED_HOSTED_RESOLVE_SECONDS * 2
    assert hook.MIN_RECALL_TIMEOUT > client.DEFAULT_RESOLVE_TIMEOUT


@contextlib.contextmanager
def _stalling_server():
    """A socket that accepts and never answers, so a real timeout has to fire.

    httpx.MockTransport enforces no timeout at all, neither the client-level one nor the
    per-request extension, so a test built on it cannot observe the transport capping
    anything: both earlier attempts at this guard passed with the fix reverted.
    """
    import socket
    import threading

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    held = []
    stop = threading.Event()

    def accept_and_hold():
        listener.settimeout(0.2)
        while not stop.is_set():
            try:
                held.append(listener.accept()[0])
            except OSError:
                continue

    thread = threading.Thread(target=accept_and_hold, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{listener.getsockname()[1]}"
    finally:
        stop.set()
        thread.join(timeout=2)
        for connection in held:
            connection.close()
        listener.close()


@pytest.mark.asyncio
async def test_the_transport_cannot_cap_the_budget_the_caller_asked_for() -> None:
    """The recall budget must outlive the client's own timeout, not be capped by it.

    httpx applies its client-level timeout to the transport, so a resolve budget above
    it is capped there and the caller's own deadline never fires. The symptom is not a
    failed resolve but a mislabelled one: the transport's error is not a TimeoutError,
    so every real timeout was recorded as a fault instead of a capacity problem.
    """
    with _stalling_server() as base_url:
        hosted = client.HostedLearningClient(
            api_key="hs_live_k.s",
            base_url=base_url,
            http_client=httpx.AsyncClient(timeout=0.2),
            resolve_timeout=1.5,
        )
        started = time.monotonic()
        try:
            with pytest.raises(TimeoutError):
                await hosted.resolve(
                    identity=AgentIdentity(agent_name="agent-x"), run_id="r", goal="g"
                )
        finally:
            await hosted.aclose()

    waited = time.monotonic() - started
    assert waited > 0.5, (
        f"gave up after {waited:.2f}s, so the 0.2s client timeout capped the 1.5s "
        "recall budget instead of the budget governing"
    )


@pytest.mark.asyncio
async def test_a_transport_timeout_reaches_the_caller_as_a_timeout() -> None:
    """And not as an httpx error, which the resolver files as a fault, not capacity.

    Both deadlines race by design, and which one wins is an implementation detail no
    caller should have to know. Driven at the seam rather than by trying to win that
    race: httpx's timeout is not a TimeoutError, and before this conversion existed the
    resolver recorded every real timeout as `resolve_failed`.
    """

    class _TimingOutClient:
        async def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("the boundary never answered")

        async def aclose(self) -> None:
            return None

    assert not issubclass(httpx.ReadTimeout, TimeoutError), (
        "httpx's timeout became a TimeoutError, so this conversion is now redundant "
        "rather than load-bearing"
    )
    hosted = client.HostedLearningClient(
        api_key="hs_live_k.s",
        base_url="http://localhost:1",
        http_client=_TimingOutClient(),
        resolve_timeout=5.0,
    )
    with pytest.raises(TimeoutError) as raised:
        await hosted.resolve(
            identity=AgentIdentity(agent_name="agent-x"), run_id="r", goal="g"
        )

    assert hook._resolve_failure(raised.value) is RecallOutcome.RESOLVE_TIMED_OUT


def _seeded_active(session_id: str) -> None:
    state.write_active(
        session_id,
        state.ActiveTurn(
            run_id="run-1",
            agent_name="agent-x",
            goal="do x",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )


@pytest.mark.parametrize("caller", ["detached", "explicit", "skill"])
@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        (None, hook.DEFAULT_DETACHED_RECALL_TIMEOUT),
        ("12.5", 12.5),
        ("0", hook.MIN_RECALL_TIMEOUT),
        ("-4", hook.MIN_RECALL_TIMEOUT),
        ("nonsense", hook.DEFAULT_DETACHED_RECALL_TIMEOUT),
    ],
)
def test_every_hook_recall_reaches_the_client_with_the_recall_budget(
    _env, monkeypatch, caller, env_value, expected
) -> None:
    """The budget must land on the client, not merely on the _aresolve seam.

    Both entry points are covered here, so a third one that constructs its own
    client is the only way left to reintroduce the 2s default.
    """
    seen = []
    seen_purposes = []

    class _RecordingClient:
        def __init__(self, **kwargs):
            seen.append(kwargs["resolve_timeout"])

        async def resolve(self, **kwargs):
            seen_purposes.append(kwargs["resolve_purpose"])
            return hook.ResolvedContext(injected_text="TEXT")

        async def aclose(self):
            return None

    if env_value is None:
        monkeypatch.delenv(hook.RESOLVE_TIMEOUT_ENV, raising=False)
    else:
        monkeypatch.setenv(hook.RESOLVE_TIMEOUT_ENV, env_value)
    monkeypatch.setattr(hook, "HostedLearningClient", _RecordingClient)
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)

    if caller == "detached":
        _seeded_active("s1")
        hook.cmd_resolve("s1")
    else:
        purpose_args = (
            ["--resolve-purpose", hook.ResolvePurpose.AGENT_LOOP.value]
            if caller == "skill"
            else []
        )
        hook.cmd_prompt(
            {"conversation_id": "s1", "cwd": "/repo"},
            hook._parse_args(
                [
                    "prompt",
                    "--readonly",
                    *purpose_args,
                    "--emit",
                    "text",
                    "--goal",
                    "do x",
                ]
            ),
        )

    assert seen == [expected]
    assert seen_purposes == [hook.ResolvePurpose.AGENT_LOOP]


def test_readonly_without_purpose_stays_agent_loop(_env, monkeypatch) -> None:
    """Already-installed --readonly skill commands never passed a purpose."""
    seen_purposes: list[object] = []

    class _RecordingClient:
        def __init__(self, **_kwargs):
            return None

        async def resolve(self, **kwargs):
            seen_purposes.append(kwargs["resolve_purpose"])
            return hook.ResolvedContext(injected_text="TEXT")

        async def aclose(self):
            return None

    monkeypatch.setattr(hook, "HostedLearningClient", _RecordingClient)
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    hook.cmd_prompt(
        {"conversation_id": "s1", "cwd": "/repo"},
        hook._parse_args(["prompt", "--readonly", "--emit", "text", "--goal", "do x"]),
    )

    assert seen_purposes == [hook.ResolvePurpose.AGENT_LOOP]


def test_readonly_explicit_recall_is_opt_in(_env, monkeypatch) -> None:
    seen_purposes: list[object] = []

    class _RecordingClient:
        def __init__(self, **_kwargs):
            return None

        async def resolve(self, **kwargs):
            seen_purposes.append(kwargs["resolve_purpose"])
            return hook.ResolvedContext(injected_text="TEXT")

        async def aclose(self):
            return None

    monkeypatch.setattr(hook, "HostedLearningClient", _RecordingClient)
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    hook.cmd_prompt(
        {"conversation_id": "s1", "cwd": "/repo"},
        hook._parse_args(
            [
                "prompt",
                "--readonly",
                "--resolve-purpose",
                hook.ResolvePurpose.EXPLICIT_RECALL.value,
                "--emit",
                "text",
                "--goal",
                "do x",
            ]
        ),
    )

    assert seen_purposes == [hook.ResolvePurpose.EXPLICIT_RECALL]


def test_packaged_skill_attributes_agent_owned_readonly_recall() -> None:
    skill_path = Path(hook.__file__).parent / "skills" / "hyper-learning" / "SKILL.md"
    skill = skill_path.read_text()

    assert "prompt --readonly" in skill
    assert "--resolve-purpose agent_loop" in skill


def test_explicit_recall_says_so_on_stderr_when_it_times_out(
    _env, capsys, monkeypatch
) -> None:
    """A timed-out recall must not read as an empty corpus, per the outage it caused."""
    monkeypatch.delenv("HYPER_HOOK_DEBUG", raising=False)

    async def timed_out(*_args, **_kwargs):
        raise TimeoutError

    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    monkeypatch.setattr(hook, "_aresolve", timed_out)

    assert (
        hook._resolve("agent-x", "run-1", "do x", hook.SOURCE_CLAUDE_CODE)
        == hook.ResolvedContext()
    )
    assert "recall timed out" in capsys.readouterr().err


def test_claude_posttooluse_injects_once_and_attributes_offers(_env, capsys) -> None:
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt"]),
    )
    hook.cmd_tool(
        {"session_id": "s1", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool"]),
    )
    payload = json.loads(capsys.readouterr().out)
    emitted = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    active = state.read_active("s1")
    assert active is not None
    # The run's marker leads the block, and it is what the stop hook finds this turn's
    # acceptance record by. Position in the transcript would pair the wrong run with the
    # wrong verdict the first time any turn's injection is denied.
    assert emitted == f"{receipt.marker(active.run_id)}\nINJECTED"
    assert active is not None
    assert hook._is_credited("s1", active)
    assert hook._offered_this_turn("s1", active)[0] == ("L1",)
    assert len(state.read_steps("s1")) == 1
    hook.cmd_tool(
        {"session_id": "s1", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool"]),
    )
    assert capsys.readouterr().out == ""


def test_failed_validation_leaves_recall_for_a_later_hook(_env, capsys) -> None:
    # A late resolve from a prior turn must not consume the one-shot claim:
    # the mismatching stash stays put, and once the current turn's recall
    # lands a later tool hook still injects it.
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt"]),
    )
    fresh = state.claim_recall("s1")  # hold this turn's recall aside
    assert fresh is not None
    state.write_recall(
        "s1",
        {
            "run_id": "prior-run",
            "injected_text": "STALE",
            "offered_learning_ids": ["L9"],
        },
    )
    hook.cmd_tool(
        {"session_id": "s1", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool"]),
    )
    assert capsys.readouterr().out == ""
    assert state.peek_recall("s1") is not None  # stash survived the failure
    assert not hook._is_credited("s1", state.read_active("s1"))
    state.write_recall("s1", fresh)  # the current turn's resolve lands
    hook.cmd_tool(
        {"session_id": "s1", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool"]),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["additionalContext"].endswith("INJECTED")
    active = state.read_active("s1")
    assert hook._is_credited("s1", active)
    assert hook._offered_this_turn("s1", active)[0] == ("L1",)


def test_cursor_posttooluse_injects_once(_env, capsys) -> None:
    hook.cmd_prompt(
        {"conversation_id": "c1", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt", "--source", "cursor"]),
    )
    capsys.readouterr()  # discard the (empty) prompt output
    hook.cmd_tool(
        {"conversation_id": "c1", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool", "--source", "cursor", "--inject"]),
    )
    assert json.loads(capsys.readouterr().out)["additional_context"].endswith(
        "INJECTED"
    )
    assert hook._is_credited("c1", state.read_active("c1"))
    # A second postToolUse in the same turn must not re-inject.
    hook.cmd_tool(
        {"conversation_id": "c1", "tool_name": "Edit", "cwd": "/repo"},
        hook._parse_args(["tool", "--source", "cursor", "--inject"]),
    )
    assert capsys.readouterr().out == ""


def test_cursor_rendezvous_credits_reinforce(_env) -> None:
    # resolve and capture both key on conversation_id, so the offered learnings
    # survive to reinforce (the attribution bug the rework fixes).
    staged = _env
    cc = ["--source", "cursor"]
    conv = {"conversation_id": "c1", "cwd": "/repo"}
    hook.cmd_prompt(
        {**conv, "prompt": "add feature to a.py"}, hook._parse_args(["prompt", *cc])
    )
    hook.cmd_tool(conv, hook._parse_args(["tool", *cc, "--inject"]))
    hook.cmd_tool(
        {**conv, "file_path": "a.py", "tool_response": "ok"},
        hook._parse_args(["tool", *cc, "--kind", "edit"]),
    )
    hook.cmd_tool(
        {**conv, "command": "pytest", "output": "2 passed"},
        hook._parse_args(["tool", *cc, "--kind", "command"]),
    )
    hook.cmd_stop(conv, hook._parse_args(["stop", *cc]))
    flushed = _last_staged(staged)
    assert flushed["do_observe"] is True  # 2 material steps captured under c1
    assert flushed["do_reinforce"] is True  # offered ids rendezvoused with the turn


def test_cursor_capture_events_do_not_inject(_env, capsys) -> None:
    conv = {"conversation_id": "c1", "cwd": "/repo"}
    hook.cmd_prompt(
        {**conv, "prompt": "do x"},
        hook._parse_args(["prompt", "--source", "cursor"]),
    )
    hook.cmd_tool(
        {**conv, "file_path": "a.py"},
        hook._parse_args(["tool", "--source", "cursor", "--kind", "edit"]),
    )
    assert capsys.readouterr().out == ""
    assert state.claim_recall("c1") is not None


def test_uninjected_recall_credits_nothing_and_is_removed(_env) -> None:
    """An uninjected recall credits no learnings and its stale recall is removed.

    The material turn still closes its loop (observe + reinforce), but with no
    offered learnings the reinforce credits nothing, so an un-injected recall can
    never be mistaken for a used one.
    """
    staged = _env
    delivered: list[state.FinishedTurn] = []
    real_stage_and_flush = hook._stage_and_flush

    def capture(session_id, turn, turn_outcome):
        delivered.append(turn)
        real_stage_and_flush(session_id, turn, turn_outcome)

    conv = {"conversation_id": "c1", "cwd": "/repo"}
    hook.cmd_prompt(
        {**conv, "prompt": "do x"},
        hook._parse_args(["prompt", "--source", "cursor"]),
    )
    hook.cmd_tool(
        {**conv, "file_path": "a.py"},
        hook._parse_args(["tool", "--source", "cursor", "--kind", "edit"]),
    )
    hook.cmd_tool(
        {**conv, "command": "pytest"},
        hook._parse_args(["tool", "--source", "cursor", "--kind", "command"]),
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(hook, "_stage_and_flush", capture)
        hook.cmd_stop(conv, hook._parse_args(["stop", "--source", "cursor"]))

    assert [turn.offered_learning_ids for turn in delivered] == [()]  # nothing credited
    assert state.claim_recall("c1") is None  # the stale recall is removed
    flushed = _last_staged(staged)
    assert flushed["do_observe"] is True
    assert flushed["do_reinforce"] is True  # a material turn still closes its loop


def test_readonly_recall_does_not_touch_state(_env, capsys) -> None:
    hook.cmd_prompt(
        {"conversation_id": "c1", "cwd": "/repo"},
        hook._parse_args(
            [
                "prompt",
                "--source",
                "cursor",
                "--readonly",
                "--emit",
                "text",
                "--goal",
                "do x",
            ]
        ),
    )
    assert capsys.readouterr().out == "INJECTED"  # printed for the skill to apply
    assert state.read_active("c1") is None  # no turn state written


def test_readonly_recall_prints_facts_and_closes_the_throwaway_run(
    _env, capsys, monkeypatch
) -> None:
    closed: list[tuple[str, str, hook.ResolvedContext, str]] = []
    monkeypatch.setattr(
        hook,
        "_resolve",
        lambda agent_id, run_id, goal, source_framework, **_kwargs: hook.ResolvedContext(
            injected_text="RULE",
            injected_facts_text="FACT",
            offered_learning_ids=("L1",),
            offered_claim_ids=("C1",),
        ),
    )
    monkeypatch.setattr(
        hook,
        "_close_readonly_run",
        lambda agent, run_id, context, source: closed.append(
            (agent, run_id, context, source)
        ),
    )
    hook.cmd_prompt(
        {"conversation_id": "c1", "cwd": "/repo"},
        hook._parse_args(
            [
                "prompt",
                "--source",
                "cursor",
                "--readonly",
                "--emit",
                "text",
                "--goal",
                "do x",
            ]
        ),
    )
    assert capsys.readouterr().out == "RULE\n\nFACT"
    assert state.read_active("c1") is None
    assert len(closed) == 1
    agent, run_id, context, source = closed[0]
    assert agent == "agent-x"
    assert run_id
    assert context.offered_claim_ids == ("C1",)
    assert source == "cursor"


def test_a_rejected_readonly_close_says_so_instead_of_failing_silently(
    capsys, monkeypatch
) -> None:
    """A refused decline is a returned outcome, not an exception, so it was invisible.

    This is the first client to send a reason a deployed boundary can refuse, and the
    client mirrors on merge while the API ships on a separate manual dispatch. Silent,
    every read-only recall in that window stays open, holds its resolve reservation to
    the retention sweep, and counts unclosed against the loop-closure alert.
    """
    # HYPER_HOOK_DEBUG is deliberately NOT set: the message has to reach an operator who
    # never went looking for it, so a test that switches the debug channel on would pass
    # against the channel this finding was raised about.
    monkeypatch.delenv("HYPER_HOOK_DEBUG", raising=False)
    # Called through the module-level capture rather than hook._close_readonly_run,
    # because the autouse _env fixture replaces that attribute with a no-op and a test
    # that forgets it asserts against nothing. The _deliver_decline patch below IS
    # consulted, since the function resolves that name from module globals at call time.
    monkeypatch.setattr(
        hook,
        "_deliver_decline",
        _async_returning((hook.FlushOutcome.TERMINAL, "422 unknown reason")),
    )

    _REAL_CLOSE_READONLY_RUN(
        "agent", "run-9", hook.ResolvedContext(injected_text="RULE"), "claude-code"
    )

    printed = capsys.readouterr().err
    assert "was not accepted" in printed
    assert "holds its reservation" in printed


def _async_returning(value):
    async def _call(*_args, **_kwargs):
        return value

    return _call


def test_a_readonly_close_reports_its_own_reason_whether_or_not_anything_was_offered() -> (
    None
):
    """The reason must not depend on the offer, or it collides with the recording path.

    Borrowing ``below_material_threshold`` and ``empty_offer`` is what put this
    population inside the daily alert's earned-and-not-recorded line, outnumbering the
    real losses 43 to 1, with nothing in the stored row able to separate the two.
    """
    empty = hook._readonly_decline_payload(
        "run-2", hook.ResolvedContext(injected_text=""), "cursor"
    )

    assert empty["reason"] == hook.REASON_READONLY_CLOSE
    assert empty["is_delivered"] is False
    assert empty["recall_outcome"] == "resolve_empty"


def test_close_readonly_run_declines_an_offered_recall() -> None:
    assert hook._readonly_decline_payload(
        "run-1",
        hook.ResolvedContext(
            injected_text="RULE",
            offered_learning_ids=("L1",),
            offered_claim_ids=("C1",),
        ),
        "cursor",
    ) == {
        "run_id": "run-1",
        "reason": hook.REASON_READONLY_CLOSE,
        "is_delivered": True,
        # This path prints the block itself, so it reports delivery rather than leaving
        # the run with the clients too old to say, whose remedy is an upgrade.
        "recall_outcome": "delivered",
        "source_framework": "cursor",
    }


def test_tool_injection_carries_claim_ids(_env, capsys) -> None:
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt"]),
    )
    active = state.read_active("s1")
    assert active is not None
    state.write_recall(
        "s1",
        {
            "run_id": active.run_id,
            "injected_text": "RULE",
            "injected_facts_text": "FACT",
            "offered_learning_ids": ["L1"],
            "offered_claim_ids": ["C1"],
        },
    )
    hook.cmd_tool(
        {"session_id": "s1", "cwd": "/repo"},
        hook._parse_args(["tool", "--kind", "command", "--name", "pytest"]),
    )
    out = capsys.readouterr().out
    assert "RULE" in out
    assert "FACT" in out
    injected = state.read_active("s1")
    assert injected is not None
    assert hook._offered_this_turn("s1", injected) == (("L1",), ("C1",))


# -- debug breadcrumbs -------------------------------------------------------


async def _aresolve_ok(agent_id, run_id, goal, **_kwargs):
    return hook.ResolvedContext(injected_text="TEXT", offered_learning_ids=("L1", "L2"))


async def _aresolve_boom(agent_id, run_id, goal, **_kwargs):
    raise RuntimeError("boom")


def test_debug_silent_by_default(_env, capsys, monkeypatch) -> None:
    monkeypatch.delenv("HYPER_HOOK_DEBUG", raising=False)
    hook._debug("should not appear")
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("off_value", ["", "0", "false", "no", "off", "FALSE"])
def test_debug_off_values_stay_silent(_env, capsys, monkeypatch, off_value) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", off_value)
    hook._debug("should not appear")
    assert capsys.readouterr().err == ""


def test_debug_on_writes_stderr(_env, capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    hook._debug("hello world")
    assert "hello world" in capsys.readouterr().err


def test_prompt_no_agent_emits_breadcrumb(_env, capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    monkeypatch.delenv("HYPER_AGENT_NAME", raising=False)
    hook.cmd_prompt(
        {"session_id": "s1", "prompt": "do x", "cwd": "/repo"}, _args("prompt")
    )
    err = capsys.readouterr().err
    assert "no agent configured" in err
    assert state.read_active("s1") is None  # still fails open, no turn written


def test_readonly_recall_sends_its_host_to_resolve(_env, monkeypatch) -> None:
    """The recall names the host that made it.

    Every retrieval event in production carried no attribution because this
    argument was never threaded through, while observe and decline carried it
    all along, so the per-host funnel saw applies and nothing else.
    """
    seen: list[str] = []
    monkeypatch.setattr(
        hook,
        "_resolve",
        lambda agent_id, run_id, goal, source_framework, **_kwargs: (
            seen.append(source_framework),
            hook.ResolvedContext(
                injected_text="INJECTED", offered_learning_ids=("L1",)
            ),
        )[1],
    )
    hook.cmd_prompt(
        {"conversation_id": "c1", "cwd": "/repo"},
        hook._parse_args(
            [
                "prompt",
                "--source",
                "cursor",
                "--readonly",
                "--emit",
                "text",
                "--goal",
                "do x",
            ]
        ),
    )
    assert seen == ["cursor"]


def test_detached_recall_sends_the_turns_host_to_resolve(monkeypatch) -> None:
    """cmd_resolve has no argv, so the host comes off the active turn."""
    seen: list[str] = []

    async def _capture(agent_name, run_id, goal, *, source_framework, **_kwargs):
        seen.append(source_framework)
        return hook.ResolvedContext()

    monkeypatch.setattr(hook, "_aresolve", _capture)
    monkeypatch.setattr(
        hook.state,
        "read_active",
        lambda _session: state.ActiveTurn(
            run_id="run-1",
            agent_name="agent-x",
            goal="do x",
            source_framework="cursor",
            started_at=0.0,
        ),
    )
    hook.cmd_resolve("s1")
    assert seen == ["cursor"]


def test_resolve_ok_breadcrumb_counts_learnings(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    monkeypatch.setattr(hook, "_aresolve", _aresolve_ok)
    context = hook._resolve("agent-x", "run-1", "do x", hook.SOURCE_CLAUDE_CODE)
    assert context.injected_text == "TEXT"
    assert context.offered_learning_ids == ("L1", "L2")
    assert "resolve ok: 2 learning(s)" in capsys.readouterr().err


def test_resolve_failure_breadcrumb_and_fails_open(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    monkeypatch.setattr(hook, "_aresolve", _aresolve_boom)
    assert (
        hook._resolve("agent-x", "run-1", "do x", hook.SOURCE_CLAUDE_CODE)
        == hook.ResolvedContext()
    )
    assert "resolve failed (RuntimeError): boom" in capsys.readouterr().err


# -- distill (caller-driven corpus extraction) -------------------------------


def _distill_spec(**overrides: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "goal": "Extract API design learnings from the referenced design doc",
        "evidence": [
            {
                "id": "before",
                "role": "contrast",
                "status": "failed",
                "content": "x" * 40,
            },
            {
                "id": "after",
                "role": "support",
                "status": "completed",
                "content": "y" * 40,
            },
        ],
    }
    spec.update(overrides)
    return spec


def _delivered_fake(captured: dict[str, Any]):
    """A stand-in for ``_adistill`` that records its kwargs and reports delivery."""

    async def fake_adistill(**kwargs):
        captured.update(kwargs)
        return {
            "status": "delivered",
            "agent": kwargs["agent_name"],
            "run_id": kwargs["run_id"],
            "evidence_count": len(kwargs["evidence"]),
            "is_contrast_declared": kwargs.get("is_contrast_declared", True),
        }

    return fake_adistill


async def _forbidden_adistill(**kwargs):  # pragma: no cover - must never be called
    raise AssertionError(f"the corpus left the machine: {kwargs}")


def test_distill_no_agent_is_skipped(_env, capsys, monkeypatch) -> None:
    monkeypatch.delenv("HYPER_AGENT_NAME", raising=False)
    hook.cmd_distill(_distill_spec(), hook._parse_args(["distill", "--emit", "text"]))
    out = capsys.readouterr().out
    assert "skipped" in out and "HYPER_AGENT_NAME" in out


def test_distill_refuses_an_empty_corpus(_env, capsys, monkeypatch) -> None:
    """The floor is local, so the refusal must arrive without a request.

    Asserting only on the message would not show that: the server's own refusal carries
    almost the same words, so a deleted local guard would still print a matching string
    after a round trip.
    """
    monkeypatch.setattr(hook, "_adistill", _forbidden_adistill)
    spec = _distill_spec(evidence=[])
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    out = capsys.readouterr().out
    assert "skipped" in out and "at least 1 evidence item" in out


def test_distill_sends_a_single_item_corpus(_env, capsys, monkeypatch) -> None:
    """The server admits a one-item corpus, so the client must not hold it back."""
    captured: dict[str, Any] = {}
    monkeypatch.setattr(hook, "_adistill", _delivered_fake(captured))
    spec = _distill_spec(evidence=[{"id": "only", "content": "z" * 40}])
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert len(captured["evidence"]) == 1
    # The singular is only reachable because this diff dropped the floor of two.
    assert "1 evidence item)" in capsys.readouterr().out


def test_distill_forwards_scrubbed_corpus_to_client(_env, capsys, monkeypatch) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(hook, "_adistill", _delivered_fake(captured))
    secret = "sk-livexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    spec = _distill_spec(
        run_id="design-doc-2026-07",
        goal=f"goal includes {secret}",
        evaluation=f"evaluation includes {secret}",
        evidence=[
            {
                "id": "before",
                "label": f"label-{secret}",
                "role": "contrast",
                "status": "failed",
                "source_ref": "https://example.com/design-doc-2026-07",
                "content": "old " * 12,
            },
            {
                "id": "after",
                "role": "support",
                "status": "completed",
                "content": f"token {secret} rotated",
            },
        ],
    )
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))

    assert captured["agent_name"] == "agent-x"  # honours HYPER_AGENT_NAME
    assert captured["run_id"] == "distill:design-doc-2026-07"  # prefixed
    # The descriptive fields are scrubbed; the identifiers are not scrubbed but
    # refused, which is asserted by
    # test_a_credential_in_an_evidence_identifier_refuses_the_whole_corpus. So a
    # credential can never reach the wire by either route.
    joined = " ".join(
        [
            captured["goal"],
            captured["evaluation"],
            *(item.label for item in captured["evidence"]),
            *(item.content for item in captured["evidence"]),
        ]
    )
    assert secret not in joined  # secret-scrubbed before it leaves the machine
    assert [item.id for item in captured["evidence"]] == ["before", "after"]
    assert (
        captured["evidence"][0].source_ref == "https://example.com/design-doc-2026-07"
    )
    out = capsys.readouterr().out
    assert "Distill delivered for agent 'agent-x'" in out


def test_distill_rejects_malformed_payload(_env, capsys, monkeypatch) -> None:
    async def forbidden_adistill(**kwargs):  # pragma: no cover - should not be called
        raise AssertionError(kwargs)

    monkeypatch.setattr(hook, "_adistill", forbidden_adistill)
    hook.cmd_distill(
        {"_hyper_parse_error": "invalid JSON on stdin: nope"},
        hook._parse_args(["distill", "--emit", "text"]),
    )
    assert "invalid JSON" in capsys.readouterr().out


def test_distill_requires_non_empty_goal(_env, capsys, monkeypatch) -> None:
    async def forbidden_adistill(**kwargs):  # pragma: no cover - should not be called
        raise AssertionError(kwargs)

    monkeypatch.setattr(hook, "_adistill", forbidden_adistill)
    spec = _distill_spec(goal="  ")
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert "non-empty goal" in capsys.readouterr().out


def test_distill_sends_a_no_contrast_corpus(_env, capsys, monkeypatch) -> None:
    """A corpus with no contrast yields no learning, but it still yields claims.

    Holding it back locally spent the caller's corpus to protect the learning shelf
    while discarding the claim shelf, and left the server unable to report
    ``weak_contrast`` for a job it never received.

    One role and one status throughout is the only shape the server calls contrast-free:
    ``has_contrast_signal`` returns true on more than one role, so a support/neutral pair
    declares contrast by its rule and would not test this at all.
    """
    captured: dict[str, Any] = {}
    monkeypatch.setattr(hook, "_adistill", _delivered_fake(captured))
    spec = _distill_spec(
        evidence=[
            {"id": "a", "role": "neutral", "status": "completed", "content": "a" * 40},
            {"id": "b", "role": "neutral", "status": "completed", "content": "b" * 40},
        ],
    )
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    out = capsys.readouterr().out
    assert len(captured["evidence"]) == 2
    assert captured["is_contrast_declared"] is False
    # The remedy the deleted refusal used to carry, now delivered alongside the corpus.
    assert "declares no contrast" in out and "claim shelf" in out
    assert "billed" in out


@pytest.mark.parametrize(
    ("first_role", "second_role", "second_status", "evaluation"),
    [
        ("support", "neutral", "completed", None),
        ("contrast", "contrast", "completed", None),
        ("neutral", "neutral", "failed", None),
        (
            "neutral",
            "neutral",
            "completed",
            "the reusable principle is bounded retries",
        ),
    ],
    ids=["two-roles", "contrast-role", "two-statuses", "evaluation-note"],
)
def test_distill_reports_declared_contrast_by_the_servers_rule(
    _env, capsys, monkeypatch, first_role, second_role, second_status, evaluation
) -> None:
    """Each of the server's three signals, mirrored exactly.

    ``_declares_contrast`` restates ``has_contrast_signal`` in the platform's learning
    boundary. It reports rather than refuses, so a drift here misdescribes the corpus to
    the caller instead of refusing it, which is quieter and therefore worth pinning.
    """
    captured: dict[str, Any] = {}
    monkeypatch.setattr(hook, "_adistill", _delivered_fake(captured))
    spec = _distill_spec(
        evidence=[
            {"id": "a", "role": first_role, "status": "completed", "content": "a" * 40},
            {
                "id": "b",
                "role": second_role,
                "status": second_status,
                "content": "b" * 40,
            },
        ],
    )
    if evaluation:
        spec["evaluation"] = evaluation
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert captured["is_contrast_declared"] is True
    assert "declares no contrast" not in capsys.readouterr().out


def test_distill_carries_the_claim_shelfs_keying_fields(_env, monkeypatch) -> None:
    """``subject`` decides whether the facts accumulate or scatter, so it must reach the wire.

    Two spellings of one company become two entities that never corroborate each other
    when it is absent, and this corpus shape is the one the claim shelf reads.
    """
    captured: dict[str, Any] = {}
    monkeypatch.setattr(hook, "_adistill", _delivered_fake(captured))
    spec = _distill_spec(
        evidence=[
            {
                "id": "sheet",
                "content": "c" * 40,
                "subject": "Northwind Freight",
                "declared_sensitivity": {
                    "provenance": {
                        "source_class": "document",
                        "source_id": "drive:pricing",
                    }
                },
            }
        ],
    )
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    item = captured["evidence"][0]
    assert item.subject == "Northwind Freight"
    assert item.declared_sensitivity["provenance"]["source_id"] == "drive:pricing"


def test_distill_carries_a_boolean_flag_and_integer_offsets_in_provenance(
    _env, monkeypatch
) -> None:
    """The boundary admits ``attacker_reachable`` only as a bool and offsets only as ints.

    This check refused both locally, so a source an outsider can write into was never held
    untrusted and no citation could cross. Mutation: restore the strings-only rule and this fails.
    """
    captured: dict[str, Any] = {}
    monkeypatch.setattr(hook, "_adistill", _delivered_fake(captured))
    provenance = {
        "source_id": "drive:pricing",
        "attacker_reachable": True,
        "doc_id": "drive:pricing",
        "text_sha256": "a" * 64,
        "segmenter_version": "v1",
        "unit_index": 2,
        "start": 0,
        "end": 41,
    }
    spec = _distill_spec(
        evidence=[
            {
                "id": "sheet",
                "content": "c" * 40,
                "declared_sensitivity": {"provenance": dict(provenance)},
            }
        ],
    )
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert captured["evidence"][0].declared_sensitivity["provenance"] == provenance


def test_a_nested_list_and_a_flat_boolean_are_still_refused() -> None:
    """Widening to booleans and integers inside a section must not admit any other shape."""
    complaints = hook._declared_sensitivity_complaints(
        {"provenance": {"source_id": ["crm"]}, "subject": True}, 0
    )
    assert complaints == [
        "evidence[0].declared_sensitivity.provenance.source_id is list, and only strings, "
        "integers and booleans are accepted",
        "evidence[0].declared_sensitivity.subject is bool, and only strings are accepted",
    ]


def test_distill_refuses_an_unknown_evidence_key_rather_than_dropping_it(
    _env, capsys, monkeypatch
) -> None:
    """A misspelled key used to vanish, which is the silent discard this path exists to end."""
    monkeypatch.setattr(hook, "_adistill", _forbidden_adistill)
    spec = _distill_spec(evidence=[{"id": "a", "content": "d" * 40, "subjekt": "Acme"}])
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    out = capsys.readouterr().out
    assert "unknown key(s) subjekt" in out and "Nothing was sent" in out


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        (
            [
                {"id": f"e{i}", "content": "x"}
                for i in range(constants.DISTILL_MAX_EVIDENCE + 1)
            ],
            f"at most {constants.DISTILL_MAX_EVIDENCE} evidence items",
        ),
        (
            [{"id": "big", "content": "x" * (constants.DISTILL_MAX_ITEM_CHARS + 1)}],
            f"exceeds {constants.DISTILL_MAX_ITEM_CHARS} characters",
        ),
        (
            [
                {"id": f"e{i}", "content": "x" * (constants.DISTILL_MAX_ITEM_CHARS - 1)}
                for i in range(20)
            ],
            f"over the {constants.DISTILL_MAX_TOTAL_CHARS} limit",
        ),
        (
            [{"id": f"doc-{i}", "content": "x" * 40_000} for i in range(7)],
            "items 0-5 fit one job, so start the next job at item 6 (doc-6)",
        ),
    ],
    ids=["too-many-items", "item-too-long", "corpus-too-large", "names-the-cut-point"],
)
def test_distill_refuses_a_corpus_outside_the_servers_bounds(
    _env, capsys, monkeypatch, evidence, expected
) -> None:
    """The ceilings are refused here because the server's refusal does not survive the trip.

    A bounds violation is a 400 whose detail the write path drops, so the caller would
    otherwise lose both the reason and the corpus to a bare status code.
    """
    monkeypatch.setattr(hook, "_adistill", _forbidden_adistill)
    hook.cmd_distill(
        _distill_spec(evidence=evidence),
        hook._parse_args(["distill", "--emit", "text"]),
    )
    out = capsys.readouterr().out
    assert "skipped" in out and expected in out


def test_the_delivered_receipt_carries_the_contrast_signal(monkeypatch, capsys) -> None:
    """The remedy is only reachable if ``_adistill`` puts the signal on the delivered dict.

    Every other test here stubs ``_adistill``, so a stub that builds the key itself would
    describe a behaviour the production function does not have. This one drives the real
    function against a faked transport, which is the only place the omission shows.
    """

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_duplicated = 0
            self.writes_failed = 0
            self.last_write_error = None

        async def distill(self, **_kwargs):
            return None

        async def drain(self, timeout=30.0):
            self.writes_delivered = 1

        async def aclose(self, drain_timeout=30.0):
            return None

    import hyperstruck.client as client_module

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)
    result = asyncio.run(
        hook._adistill(
            agent_name="agent-x",
            run_id="distill:facts-only",
            goal="Capture the durable facts",
            evidence=hook._evidence_from_spec(
                [{"id": "a", "content": "a" * 40}, {"id": "b", "content": "b" * 40}]
            )[0],
            outcome_spec={},
            evaluation=None,
            is_contrast_declared=False,
        )
    )

    assert result["status"] == "delivered"
    assert result["is_contrast_declared"] is False
    hook._emit_distill_result(result, hook._parse_args(["distill", "--emit", "text"]))
    assert "declares no contrast" in capsys.readouterr().out


def test_distill_run_id_prefix_and_mint() -> None:
    assert hook._distill_run_id("distill:x") == "distill:x"
    assert hook._distill_run_id("x") == "distill:x"
    minted = hook._distill_run_id(None)
    assert minted.startswith("distill:ide-")


def test_a_run_id_is_never_rewritten() -> None:
    # Rewriting is what caused the incident: the scrubber flattened every long
    # descriptive id to one literal, so an idempotent distil silently discarded
    # all but the first. An identifier must survive verbatim or be refused.
    descriptive = "learning-gate-observability-2026-08-02"
    assert (
        hook._scrub_distill_string(descriptive) != descriptive
    ), "fixture must actually trip the scrubber"

    assert hook._distill_run_id(descriptive) == f"distill:{descriptive}"


def test_a_run_id_carrying_a_real_credential_is_refused_with_a_reason() -> None:
    rejection = hook._distill_run_id_rejection("run-sk-AbCdEf0123456789AbCdEf")

    assert rejection is not None
    assert "refused" in rejection


@pytest.mark.parametrize(
    "credential",
    [
        "run-sk-AbCdEf0123456789AbCdEf",
        "job-ghp_AbCdEf0123456789AbCdEf0123",
        "xoxb-0123456789-AbCdEfGhIj",
        "deploy-AKIA0123456789ABCDEF",
        "password=hunter2000",
    ],
)
def test_every_known_credential_shape_is_refused(credential: str) -> None:
    # The refusal must span the shapes the shared detector knows, not just the
    # one the incident happened to involve.
    assert hook._distill_run_id_rejection(credential) is not None


@pytest.mark.parametrize(
    "descriptive",
    [
        # Each is 32+ chars with no whitespace, so the scrubber's generic entropy
        # arm flattens it. Refusing these is the defect this test pins: they are
        # the correlatable ids the refusal exists to protect, not credentials.
        "learning-gate-observability-2026-08-02",
        "client-review-round-2-fixes-and-followups",
        "quarterly-supplier-code-of-conduct-review-2026-08-04",
        "distill-run-id-collision-fix-verification",
    ],
)
def test_a_long_descriptive_run_id_is_accepted_though_the_scrubber_would_flatten_it(
    descriptive: str,
) -> None:
    assert (
        hook._scrub_distill_string(descriptive) != descriptive
    ), "fixture must actually trip the scrubber"

    assert hook._distill_run_id_rejection(descriptive) is None
    assert hook._distill_run_id(descriptive) == f"distill:{descriptive}"


def test_ordinary_run_ids_are_accepted() -> None:
    for clean in (
        "ci-lint-bandit-gate-2026-08-02",
        "meeting-8220",
        "distill:already-prefixed",
        None,
        "  ",
    ):
        assert hook._distill_run_id_rejection(clean) is None


def test_clean_run_id_keeps_its_prefix_exactly_once() -> None:
    assert (
        hook._distill_run_id("ci-lint-bandit-gate-2026-08-02")
        == "distill:ci-lint-bandit-gate-2026-08-02"
    )
    assert (
        hook._distill_run_id("distill:already-prefixed") == "distill:already-prefixed"
    )


def _run_distill_with_run_id(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> tuple[list[str], list[dict[str, Any]]]:
    monkeypatch.setattr(hook, "configured_agent_name", lambda: "dev-copilot")
    dispatched: list[str] = []
    monkeypatch.setattr(hook, "_adistill", lambda **kw: dispatched.append(kw["run_id"]))

    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(
        hook, "_emit_distill_result", lambda result, args: emitted.append(result)
    )

    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": run_id,
            "evidence": [
                {
                    "id": "a",
                    "role": "contrast",
                    "status": "failed",
                    "content": "the rejected approach",
                },
                {
                    "id": "b",
                    "role": "support",
                    "status": "completed",
                    "content": "the accepted approach",
                },
            ],
        },
        argparse.Namespace(emit="json", source="claude-code", goal=None),
    )
    return dispatched, emitted


def test_a_refused_run_id_never_reaches_the_wire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The unit tests above exercise a pure function; the original defect was that a
    # bad id reached the server. This asserts the refusal actually stops dispatch.
    dispatched, emitted = _run_distill_with_run_id(
        monkeypatch, "run-sk-AbCdEf0123456789AbCdEf"
    )

    assert dispatched == [], "a refused run id must never be dispatched"
    assert emitted and emitted[0]["status"] == "skipped"


def test_the_refusal_reason_survives_onto_the_emitted_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Asserted on the dispatch path, not just the pure function: a caller who is
    # refused learns why only from what cmd_distill emits, so a regression that
    # dropped the reason there would leave every other assertion green.
    _, emitted = _run_distill_with_run_id(monkeypatch, "run-sk-AbCdEf0123456789AbCdEf")

    reason = emitted[0]["reason"]
    assert "refused rather than rewritten" in reason
    assert "omit run_id" in reason, "the reason must carry the escape hatch"
    assert (
        "sk-AbCdEf0123456789AbCdEf" not in reason
    ), "the reason must not echo the secret"


def test_the_refusal_reveals_at_most_the_shape_head() -> None:
    # Pins CREDENTIAL_HEAD_CHARS itself. Asserting only that the whole secret is
    # absent passes for any width up to len-1: raising the constant to 20 left the
    # suite green while the reason printed 17 characters of a 25-character key.
    assert CREDENTIAL_HEAD_CHARS == 4
    secret = "sk-AbCdEf0123456789AbCdEf"

    reason = hook._distill_run_id_rejection(secret) or ""

    assert secret[:CREDENTIAL_HEAD_CHARS] in reason
    assert secret[: CREDENTIAL_HEAD_CHARS + 1] not in reason


def test_a_descriptive_run_id_reaches_the_wire_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The complement, and the regression that matters: refusing this is what made
    # a correlatable id unusable, so dispatch must happen and carry it unaltered.
    descriptive = "quarterly-supplier-code-of-conduct-review-2026-08-04"
    assert (
        hook._scrub_distill_string(descriptive) != descriptive
    ), "fixture must actually trip the scrubber, or this proves nothing"

    dispatched, emitted = _run_distill_with_run_id(monkeypatch, descriptive)

    assert dispatched == [f"distill:{descriptive}"]
    assert not any(result["status"] == "skipped" for result in emitted)


def test_distinct_evidence_ids_stay_distinct() -> None:
    # The run-id defect one level down. Both of these tripped the entropy scrubber
    # and were flattened to the same marker, so two evidence items arrived sharing
    # one step id. A many-to-one map over a key manufactures collisions.
    first, second = (
        "baseline-approach-before-the-fix-2026",
        "the-accepted-approach-after-fix-2026",
    )
    assert hook._scrub_distill_string(first) == hook._scrub_distill_string(
        second
    ), "fixture must actually collide under the scrubber"

    evidence, _ = hook._evidence_from_spec(
        [
            {"id": first, "role": "contrast", "status": "failed", "content": "a"},
            {"id": second, "role": "support", "status": "completed", "content": "b"},
        ]
    )

    assert [item.id for item in evidence] == [first, second]


def test_a_source_ref_url_survives_intact() -> None:
    # source_ref is documented in the API as "non-secret provenance: a doc id or
    # URL". Flattening it shredded the citation a distilled learning rests on.
    url = "https://github.com/hyperstruck/core-platform/blob/main/docs/prompt_leak_backfill.md"
    assert hook._scrub_distill_string(url) != url, "fixture must trip the scrubber"

    evidence, _ = hook._evidence_from_spec(
        [{"id": "a", "content": "x", "source_ref": url, "status": "completed"}]
    )

    assert evidence[0].source_ref == url


def test_evidence_label_and_content_are_still_scrubbed() -> None:
    # The other half of the rule: these carry meaning by content, so a redacted
    # span still reads as what it was and scrubbing stays correct.
    secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    evidence, _ = hook._evidence_from_spec(
        [
            {
                "id": "a",
                "content": f"we used {secret}",
                "label": secret,
                "status": "completed",
            }
        ]
    )

    assert secret not in evidence[0].content
    assert secret not in evidence[0].label


@pytest.mark.parametrize("field", ["id", "source_ref"])
def test_a_credential_in_an_evidence_identifier_refuses_the_whole_corpus(
    field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook, "configured_agent_name", lambda: "dev-copilot")
    dispatched: list[str] = []
    monkeypatch.setattr(hook, "_adistill", lambda **kw: dispatched.append(kw["run_id"]))
    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(
        hook, "_emit_distill_result", lambda result, args: emitted.append(result)
    )

    entry: dict[str, Any] = {
        "id": "a",
        "role": "contrast",
        "status": "failed",
        "content": "x",
    }
    entry[field] = "run-ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": "an-ordinary-descriptive-run-id-2026",
            "evidence": [
                entry,
                {"id": "b", "role": "support", "status": "completed", "content": "y"},
            ],
        },
        argparse.Namespace(emit="json", source="claude-code", goal=None),
    )

    assert (
        dispatched == []
    ), "a corpus with a credential in an identifier must not dispatch"
    assert emitted[0]["status"] == "skipped"
    assert field in emitted[0]["reason"]
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" not in emitted[0]["reason"]


def test_an_unusable_evidence_entry_is_reported_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Five items in, two usable: the other three used to vanish and the client
    # then printed "delivered, 2 evidence items". A dropped item changes what is
    # learned, so it cannot be silent, which is this path's whole premise.
    monkeypatch.setattr(hook, "configured_agent_name", lambda: "dev-copilot")
    dispatched: list[str] = []
    monkeypatch.setattr(hook, "_adistill", lambda **kw: dispatched.append(kw["run_id"]))
    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(
        hook, "_emit_distill_result", lambda result, args: emitted.append(result)
    )

    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": "an-ordinary-descriptive-run-id-2026",
            "evidence": [
                {
                    "id": "a",
                    "content": "real one",
                    "status": "failed",
                    "role": "contrast",
                },
                {"id": "b", "content": "", "status": "completed"},
                "not-a-dict",
                {
                    "id": "d",
                    "content": "real two",
                    "status": "completed",
                    "role": "support",
                },
            ],
        },
        argparse.Namespace(emit="json", source="claude-code", goal=None),
    )

    assert dispatched == [], "a corpus that lost items must not be delivered"
    reason = emitted[0]["reason"]
    assert "evidence[1] has no content" in reason
    assert "evidence[2] is not an object" in reason
    assert "retry on the same run id" in reason


def test_an_unknown_status_is_reported_rather_than_coerced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # status is one of the three signals establishing contrast, so coercing
    # "error" to "completed" can invert what the corpus asserts.
    monkeypatch.setattr(hook, "configured_agent_name", lambda: "dev-copilot")
    monkeypatch.setattr(hook, "_adistill", lambda **kw: None)
    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(
        hook, "_emit_distill_result", lambda result, args: emitted.append(result)
    )

    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": "an-ordinary-descriptive-run-id-2026",
            "evidence": [
                {"id": "a", "content": "one", "status": "error"},
                {"id": "b", "content": "two", "status": "completed"},
            ],
        },
        argparse.Namespace(emit="json", source="claude-code", goal=None),
    )

    assert "evidence[0].status 'error'" in emitted[0]["reason"]


def test_evidence_from_spec_reports_empty_and_defaults_role() -> None:
    items, _ = hook._evidence_from_spec(
        [
            {"id": "a", "content": "real content here"},
            {"id": "b", "content": "   "},  # dropped: blank
            "not-a-dict",  # dropped: wrong type
        ]
    )
    assert len(items) == 1
    assert items[0].role == "neutral" and items[0].status == "completed"


def test_distill_success_coercion() -> None:
    assert hook._distill_success(False) is False
    assert hook._distill_success("false") is False
    assert hook._distill_success("0") is False
    assert hook._distill_success("true") is True
    assert hook._distill_success("not-a-bool") is True


def test_read_stdin_preserves_json_parse_error(monkeypatch) -> None:
    monkeypatch.setattr(hook.sys.stdin, "read", lambda: "{")
    assert "invalid JSON" in hook._read_stdin()["_hyper_parse_error"]


@pytest.mark.parametrize(
    ("mode", "expected_status"),
    [
        ("delivered", "delivered"),
        ("failed", "error"),
        ("pending", "pending"),
        # A duplicate is a 2xx that dispatched nothing. Reporting it as delivered
        # is the misreport that let silently discarded distils go unnoticed.
        ("duplicated", "skipped"),
    ],
)
def test_adistill_reports_delivery_outcome(
    _env, monkeypatch, mode, expected_status
) -> None:
    import hyperstruck.client as client_module

    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_duplicated = 0
            self.writes_failed = 0
            self.last_write_error = None

        async def distill(self, **kwargs):
            captured.update(kwargs)

        async def drain(self, timeout=30.0):
            if mode == "delivered":
                self.writes_delivered = 1
            elif mode == "duplicated":
                self.writes_delivered = 1
                self.writes_duplicated = 1
            elif mode == "failed":
                self.writes_failed = 1
                self.last_write_error = "HTTP 422: bad corpus"

        async def aclose(self, drain_timeout=30.0):
            captured["drain_timeout"] = drain_timeout

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)
    secret = "sk-livexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    result = asyncio.run(
        hook._adistill(
            agent_name="agent-x",
            run_id="distill:x",
            goal="goal",
            evidence=hook._evidence_from_spec(_distill_spec()["evidence"])[0],
            outcome_spec={"is_success": "false", "summary": f"summary {secret}"},
            evaluation=None,
            is_contrast_declared=True,
        )
    )

    assert result["status"] == expected_status
    assert captured["outcome"].is_success is False
    assert secret not in (captured["outcome"].summary or "")


def test_the_delivered_spans_are_cut_from_the_goal_that_is_actually_sent(
    _env, monkeypatch
) -> None:
    """The scrub-order trap, pinned against the string that is actually sent.

    The boundary matches a client span to the text by content. One span it cannot find
    discards the whole tagging for that episode, counted on the server and silent to us,
    so a run reads as fully tagged while every span was thrown away. The goal is scrubbed
    before it is ever stored, so spans cut from the host's raw prompt carry a secret where
    the goal carries a placeholder, and miss on exactly the episodes that had one.

    **What this can and cannot fail is worth stating, because the obvious claim is false.**
    Moving the cut back to ``cmd_prompt`` would pass: the scrub and the clip are both
    idempotent, so the goal at capture and the goal on the wire are the same string today.
    That was checked rather than assumed, and the last block below is what keeps it honest.
    It drives the same minting over the RAW prompt and shows those spans do not concatenate
    to what was sent, so the property pinned here is "cut from the sent string", not "cut
    late".

    So this fails on a cut moved anywhere upstream of the scrub, and on any future step
    that rewrites the goal between capture and delivery, which is the direction the risk
    actually runs: a second pass over the goal would strand every span in silence.
    """
    import hyperstruck.client as client_module

    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 0
            self.writes_terminal_failed = False
            self.last_write_error = None

        async def observe(self, **kwargs):
            captured["episode"] = kwargs["episode"]

        async def reinforce(self, **kwargs):
            captured.setdefault("episode", kwargs.get("episode"))

        async def drain(self, timeout=30.0):
            self.writes_delivered = 1

        async def aclose(self, drain_timeout=30.0):
            return None

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    staged = _env
    session = "s-spans"
    # A slash-command envelope the host wrote, with a secret inside it, so the scrub has
    # something to rewrite in the same string the spans cover.
    raw_prompt = (
        "<command-name>/deploy</command-name>\n"
        "<command-args>--token sk-live-4c9f2a7b1e8d3f60a5c7b9e1d2f4a6c8</command-args>\n"
        "Now check the deploy landed."
    )
    hook.cmd_prompt(
        {"session_id": session, "prompt": raw_prompt, "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "client.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "2 passed",
            "exit_code": 0,
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))

    flushed = _last_staged(staged)
    assert "episode" in flushed, "the turn declined rather than staging an episode"
    outcome, _cause = asyncio.run(hook._deliver(flushed))

    assert outcome is hook.FlushOutcome.DELIVERED
    episode = captured["episode"]
    assert episode.spans, "the goal was not tagged at all"
    assert "".join(span.text for span in episode.spans) == episode.goal
    harness = [span.text for span in episode.spans if span.origin == "harness"]
    assert any(text.startswith("<command-name>") for text in harness)
    prose = "".join(s.text for s in episode.spans if s.origin == "user_prose")
    assert "Now check the deploy landed." in prose

    # The pre-change shape, driven not described: minting from the raw prompt gives spans
    # the boundary cannot find.
    from hyperstruck.ide.prompt_spans import prompt_spans as _mint

    raw_spans = _mint(raw_prompt, "claude-code")
    assert raw_spans, "the raw prompt carried no markup, so this proves nothing"
    assert "".join(span.text for span in raw_spans) != episode.goal
    assert any("sk-live" in span.text for span in raw_spans)
    assert not any("sk-live" in span.text for span in episode.spans)


def test_deliver_decline_calls_the_client_and_reports_outcome(
    _env, monkeypatch
) -> None:
    """Drive a staged decline all the way through delivery, not just staging.

    Staging assertions alone cannot catch a broken client call: they stop before
    the client is ever constructed. This runs the real _deliver dispatch so the
    decline's signature and await are exercised.
    """
    import hyperstruck.client as client_module

    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 0
            self.writes_terminal_failed = False
            self.last_write_error = None

        async def decline(self, **kwargs):
            captured.update(kwargs)

        async def drain(self, timeout=30.0):
            self.writes_delivered = 1

        async def aclose(self, drain_timeout=30.0):
            captured["closed"] = True

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    outcome, cause = asyncio.run(
        hook._deliver(
            {
                "agent_name": "agent-x",
                "decline": {
                    "run_id": "agent-x:s1:r",
                    "reason": REASON_NO_TOOL_CALLS,
                    "is_delivered": True,
                    "source_framework": "claude-code",
                },
            }
        )
    )

    assert outcome is hook.FlushOutcome.DELIVERED
    assert cause is None
    assert captured["run_id"] == "agent-x:s1:r"
    assert captured["reason"] == REASON_NO_TOOL_CALLS
    assert captured["is_delivered"] is True
    assert captured["closed"] is True


def test_reinforce_tells_the_boundary_whether_the_recall_was_ever_shown(
    _env, monkeypatch
) -> None:
    """Without this the boundary has one field for two very different runs.

    An absent receipt reads as a client that lost its evidence, and the run that was
    never shown its learnings at all is recorded as the same defect. It is the larger
    population by far, and it is the client behaving correctly.
    """
    import hyperstruck.client as client_module

    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 0
            self.writes_terminal_failed = False
            self.last_write_error = None

        async def reinforce(self, **kwargs):
            captured.update(kwargs)

        async def drain(self, timeout=30.0):
            self.writes_delivered = 1

        async def aclose(self, drain_timeout=30.0):
            return None

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    outcome, _cause = asyncio.run(
        hook._deliver(
            {
                "agent_name": "agent-x",
                "episode": {
                    "run_id": "agent-x:s1:r",
                    "goal": "do x",
                    "steps": [],
                    "outcome": {"is_success": True},
                    "source_framework": "claude-code",
                },
                "do_reinforce": True,
                "context_receipt": None,
                "is_delivered": False,
                "recall_outcome": RecallOutcome.RESOLVE_TIMED_OUT,
            }
        )
    )

    assert outcome is hook.FlushOutcome.DELIVERED
    assert captured["is_delivered"] is False
    assert captured["recall_outcome"] == RecallOutcome.RESOLVE_TIMED_OUT


def test_a_finished_turn_stages_the_reason_it_has_no_receipt(_env, monkeypatch) -> None:
    """The reason has to survive staging, or only the machine that made it can see it."""
    staged: list[dict[str, Any]] = []
    monkeypatch.setattr(hook, "_spawn_flush", lambda _path: None)
    monkeypatch.setattr(
        state, "stage_flush", lambda _s, _r, payload: staged.append(payload) or "p"
    )
    state.write_active(
        "s-stage",
        state.ActiveTurn(
            run_id="run-1",
            agent_name="agent-x",
            goal="do x",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )
    state.mark_injection_point("s-stage", "run-1")
    state.write_recall_status("s-stage", "run-1", RecallOutcome.RECALL_UNCLAIMED)
    state.append_step("s-stage", {"id": "1", "name": "Bash", "status": "completed"})
    state.append_step("s-stage", {"id": "2", "name": "Bash", "status": "completed"})

    hook.cmd_stop(
        {"session_id": "s-stage", "cwd": "/repo", "status": "completed"},
        hook._parse_args(["stop"]),
    )

    assert staged, "the turn staged nothing at all"
    declined = staged[0]["decline"]
    assert declined["is_delivered"] is False
    assert declined["recall_outcome"] == RecallOutcome.RECALL_UNCLAIMED

    staged.clear()
    state.write_active(
        "s-stage",
        state.ActiveTurn(
            run_id="run-2",
            agent_name="agent-x",
            goal="do x",
            source_framework="claude-code",
            started_at=1.0,
            offered_learning_ids=("L1",),
        ),
    )
    state.write_recall_status("s-stage", "run-2", RecallOutcome.RESOLVE_TIMED_OUT)
    state.append_step("s-stage", {"id": "1", "name": "Bash", "status": "completed"})
    state.append_step("s-stage", {"id": "2", "name": "Bash", "status": "completed"})

    hook.cmd_stop(
        {"session_id": "s-stage", "cwd": "/repo", "status": "completed"},
        hook._parse_args(["stop"]),
    )

    assert staged[0]["do_reinforce"] is True
    assert staged[0]["is_delivered"] is False
    assert staged[0]["recall_outcome"] == RecallOutcome.RESOLVE_TIMED_OUT


def test_deliver_decline_reports_a_terminal_rejection(_env, monkeypatch) -> None:
    """A 4xx on a decline must be terminal, so it counts toward the retry cap."""
    import hyperstruck.client as client_module

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 1
            self.writes_terminal_failed = True
            self.last_write_error = "HTTP 422"

        async def decline(self, **kwargs):
            return None

        async def drain(self, timeout=30.0):
            return None

        async def aclose(self, drain_timeout=30.0):
            return None

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    outcome, cause = asyncio.run(
        hook._deliver(
            {
                "agent_name": "agent-x",
                "decline": {"run_id": "r", "reason": REASON_NO_TOOL_CALLS},
            }
        )
    )

    assert outcome is hook.FlushOutcome.TERMINAL
    assert cause == "HTTP 422"


def test_this_host_no_longer_puts_an_utterance_on_the_wire() -> None:
    """Asserted by the key's absence, so reintroducing it unpopulated fails here.

    The field remains on the API for callers with a human-input channel to populate.
    This host had one only because it deferred a turn until the next message arrived,
    and with the deferral gone there is no moment at which it could honestly speak for
    the turn being written.
    """
    finished = state.FinishedTurn(
        run_id="r1",
        agent_name="a",
        goal="fix the vacuity gate",
        steps=({"status": "completed", "description": "edit"},),
        source_framework="claude-code",
        ended_at=0.0,
    )

    episode = hook._build_episode(finished, is_success=True)

    assert "principal_utterance" not in episode
    assert not hasattr(finished, "principal_utterance")
    assert "principal_utterance" not in redact_ide_episode(episode)


def test_the_wire_model_carries_the_utterance_into_the_payload() -> None:
    """The wire object's own projection, which is a different question from where the value comes from.

    Delivery no longer reads a staged utterance at all: it mints one from the spans it cut, and
    ``test_delivery_mints_the_utterance_from_the_prose_it_tagged`` is what pins that. This one is
    still worth keeping and is now named for what it actually covers, because a field can be
    correct on the ``Episode`` and dropped by ``to_payload``, which is how this field came to be
    plumbed through five layers and never transmitted.
    """
    staged = {
        "run_id": "r1",
        "goal": "write the README",
        "steps": [],
        "outcome": {
            "is_success": False,
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0,
        },
        "source_framework": "claude-code",
        "principal_utterance": "we use British English in this repository",
        "thread_id": None,
    }

    episode = Episode(
        run_id=staged["run_id"],
        goal=staged["goal"],
        steps=(),
        outcome=TerminalOutcome(
            is_success=False, total_steps=0, completed_steps=0, failed_steps=0
        ),
        source_framework=staged["source_framework"],
        principal_utterance=staged.get("principal_utterance"),
        thread_id=staged.get("thread_id"),
    )

    assert (
        episode.to_payload()["principal_utterance"]
        == "we use British English in this repository"
    )


def test_the_payload_omits_the_key_when_there_is_no_utterance() -> None:
    """The API forbids extra keys and rejects a forbidden one even when its value is null."""
    episode = Episode(
        run_id="r1",
        goal="g",
        steps=(),
        outcome=TerminalOutcome(
            is_success=True, total_steps=0, completed_steps=0, failed_steps=0
        ),
        source_framework="claude-code",
    )

    assert "principal_utterance" not in episode.to_payload()


def test_delivery_hands_the_receipt_to_reinforce(monkeypatch) -> None:
    """The staged receipt must survive the rebuild that happens at the moment of delivery.

    Delivery reconstructs the wire call field by field in a detached process, which is how
    the principal utterance was plumbed through five layers and never transmitted. A receipt
    lost there is worse than one never captured: the run credits nothing and every counter
    reports a host that stayed silent.
    """
    import asyncio

    from hyperstruck import client as client_module

    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 0
            self.writes_terminal_failed = False
            self.last_write_error = None

        async def observe(self, **kwargs):
            captured["observed"] = True

        async def reinforce(self, **kwargs):
            captured.update(kwargs)

        async def drain(self, timeout=30.0):
            return None

        async def aclose(self, drain_timeout=30.0):
            return None

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    outcome, _cause = asyncio.run(
        hook._deliver(
            {
                "agent_name": "agent-x",
                "episode": {
                    "run_id": "agent-x:s1:r",
                    "goal": "ship it",
                    "steps": [],
                    "outcome": {
                        "is_success": True,
                        "total_steps": 0,
                        "completed_steps": 0,
                        "failed_steps": 0,
                    },
                    "source_framework": "claude-code",
                },
                "do_observe": False,
                "do_reinforce": True,
                "context_receipt": "<!-- hyperstruck-run: agent-x:s1:r -->\n- the rule",
            }
        )
    )

    assert outcome is hook.FlushOutcome.DELIVERED
    assert captured["context_receipt"] == (
        "<!-- hyperstruck-run: agent-x:s1:r -->\n- the rule"
    )


def test_a_turn_with_no_receipt_delivers_none_rather_than_a_claim(monkeypatch) -> None:
    """A host that observed nothing says nothing; it never substitutes what it emitted."""
    import asyncio

    from hyperstruck import client as client_module

    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 0
            self.writes_terminal_failed = False
            self.last_write_error = None

        async def reinforce(self, **kwargs):
            captured.update(kwargs)

        async def drain(self, timeout=30.0):
            return None

        async def aclose(self, drain_timeout=30.0):
            return None

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    asyncio.run(
        hook._deliver(
            {
                "agent_name": "agent-x",
                "episode": {
                    "run_id": "agent-x:s1:r",
                    "goal": "ship it",
                    "steps": [],
                    "outcome": {
                        "is_success": True,
                        "total_steps": 0,
                        "completed_steps": 0,
                        "failed_steps": 0,
                    },
                    "source_framework": "claude-code",
                },
                "do_observe": False,
                "do_reinforce": True,
            }
        )
    )

    assert captured["context_receipt"] is None


# -- exposure receipt capture ------------------------------------------------


def _accepted_line(run_id: str, body: str) -> str:
    """One editor acceptance record, the artefact the receipt is read out of."""
    return json.dumps(
        {
            "type": "attachment",
            "attachment": {
                "type": "hook_additional_context",
                "content": [f"{receipt.marker(run_id)}\n{body}"],
            },
        }
    )


def _transcript(tmp_path, *lines: str):
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return str(path)


def test_an_interrupted_turn_still_reports_what_the_editor_accepted(
    _env, tmp_path
) -> None:
    """Orphan recovery is the commonest end for a turn, so a blind one loses most credit.

    A turn whose stop hook never fired is finalised by the NEXT prompt, and its marker is
    already in the transcript the next prompt is handed. Recovering with no receipt would
    make every interrupted turn credit nothing while looking exactly like a host that
    reported honestly and matched nothing.
    """
    session = "s-orphan"
    hook.cmd_prompt(
        {"session_id": session, "prompt": "edit a.py", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "a.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    orphan = state.read_active(session)
    assert orphan is not None
    path = _transcript(tmp_path, _accepted_line(orphan.run_id, "- the recovered rule"))

    with _capturing_delivered_turns() as delivered:
        hook.cmd_prompt(
            {
                "session_id": session,
                "prompt": "now edit b.py",
                "cwd": "/repo",
                "transcript_path": path,
            },
            _args("prompt"),
        )

    assert len(delivered) == 1
    assert "the recovered rule" in delivered[0].context_receipt


def test_a_swept_turn_reads_the_transcript_it_recorded_at_its_start(
    _env, tmp_path
) -> None:
    """The sweep finalises ANOTHER session's turn, so no payload it holds is about it.

    Without the path stored on the turn there is nowhere to look, and every abandoned
    session credits nothing however faithfully its editor recorded the block.
    """
    staged = _env
    path = _transcript(
        tmp_path, _accepted_line("agent-x:oldsess:r1", "- the swept rule")
    )
    state.write_active(
        "oldsess",
        state.ActiveTurn(
            run_id="agent-x:oldsess:r1",
            agent_name="agent-x",
            goal="g",
            source_framework="claude-code",
            started_at=0.0,  # far past the eviction window
            offered_learning_ids=("L1",),
            is_injected_by_previous_release=True,
            transcript_path=path,
        ),
    )

    with _capturing_delivered_turns() as delivered:
        hook._sweep_stale(exclude="other")

    assert len(delivered) == 1
    assert "the swept rule" in delivered[0].context_receipt
    assert len(staged) == 1  # the swept turn is delivered, not held


def test_the_live_payloads_transcript_wins_over_the_one_stored_at_turn_start(
    _env, tmp_path
) -> None:
    """A resumed session writes to a new transcript, so the stored path goes stale."""
    session = "s-resumed"
    hook.cmd_prompt(
        {
            "session_id": session,
            "prompt": "do x",
            "cwd": "/repo",
            "transcript_path": str(tmp_path / "gone.jsonl"),
        },
        _args("prompt"),
    )
    active = state.read_active(session)
    assert active is not None
    current = tmp_path / "resumed.jsonl"
    current.write_text(_accepted_line(active.run_id, "- the rule after resume") + "\n")
    state.write_active(
        session,
        replace(active, is_injected_by_previous_release=True),
        reset_steps=False,
    )

    with _capturing_delivered_turns() as delivered:
        hook.cmd_stop(
            {"session_id": session, "cwd": "/repo", "transcript_path": str(current)},
            _args("stop"),
        )

    assert len(delivered) == 1
    assert "the rule after resume" in delivered[0].context_receipt


def test_only_claude_codes_block_is_stamped_with_a_marker(_env, capsys) -> None:
    """Cursor keeps no acceptance record, so a marker there is context spent for nothing."""
    hook.cmd_prompt(
        {"conversation_id": "c-mark", "prompt": "do x", "cwd": "/repo"},
        hook._parse_args(["prompt", "--source", "cursor"]),
    )
    capsys.readouterr()
    hook.cmd_tool(
        {"conversation_id": "c-mark", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool", "--source", "cursor", "--inject"]),
    )

    emitted = json.loads(capsys.readouterr().out)["additional_context"]

    assert emitted == "INJECTED"
    active = state.read_active("c-mark")
    assert active is not None
    assert receipt.marker(active.run_id) not in emitted


def test_an_oversized_receipt_is_clipped_rather_than_dropped(_env) -> None:
    """Clipping costs the rules past the cut; dropping costs the run every rule it has.

    What the clip must preserve is the server's ability to SEE that it was clipped.
    An over-cap receipt puts the boundary into its confirm-only lane, where nothing is
    demoted; a receipt cut to fit under that ceiling would read as a complete account of
    the block, and every rule past the cut would be recorded UNEXPOSED, which is
    terminal. So the assertion that matters is not the length, it is that the delivered
    body is still over the boundary's ceiling and still names its run.
    """
    marker = receipt.marker("agent-x:s1:r1")
    oversized = marker + "\n" + ("- a rule that will not fit. " * 20_000)
    assert len(oversized) > hook.MAX_RECEIPT_CHARS

    clipped = hook._clipped_receipt(oversized)

    assert clipped is not None
    assert len(clipped) > _BOUNDARY_RECEIPT_CEILING, (
        "a clip below the boundary's ceiling would be read as complete evidence and "
        "would demote every rule past the cut"
    )
    assert clipped.startswith(marker), "a clipped receipt must still name its run"
    assert hook._clipped_receipt("") is None
    assert hook._clipped_receipt(marker) == marker


def test_a_turn_that_never_injected_reads_no_transcript(_env, tmp_path) -> None:
    """No injection means no marker, so the read is a guaranteed miss over a growing file.

    It also means nothing was shown, so the turn reports why the recall never reached
    the model rather than reporting a receipt it was never owed.
    """
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(_accepted_line("agent-x:s:r", "- a rule") + "\n")
    turn = state.ActiveTurn(
        run_id="agent-x:s:r",
        agent_name="agent-x",
        goal="do x",
        source_framework="claude-code",
        started_at=0.0,
        transcript_path=str(transcript),
    )
    state.write_recall_status("s1", turn.run_id, RecallOutcome.RESOLVE_TIMED_OUT)

    assert (
        hook._acceptance_record("s1", turn, []).outcome
        is RecallOutcome.RESOLVE_TIMED_OUT
    )
    delivered = hook._acceptance_record(
        "s1", replace(turn, is_injected_by_previous_release=True), []
    )
    assert delivered.receipt != ""
    assert delivered.outcome is RecallOutcome.DELIVERED


def test_a_turn_whose_resolve_never_landed_says_so_rather_than_blaming_the_receipt(
    _env,
) -> None:
    """An absent verdict is its own answer: the resolve had not finished by the stop.

    Reported apart from a resolve that timed out or failed, because one is a race the
    turn lost and the other is the hosted call not clearing the deadline it is given.
    """
    turn = state.ActiveTurn(
        run_id="agent-x:s:r",
        agent_name="agent-x",
        goal="do x",
        source_framework="claude-code",
        started_at=0.0,
    )

    assert (
        hook._acceptance_record("s-none", turn, []).outcome
        is RecallOutcome.RECALL_MISSING
    )


def test_a_stash_nothing_claimed_says_whether_there_was_anywhere_to_put_it(
    _env,
) -> None:
    """One recorded verdict, two causes, and only one of them is a defect.

    This turn's own recall rides a tool event on both hosts, so a turn that called no
    tool offered nowhere to show it: crediting nothing is correct and there is no fix.
    A turn that did call one had every chance and did not take it, which is the drop
    the credit-rate alert exists to catch. Reported as one number the second is hidden
    inside the first.
    """
    turn = state.ActiveTurn(
        run_id="agent-x:s:r",
        agent_name="agent-x",
        goal="do x",
        source_framework="claude-code",
        started_at=0.0,
    )
    state.write_recall_status("s2", turn.run_id, RecallOutcome.RECALL_UNCLAIMED)

    no_point = hook._acceptance_record("s2", turn)
    state.mark_injection_point("s2", turn.run_id)
    had_point = hook._acceptance_record("s2", turn)

    assert no_point.outcome is RecallOutcome.RECALL_NO_INJECTION_POINT
    assert had_point.outcome is RecallOutcome.RECALL_UNCLAIMED
    assert not no_point.is_delivered and not had_point.is_delivered


def test_the_injection_point_is_recorded_not_inferred_from_captured_steps(_env) -> None:
    """The two diverge on Cursor, which is the host this most affects.

    Cursor injects from ``postToolUse`` and captures steps from its file-edit and shell
    hooks, so a turn of pure reads has every chance to be shown its recall and captures
    nothing. Inferring from the step count would call that drop structural, when it is the
    fixable kind the credit alert exists to catch.
    """
    state.write_active(
        "s-cursor",
        state.ActiveTurn(
            run_id="run-c",
            agent_name="agent-x",
            goal="read around the codebase",
            source_framework=hook.SOURCE_CURSOR,
            started_at=1.0,
        ),
    )
    state.write_recall("s-cursor", {"run_id": "run-c", "injected_text": "ADVICE"})

    hook.cmd_tool(
        {"session_id": "s-cursor", "cwd": "/repo"},
        hook._parse_args(["tool", "--source", "cursor", "--inject"]),
    )

    assert state.has_injection_point(
        "s-cursor", "run-c"
    ), "the injecting hook fired and was not recorded"
    assert state.read_steps("s-cursor") == [], "this hook captures no step, by design"


def test_a_turn_whose_resolve_is_merely_slow_still_had_somewhere_to_show_it(
    _env,
) -> None:
    """The marker records that the host *offered* a place, not that a stash was ready.

    The resolve is detached, so it routinely lands after the model has already chosen its
    first tool. Recording the marker only once a stash was found made every one of those
    turns report as having had nowhere to show anything, which is the structural verdict
    with no remedy: the exact conflation the outcome split was built to remove, and it
    hides the drops the credit alert exists to catch.
    """
    state.write_active(
        "s-slow",
        state.ActiveTurn(
            run_id="run-slow",
            agent_name="agent-x",
            goal="do x",
            source_framework=hook.SOURCE_CURSOR,
            started_at=1.0,
        ),
    )

    hook.cmd_tool(
        {"session_id": "s-slow", "cwd": "/repo"},
        hook._parse_args(["tool", "--source", "cursor", "--inject"]),
    )

    assert (
        state.peek_recall("s-slow") is None
    ), "no stash had landed yet, by construction"
    assert state.has_injection_point(
        "s-slow", "run-slow"
    ), "the hook that shows recall fired; a stash arriving late does not unfire it"


def test_a_receipt_is_scrubbed_before_it_leaves_the_machine() -> None:
    """The receipt is a slice of the user's transcript, not an exempt internal field.

    It is matched rather than stored server-side, which is a reason to keep it out of a
    column, never a reason to put a credential on the wire.
    """
    marker = receipt.marker("agent-x:s1:r1")
    body = f"{marker}\n- use the key sk-abcdefghijklmnop0123456789 when calling out"

    scrubbed = hook._clipped_receipt(body)

    assert scrubbed is not None
    assert "sk-abcdefghijklmnop0123456789" not in scrubbed
    assert scrubbed.startswith(marker)


# -- resolve_session_id: the three hooks of one turn must agree ---------------


def _resolve_sid(payload: dict, cwd: str = "/repo") -> str:
    return hook.resolve_session_id(payload, cwd, _args("prompt"))


SESSION_UUID = "f7e285a4-ca69-46bc-bdac-3f88b46698d6"


def test_explicit_session_id_wins_over_every_fallback() -> None:
    payload = {"session_id": "abc-123", "transcript_path": f"/t/{SESSION_UUID}.jsonl"}
    assert _resolve_sid(payload) == "abc-123"


def test_uuid_transcript_stem_is_recovered_as_the_session_id() -> None:
    """The editor names the transcript for the session, so the stem is the real id."""
    assert _resolve_sid({"transcript_path": f"/p/{SESSION_UUID}.jsonl"}) == SESSION_UUID


@pytest.mark.parametrize(
    "stem",
    [
        SESSION_UUID,
        f"{{{SESSION_UUID}}}",
        f"urn:uuid:{SESSION_UUID}",
        SESSION_UUID.replace("-", ""),
        f"-{SESSION_UUID}",
    ],
)
def test_every_spelling_uuid_accepts_is_returned_canonical(stem: str) -> None:
    """uuid.UUID accepts far more than the canonical spelling; the key must not.

    A leading hyphen is the one that bites: the key is passed as a command-line
    argument to the detached resolve, where argparse would read it as an option and
    exit, losing the recall for that session with no diagnostic.
    """
    assert _resolve_sid({"transcript_path": f"/p/{stem}.jsonl"}) == SESSION_UUID


def test_one_turns_hooks_agree_when_the_session_leader_changes(monkeypatch) -> None:
    """The regression: hooks spawned into separate sessions must still rendezvous."""
    payload = {"transcript_path": f"/p/{SESSION_UUID}.jsonl"}
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 47163)
    first = _resolve_sid(payload)
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 55144)
    assert _resolve_sid(payload) == first


def test_a_turn_closes_though_every_hook_saw_a_different_session(
    _env, monkeypatch
) -> None:
    """The rendezvous itself, not just the key: the turn must reach a staged flush."""
    staged = _env
    payload = {"cwd": "/repo", "transcript_path": f"/p/{SESSION_UUID}.jsonl"}
    sids = iter([101, 202, 303, 404, 505])
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: next(sids))
    hook.cmd_prompt({**payload, "prompt": "Tidy the parser"}, _args("prompt"))
    hook.cmd_tool(
        {**payload, "tool_name": "Bash", "tool_input": {"command": "pytest -q"}},
        _args("tool"),
    )
    hook.cmd_stop(dict(payload), _args("stop"))
    assert staged, "the stop hook never found the turn the prompt hook opened"


def test_non_uuid_transcript_is_scoped_by_repo_as_well_as_path() -> None:
    """A relative or shared transcript name must not alias two projects onto one key."""
    payload = {"transcript_path": "transcript.jsonl"}
    in_a = _resolve_sid(payload, cwd="/repoA")
    in_b = _resolve_sid(payload, cwd="/repoB")
    assert in_a != in_b
    assert in_a.startswith("derived-")
    assert in_a == _resolve_sid(payload, cwd="/repoA")


def test_non_uuid_transcript_still_gives_one_key_per_session(monkeypatch) -> None:
    payload = {"transcript_path": "/p/cursor-chat.log"}
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 100)
    first = _resolve_sid(payload)
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 200)
    assert _resolve_sid(payload) == first
    assert first != _resolve_sid({"transcript_path": "/p/other-chat.log"})


@pytest.mark.parametrize(
    "value", [12345, ["/p/a.jsonl"], {"a": 1}, "", "   ", None, True]
)
def test_a_transcript_path_that_is_not_a_path_is_ignored(value, monkeypatch) -> None:
    """Anything not a non-blank string falls through, rather than keying on its repr."""
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 4242)
    assert _resolve_sid({"transcript_path": value}) == _resolve_sid({})


def test_without_a_transcript_the_previous_fallback_is_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 4242)
    derived = _resolve_sid({}, cwd="/repo")
    assert derived.startswith("derived-4242-")
    assert derived != _resolve_sid({}, cwd="/other-repo")


def test_a_host_that_reports_the_transcript_unevenly_still_splits(monkeypatch) -> None:
    """A known limit, pinned so it is a decision rather than a surprise.

    Where a host names the transcript on one hook event and omits it on another, the
    two derive different keys and the turn does not close. No wired host behaves this
    way, and the fallback cannot detect it, so this documents the boundary rather than
    asserting desirable behaviour.
    """
    monkeypatch.setattr(hook.os, "getsid", lambda _pid: 7)
    with_transcript = _resolve_sid({"transcript_path": f"/p/{SESSION_UUID}.jsonl"})
    without = _resolve_sid({})
    assert with_transcript != without


def _stage_a_goalless_turn(monkeypatch, session_id: str) -> list[dict[str, Any]]:
    """A turn started by a tool event alone: material steps, no prompt, no goal."""
    staged: list[dict[str, Any]] = []
    monkeypatch.setattr(hook, "_spawn_flush", lambda _path: None)
    monkeypatch.setattr(
        state, "stage_flush", lambda _s, _r, payload: staged.append(payload) or "p"
    )
    state.write_active(
        session_id,
        state.ActiveTurn(
            run_id="run-goalless",
            agent_name="agent-x",
            goal="",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )
    for index in ("1", "2"):
        state.append_step(
            session_id,
            {"id": index, "name": "Bash", "status": "completed", "kind": "command"},
        )
    hook.cmd_stop(
        {"session_id": session_id, "cwd": "/repo", "status": "completed"},
        hook._parse_args(["stop"]),
    )
    return staged


def _stage_a_turn_worth_declining(monkeypatch, session_id: str) -> list[dict[str, Any]]:
    """A turn with a goal and no material step: declined on its steps, not its goal."""
    staged: list[dict[str, Any]] = []
    monkeypatch.setattr(hook, "_spawn_flush", lambda _path: None)
    monkeypatch.setattr(
        state, "stage_flush", lambda _s, _r, payload: staged.append(payload) or "p"
    )
    state.write_active(
        session_id,
        state.ActiveTurn(
            run_id="run-declinable",
            agent_name="agent-x",
            goal="reconcile the invoice",
            source_framework="claude-code",
            started_at=1.0,
        ),
    )
    hook.cmd_stop(
        {"session_id": session_id, "cwd": "/repo", "status": "completed"},
        hook._parse_args(["stop"]),
    )
    return staged


def test_a_goalless_turn_declines_instead_of_observing_an_episode_about_nothing(
    _env, monkeypatch
) -> None:
    """Its steps are material and it is still declined, which no other reason covers.

    A goal is what an extracted rule is transferable against, so an episode without one
    asks the corpus to generalise from what was done with no account of what it was for.
    Reporting it by its step count would name a gate that never ran.
    """
    # Both names, and that is the point rather than boilerplate. `_is_goalless_decline`
    # reads the copy imported into this module; the publication gate on the staged
    # reason reads `_wire`'s, because the rule lives there now so three client paths
    # cannot drift. Patching one and not the other tests half the question.
    published = lambda: frozenset({hook.REASON_NO_GOAL})  # noqa: E731
    monkeypatch.setattr(hook, "published_decline_reasons", published)
    monkeypatch.setattr("hyperstruck._wire.published_decline_reasons", published)

    staged = _stage_a_goalless_turn(monkeypatch, "s-goalless-on")

    assert staged, "the goalless turn staged nothing at all"
    assert "episode" not in staged[0]
    assert staged[0]["decline"]["reason"] == hook.REASON_NO_GOAL


def test_the_hook_withholds_a_decline_reason_the_boundary_has_not_published(
    _env, monkeypatch
) -> None:
    """This path staged whatever `turn_gate` returned, with no publication gate at all.

    It gated the recall outcome beside it (`_wire_recall_outcome`) and not the reason, so
    a member added to `turn_gate` and not yet published would 422 the whole decline and
    leave every such run open holding its resolve reservation. `turn_gate` is shared with
    every other host, so a member lands there for all of them at once.

    Driven with a published set that is NON-EMPTY and simply lacks the reason. An empty
    set is a different state: it means the contract file could not be read, and the
    escape hatch in `is_unpublished_decline_reason` sends optimistically rather than
    withholding every decline.
    """
    monkeypatch.setattr(
        "hyperstruck._wire.published_decline_reasons",
        lambda: frozenset({"a_reason_this_turn_will_not_choose"}),
    )

    staged = _stage_a_turn_worth_declining(monkeypatch, "s-unpublished-reason")

    assert staged == [], f"staged a decline the boundary would refuse: {staged!r}"


def test_a_goalless_turn_is_observed_while_its_reason_is_unpublished(
    _env, monkeypatch
) -> None:
    """The boundary refuses a reason it does not know, and a refused decline leaks the run.

    An unclosed run holding its resolve reservation is strictly worse than the goalless
    observe this replaces, so the branch stays off until the reason is published rather
    than declining under a reason that means something else.
    """
    monkeypatch.setattr(hook, "published_decline_reasons", frozenset)
    # Not patched in `_wire`: an EMPTY published set means the contract file is
    # unreadable, and the escape hatch there deliberately sends rather than withholds.
    # This test is about a reason that is genuinely not published, so the real contract
    # (which does not carry no_goal) is the right thing for the gate to read.

    staged = _stage_a_goalless_turn(monkeypatch, "s-goalless-off")

    assert staged, "the goalless turn staged nothing at all"
    assert "decline" not in staged[0]
    assert staged[0]["episode"]["goal"] == ""


def test_the_prompt_hook_shows_the_projects_warm_stash_before_the_model_acts(
    _env, monkeypatch, capsys
) -> None:
    """This turn's own recall lands after the prompt hook has already returned.

    So the opening plan and the first tool choice are always made with nothing, which is
    where the choices that matter are made. The previous resolve for the same project is
    the one piece of experience that is already on disk when the prompt arrives.
    """
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", "sk-test-key")
    stash.write(
        "agent-x",
        "/repo",
        goal="add retry to the uploader",
        context=hook.ResolvedContext(injected_text="EARLIER ADVICE"),
    )

    hook.cmd_prompt(
        {"session_id": "s-warm", "prompt": "now fix the parser", "cwd": "/repo"},
        _args("prompt"),
    )

    emitted = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert emitted["hookEventName"] == "UserPromptSubmit"
    assert "EARLIER ADVICE" in emitted["additionalContext"]
    assert "add retry to the uploader" in emitted["additionalContext"]
    assert "not checked against" in emitted["additionalContext"]


def test_a_warm_stash_is_shown_without_a_marker_so_it_can_never_be_credited(
    _env, monkeypatch, capsys
) -> None:
    """It was bound against another turn's goal, and that turn's receipt is finalised.

    Stamping this run over it would credit an exposure this client cannot evidence, and
    would inflate the very delivery rate the outcome vocabulary exists to make honest.
    """
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", "sk-test-key")
    stash.write(
        "agent-x",
        "/repo",
        goal="earlier",
        context=hook.ResolvedContext(injected_text="A"),
    )

    hook.cmd_prompt(
        {"session_id": "s-nomark", "prompt": "next", "cwd": "/repo"}, _args("prompt")
    )
    emitted = json.loads(capsys.readouterr().out)["hookSpecificOutput"]

    assert "hyperstruck-run:" not in emitted["additionalContext"]
    active = state.read_active("s-nomark")
    assert active is not None and active.is_stash_emitted


def test_a_turn_shown_only_a_warm_stash_reports_an_uncreditable_exposure(
    _env, monkeypatch
) -> None:
    """Its own recall never reached the model, but experience did, so neither
    ``recall_unclaimed`` nor ``recall_no_injection_point`` is the whole truth."""
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", "sk-test-key")
    stash.write(
        "agent-x",
        "/repo",
        goal="earlier",
        context=hook.ResolvedContext(injected_text="A"),
    )
    hook.cmd_prompt(
        {"session_id": "s-warm-out", "prompt": "next", "cwd": "/repo"}, _args("prompt")
    )
    state.write_recall_status(
        "s-warm-out",
        state.read_active("s-warm-out").run_id,
        RecallOutcome.RECALL_UNCLAIMED,
    )

    result = hook._acceptance_record("s-warm-out", state.read_active("s-warm-out"), [])

    assert result.outcome is RecallOutcome.STASH_EMITTED
    assert not result.is_delivered


def test_a_resolve_fault_is_never_hidden_behind_a_warm_emission(
    _env, monkeypatch
) -> None:
    """A timeout names a fault with a remedy; reporting a stash over it buries that."""
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", "sk-test-key")
    stash.write(
        "agent-x",
        "/repo",
        goal="earlier",
        context=hook.ResolvedContext(injected_text="A"),
    )
    hook.cmd_prompt(
        {"session_id": "s-warm-fault", "prompt": "next", "cwd": "/repo"},
        _args("prompt"),
    )
    state.write_recall_status(
        "s-warm-fault",
        state.read_active("s-warm-fault").run_id,
        RecallOutcome.RESOLVE_TIMED_OUT,
    )

    result = hook._acceptance_record(
        "s-warm-fault", state.read_active("s-warm-fault"), []
    )

    assert result.outcome is RecallOutcome.RESOLVE_TIMED_OUT


def test_a_resolve_publishes_the_projects_warm_stash_for_the_next_turn(
    _env, monkeypatch
) -> None:
    """The per-turn stash is cleared at both ends of its turn; this one has to outlive it."""
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", "sk-test-key")
    monkeypatch.setattr(hook, "_spawn_resolve", lambda _session: None)
    monkeypatch.setattr(
        hook,
        "_aresolve",
        _async_returning(hook.ResolvedContext(injected_text="FRESH")),
    )
    hook.cmd_prompt(
        {"session_id": "s-pub", "prompt": "do the thing", "cwd": "/repo"},
        _args("prompt"),
    )

    hook.cmd_resolve("s-pub")

    record = stash.read("agent-x", "/repo")
    assert record is not None
    assert record["injected_text"] == "FRESH"
    assert record["goal"] == "do the thing"


def _async_returning(value):
    async def _call(*_args, **_kwargs):
        return value

    return _call


def test_the_stored_reason_stays_truthful_while_the_wire_one_degrades(_env) -> None:
    """Two different jobs, so they are two different values.

    The staged file is this machine's own record and must say what actually happened. The
    wire value has to survive a closed enum on a boundary that may not know the member yet,
    and losing the whole episode over a diagnostic field is a far worse trade than losing
    the precision of that one field.
    """
    assert (
        hook._wire_recall_outcome(RecallOutcome.RESOLVE_TIMED_OUT)
        == "resolve_timed_out"
    )

    degraded = hook._wire_recall_outcome(RecallOutcome.RECALL_NO_INJECTION_POINT)

    assert degraded in {
        str(RecallOutcome.RECALL_NO_INJECTION_POINT),
        str(RecallOutcome.RECALL_UNCLAIMED),
    }
    assert not RecallOutcome(
        degraded
    ).is_delivered, "a degraded reason must never report credit the run did not earn"


def test_the_palette_and_window_actually_reach_the_resolve_call(
    _env, monkeypatch
) -> None:
    """Plumbed is not sent. Every layer of this existed already and nothing passed it, which
    is precisely how a field reaches production empty in every real run."""
    sent: dict[str, Any] = {}

    class _Client:
        def __init__(self, **_kwargs) -> None:
            pass

        async def resolve(self, **kwargs):
            sent.update(kwargs)
            return hook.ResolvedContext(injected_text="A")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(hook, "HostedLearningClient", _Client)
    registration.register(
        hook.SOURCE_CLAUDE_CODE,
        [
            {"name": "mcp__docs__search", "category": "read_only"},
            {"name": "mcp__slack__post", "category": "write"},
        ],
        declared_servers=["docs", "slack"],
        registered_servers=["docs", "slack"],
        model_context_window=200_000,
    )

    asyncio.run(hook._aresolve("agent-x", "run-1", "do x"))

    assert sent["model_context_window"] == 200_000
    assert {tool.name for tool in sent["available_tools"]} == {
        "mcp__docs__search",
        "mcp__slack__post",
    }
    assert {tool.category for tool in sent["available_tools"]} == {
        "read_only",
        "write",
    }, (
        "a declared category must survive to the server, which reads it to tell a write "
        "from a delegation; re-deriving it would report every tool as the same kind"
    )


def test_an_incomplete_registration_sends_no_palette_to_the_resolve(
    _env, monkeypatch
) -> None:
    """A partial palette is read by the server as tools the agent does not have."""
    sent: dict[str, Any] = {}

    class _Client:
        def __init__(self, **_kwargs) -> None:
            pass

        async def resolve(self, **kwargs):
            sent.update(kwargs)
            return hook.ResolvedContext()

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(hook, "HostedLearningClient", _Client)
    registration.register(
        hook.SOURCE_CLAUDE_CODE,
        [{"name": "mcp__docs__search"}],
        declared_servers=["docs", "slack"],
        registered_servers=["docs"],
        model_context_window=200_000,
    )

    asyncio.run(hook._aresolve("agent-x", "run-1", "do x"))

    assert sent["available_tools"] == ()
    assert (
        sent["model_context_window"] == 200_000
    ), "the window suppresses nothing, so it ships whatever the palette does"


def test_an_mcp_only_turn_can_now_reach_the_corpus_at_all(_env, monkeypatch) -> None:
    """The reversal tested at the outcome it promises, not only at the classifier.

    Before this change every server-contributed tool classified as a kind the observe gate
    refuses, so a turn made entirely of them was never learned from however much it did.
    """
    staged: list[dict[str, Any]] = []
    monkeypatch.setattr(hook, "_spawn_flush", lambda _path: None)
    monkeypatch.setattr(
        state, "stage_flush", lambda _s, _r, payload: staged.append(payload) or "p"
    )
    registration.register(
        hook.SOURCE_CLAUDE_CODE,
        [{"name": "mcp__browser__navigate"}, {"name": "mcp__slack__post"}],
        declared_servers=[],
        registered_servers=[],
    )
    hook.cmd_prompt(
        {"session_id": "s-mcp", "prompt": "book the room", "cwd": "/repo"},
        _args("prompt"),
    )
    for name, response in (
        ("mcp__browser__navigate", "Error: timed out"),
        ("mcp__slack__post", {"ok": True}),
    ):
        hook.cmd_tool(
            {
                "session_id": "s-mcp",
                "cwd": "/repo",
                "tool_name": name,
                "tool_response": response,
            },
            _args("tool"),
        )
    hook.cmd_stop({"session_id": "s-mcp", "cwd": "/repo"}, _args("stop"))

    assert staged, "the turn staged nothing at all"
    assert (
        "episode" in staged[0]
    ), "a recovered MCP turn is the highest-signal turn there is and was being declined"
    assert [step["name"] for step in staged[0]["episode"]["steps"]] == [
        "mcp__browser__navigate",
        "mcp__slack__post",
    ]


def test_an_editors_refusal_survives_the_never_injected_guard(
    _env, monkeypatch
) -> None:
    """The one interaction neither parent of this file could have tested.

    The guard above rewrites any *delivered-family* verdict to ``recall_unrecognised``,
    because a delivered claim contradicts a turn that never injected. While
    ``no_matching_record`` was delivered it hit that branch and lost its name; it is now
    never-delivered, so it falls through and reports itself. The two changes landed in
    different repositories, so this combination is only reachable here, and reporting the
    refusal as ``recall_unrecognised`` would file a decision somebody can act on under a
    parse fault nobody can.
    """
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", "sk-test-key")
    hook.cmd_prompt(
        {"session_id": "s-refusal", "prompt": "next", "cwd": "/repo"}, _args("prompt")
    )
    active = state.read_active("s-refusal")
    state.write_recall_status(
        "s-refusal", active.run_id, RecallOutcome.NO_MATCHING_RECORD
    )

    result = hook._acceptance_record("s-refusal", state.read_active("s-refusal"), [])

    assert result.outcome is RecallOutcome.NO_MATCHING_RECORD
    assert not result.is_delivered


class TestTheLongTurnCheckpoint:
    """A long turn re-resolves mid-flight, bounded, and records what that bought.

    Experience is injected once per turn and never refreshed, so on a long turn the block
    sits thousands of tokens back and was resolved against a goal that may no longer
    describe the work. These cover the four things that has to be true of the fix: it fires
    exactly twice however long the turn runs, it shows a block only when the block changed,
    it cannot destroy an injection that was about to happen, and every failure degrades to
    exactly today's single-injection behaviour.
    """

    @staticmethod
    def _start(session: str) -> None:
        hook.cmd_prompt(
            {"session_id": session, "prompt": "work", "cwd": "/repo"}, _args("prompt")
        )

    @staticmethod
    def _run(session: str) -> str:
        active = state.read_active(session)
        assert active is not None
        return active.run_id

    @staticmethod
    def _material_steps(
        session: str, count: int, name: str = "Edit", directory: str = ""
    ) -> None:
        for index in range(count):
            hook.cmd_tool(
                {
                    "session_id": session,
                    "cwd": "/repo",
                    "tool_name": name,
                    "file_path": f"{directory}f{index}.py",
                    "tool_response": "updated",
                },
                _args("tool"),
            )

    @staticmethod
    def _stash(session: str, text: str, ordinal: int = 1, drift: float | None = 0.5):
        active = state.read_active(session)
        assert active is not None
        state.write_recall(
            session,
            {
                "run_id": active.run_id,
                "injected_text": text,
                "offered_learning_ids": ["L2"],
                "checkpoint_ordinal": ordinal,
                "drift": drift,
            },
        )

    def test_a_write_lost_to_a_parallel_hook_cannot_uncredit_the_block(
        self, _env, capsys
    ) -> None:
        """The credit gate may not ride the clobberable write either.

        Moving the offers to the marker and leaving the injection record on the turn
        relocated this rather than fixing it. A parallel hook writing back a pre-injection
        snapshot leaves a turn that shows every sign of having injected -- the marker, the
        offers -- and reads as never injected, so ``_acceptance_record`` short-circuits and
        reports a block the model genuinely received as a missing recall. A lost increment
        is survivable; a lost verdict is not.
        """
        self._start("s-uncredit")
        stale = state.read_active("s-uncredit")
        self._material_steps("s-uncredit", 1)
        assert "INJECTED" in capsys.readouterr().out

        state.write_active("s-uncredit", stale, reset_steps=False)
        current = state.read_active("s-uncredit")

        assert hook._is_credited("s-uncredit", current)
        assert hook._acceptance_record("s-uncredit", current, {}).outcome is not (
            RecallOutcome.RECALL_MISSING
        )

    def test_a_long_opening_prompt_still_gets_its_expansion(self, _env) -> None:
        """At the bound the anchor gives way, never the expansion.

        The opening goal is already clipped to exactly ``MAX_BOUNDARY_GOAL_CHARS`` at
        capture, so composing and clipping the whole drops every character of the expansion
        for a prompt that long and re-sends a truncated copy of the goal the checkpoint was
        supposed to move away from. That is the inert case restored silently, on the turns
        that opened with the most to say.
        """
        material = [
            {"kind": constants.STEP_KIND_EDIT, "args": {"path": f"api/billing/c{i}.py"}}
            for i in range(8)
        ]

        for length in (
            constants.MAX_BOUNDARY_GOAL_CHARS - 100,
            constants.MAX_BOUNDARY_GOAL_CHARS,
            constants.MAX_BOUNDARY_GOAL_CHARS + 500,
        ):
            goal = hook._checkpoint_goal("x" * length, material)

            assert len(goal) <= constants.MAX_BOUNDARY_GOAL_CHARS
            assert constants.CHECKPOINT_GOAL_PREFIX in goal
            assert goal.endswith("api/billing/c0.py")
            assert goal.count("api/billing/c") == len(material)

    def test_the_expansion_never_carries_half_a_path(self, _env) -> None:
        """Terms are dropped whole, because half a path locates nothing and reads as though
        it does."""
        material = [
            {"kind": constants.STEP_KIND_EDIT, "args": {"path": "a" * 400 + f"{i}.py"}}
            for i in range(8)
        ]

        goal = hook._checkpoint_goal("fix the flake", material)
        terms = goal.split(constants.CHECKPOINT_GOAL_PREFIX)[1].split(", ")

        assert len(goal) <= constants.MAX_BOUNDARY_GOAL_CHARS
        assert constants.TRUNCATION_MARKER not in goal
        assert all(term.endswith(".py") for term in terms)

    def test_a_claim_that_could_not_be_written_is_not_a_verdict_on_the_block(
        self, _env, monkeypatch, capsys
    ) -> None:
        """An unwritable session dir says nothing about whether the block changed.

        Recording it as unchanged puts a disk fault into the log as an observation about the
        corpus, which is the same conflation a separate name was introduced for on the
        publish path.
        """
        self._start("s-unknown")
        self._material_steps("s-unknown", 1)
        capsys.readouterr()
        monkeypatch.setattr(state, "claim_shown_block", lambda *_a, **_k: None)

        self._stash("s-unknown", "A DIFFERENT BLOCK")
        hook._inject_pending("s-unknown", constants.SOURCE_CLAUDE_CODE)

        assert capsys.readouterr().out == ""
        assert [row["is_block_changed"] for row in _checkpoint_records()] == [None]

    def test_a_sweep_does_not_clear_a_live_turn_it_could_not_read(
        self, _env, monkeypatch, capsys
    ) -> None:
        """The sweep runs across other sessions and now deletes the credit record.

        ``clear_recall`` drops the shown-block markers, which are the whole of this
        release's evidence that a block reached the model. ``read_active`` answers ``None``
        both for a session with no turn and for one whose file it could not read, and a hook
        that runs out of descriptors against the parallel checkpoint subprocesses this loop
        itself spawns gets that answer about a turn that is very much alive. Clearing on it
        finalises a turn that showed its block as one that never did.
        """
        self._start("s-live")
        self._material_steps("s-live", 1)
        capsys.readouterr()
        live = state.read_active("s-live")
        assert hook._is_credited("s-live", live)

        readable = state.read_active
        monkeypatch.setattr(state, "read_active", lambda _sid: None)
        hook._sweep_stale(exclude="s-other")
        monkeypatch.setattr(state, "read_active", readable)

        assert hook._is_credited("s-live", state.read_active("s-live"))
        assert hook._offered_this_turn("s-live", live)[0] == ("L1",)

    def test_a_sweep_still_clears_a_session_with_no_turn_left(
        self, _env, monkeypatch
    ) -> None:
        """The cleanup it exists for is unchanged where the turn is genuinely gone."""
        self._start("s-gone")
        state.clear_active("s-gone")

        hook._sweep_stale(exclude="s-other")

        assert state.peek_recall("s-gone") is None

    def test_a_checkpoint_whose_turn_ended_before_it_started_still_counts(
        self, _env, monkeypatch
    ) -> None:
        """Nothing orders the spawn against the stop hook, and the ordinal is spent either way.

        A threshold crossed on a turn's last tool call reaches a session the stop hook has
        already retired. No resolve is sent and nothing is charged, but the claim is taken
        and never released, so a log that skips this ending undercounts exactly the thing it
        exists to count.
        """
        self._start("s-retired")
        active = state.read_active("s-retired")
        state.retire_active("s-retired")

        hook.cmd_resolve("s-retired", 2, 0.5, active.run_id)

        assert [
            (row["run_id"], row["ordinal"], row["outcome"], row["drift"])
            for row in _checkpoint_records()
        ] == [(active.run_id, 2, constants.CHECKPOINT_TURN_GONE, 0.5)]

    def test_a_checkpoints_line_names_the_run_that_claimed_it(
        self, _env, monkeypatch
    ) -> None:
        """Not the run that happens to be active when the resolve gets around to reading.

        The next prompt can land first, and the count this log exists for is per run: a line
        filed under the successor makes one turn look like it spent a checkpoint it never
        claimed and the other like it spent one fewer.
        """
        self._start("s-super")
        claimed = state.read_active("s-super")
        monkeypatch.setattr(hook, "_aresolve", _resolved_to(""))
        self._start("s-super")
        successor = state.read_active("s-super")
        assert successor.run_id != claimed.run_id

        hook.cmd_resolve("s-super", 1, None, claimed.run_id)

        assert [row["run_id"] for row in _checkpoint_records()] == [claimed.run_id]

    def test_a_checkpoint_asks_about_the_work_the_turn_has_since_done(
        self, _env, monkeypatch, capsys
    ) -> None:
        """Otherwise the checkpoint is inert, and expensively so.

        The corpus cannot change mid-turn, because harvest runs at the stop hook, and the
        render is deterministic. So a checkpoint re-sending the opening goal asks the same
        question of the same corpus, gets the same block, and has it suppressed by the
        digest test: two billed resolves and nothing shown, on exactly the longest turns.
        The query has to carry where the work has moved to.
        """
        asked: list[str] = []

        async def record(_agent, _run, goal, **_kwargs):
            asked.append(goal)
            return hook.ResolvedContext(injected_text="B", offered_learning_ids=("L2",))

        monkeypatch.setattr(hook, "_spawn_detached", lambda *_args: None)
        self._start("s-goal")
        self._material_steps("s-goal", 8, directory="api/billing/")
        capsys.readouterr()
        monkeypatch.setattr(hook, "_aresolve", record)

        hook.cmd_resolve("s-goal", 1, 0.5)

        assert asked and asked[0].startswith("work")
        assert asked[0] != "work"
        assert "api/billing/f7.py" in asked[0]

    def test_the_checkpoints_question_stays_anchored_to_the_opening_goal(
        self, _env
    ) -> None:
        """Bounded expansion, because the failure of query rewriting is topic drift.

        A query that is neither the old task nor the new one retrieves worse than either
        alone, and paths are high-entropy tokens: enough of them stop expanding the goal in
        the vector and start replacing it. The window keeps the terms inside the work this
        checkpoint is measured over, and the cap keeps the anchor the larger half.
        """
        material = [
            {
                "kind": constants.STEP_KIND_COMMAND,
                "args": {"path": f"pkg/m{index}.py", "command": f"tool{index} --run"},
            }
            for index in range(12)
        ]

        goal = hook._checkpoint_goal("fix the flake", material)
        terms = goal.split(constants.CHECKPOINT_GOAL_PREFIX)[1].split(", ")

        assert goal.startswith("fix the flake")
        assert len(terms) == constants.CHECKPOINT_GOAL_TERMS
        assert "pkg/m11.py" in terms and "tool11" in terms
        assert not [term for term in terms if term.endswith(("m0.py", "m3.py"))]

    def test_a_checkpoints_question_cannot_reach_back_past_its_own_window(
        self, _env
    ) -> None:
        """The window bounds how far back it looks, not merely how many terms it takes.

        Recency alone does not: a run of steps that captured no path and no command, which
        is every ``act`` step and any shell call whose command was not on the payload, would
        otherwise let the search walk back through the whole turn to fill its quota and
        describe the work as it was before the resolve this checkpoint is measured against.
        An empty window is the honest answer, and it sends the opening goal alone.
        """
        material = [
            {"kind": constants.STEP_KIND_EDIT, "args": {"path": f"old/m{index}.py"}}
            for index in range(8)
        ] + [{"kind": constants.STEP_KIND_ACT, "args": {}} for _ in range(8)]

        assert hook._checkpoint_goal("fix the flake", material) == "fix the flake"

    def test_a_tool_call_stops_reading_the_steps_once_both_checkpoints_are_taken(
        self, _env, monkeypatch, capsys
    ) -> None:
        """This runs on the editor's synchronous path, on every tool call, forever.

        Reading and parsing every step file to count them makes a turn quadratic in its own
        length, and does it hardest on the long turns the feature exists for. For almost all
        of such a turn there is nothing left to decide, and two stats say so.
        """
        monkeypatch.setattr(hook, "_spawn_detached", lambda *_args: None)
        self._start("s-cost")
        self._material_steps("s-cost", 24)
        capsys.readouterr()
        read: list[str] = []
        as_read = state.read_steps
        monkeypatch.setattr(
            state, "read_steps", lambda sid: read.append(sid) or as_read(sid)
        )

        self._material_steps("s-cost", 6)
        capsys.readouterr()

        assert read == []

    def test_a_write_lost_to_a_parallel_hook_cannot_show_a_block_twice(
        self, _env, capsys
    ) -> None:
        """The guarantee may not ride on a read-modify-write of the active turn.

        A turn can now hold more than one stash, so two hooks can be past their claims at
        once, and this module already documents what that does to ``active.json``: the one
        that writes second restores what it read, dropping the other's record. Reproduced
        exactly, by writing back the snapshot a parallel hook took before the injection.
        """
        self._start("s-clobber")
        stale = state.read_active("s-clobber")
        self._material_steps("s-clobber", 1)
        assert "INJECTED" in capsys.readouterr().out

        state.write_active("s-clobber", stale, reset_steps=False)
        self._stash("s-clobber", "INJECTED")
        hook._inject_pending("s-clobber", constants.SOURCE_CLAUDE_CODE)

        assert capsys.readouterr().out == ""
        current = state.read_active("s-clobber")
        assert hook._offered_this_turn("s-clobber", current)[0] == ("L1",)

    def test_a_late_turn_start_resolve_does_not_displace_a_landed_checkpoint(
        self, _env, monkeypatch
    ) -> None:
        """The exclusive slot protected one direction of this race and not the other.

        The opening resolve returns whenever the boundary answers, which can be after a
        burst of tool calls has crossed a threshold and landed a checkpoint's stash.
        Replacing it discards a block that was already resolved, charged and recorded on the
        server, and the ordinal is spent, so nothing local records that it ever existed.
        """
        self._start("s-late")
        active = state.read_active("s-late")
        state.clear_recall("s-late")
        self._stash("s-late", "A CHECKPOINT BLOCK")
        monkeypatch.setattr(hook, "_aresolve", _resolved_to("THE OPENING BLOCK"))

        hook.cmd_resolve("s-late")

        assert state.peek_recall("s-late")["injected_text"] == "A CHECKPOINT BLOCK"
        assert (
            state.read_recall_status("s-late", active.run_id)
            == RecallOutcome.RECALL_UNCLAIMED
        )

    def test_a_checkpoint_whose_spawn_fails_leaves_a_row_saying_so(
        self, _env, monkeypatch, capsys
    ) -> None:
        """Nothing releases a claim, so a failed spawn spends the ordinal for the run.

        The only other trace is a debug line that is off unless someone set the variable, so
        the turn silently gets fewer checkpoints than it should and nobody can find out why.
        This client already writes a durable row for the other loss whose process had
        nowhere to report itself.
        """

        def refuse(*_args: str) -> None:
            raise OSError("no processes available")

        monkeypatch.setattr(hook, "_spawn_detached", refuse)
        self._start("s-spawn")
        self._material_steps("s-spawn", 8)
        capsys.readouterr()
        active = state.read_active("s-spawn")

        assert [(row["ordinal"], row["outcome"]) for row in _checkpoint_records()] == [
            (1, constants.CHECKPOINT_SPAWN_FAILED)
        ]
        assert not state.claim_checkpoint("s-spawn", active.run_id, 1)

    def test_a_checkpoint_the_turn_ended_before_showing_is_still_counted(
        self, _env, capsys
    ) -> None:
        """The count is the only local check that the two-resolve bound still holds.

        Nothing caps the spend but ``CHECKPOINT_MATERIAL_STEPS``, and this log is the only
        place on the machine that says how many checkpoints a turn actually spent. Its most
        likely ending wrote no line at all: the second checkpoint fires at twenty-four
        material steps, is often among the last things a long turn does, and its stash is
        deleted with the turn. A count that drops that ending cannot answer the one question
        it exists for.
        """
        self._start("s-unclaimed")
        self._material_steps("s-unclaimed", 1)
        capsys.readouterr()
        self._stash("s-unclaimed", "A CHECKPOINT BLOCK", ordinal=2, drift=0.5)

        hook.cmd_stop({"session_id": "s-unclaimed", "cwd": "/repo"}, _args("stop"))
        capsys.readouterr()

        assert [
            (row["ordinal"], row["outcome"], row["drift"])
            for row in _checkpoint_records()
        ] == [(2, str(RecallOutcome.RECALL_UNCLAIMED), 0.5)]

    def test_a_checkpoint_that_published_nothing_is_not_called_unclaimed(
        self, _env, monkeypatch
    ) -> None:
        """Two causes under one name is what the outcome vocabulary exists to prevent.

        ``RECALL_UNCLAIMED`` means a stash was published and shown to nobody, which is a
        client-side drop with a remedy. A checkpoint that refused an occupied slot published
        nothing at all. That value already carried two answers once and was split for it.
        """
        self._start("s-occupied")
        assert state.peek_recall("s-occupied") is not None
        monkeypatch.setattr(hook, "_aresolve", _resolved_to("A CHECKPOINT BLOCK"))

        hook.cmd_resolve("s-occupied", 1, 0.5)

        assert [row["outcome"] for row in _checkpoint_records()] == [
            constants.CHECKPOINT_SLOT_OCCUPIED
        ]

    def test_a_long_cursor_turn_reaches_its_checkpoints_too(
        self, _env, monkeypatch
    ) -> None:
        """The capture hooks are host-neutral, so a Cursor turn spends this money as well.

        Pinned because the alternative to documenting it was gating the spawn on the host,
        and a Cursor customer reading only the Claude Code row would not know either that it
        happens or that it stopped.
        """
        spawned: list[tuple[str, ...]] = []
        monkeypatch.setattr(hook, "_spawn_detached", lambda *args: spawned.append(args))
        cursor = ["--source", "cursor"]
        hook.cmd_prompt(
            {"conversation_id": "c-long", "prompt": "work", "cwd": "/repo"},
            hook._parse_args(["prompt", *cursor]),
        )
        for index in range(8):
            hook.cmd_tool(
                {
                    "conversation_id": "c-long",
                    "cwd": "/repo",
                    "file_path": f"a{index}.py",
                    "tool_response": "ok",
                },
                hook._parse_args(["tool", *cursor, "--kind", "edit"]),
            )

        assert [
            args[args.index("--checkpoint") + 1]
            for args in spawned
            if "--checkpoint" in args
        ] == ["1"]

    def test_a_turn_of_sixty_material_steps_spawns_exactly_two_checkpoints(
        self, _env, monkeypatch, capsys
    ) -> None:
        """The cap is on resolves, because a resolve is charged before the diff test can run.

        You have to resolve before you can know whether the block changed, so the digest
        comparison saves context and never spend, and resolve spend reserves against a run
        cap that sums reserved rather than actual. A design bounded only by the diff test
        puts resolve count in proportion to turn length and pays for every check it throws
        away.
        """
        spawned: list[tuple[str, ...]] = []
        monkeypatch.setattr(hook, "_spawn_detached", lambda *args: spawned.append(args))
        self._start("s-cap")
        self._material_steps("s-cap", 60)
        capsys.readouterr()

        checkpoints = [args for args in spawned if "--checkpoint" in args]
        assert [args[args.index("--checkpoint") + 1] for args in checkpoints] == [
            "1",
            "2",
        ]

    def test_a_checkpoint_that_cannot_be_claimed_costs_the_checkpoint_and_not_the_turn(
        self, _env, monkeypatch, capsys
    ) -> None:
        """Fail-open, in the direction that loses least: one stale block, never the turn."""
        spawned: list[tuple[str, ...]] = []
        monkeypatch.setattr(hook, "_spawn_detached", lambda *args: spawned.append(args))
        monkeypatch.setattr(state, "claim_checkpoint", lambda *_a, **_k: False)
        self._start("s-nocap")
        self._material_steps("s-nocap", 30)
        capsys.readouterr()

        assert not spawned
        assert state.read_active("s-nocap") is not None
        assert len(state.read_steps("s-nocap")) == 30

    def test_parallel_tool_hooks_crossing_one_threshold_spawn_one_resolve(
        self, _env, monkeypatch, capsys
    ) -> None:
        """Tool hooks are parallel sibling processes with no lock between them.

        Two tool calls landing either side of the threshold each read the same steps
        directory and each see the count crossed. Without an exclusive claim they both
        spawn, which doubles the spend the whole idempotency-key design exists to bound and
        breaks the two-resolve cap outright. The claim is what makes the crossing a
        decision exactly one of them wins.
        """
        spawned: list[tuple[str, ...]] = []
        monkeypatch.setattr(hook, "_spawn_detached", lambda *args: spawned.append(args))
        self._start("s-race")
        self._material_steps("s-race", 8)
        capsys.readouterr()
        assert len(spawned) == 1

        hook._spawn_due_checkpoint("s-race")
        hook._spawn_due_checkpoint("s-race")

        assert len(spawned) == 1

    def test_a_checkpoint_block_identical_to_one_already_shown_is_not_shown_again(
        self, _env, capsys
    ) -> None:
        """The digest test, against every block this turn has shown rather than only its last.

        Claiming the digest is what asks it, so a turn holding two stashes at once cannot
        have both hooks read "nothing like this yet" before either records that it has.
        """
        self._start("s-same")
        self._material_steps("s-same", 1)
        capsys.readouterr()
        assert len(state.read_shown_blocks("s-same", self._run("s-same"))) == 1

        self._stash("s-same", "INJECTED")
        hook._inject_pending("s-same", constants.SOURCE_CLAUDE_CODE)
        emitted = capsys.readouterr().out

        assert emitted == ""
        assert len(state.read_shown_blocks("s-same", self._run("s-same"))) == 1

    def test_a_checkpoint_block_that_changed_is_shown_and_counted(
        self, _env, capsys
    ) -> None:
        self._start("s-diff")
        self._material_steps("s-diff", 1)
        capsys.readouterr()

        self._stash("s-diff", "A DIFFERENT BLOCK")
        hook._inject_pending("s-diff", constants.SOURCE_CLAUDE_CODE)
        emitted = capsys.readouterr().out

        assert "A DIFFERENT BLOCK" in emitted
        active = state.read_active("s-diff")
        assert len(state.read_shown_blocks("s-diff", active.run_id)) == 2
        assert set(hook._offered_this_turn("s-diff", active)[0]) == {"L1", "L2"}

    def test_a_checkpoint_refuses_to_clobber_a_stash_nothing_has_claimed_yet(
        self, _env, monkeypatch
    ) -> None:
        """The in-flight race the single recall slot does not handle on its own.

        A checkpoint returning while the opening stash is still waiting to be claimed would
        overwrite it, destroying an injection that was about to happen. Losing the
        checkpoint costs one stale block; losing the slot could lose the injection.
        """
        self._start("s-inflight")
        assert state.peek_recall("s-inflight")["injected_text"] == "INJECTED"

        monkeypatch.setattr(hook, "_aresolve", _resolved_to("A CHECKPOINT BLOCK"))
        hook.cmd_resolve("s-inflight", 1, 0.5)

        assert state.peek_recall("s-inflight")["injected_text"] == "INJECTED"

    def test_a_checkpoint_never_overwrites_the_turns_own_recall_verdict(
        self, _env, monkeypatch
    ) -> None:
        """That slot answers a turn-level question a checkpoint has no standing to answer.

        One status file per session, and a checkpoint writing there would erase the opening
        resolve's account of why the turn was or was not shown its recall. A turn whose
        first resolve published and whose checkpoint came back empty would then read as a
        turn that resolved to nothing.
        """
        self._start("s-verdict")
        active = state.read_active("s-verdict")
        state.write_recall_status(
            "s-verdict", active.run_id, RecallOutcome.RECALL_UNCLAIMED
        )
        monkeypatch.setattr(hook, "_aresolve", _resolved_to(""))

        hook.cmd_resolve("s-verdict", 2, 0.5)

        assert (
            state.read_recall_status("s-verdict", active.run_id)
            == RecallOutcome.RECALL_UNCLAIMED
        )
        assert [(row["ordinal"], row["outcome"]) for row in _checkpoint_records()] == [
            (2, str(RecallOutcome.RESOLVE_EMPTY))
        ]

    def test_a_checkpoint_that_fails_degrades_to_todays_single_injection(
        self, _env, monkeypatch, capsys
    ) -> None:
        """A resolve that times out, errors, or answers nothing leaves the turn untouched."""
        self._start("s-open")
        self._material_steps("s-open", 1)
        capsys.readouterr()
        before = state.read_active("s-open")

        async def explode(*_args, **_kwargs):
            raise TimeoutError("the boundary was slower than the deadline")

        monkeypatch.setattr(hook, "_aresolve", explode)
        hook.cmd_resolve("s-open", 1, 0.5)

        assert capsys.readouterr().out == ""
        assert state.read_active("s-open") == before
        assert [row["outcome"] for row in _checkpoint_records()] == [
            str(RecallOutcome.RESOLVE_TIMED_OUT)
        ]

    def test_every_checkpoint_records_its_drift_beside_whether_the_block_changed(
        self, _env, capsys
    ) -> None:
        """A line missing either half is worthless, so both or neither.

        A distance with no outcome beside it explains nothing, and an outcome with nothing
        that might explain it is what the log already had. The pair is what makes the file
        worth reading when someone is working out why a long turn did or did not show a
        second block, and the second half costs nothing because the digest comparison one
        line above already computed it.
        """
        self._start("s-drift")
        self._material_steps("s-drift", 1)
        capsys.readouterr()

        self._stash("s-drift", "A DIFFERENT BLOCK", ordinal=1, drift=0.75)
        hook._inject_pending("s-drift", constants.SOURCE_CLAUDE_CODE)
        capsys.readouterr()
        self._stash("s-drift", "A DIFFERENT BLOCK", ordinal=2, drift=0.25)
        hook._inject_pending("s-drift", constants.SOURCE_CLAUDE_CODE)
        capsys.readouterr()

        recorded = [
            (row["ordinal"], row["drift"], row["is_block_changed"], row["is_injected"])
            for row in _checkpoint_records()
        ]
        assert recorded == [(1, 0.75, True, True), (2, 0.25, False, False)]

    def test_the_first_checkpoints_drift_is_absent_rather_than_a_constant(
        self, _env
    ) -> None:
        """Its previous resolve ran before any tool did, so it covers no tool set at all.

        Reported as a maximum distance it would be the same number on every first
        checkpoint regardless of what the turn actually did, and a sample whose first point
        is a constant is not a sample.
        """
        material = [{"name": "Edit"} for _ in range(8)]

        assert hook._tool_set_drift(material, 1) is None

    def test_drift_measures_equal_windows_so_one_checkpoint_compares_to_another(
        self, _env
    ) -> None:
        """A window that grows with the checkpoint index does not mean the same thing twice.

        This turn edited, detoured into reading, and came back to editing. Measured over
        equal trailing windows it has drifted nowhere: it is doing now what it was doing
        then. Measured over everything since the last resolve, the detour is still in the
        set and the same turn reports drift, so the two checkpoints of one turn would be
        putting different quantities into one sample.
        """
        returned = (
            [{"name": "Edit"} for _ in range(8)]
            + [{"name": "Read"} for _ in range(8)]
            + [{"name": "Edit"} for _ in range(8)]
        )
        moved = [{"name": "Edit"} for _ in range(16)] + [
            {"name": "Read"} for _ in range(8)
        ]

        assert hook._tool_set_drift(returned, 2) == 0.0
        assert hook._tool_set_drift(moved, 2) == 1.0


def _resolved_to(text: str):
    async def resolved(*_args, **_kwargs):
        return hook.ResolvedContext(
            injected_text=text or None, offered_learning_ids=("L2",) if text else ()
        )

    return resolved


def _checkpoint_records() -> list[dict]:
    path = constants.checkpoint_drift_log()
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# -- liveness-gated orphan eviction ------------------------------------------
#
# The sweep used to hold every orphan for 48 hours, which is thirty-six hours after the
# loop-closure alert stops looking, so none of its recoveries were ever visible to the
# alert. These cover the narrow case that may now close early, and, more importantly, the
# cases that must not: the failure mode is deleting the state a live turn still needs.


def _unevidenced_orphan(session: str, *, pid: int, age_seconds: float) -> None:
    """A turn that edited files, ran no command, and whose session went quiet."""
    hook.cmd_prompt(
        {"session_id": session, "prompt": "edit a.py", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "a.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    active = state.read_active(session)
    assert active is not None
    state.write_active(
        session,
        replace(active, started_at=time.time() - age_seconds, editor_pid=pid),
        reset_steps=False,
    )


def _editor_is(monkeypatch, *, alive: bool) -> None:
    def kill(pid, sig):  # signature must match os.kill; both args deliberately unused
        if not alive:
            raise ProcessLookupError(pid)

    monkeypatch.setattr(hook.os, "kill", kill)


def test_an_unevidenced_orphan_whose_editor_died_is_declined_past_the_floor(
    _env, monkeypatch
) -> None:
    staged = _env
    _editor_is(monkeypatch, alive=False)
    _unevidenced_orphan("s-dead", pid=424242, age_seconds=LIVENESS_FLOOR_SECONDS + 60)

    hook._sweep_stale(exclude="other-session")

    assert len(staged) == 1, "a dead session's unevidenced turn should close now"
    assert _last_staged(staged)["decline"]["reason"] == "unevidenced_outcome"


def test_it_is_not_declined_before_the_floor(_env, monkeypatch) -> None:
    """The floor guards a recorded parent that is a short-lived wrapper, not the editor."""
    staged = _env
    _editor_is(monkeypatch, alive=False)
    _unevidenced_orphan("s-young", pid=424242, age_seconds=LIVENESS_FLOOR_SECONDS - 60)

    hook._sweep_stale(exclude="other-session")

    assert staged == []
    assert state.read_active("s-young") is not None


def test_a_live_editor_is_never_early_declined(_env, monkeypatch) -> None:
    """A user away from a permission prompt writes nothing and is still working."""
    staged = _env
    _editor_is(monkeypatch, alive=True)
    _unevidenced_orphan("s-live", pid=424242, age_seconds=10 * 60 * 60)

    hook._sweep_stale(exclude="other-session")

    assert staged == []
    assert state.read_active("s-live") is not None


def test_no_recorded_pid_falls_back_to_the_age_gate(_env, monkeypatch) -> None:
    """A client older than the field, or a host that supplies none, changes nothing."""
    staged = _env
    _editor_is(monkeypatch, alive=False)
    _unevidenced_orphan("s-nopid", pid=0, age_seconds=10 * 60 * 60)

    hook._sweep_stale(exclude="other-session")

    assert staged == []
    assert state.read_active("s-nopid") is not None


def test_an_evidenced_orphan_is_never_early_declined(_env, monkeypatch) -> None:
    """This changes when an unevidenced decline lands, never which turns are declined."""
    staged = _env
    _editor_is(monkeypatch, alive=False)
    hook.cmd_prompt(
        {"session_id": "s-eviden", "prompt": "run tests", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": "s-eviden",
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "2 passed",
            "exit_code": 0,
        },
        _args("tool"),
    )
    active = state.read_active("s-eviden")
    assert active is not None
    state.write_active(
        "s-eviden",
        replace(active, started_at=time.time() - 10 * 60 * 60, editor_pid=424242),
        reset_steps=False,
    )

    hook._sweep_stale(exclude="other-session")

    assert staged == [], "an evidenced turn keeps the 48h path"
    assert state.read_active("s-eviden") is not None


def test_a_live_turn_survives_repeated_sweeps_with_its_state_intact(
    _env, monkeypatch
) -> None:
    """The blocker this spec was nearly shipped with.

    ``_finalise`` ends in ``retire_active``, so an early decline of a live turn deletes
    the state its stop hook still needs and the real outcome is lost rather than recorded
    late. Assert on the state, not the label: a wrong label is recoverable and a deleted
    active record is not.
    """
    staged = _env
    _editor_is(monkeypatch, alive=True)
    _unevidenced_orphan("s-blocked", pid=424242, age_seconds=10 * 60 * 60)

    for _ in range(3):
        hook._sweep_stale(exclude="other-session")

    assert state.has_active("s-blocked"), "a live turn's state must survive the sweep"
    assert state.read_steps(
        "s-blocked"
    ), "and so must the steps its label is drawn from"
    assert staged == []


def test_the_stop_hook_restages_when_the_active_record_is_gone(_env) -> None:
    """A stop hook that finds no active record must not write nothing and return.

    Without this the loss is silent and total: the turn's real outcome is never recorded
    and no error appears anywhere.
    """
    staged = _env
    hook.cmd_prompt(
        {"session_id": "s-lost", "prompt": "run tests", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_tool(
        {
            "session_id": "s-lost",
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": "2 passed",
            "exit_code": 0,
        },
        _args("tool"),
    )
    lost = state.read_active("s-lost")
    assert lost is not None
    (state.session_dir("s-lost") / "active.json").unlink()
    assert state.read_active("s-lost") is None

    hook.cmd_stop({"session_id": "s-lost", "cwd": "/repo"}, _args("stop"))

    assert len(staged) == 1, "the turn must still be delivered from its own steps"
    # Recovered from the recall artefacts rather than minted, so the delivered turn is the
    # one the resolve recorded an offer against. Whether this particular turn then clears
    # the materiality gate is that gate's business and not this path's.
    flushed = _last_staged(staged)
    assert (
        flushed.get("decline", flushed.get("episode", {})).get(
            "run_id", flushed.get("run_id")
        )
        == lost.run_id
    )


def test_a_stop_hook_with_no_steps_left_stages_nothing(_env) -> None:
    """Steps are the interlock that stops recovery re-delivering a closed turn.

    ``clear_active`` removes the steps with the record, so surviving steps are what prove
    no finalise has run. With none, this must behave exactly as it did before.
    """
    staged = _env
    hook.cmd_prompt(
        {"session_id": "s-empty", "prompt": "think", "cwd": "/repo"}, _args("prompt")
    )
    state.clear_active("s-empty")

    hook.cmd_stop({"session_id": "s-empty", "cwd": "/repo"}, _args("stop"))

    assert staged == []


def test_the_liveness_probe_never_runs_off_posix(monkeypatch) -> None:
    """On Windows ``os.kill`` is not a probe, it is a kill.

    Every signal but ``CTRL_C_EVENT`` and ``CTRL_BREAK_EVENT`` goes to
    ``TerminateProcess`` there, so asking whether the editor is alive would end it. The
    installer supports Windows, so this is reachable. Assert ``os.kill`` is never called
    at all rather than that the verdict happens to be right: a correct answer reached by
    killing the editor is the defect.

    The predicate is exercised directly because ``os.name`` cannot be patched around
    anything that touches the filesystem: ``pathlib`` reads it too.
    """
    called: list = []
    monkeypatch.setattr(hook.os, "kill", lambda pid, sig: called.append((pid, sig)))
    monkeypatch.setattr(hook.os, "name", "nt")
    turn = state.ActiveTurn(
        run_id="r",
        agent_name="a",
        goal="",
        source_framework="claude-code",
        started_at=time.time() - 10 * 60 * 60,
        editor_pid=424242,
    )

    assert hook._is_editor_gone(turn, time.time()) is False
    assert called == [], "os.kill must never be reached off posix"


def test_the_liveness_probe_does_run_on_posix(monkeypatch) -> None:
    """The guard above must not be the reason every verdict is False."""
    monkeypatch.setattr(
        hook.os, "kill", lambda pid, sig: (_ for _ in ()).throw(ProcessLookupError(pid))
    )
    monkeypatch.setattr(hook.os, "name", "posix")
    turn = state.ActiveTurn(
        run_id="r",
        agent_name="a",
        goal="",
        source_framework="claude-code",
        started_at=time.time() - 10 * 60 * 60,
        editor_pid=424242,
    )

    assert hook._is_editor_gone(turn, time.time()) is True


def test_the_composed_answer_reaches_the_staged_episode_and_survives_the_rebuild() -> (
    None
):
    """Both halves, because they fail separately and both have failed before.

    ``_build_episode`` projects a finished turn onto the wire shape field by field, and ``_deliver``
    rebuilds a wire ``Episode`` from the staged file field by field. A field present in one and
    absent in the other is staged, scrubbed, written to disk and then silently dropped at the moment
    of delivery, which is how the utterance came to be plumbed through five layers and never
    transmitted.
    """
    from hyperstruck._wire import Episode, TerminalOutcome

    answer = "I will confirm the shipment volumes with the depot and send them over by Friday."
    finished = state.FinishedTurn(
        run_id="r1",
        agent_name="a",
        goal="check the depot schedule",
        steps=({"status": "completed", "description": "read the schedule"},),
        source_framework="claude-code",
        ended_at=0.0,
        final_output=answer,
    )

    episode = hook._build_episode(finished, is_success=True)
    assert episode["outcome"]["final_output"] == answer
    assert redact_ide_episode(episode)["outcome"]["final_output"] == answer

    # The rebuild, on the shape the staged file carries.
    outcome_data = episode["outcome"]
    rebuilt = Episode(
        run_id=episode["run_id"],
        goal=episode["goal"],
        outcome=TerminalOutcome(
            is_success=bool(outcome_data.get("is_success", True)),
            final_output=outcome_data.get("final_output") or None,
        ),
    )
    assert rebuilt.to_payload()["outcome"]["final_output"] == answer


def test_a_turn_whose_transcript_gave_nothing_emits_no_key_at_all() -> None:
    """Omitted rather than sent as null: the API model forbids extra keys and rejects a forbidden one
    even with a null value, so a client upgraded ahead of the API deploy would 422 every write, and a
    4xx is terminal to the flush retry."""
    finished = state.FinishedTurn(
        run_id="r1",
        agent_name="a",
        goal="check the depot schedule",
        steps=({"status": "completed"},),
        source_framework="claude-code",
        ended_at=0.0,
    )

    assert (
        "final_output" not in hook._build_episode(finished, is_success=True)["outcome"]
    )


def test_delivery_mints_the_utterance_from_the_prose_it_tagged(monkeypatch) -> None:
    """The value on the wire is cut from the goal, and a staged one is not trusted.

    Both halves matter and only one is obvious. A host that populates the field puts text there
    that never passed the admission rules that used to guard it, which is why redaction drops it;
    what ships instead is the stretch of the goal this client tagged as the principal's own prose,
    out of the same local that fills ``spans``. Asserting only that SOMETHING arrives would pass
    with the staged value still being forwarded.
    """
    import asyncio

    from hyperstruck import client as client_module

    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **_kwargs):
            self.writes_delivered = 0
            self.writes_failed = 0
            self.writes_terminal_failed = False
            self.last_write_error = None

        async def observe(self, **kwargs):
            captured.update(kwargs)

        async def reinforce(self, **kwargs):
            return None

        async def drain(self, timeout=30.0):
            return None

        async def aclose(self, drain_timeout=30.0):
            return None

    monkeypatch.setattr(client_module, "HostedLearningClient", FakeClient)

    asyncio.run(
        hook._deliver(
            {
                "agent_name": "agent-x",
                "episode": {
                    "run_id": "agent-x:s1:r",
                    "goal": (
                        "<command-name>/clear</command-name>\n"
                        "We use British English in this repository."
                    ),
                    "steps": [],
                    "outcome": {
                        "is_success": True,
                        "total_steps": 0,
                        "completed_steps": 0,
                        "failed_steps": 0,
                    },
                    "source_framework": "claude-code",
                    "principal_utterance": "a value the host staged and nobody accounted for",
                },
                "do_observe": True,
            }
        )
    )

    episode = captured["episode"]
    assert episode.principal_utterance == "We use British English in this repository."
    assert "a value the host staged" not in (episode.principal_utterance or "")
    prose = "".join(s.text for s in episode.spans if s.origin == "user_prose")
    assert episode.principal_utterance in prose


def test_an_absolute_tool_path_is_relativised_against_the_repository_root(
    _env, monkeypatch
) -> None:
    """Both editors send an absolute path; safe_repository_path refuses any leading '/'.

    Mutation: stop calling the relativiser and this fails on the locator ending at
    the tree with no path part at all.
    """
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{'a' * 40}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            return argparse.Namespace(returncode=0, stdout="/repo\n")
        raise AssertionError(f"unexpected git call: {argv}")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": "/repo",
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": "/repo/src/x.py"},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )
    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert provenance["locator"].endswith(":src/x.py")


def test_a_tool_path_outside_the_repository_is_dropped_not_shipped(
    _env, monkeypatch
) -> None:
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{'a' * 40}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            return argparse.Namespace(returncode=0, stdout="/repo\n")
        raise AssertionError(f"unexpected git call: {argv}")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": "/repo",
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": "/etc/passwd"},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )
    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert ":passwd" not in provenance["locator"]
    assert not provenance["locator"].endswith(":passwd")
    assert "^{tree:" in provenance["locator"] and provenance["locator"].endswith(
        f"{'b' * 40}}}"
    )


def test_a_retried_flush_reuses_the_first_attempts_locator(_env, monkeypatch) -> None:
    """A TRANSIENT outcome leaves the staged file for a later sweep, which re-reads

    git as the working tree is *then*. If the repository moved on in between, the
    turn's own commit should still be what is delivered, not the retry's HEAD.

    Mutation: stop persisting the stamped locator on the first attempt and this
    fails on the retry's locator naming the second commit.
    """
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    commits = iter(["a" * 40, "c" * 40])

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{next(commits)}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            return argparse.Namespace(returncode=0, stdout="/repo\n")
        raise AssertionError(f"unexpected git call: {argv}")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": "/repo",
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": "src/x.py"},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )

    async def transient(_payload):
        return hook.FlushOutcome.TRANSIENT, None

    monkeypatch.setattr(hook, "_deliver", transient)
    hook.cmd_flush(
        hook._parse_args(["flush", str(path)])
    )  # first attempt, stamps commit a*40

    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(
        hook._parse_args(["flush", str(path)])
    )  # retry, HEAD has moved to c*40

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert (
        provenance["locator"]
        == f"git:github.com/acme/api@{'a' * 40}^{{tree:{'b' * 40}}}:src/x.py"
    )


def test_the_tool_path_used_for_relativisation_survives_staging_redaction(
    _env, monkeypatch
) -> None:
    """A high-entropy-looking directory segment (a real tmp dir name, or a hash-shaped

    folder) must not corrupt the path fed into relativisation: the redaction that
    runs at staging (`redact_ide_episode`) applies to the whole step, same as R1's
    `source_id`, so an absolute path carrying one is scrubbed before flush ever
    sees it, and `os.path.relpath` against the real, unscrubbed root then produces
    garbage.

    Mutation: stop carrying the raw path through staging (fall back to args.path
    alone) and this fails on the locator carrying the redaction marker.
    """
    from hyperstruck.ide.redaction import redact_ide_episode

    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    high_entropy_dir = "tmpZQ8xK2vN9mLpR4wYcH7dTfJ3aXbGsUe"
    abs_path = f"/private/var/folders/xy/{high_entropy_dir}/T/scratch-repo/src/x.py"

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{'a' * 40}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            return argparse.Namespace(
                returncode=0,
                stdout=f"/private/var/folders/xy/{high_entropy_dir}/T/scratch-repo\n",
            )
        raise AssertionError(f"unexpected git call: {argv}")

    step = hook._step_from_payload(
        {"tool_name": "Edit", "tool_input": {"file_path": abs_path}},
        hook._parse_args(["tool"]),
        run_id="dev-copilot:sess-1:run-1",
    )
    episode = redact_ide_episode({"run_id": "r", "goal": "g", "steps": [step]})
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": f"/private/var/folders/xy/{high_entropy_dir}/T/scratch-repo",
            "episode": episode,
            "do_observe": True,
        },
    )

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert provenance["locator"].endswith(":src/x.py")
    assert "_raw_path" not in provenance


def test_relativisation_resolves_symlinks_in_both_the_path_and_the_root(
    _env, monkeypatch, tmp_path
) -> None:
    """macOS resolves `/tmp` to `/private/tmp`: git's real, canonicalised repo root

    and the editor's own (unresolved) cwd/path can name the same tree through two
    different strings, and a plain string-prefix relpath between them produces a
    `..`-leading path that `safe_repository_path` then refuses, dropping the file
    from every locator on any such machine.

    Mutation: relativise without resolving either side and this fails on the
    locator carrying no path at all.
    """
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link_dir = tmp_path / "link"
    link_dir.symlink_to(real_dir)

    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{'a' * 40}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            # git canonicalises, same as macOS resolving /tmp -> /private/tmp.
            return argparse.Namespace(returncode=0, stdout=f"{real_dir}\n")
        raise AssertionError(f"unexpected git call: {argv}")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    abs_path = str(link_dir / "src" / "x.py")
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": str(link_dir),
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": abs_path},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                                "_raw_path": abs_path,
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )
    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert provenance["locator"].endswith(":src/x.py")


def test_a_relativised_path_carrying_a_known_credential_shape_is_dropped(
    _env, monkeypatch
) -> None:
    """Before relativisation, an absolute path with this shape never reached the

    locator at all (safe_repository_path refused the leading '/'); relativising it
    now ships it as a clean relative path with no scrub applied to it.

    Mutation: stop checking the relativised path for a known credential and this
    fails on the token surviving in the locator.
    """
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)
    token = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{'a' * 40}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            return argparse.Namespace(returncode=0, stdout="/repo\n")
        raise AssertionError(f"unexpected git call: {argv}")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": "/repo",
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": f"/repo/src/{token}.json"},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                                "_raw_path": f"/repo/src/{token}.json",
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )
    seen: dict = {}

    async def spy(payload):
        seen["steps"] = payload["episode"]["steps"]
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    provenance = seen["steps"][0]["declared_sensitivity"]["provenance"]
    assert "locator" in provenance
    assert token not in provenance["locator"]
    assert provenance["locator"].endswith(f"^{{tree:{'b' * 40}}}")


def test_relativisation_returns_none_on_a_nul_byte_rather_than_raising(_env) -> None:
    """os.path.realpath raises on an embedded NUL, outside cmd_flush's own try, so a

    single malformed path crashed every flush of that turn until eviction, with
    nothing recorded about the drop.

    Mutation: stop catching the error and this fails on the raised ValueError.
    """
    assert hook._relativise_tool_path("/r/a\x00b.py", "/r") is None


def test_a_nul_byte_in_the_tool_path_does_not_crash_the_flush(
    _env, monkeypatch
) -> None:
    """Before the fix, cmd_flush raised on this step (realpath's ValueError was

    outside its own try), so the staged file survived and every sweep repeated
    the crash until eviction, losing the turn's observe, reinforce and close.

    Mutation: revert the `except` in `_relativise_tool_path` and this fails with
    the raised ValueError instead of delivering.
    """
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)

    def fake_run(argv, **kwargs):
        if argv[3:5] == ["remote", "get-url"]:
            return argparse.Namespace(
                returncode=0, stdout="https://github.com/acme/api.git\n"
            )
        if argv[3:] == ["rev-parse", "HEAD"]:
            return argparse.Namespace(returncode=0, stdout=f"{'a' * 40}\n")
        if argv[3:] == ["rev-parse", "HEAD^{tree}"]:
            return argparse.Namespace(returncode=0, stdout=f"{'b' * 40}\n")
        if argv[3:] == ["rev-parse", "--show-toplevel"]:
            return argparse.Namespace(returncode=0, stdout="/repo\n")
        raise AssertionError(f"unexpected git call: {argv}")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {
            "agent_name": "agent-x",
            "cwd": "/repo",
            "episode": {
                "run_id": "r",
                "steps": [
                    {
                        "id": "1",
                        "name": "Edit",
                        "args": {"path": "/repo/src/a\x00b.py"},
                        "status": "completed",
                        "declared_sensitivity": {
                            "provenance": {
                                "channel": "claude_code",
                                "genre": "coding_session",
                                "_raw_path": "/repo/src/a\x00b.py",
                            }
                        },
                    }
                ],
            },
            "do_observe": True,
        },
    )
    delivered: dict = {}

    async def spy(payload):
        delivered["ok"] = True
        return hook.FlushOutcome.DELIVERED, None

    monkeypatch.setattr(hook, "_deliver", spy)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))

    assert delivered.get("ok") is True
    assert state.read_flush(path) is None
