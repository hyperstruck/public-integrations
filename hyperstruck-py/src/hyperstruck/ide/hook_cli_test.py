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

import http.server
import json
import os
import threading
import time
import subprocess  # nosec B404 - fixed argv, no shell
import sys
from pathlib import Path

import pytest

from hyperstruck.ide import registration

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
    home: Path, args: list[str], payload: dict, *, base_url: str = UNREACHABLE_BOUNDARY
) -> subprocess.CompletedProcess:
    """One hook event, exactly as an editor fires it."""
    env = os.environ | {
        "HYPER_HOME": str(home),
        "HOME": str(home.parent / "fake-home"),
        "HYPERSTRUCK_API_KEY": API_KEY,
        "HYPER_AGENT_NAME": "agent-x",
        "HYPERSTRUCK_BASE_URL": base_url,
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


def test_the_prompt_hook_emits_nothing_for_a_project_with_an_earlier_stash(
    hook_home,
) -> None:
    """An editor treats any stdout as context, and a previous turn's block is not wanted."""
    root = hook_home / "stash"
    root.mkdir()
    (root / "agent-x.0123456789abcdef.json").write_text(
        json.dumps({"agent_name": "agent-x", "injected_text": "PRIOR ADVICE"})
    )

    result = _run_hook(
        hook_home,
        ["prompt", "--source", "claude-code"],
        {"session_id": "s-cli", "prompt": "now fix the parser", "cwd": "/repo"},
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert not (hook_home / "stash").exists()


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


class _ResolveRecorder(http.server.BaseHTTPRequestHandler):
    bodies: list[dict]

    def do_POST(self) -> None:  # noqa: N802 - the http.server hook name
        length = int(self.headers.get("Content-Length", "0"))
        if self.path == "/resolve":
            type(self).bodies.append(json.loads(self.rfile.read(length)))
        else:
            self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *_args) -> None:
        return None


@pytest.fixture
def local_boundary(hook_home):
    """A real HTTP listener standing in for the boundary, so the real hook has something to call."""
    handler = type("Handler", (_ResolveRecorder,), {"bodies": []})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, handler.bodies
    finally:
        server.shutdown()
        server.server_close()


def _turn_against(hook_home: Path, base: str, session: str, prompt: str) -> None:
    result = _run_hook(
        hook_home,
        ["prompt", "--source", "claude-code"],
        {"session_id": session, "prompt": prompt, "cwd": "/repo"},
        base_url=base,
    )
    assert result.returncode == 0


def _wait_for(bodies: list, count: int) -> None:
    deadline = time.time() + 30
    while len(bodies) < count and time.time() < deadline:
        time.sleep(0.1)
    assert len(bodies) >= count, f"the boundary saw {len(bodies)} resolve(s), wanted {count}"


def test_the_real_hook_keeps_one_window_until_the_host_compacts(
    hook_home, local_boundary
) -> None:
    """The real hook process over a real socket: same window across turns, a new one after compaction."""
    base, bodies = local_boundary
    _turn_against(hook_home, base, "host-session-1", "first turn")
    _wait_for(bodies, 1)
    _turn_against(hook_home, base, "host-session-1", "second turn")
    _wait_for(bodies, 2)
    compact = _run_hook(
        hook_home,
        ["session-start", "--source", "claude-code"],
        {"session_id": "host-session-1", "source": "compact", "cwd": "/repo"},
    )
    assert compact.returncode == 0
    _turn_against(hook_home, base, "host-session-1", "third turn")
    _wait_for(bodies, 3)

    assert {body["session_id"] for body in bodies[:3]} == {"host-session-1"}
    assert bodies[0]["session_epoch"] == bodies[1]["session_epoch"]
    assert bodies[2]["session_epoch"] != bodies[1]["session_epoch"]
