"""End-to-end turn lifecycle: capture, deferral, structural-rework resolution."""

from __future__ import annotations

import argparse
import asyncio

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
from hyperstruck.ide import hook, registration, stash, state
from hyperstruck.ide.recall import RecallOutcome
from hyperstruck.ide.constants import CREDENTIAL_HEAD_CHARS, PENDING_FILE
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
        assert set(step) <= {"id", "name", "args", "status", "result", "error"}
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
            offered_learning_ids=("L1", "L2"),
            offered_claim_ids=("C1",),
        )

    monkeypatch.setattr(hook, "_aresolve", resolved)
    hook.cmd_resolve("s1")
    assert state.claim_recall("s1") == {
        "run_id": "run-1",
        "injected_text": "TEXT",
        "injected_facts_text": "FACT",
        "offered_learning_ids": ["L1", "L2"],
        "offered_claim_ids": ["C1"],
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
    assert payload["hookSpecificOutput"]["additionalContext"].endswith("INJECTED")
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
    assert json.loads(capsys.readouterr().out)["additional_context"].endswith(
        "INJECTED"
    )
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
    assert injected.offered_learning_ids == ("L1",)
    assert injected.offered_claim_ids == ("C1",)


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
        "pr-305-review-round-2-fixes-and-followups",
        "superloop-supplier-code-of-conduct-review-2026-08-04",
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
    descriptive = "superloop-supplier-code-of-conduct-review-2026-08-04"
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
            is_injected=True,
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
    state.write_active(session, replace(active, is_injected=True), reset_steps=False)

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
        is_injected=False,
    )
    state.write_recall_status("s1", turn.run_id, RecallOutcome.RESOLVE_TIMED_OUT)

    assert (
        hook._acceptance_record("s1", turn, []).outcome
        is RecallOutcome.RESOLVE_TIMED_OUT
    )
    delivered = hook._acceptance_record("s1", replace(turn, is_injected=True), [])
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


def test_a_goalless_turn_declines_instead_of_observing_an_episode_about_nothing(
    _env, monkeypatch
) -> None:
    """Its steps are material and it is still declined, which no other reason covers.

    A goal is what an extracted rule is transferable against, so an episode without one
    asks the corpus to generalise from what was done with no account of what it was for.
    Reporting it by its step count would name a gate that never ran.
    """
    monkeypatch.setattr(
        hook, "published_decline_reasons", lambda: frozenset({hook.REASON_NO_GOAL})
    )

    staged = _stage_a_goalless_turn(monkeypatch, "s-goalless-on")

    assert staged, "the goalless turn staged nothing at all"
    assert "episode" not in staged[0]
    assert staged[0]["decline"]["reason"] == hook.REASON_NO_GOAL


def test_a_goalless_turn_is_observed_while_its_reason_is_unpublished(
    _env, monkeypatch
) -> None:
    """The boundary refuses a reason it does not know, and a refused decline leaks the run.

    An unclosed run holding its resolve reservation is strictly worse than the goalless
    observe this replaces, so the branch stays off until the reason is published rather
    than declining under a reason that means something else.
    """
    monkeypatch.setattr(hook, "published_decline_reasons", frozenset)

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
