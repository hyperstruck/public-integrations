"""End-to-end turn lifecycle: capture, deferral, structural-rework resolution."""

from __future__ import annotations

import argparse
import asyncio
import json
from types import SimpleNamespace
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
from hyperstruck.ide import hook, state
from hyperstruck.ide.constants import CREDENTIAL_HEAD_CHARS
from hyperstruck.redaction import REDACTION_MARKER
from hyperstruck.ide.constants import (
    MAX_BOUNDARY_GOAL_CHARS,
    MAX_EPISODE_STEPS,
    MAX_STEP_FIELD_CHARS,
)

# Captured before the autouse fixture patches it, so the resolve breadcrumb tests
# can exercise the real _resolve rather than the fixture's readonly stub.
_REAL_RESOLVE = hook._resolve
_REAL_SPAWN_RESOLVE = hook._spawn_resolve


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))
    monkeypatch.setenv("HYPER_AGENT_NAME", "agent-x")
    # Readonly resolve always offers one learning. Detached resolve is modelled as
    # immediately ready so lifecycle tests can exercise the tool-time handoff.
    monkeypatch.setattr(
        hook, "_resolve", lambda agent_id, run_id, goal: ("INJECTED", ("L1",))
    )

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


def test_turn_captured_and_deferred(_env) -> None:
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
    # Nothing flushed yet: the first turn has no prior to resolve.
    assert staged == []
    pending = state.read_pending("s1")
    assert (
        pending is not None and pending.is_success is True
    )  # tests passed -> provisional green


def test_rework_resolution_on_one_session(_env) -> None:
    staged = _env
    session = "s1"
    # Turn 1: green, edits client.py.
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
    assert staged == []  # deferred

    # Turn 2: reworks client.py -> resolves turn 1 as failed (false-green caught).
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
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))

    assert len(staged) == 1
    flushed = _last_staged(staged)
    assert flushed["agent_name"] == "agent-x"
    assert (
        flushed["episode"]["outcome"]["is_success"] is False
    )  # rework overrode the green
    assert flushed["do_observe"] is True  # 2 material steps
    assert flushed["do_reinforce"] is True  # L1 was offered
    # Steps validate against the wire StepModel shape (no client-only fields).
    for step in flushed["episode"]["steps"]:
        assert set(step) <= {"id", "name", "args", "status", "result", "error"}
        assert step["id"]
        StepRecord(**step)


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
    assert staged == []  # deferred until the next turn resolves it
    _run_turn(session, "next", [{"tool_name": "Read", "file_path": "a.py"}])

    flushed = state.read_flush(staged[0])
    assert flushed["do_observe"] is True
    assert flushed["do_reinforce"] is True  # empty offer still closes the loop


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
    _run_turn(session, "read again", [{"tool_name": "Read", "file_path": "b.py"}])

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
    _run_turn(session, "and this?", [])

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
    # Turn 2 is a different file, ambiguous prompt -> turn 1 stays green.
    hook.cmd_prompt(
        {"session_id": session, "prompt": "now add b.py", "cwd": "/repo"},
        _args("prompt"),
    )
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "b.py",
            "tool_response": "ok",
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
    # No cmd_stop. Turn 2 begins: the orphan must be promoted, not discarded.
    hook.cmd_prompt(
        {"session_id": session, "prompt": "now edit b.py", "cwd": "/repo"},
        _args("prompt"),
    )
    pending = state.read_pending(session)
    assert pending is not None and pending.goal == "edit a.py"  # orphan promoted
    # Turn 2 completes -> the recovered turn 1 is resolved and flushed, not lost.
    hook.cmd_tool(
        {
            "session_id": session,
            "tool_name": "Edit",
            "file_path": "b.py",
            "tool_response": "ok",
        },
        _args("tool"),
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    assert len(staged) == 1
    assert _last_staged(staged)["episode"]["goal"] == "edit a.py"


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
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    hook.cmd_prompt(
        {"session_id": session, "prompt": "next", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    flushed = _last_staged(staged)
    blob = str(flushed)
    assert "RAW_FILE_BODY_LINE" not in blob  # read content never ships
    assert "RAW_DIFF_BODY" not in blob  # edit diff never ships
    for step in flushed["episode"]["steps"]:
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
    hook.cmd_prompt(
        {"session_id": session, "prompt": "y", "cwd": "/repo"}, _args("prompt")
    )
    hook.cmd_stop({"session_id": session, "cwd": "/repo"}, _args("stop"))
    flushed = _last_staged(staged)
    # The shipped run_id must equal turn 1's resolve run_id (the server keys its
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


def test_eviction_flushes_stale_pending(_env) -> None:
    staged = _env
    state.write_pending(
        "oldsess",
        state.PendingTurn(
            run_id="agent-x:oldsess:r1",
            agent_name="agent-x",
            goal="g",
            steps=(
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
            ),
            is_success=True,
            source_framework="claude-code",
            ended_at=0.0,  # far past the eviction window
            offered_learning_ids=("L1",),
        ),
    )
    hook._sweep_stale(exclude="other")
    assert len(staged) == 1
    assert state.read_pending("oldsess") is None
    assert _last_staged(staged)["episode"]["run_id"] == "agent-x:oldsess:r1"


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


def test_nested_bash_failure_detected(_env) -> None:
    # Claude Code Bash failures live inside tool_response, not top-level.
    step = hook._step_from_payload(
        {
            "tool_name": "Bash",
            "command": "pytest",
            "tool_response": {"stderr": "AssertionError boom", "interrupted": False},
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
    assert active.is_injected is False


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
    pending = state.PendingTurn(
        run_id="a:b:c",
        agent_name="agent-x",
        goal="g",
        steps=tuple(steps),
        is_success=True,
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
        return "TEXT", ("L1",)

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
        return "TEXT", ("L1", "L2")

    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s1")
    assert state.claim_recall("s1") == {
        "run_id": "run-1",
        "injected_text": "TEXT",
        "offered_learning_ids": ["L1", "L2"],
    }


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
        return None, ()

    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s1")
    assert state.peek_recall("s1") is None


# A hosted resolve measured 13.1s against api.hyperstruck.com on 2026-08-10. The
# budget has to clear that, which is the property that actually failed: asserting
# only that the two hook paths agree stays green if the constant is lowered.
MEASURED_HOSTED_RESOLVE_SECONDS = 13.1


def test_recall_budget_clears_a_real_hosted_resolve() -> None:
    assert hook.DEFAULT_RECALL_TIMEOUT > MEASURED_HOSTED_RESOLVE_SECONDS
    assert hook.MIN_RECALL_TIMEOUT > client.DEFAULT_RESOLVE_TIMEOUT


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


@pytest.mark.parametrize("caller", ["detached", "explicit"])
@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        (None, hook.DEFAULT_RECALL_TIMEOUT),
        ("12.5", 12.5),
        ("0", hook.MIN_RECALL_TIMEOUT),
        ("-4", hook.MIN_RECALL_TIMEOUT),
        ("nonsense", hook.DEFAULT_RECALL_TIMEOUT),
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

    class _RecordingClient:
        def __init__(self, **kwargs):
            seen.append(kwargs["resolve_timeout"])

        async def resolve(self, **_kwargs):
            return SimpleNamespace(injected_text="TEXT", offered_learning_ids=())

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
        hook._resolve("agent-x", "run-1", "do x")

    assert seen == [expected]


def test_explicit_recall_says_so_on_stderr_when_it_times_out(
    _env, capsys, monkeypatch
) -> None:
    """A timed-out recall must not read as an empty corpus, per the outage it caused."""
    monkeypatch.delenv("HYPER_HOOK_DEBUG", raising=False)

    async def timed_out(*_args, **_kwargs):
        raise TimeoutError

    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    monkeypatch.setattr(hook, "_aresolve", timed_out)

    assert hook._resolve("agent-x", "run-1", "do x") == (None, ())
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
    assert payload == {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "INJECTED",
        }
    }
    active = state.read_active("s1")
    assert active is not None
    assert active.is_injected is True
    assert active.offered_learning_ids == ("L1",)
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
    assert state.read_active("s1").is_injected is False
    state.write_recall("s1", fresh)  # the current turn's resolve lands
    hook.cmd_tool(
        {"session_id": "s1", "tool_name": "Read", "cwd": "/repo"},
        hook._parse_args(["tool"]),
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["additionalContext"] == "INJECTED"
    active = state.read_active("s1")
    assert active.is_injected is True
    assert active.offered_learning_ids == ("L1",)


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
    assert json.loads(capsys.readouterr().out) == {"additional_context": "INJECTED"}
    assert state.read_active("c1").is_injected is True
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
    assert staged == []  # deferred
    # Next turn finalises and flushes the prior one.
    hook.cmd_prompt({**conv, "prompt": "next"}, hook._parse_args(["prompt", *cc]))
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
    hook.cmd_stop(conv, hook._parse_args(["stop", "--source", "cursor"]))
    pending = state.read_pending("c1")
    assert (
        pending is not None and pending.offered_learning_ids == ()
    )  # nothing credited
    assert state.claim_recall("c1") is None  # the stale recall is removed
    hook._stage_and_flush("c1", pending, True)
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


# -- debug breadcrumbs -------------------------------------------------------


async def _aresolve_ok(agent_id, run_id, goal, **_kwargs):
    return "TEXT", ("L1", "L2")


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


def test_resolve_ok_breadcrumb_counts_learnings(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    monkeypatch.setattr(hook, "_aresolve", _aresolve_ok)
    text, offered = hook._resolve("agent-x", "run-1", "do x")
    assert (text, offered) == ("TEXT", ("L1", "L2"))
    assert "resolve ok: 2 learning(s)" in capsys.readouterr().err


def test_resolve_failure_breadcrumb_and_fails_open(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    monkeypatch.setattr(hook, "_resolve", _REAL_RESOLVE)
    monkeypatch.setattr(hook, "_aresolve", _aresolve_boom)
    assert hook._resolve("agent-x", "run-1", "do x") == (None, ())
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


def test_distill_no_agent_is_skipped(_env, capsys, monkeypatch) -> None:
    monkeypatch.delenv("HYPER_AGENT_NAME", raising=False)
    hook.cmd_distill(_distill_spec(), hook._parse_args(["distill", "--emit", "text"]))
    out = capsys.readouterr().out
    assert "skipped" in out and "HYPER_AGENT_NAME" in out


def test_distill_requires_two_evidence_items(_env, capsys) -> None:
    spec = _distill_spec(evidence=[{"id": "only", "content": "z" * 40}])
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert "at least 2" in capsys.readouterr().out


def test_distill_forwards_scrubbed_corpus_to_client(_env, capsys, monkeypatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_adistill(**kwargs):
        captured.update(kwargs)
        return {
            "status": "delivered",
            "agent": kwargs["agent_name"],
            "run_id": kwargs["run_id"],
            "evidence_count": len(kwargs["evidence"]),
        }

    monkeypatch.setattr(hook, "_adistill", fake_adistill)
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
    assert captured["evidence"][0].source_ref == "https://example.com/design-doc-2026-07"
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


def test_distill_rejects_no_contrast_before_network(_env, capsys, monkeypatch) -> None:
    async def forbidden_adistill(**kwargs):  # pragma: no cover - should not be called
        raise AssertionError(kwargs)

    monkeypatch.setattr(hook, "_adistill", forbidden_adistill)
    spec = _distill_spec(
        evidence=[
            {"id": "a", "role": "neutral", "status": "completed", "content": "a" * 40},
            {"id": "b", "role": "neutral", "status": "completed", "content": "b" * 40},
        ],
    )
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert "declared contrast" in capsys.readouterr().out


def test_distill_rejects_support_neutral_roles_without_contrast(
    _env, capsys, monkeypatch
) -> None:
    async def forbidden_adistill(**kwargs):  # pragma: no cover - should not be called
        raise AssertionError(kwargs)

    monkeypatch.setattr(hook, "_adistill", forbidden_adistill)
    spec = _distill_spec(
        evidence=[
            {"id": "a", "role": "support", "status": "completed", "content": "a" * 40},
            {"id": "b", "role": "neutral", "status": "completed", "content": "b" * 40},
        ],
    )
    hook.cmd_distill(spec, hook._parse_args(["distill", "--emit", "text"]))
    assert "declared contrast" in capsys.readouterr().out


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
    assert hook._scrub_distill_string(descriptive) != descriptive, "fixture must actually trip the scrubber"

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
        "pr-305-review-round-2-fixes-and-followups",
        "superloop-supplier-code-of-conduct-review-2026-08-04",
        "distill-run-id-collision-fix-verification",
    ],
)
def test_a_long_descriptive_run_id_is_accepted_though_the_scrubber_would_flatten_it(
    descriptive: str,
) -> None:
    assert hook._scrub_distill_string(descriptive) != descriptive, "fixture must actually trip the scrubber"

    assert hook._distill_run_id_rejection(descriptive) is None
    assert hook._distill_run_id(descriptive) == f"distill:{descriptive}"


def test_ordinary_run_ids_are_accepted() -> None:
    for clean in ("ci-lint-bandit-gate-2026-08-02", "meeting-8220", "distill:already-prefixed", None, "  "):
        assert hook._distill_run_id_rejection(clean) is None


def test_clean_run_id_keeps_its_prefix_exactly_once() -> None:
    assert hook._distill_run_id("ci-lint-bandit-gate-2026-08-02") == "distill:ci-lint-bandit-gate-2026-08-02"
    assert hook._distill_run_id("distill:already-prefixed") == "distill:already-prefixed"


def _run_distill_with_run_id(
    monkeypatch: pytest.MonkeyPatch, run_id: str
) -> tuple[list[str], list[dict[str, Any]]]:
    monkeypatch.setattr(hook, "configured_agent_name", lambda: "dev-copilot")
    dispatched: list[str] = []
    monkeypatch.setattr(hook, "_adistill", lambda **kw: dispatched.append(kw["run_id"]))

    emitted: list[dict[str, Any]] = []
    monkeypatch.setattr(hook, "_emit_distill_result", lambda result, args: emitted.append(result))

    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": run_id,
            "evidence": [
                {"id": "a", "role": "contrast", "status": "failed", "content": "the rejected approach"},
                {"id": "b", "role": "support", "status": "completed", "content": "the accepted approach"},
            ],
        },
        argparse.Namespace(emit="json", source="claude-code", goal=None),
    )
    return dispatched, emitted


def test_a_refused_run_id_never_reaches_the_wire(monkeypatch: pytest.MonkeyPatch) -> None:
    # The unit tests above exercise a pure function; the original defect was that a
    # bad id reached the server. This asserts the refusal actually stops dispatch.
    dispatched, emitted = _run_distill_with_run_id(monkeypatch, "run-sk-AbCdEf0123456789AbCdEf")

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
    assert "sk-AbCdEf0123456789AbCdEf" not in reason, "the reason must not echo the secret"


def test_the_refusal_reveals_at_most_the_shape_head() -> None:
    # Pins CREDENTIAL_HEAD_CHARS itself. Asserting only that the whole secret is
    # absent passes for any width up to len-1: raising the constant to 20 left the
    # suite green while the reason printed 17 characters of a 25-character key.
    assert CREDENTIAL_HEAD_CHARS == 4
    secret = "sk-AbCdEf0123456789AbCdEf"

    reason = hook._distill_run_id_rejection(secret) or ""

    assert secret[:CREDENTIAL_HEAD_CHARS] in reason
    assert secret[: CREDENTIAL_HEAD_CHARS + 1] not in reason


def test_a_descriptive_run_id_reaches_the_wire_verbatim(monkeypatch: pytest.MonkeyPatch) -> None:
    # The complement, and the regression that matters: refusing this is what made
    # a correlatable id unusable, so dispatch must happen and carry it unaltered.
    descriptive = "superloop-supplier-code-of-conduct-review-2026-08-04"
    assert hook._scrub_distill_string(descriptive) != descriptive, (
        "fixture must actually trip the scrubber, or this proves nothing"
    )

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
    assert hook._scrub_distill_string(first) == hook._scrub_distill_string(second), (
        "fixture must actually collide under the scrubber"
    )

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
        [{"id": "a", "content": f"we used {secret}", "label": secret, "status": "completed"}]
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
    monkeypatch.setattr(hook, "_emit_distill_result", lambda result, args: emitted.append(result))

    entry: dict[str, Any] = {"id": "a", "role": "contrast", "status": "failed", "content": "x"}
    entry[field] = "run-ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": "an-ordinary-descriptive-run-id-2026",
            "evidence": [entry, {"id": "b", "role": "support", "status": "completed", "content": "y"}],
        },
        argparse.Namespace(emit="json", source="claude-code", goal=None),
    )

    assert dispatched == [], "a corpus with a credential in an identifier must not dispatch"
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
    monkeypatch.setattr(hook, "_emit_distill_result", lambda result, args: emitted.append(result))

    hook.cmd_distill(
        {
            "goal": "teach the agent a house rule",
            "run_id": "an-ordinary-descriptive-run-id-2026",
            "evidence": [
                {"id": "a", "content": "real one", "status": "failed", "role": "contrast"},
                {"id": "b", "content": "", "status": "completed"},
                "not-a-dict",
                {"id": "d", "content": "real two", "status": "completed", "role": "support"},
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
    monkeypatch.setattr(hook, "_emit_distill_result", lambda result, args: emitted.append(result))

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
        def __init__(self):
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
        )
    )

    assert result["status"] == expected_status
    assert captured["outcome"].is_success is False
    assert secret not in (captured["outcome"].summary or "")


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
        def __init__(self):
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


def test_deliver_decline_reports_a_terminal_rejection(_env, monkeypatch) -> None:
    """A 4xx on a decline must be terminal, so it counts toward the retry cap."""
    import hyperstruck.client as client_module

    class FakeClient:
        def __init__(self):
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


def test_the_successors_message_lands_on_the_prior_turns_episode() -> None:
    """The objection is typed on turn N+1 and is about turn N."""
    pending = state.PendingTurn(
        run_id="r1",
        agent_name="a",
        goal="fix the vacuity gate",
        steps=({"status": "completed", "description": "edit"},),
        is_success=True,
        source_framework="claude-code",
        ended_at=0.0,
        principal_utterance="we do not add word lists to our code",
    )

    episode = hook._build_episode(pending, is_success=False)

    assert episode["principal_utterance"] == "we do not add word lists to our code"


def test_a_turn_with_no_successor_message_sends_none() -> None:
    pending = state.PendingTurn(
        run_id="r1",
        agent_name="a",
        goal="fix the vacuity gate",
        steps=({"status": "completed", "description": "edit"},),
        is_success=True,
        source_framework="claude-code",
        ended_at=0.0,
    )

    assert hook._build_episode(pending, is_success=True)["principal_utterance"] is None


class TestUtteranceAdmission:
    """A non-empty utterance authorises a frozen, undecayable, primacy-rendered rule."""

    def test_an_ordinary_message_is_admitted(self) -> None:
        assert (
            hook._principal_utterance("we use British English here", "sess-1")
            == "we use British English here"
        )

    def test_a_derived_session_admits_nothing(self) -> None:
        """Two conversations collapse onto one derived session, so the turn is not established."""
        assert (
            hook._principal_utterance("we use British English here", "derived-42-abc")
            == ""
        )

    def test_a_message_the_scrub_touched_is_refused(self) -> None:
        scrubbed = f"the key is {REDACTION_MARKER} so be careful"

        assert hook._principal_utterance(scrubbed, "sess-1") == ""

    def test_a_message_past_the_bound_is_refused_not_truncated(self) -> None:
        """Half a stated norm can mean the opposite of the whole one."""
        assert (
            hook._principal_utterance("x" * (hook.MAX_UTTERANCE_CHARS + 1), "sess-1")
            == ""
        )

    def test_a_message_at_the_bound_is_kept(self) -> None:
        at_bound = "y" * hook.MAX_UTTERANCE_CHARS

        assert hook._principal_utterance(at_bound, "sess-1") == at_bound

    def test_every_measured_norm_statement_fits(self) -> None:
        """Calibrated on real sessions: the longest observed statement was 368 characters."""
        assert hook.MAX_UTTERANCE_CHARS > 368


def test_delivery_carries_the_utterance_to_the_client() -> None:
    """Staging assertions alone cannot catch a field dropped when the wire object is rebuilt."""
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
