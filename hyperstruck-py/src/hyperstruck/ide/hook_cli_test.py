"""The hook driven the way an editor drives it: a real subprocess over stdin and stdout.

Every other test in this package reaches inside the process — it monkeypatches
``_read_stdin``, or mocks the transport, or calls a ``cmd_*`` function directly. None of
them exercises the contract the editors actually depend on, which is a fresh interpreter
that reads one JSON object on stdin, writes one JSON object on stdout, and exits zero
whatever happens. That is the whole interface, and until now nothing covered it.

It matters most for the prompt-time emission, which fails *silently* by design: an editor
that cannot parse the block simply shows nothing, and no error reaches anyone.

Every run gets its own ``HYPER_HOME``, and ``HOME`` is redirected with it, so a developer's
real ``~/.hyperstruck`` is never read or written.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argv, no shell
import sys
from pathlib import Path

import pytest

from hyperstruck._wire import ResolvedContext
from hyperstruck.ide import registration, stash

API_KEY = "sk-e2e-test-key"
# The prompt hook detaches a resolve. It fails open and never blocks, but it must not
# reach the real boundary from a test, so it is pointed at a port nothing is listening on.
UNREACHABLE_BOUNDARY = "http://127.0.0.1:1"


@pytest.fixture
def hook_home(tmp_path, monkeypatch) -> Path:
    """A private loop root that this process and the subprocess both see."""
    home = tmp_path / "hyper-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    monkeypatch.setenv("HYPER_HOME", str(home))
    monkeypatch.setenv("HYPERSTRUCK_API_KEY", API_KEY)
    monkeypatch.setenv("HYPER_AGENT_NAME", "agent-x")
    monkeypatch.setenv("HYPERSTRUCK_BASE_URL", UNREACHABLE_BOUNDARY)
    return home


def _run_hook(
    home: Path, args: list[str], payload: dict
) -> subprocess.CompletedProcess:
    """One hook event, exactly as an editor fires it."""
    env = os.environ | {
        "HYPER_HOME": str(home),
        "HOME": str(home.parent / "fake-home"),
        "HYPERSTRUCK_API_KEY": API_KEY,
        "HYPER_AGENT_NAME": "agent-x",
        "HYPERSTRUCK_BASE_URL": UNREACHABLE_BOUNDARY,
        "PYTHONSAFEPATH": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
    }
    return subprocess.run(  # nosec B603 - fixed argv, no shell
        [sys.executable, "-m", "hyperstruck.ide.hook", *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_the_prompt_hook_emits_the_block_the_editor_parses(hook_home) -> None:
    """Byte for byte, because a block the editor cannot parse shows nothing and says
    nothing: the failure mode of this path is silence, on both sides."""
    stash.write(
        "agent-x",
        "/repo",
        goal="add retry to the uploader",
        context=ResolvedContext(injected_text="PRIOR ADVICE"),
    )

    result = _run_hook(
        hook_home,
        ["prompt", "--source", "claude-code"],
        {"session_id": "s-cli", "prompt": "now fix the parser", "cwd": "/repo"},
    )

    assert result.returncode == 0
    emitted = json.loads(result.stdout)
    assert set(emitted) == {"hookSpecificOutput"}
    assert emitted["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    context = emitted["hookSpecificOutput"]["additionalContext"]
    assert context.endswith("PRIOR ADVICE")
    assert context.startswith("From your previous turn in this project")


def test_a_warm_emission_carries_no_run_marker(hook_home) -> None:
    """Read back from what was printed at the boundary the editor sees, not from a
    helper: a marker here would be redeemed against a receipt that cannot exist."""
    stash.write(
        "agent-x",
        "/repo",
        goal="earlier",
        context=ResolvedContext(injected_text="A"),
    )

    result = _run_hook(
        hook_home,
        ["prompt", "--source", "claude-code"],
        {"session_id": "s-cli-mark", "prompt": "next", "cwd": "/repo"},
    )

    assert "hyperstruck-run:" not in result.stdout


def test_a_prompt_with_no_stash_emits_nothing_at_all(hook_home) -> None:
    """An editor treats any stdout as context, so an empty answer must be empty output."""
    result = _run_hook(
        hook_home,
        ["prompt", "--source", "claude-code"],
        {"session_id": "s-cli-cold", "prompt": "first ever turn", "cwd": "/repo"},
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_a_registration_is_read_back_by_a_later_hook_process(hook_home) -> None:
    """The point of the store: the verdict is written once, out of band, and every
    short-lived tool hook after it does a lookup rather than a judgement."""
    registered = _run_hook(
        hook_home,
        ["register", "--source", "claude-code"],
        {
            "tools": [
                {"name": "mcp__docs__search", "annotations": {"readOnlyHint": True}},
                {"name": "mcp__slack__post", "annotations": {"readOnlyHint": False}},
            ],
            "servers": ["docs", "slack"],
            "registered_servers": ["docs", "slack"],
            "model_context_window": 200_000,
        },
    )

    assert registered.returncode == 0
    assert registration.registered_kind("claude-code", "mcp__docs__search") == "read"
    assert registration.registered_kind("claude-code", "mcp__slack__post") == "act"
    assert registration.context_window("claude-code") == 200_000


def test_a_malformed_payload_exits_zero_and_says_nothing(hook_home) -> None:
    """The loop must never break the editor. Failing open is the whole contract."""
    result = subprocess.run(  # nosec B603 - fixed argv, no shell
        [sys.executable, "-m", "hyperstruck.ide.hook", "prompt"],
        input="{ this is not json",
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "HYPER_HOME": str(hook_home),
            "HYPERSTRUCK_BASE_URL": UNREACHABLE_BOUNDARY,
            "PYTHONSAFEPATH": "1",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        },
        timeout=60,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
