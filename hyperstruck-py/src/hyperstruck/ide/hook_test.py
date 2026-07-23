"""End-to-end turn lifecycle: capture, deferral, structural-rework resolution."""

from __future__ import annotations

import json

import pytest

from hyperstruck._wire import StepRecord
from hyperstruck.ide import hook, state

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


def test_flush_retries_on_failed_delivery(_env, monkeypatch) -> None:
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)  # don't spawn
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def fail(_payload):
        return False

    monkeypatch.setattr(hook, "_deliver", fail)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is not None  # kept for retry on failed delivery
    assert state.read_flush_attempts(path) == 1

    async def ok(_payload):
        return True

    monkeypatch.setattr(hook, "_deliver", ok)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is None  # removed once delivered


def test_flush_drops_after_max_failed_attempts(_env, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_FLUSH_MAX_ATTEMPTS", "2")
    monkeypatch.setattr(hook, "_spawn_flush", lambda path: None)  # don't spawn
    path = state.stage_flush(
        "s1",
        "agent-x:s1:r",
        {"agent_name": "agent-x", "episode": {"run_id": "r"}, "do_observe": True},
    )

    async def fail(_payload):
        return False

    monkeypatch.setattr(hook, "_deliver", fail)
    hook.cmd_flush(hook._parse_args(["flush", str(path)]))
    assert state.read_flush(path) is not None
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
        return False

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
    assert kwargs["stderr"] is hook.subprocess.DEVNULL


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


@pytest.mark.parametrize(
    ("env_value", "expected"), [(None, hook.DETACHED_RESOLVE_TIMEOUT), ("12.5", 12.5)]
)
def test_resolver_timeout_default_and_env_override(
    _env, monkeypatch, env_value, expected
) -> None:
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
    seen = []

    async def resolved(*_args, **kwargs):
        seen.append(kwargs["resolve_timeout"])
        return "TEXT", ()

    if env_value is None:
        monkeypatch.delenv("HYPER_RESOLVE_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("HYPER_RESOLVE_TIMEOUT", env_value)
    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s1")
    assert seen == [expected]


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


def test_uninjected_recall_is_not_reinforced_and_is_removed(_env) -> None:
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
    assert pending is not None and pending.offered_learning_ids == ()
    assert state.claim_recall("c1") is None
    hook._stage_and_flush("c1", pending, True)
    assert _last_staged(staged)["do_reinforce"] is False


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


async def _aresolve_ok(agent_id, run_id, goal):
    return "TEXT", ("L1", "L2")


async def _aresolve_boom(agent_id, run_id, goal):
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
