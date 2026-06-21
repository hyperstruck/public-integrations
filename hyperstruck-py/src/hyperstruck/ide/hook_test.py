"""End-to-end turn lifecycle: capture, deferral, structural-rework resolution."""

from __future__ import annotations

import pytest

from hyperstruck._wire import StepRecord
from hyperstruck.ide import hook, state


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))
    monkeypatch.setenv("HYPER_AGENT_ID", "agent-x")
    # Resolve always offers one learning; capture flushes instead of spawning.
    monkeypatch.setattr(
        hook, "_resolve", lambda agent_id, run_id, goal: ("INJECTED", ("L1",))
    )
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
    assert flushed["agent_id"] == "agent-x"
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
    monkeypatch.delenv("HYPER_AGENT_ID", raising=False)
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

    def capture(agent_id, run_id, goal):
        run_ids.append(run_id)
        return ("INJECTED", ("L1",))

    monkeypatch.setattr(hook, "_resolve", capture)
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
    # The shipped run_id must equal turn 1's resolve run_id (server keys offer log on it).
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
            agent_id="agent-x",
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


def test_flush_retries_on_failed_delivery(_env, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)  # don't spawn
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_id": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def fail(_payload):
        return False

    monkeypatch.setattr(hook, "_deliver", fail)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is not None  # kept for retry on failed delivery

    async def ok(_payload):
        return True

    monkeypatch.setattr(hook, "_deliver", ok)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is None  # removed once delivered
