"""Installer: idempotent deep-merge, foreign-hook safety, agent resolution."""

from __future__ import annotations

import json

import pytest

import hyperstruck.ide.install as install


@pytest.fixture(autouse=True)
def _dirs(tmp_path, monkeypatch):
    claude = tmp_path / "claude"
    cursor = tmp_path / "cursor"
    claude.mkdir()
    cursor.mkdir()
    monkeypatch.setenv("HYPER_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HYPER_CLAUDE_DIR", str(claude))
    monkeypatch.setenv("HYPER_CURSOR_DIR", str(cursor))
    for var in (
        "HYPER_API_KEY",
        "HYPER_BASE_URL",
        "HYPER_AGENT_ID",
        "HYPER_LEARNING_AGENT_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    return claude, cursor


def _claude_cmds(claude, event="UserPromptSubmit"):
    data = json.loads((claude / "settings.json").read_text())
    return [h["command"] for g in data["hooks"][event] for h in g["hooks"]]


def test_wires_both_editors_and_is_idempotent(_dirs) -> None:
    claude, cursor = _dirs
    install.install(validate=False)
    install.install(validate=False)  # twice
    cmds = _claude_cmds(claude)
    assert sum("hyperstruck.ide.hook" in c for c in cmds) == 1  # no duplicate
    cursor_cfg = json.loads((cursor / "hooks.json").read_text())
    assert set(cursor_cfg["hooks"]) == {"afterFileEdit", "afterShellExecution", "stop"}
    assert (cursor / "rules" / "hyperstruck-learning.mdc").exists()


def test_preserves_foreign_hooks(_dirs) -> None:
    claude, _ = _dirs
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "my-own-hook"}]}
                    ]
                }
            }
        )
    )
    install.install(validate=False)
    cmds = _claude_cmds(claude)
    assert "my-own-hook" in cmds
    assert any("hyperstruck.ide.hook" in c for c in cmds)


def test_unparseable_config_backed_up_and_skipped(_dirs) -> None:
    claude, _ = _dirs
    (claude / "settings.json").write_text("{ this is not json")
    install.install(validate=False)
    assert (claude / "settings.json.bak").exists()
    # Original left untouched (still not valid json), not overwritten.
    assert (claude / "settings.json").read_text() == "{ this is not json"


def test_uninstall_removes_only_ours(_dirs) -> None:
    claude, _ = _dirs
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "my-own-hook"}]}
                    ]
                }
            }
        )
    )
    install.install(validate=False)
    install.uninstall()
    assert _claude_cmds(claude) == ["my-own-hook"]


def test_single_agent_wired_automatically(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install, "_list_agents", lambda key, base: [{"id": "only-agent"}]
    )
    install.install(api_key="k", validate=False)
    env = (install.env_file()).read_text()
    assert "HYPER_AGENT_ID=only-agent" in env
    assert "HYPER_API_KEY=k" in env


def test_multiple_agents_left_for_user(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install, "_list_agents", lambda key, base: [{"id": "a"}, {"id": "b"}]
    )
    report = install.install(api_key="k", validate=False)
    assert any("multiple agents" in w for w in report.warnings)
    assert "HYPER_AGENT_ID" not in (install.env_file()).read_text()


def test_explicit_agent_id_wins(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install, "_list_agents", lambda key, base: [{"id": "a"}, {"id": "b"}]
    )
    install.install(api_key="k", agent_id="chosen", validate=False)
    assert "HYPER_AGENT_ID=chosen" in (install.env_file()).read_text()
