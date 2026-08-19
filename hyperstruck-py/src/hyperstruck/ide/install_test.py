"""Installer: idempotent deep-merge, foreign-hook safety, agent resolution."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import hyperstruck.ide.install as install

_REAL_ENSURE_DURABLE_VENV = install._ensure_durable_venv
_AGENT_UUID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture(autouse=True)
def _dirs(tmp_path, monkeypatch):
    claude = tmp_path / "claude"
    cursor = tmp_path / "cursor"
    claude.mkdir()
    cursor.mkdir()
    home = tmp_path / "home"
    venv_dir = home / "venv"
    monkeypatch.setenv("HYPER_HOME", str(home))
    monkeypatch.setenv("HYPER_IDE_VENV", str(venv_dir))
    monkeypatch.setenv("HYPER_CLAUDE_DIR", str(claude))
    monkeypatch.setenv("HYPER_CURSOR_DIR", str(cursor))
    for var in (
        "HYPER_API_KEY",
        "HYPER_BASE_URL",
        "HYPER_AGENT_NAME",
        "HYPER_AGENT_ID",
        "HYPER_LEARNING_AGENT_NAME",
        "HYPER_LEARNING_AGENT_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(install, "_ensure_durable_venv", lambda report: True)
    return claude, cursor, venv_dir


def _claude_cmds(claude, event="UserPromptSubmit"):
    data = json.loads((claude / "settings.json").read_text())
    return [h["command"] for g in data["hooks"][event] for h in g["hooks"]]


def _expected_hook_python(venv_dir: Path) -> str:
    return str(install._venv_python(venv_dir))


def test_wires_both_editors_and_is_idempotent(_dirs) -> None:
    claude, cursor, venv_dir = _dirs
    install.install(validate=False)
    install.install(validate=False)
    cmds = _claude_cmds(claude)
    assert sum("hyperstruck.ide.hook" in c for c in cmds) == 1
    cursor_cfg = json.loads((cursor / "hooks.json").read_text())
    assert set(cursor_cfg["hooks"]) == {
        "beforeSubmitPrompt",
        "postToolUse",
        "afterFileEdit",
        "afterShellExecution",
        "stop",
    }
    assert "--inject" in cursor_cfg["hooks"]["postToolUse"][0]["command"]
    assert "prompt" in cursor_cfg["hooks"]["beforeSubmitPrompt"][0]["command"]
    expected = _expected_hook_python(venv_dir)
    assert expected in cmds[0]
    assert sys.executable not in cmds[0]
    assert expected in cursor_cfg["hooks"]["beforeSubmitPrompt"][0]["command"]
    assert not (cursor / "rules" / "hyperstruck-learning.mdc").exists()


def _wired_commands(claude: Path, cursor: Path) -> tuple[list[str], list[str]]:
    claude_cmds = [
        c
        for event in json.loads((claude / "settings.json").read_text())["hooks"]
        for c in _claude_cmds(claude, event)
    ]
    cursor_cfg = json.loads((cursor / "hooks.json").read_text())
    cursor_cmds = [
        h["command"] for hooks in cursor_cfg["hooks"].values() for h in hooks
    ]
    return claude_cmds, cursor_cmds


def test_every_wired_command_keeps_cwd_off_sys_path(_dirs) -> None:
    """A repo file named after a stdlib module must not shadow it and kill the hook."""
    claude, cursor, _ = _dirs
    install.install(validate=False)

    claude_cmds, cursor_cmds = _wired_commands(claude, cursor)
    assert len(claude_cmds) == 3
    assert len(cursor_cmds) == 5

    for command in claude_cmds + cursor_cmds:
        parts = shlex.split(command)
        # Exact, not "contains": after -m every token is a hook argument, so the
        # flag isolates sys.path only while it stays ahead of it.
        assert parts[1 : parts.index("-m")] == ["-P"], command


def test_wired_flags_are_accepted_by_the_interpreter_that_runs_them() -> None:
    """Asserting the flag string is not enough: an interpreter must accept it.

    This is what pins the package floor to the flag. If ``requires-python`` ever
    drops below 3.11 again, the CI leg for that version fails here rather than
    shipping a wired command that aborts before any hook code runs.
    """
    probe = subprocess.run(
        [sys.executable, *install.SAFE_PATH_FLAGS, "-c", "import sys"],
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr


def test_legacy_command_shape_is_migrated_not_duplicated(_dirs) -> None:
    """An install predating the flag must be rewired, not left broken beside a new one."""
    claude, _, _ = _dirs
    (claude / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "/old/python -m hyperstruck.ide.hook prompt",
                                }
                            ]
                        }
                    ]
                }
            }
        )
    )
    install.install(validate=False)
    cmds = _claude_cmds(claude)
    assert sum("hyperstruck.ide.hook" in c for c in cmds) == 1
    assert not any(c.startswith("/old/python") for c in cmds)


def test_preserves_foreign_hooks(_dirs) -> None:
    claude, _, _ = _dirs
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
    claude, _, _ = _dirs
    (claude / "settings.json").write_text("{ this is not json")
    install.install(validate=False)
    assert (claude / "settings.json.bak").exists()
    assert (claude / "settings.json").read_text() == "{ this is not json"


def test_uninstall_removes_only_ours(_dirs) -> None:
    claude, _, venv_dir = _dirs
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
    venv_dir.mkdir(parents=True, exist_ok=True)
    (venv_dir / "marker").write_text("keep")
    install.uninstall()
    assert _claude_cmds(claude) == ["my-own-hook"]
    assert (venv_dir / "marker").read_text() == "keep"


def test_single_agent_wired_automatically(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base: [{"id": _AGENT_UUID, "name": "only-agent"}],
    )
    install.install(api_key="k", validate=False)
    env = (install.env_file()).read_text()
    assert "HYPER_AGENT_NAME=only-agent" in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env
    assert "HYPER_API_KEY=k" in env


def test_multiple_agents_left_for_user(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base: [
            {"id": _AGENT_UUID, "name": "a"},
            {"id": "22222222-2222-4222-8222-222222222222", "name": "b"},
        ],
    )
    report = install.install(api_key="k", validate=False)
    assert any("multiple agents" in w for w in report.warnings)
    env = (install.env_file()).read_text()
    assert "HYPER_AGENT_NAME" not in env
    assert "HYPER_AGENT_ID" not in env


def test_explicit_agent_name_wins(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base: [
            {"id": _AGENT_UUID, "name": "a"},
            {"id": "22222222-2222-4222-8222-222222222222", "name": "b"},
        ],
    )
    install.install(api_key="k", agent_name="chosen", validate=False)
    env = (install.env_file()).read_text()
    assert "HYPER_AGENT_NAME=chosen" in env


def test_explicit_agent_uuid_resolves_name(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base: [{"id": _AGENT_UUID, "name": "resolved-name"}],
    )
    install.install(api_key="k", agent_id=_AGENT_UUID, validate=False)
    env = (install.env_file()).read_text()
    assert "HYPER_AGENT_NAME=resolved-name" in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env


def test_rerun_migrates_managed_legacy_learning_agent_name(_dirs) -> None:
    path = install.env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HYPER_API_KEY=k\nHYPER_LEARNING_AGENT_ID=legacy-agent\n")

    install.install(validate=False)

    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME=legacy-agent" in env
    assert "HYPER_LEARNING_AGENT_ID" not in env


def test_rerun_migrates_managed_legacy_agent_name(_dirs) -> None:
    path = install.env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HYPER_API_KEY=k\nHYPER_AGENT_ID=legacy-agent\n")

    install.install(validate=False)

    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME=legacy-agent" in env
    assert "HYPER_AGENT_ID=legacy-agent" not in env


def test_rerun_migrates_managed_legacy_agent_uuid(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base: [{"id": _AGENT_UUID, "name": "resolved-name"}],
    )
    path = install.env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"HYPER_API_KEY=k\nHYPER_AGENT_ID={_AGENT_UUID}\n")

    install.install(validate=False)

    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME=resolved-name" in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env


def test_rerun_migrates_managed_legacy_learning_agent_uuid(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base: [{"id": _AGENT_UUID, "name": "resolved-name"}],
    )
    path = install.env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"HYPER_API_KEY=k\nHYPER_LEARNING_AGENT_ID={_AGENT_UUID}\n")

    install.install(validate=False)

    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME=resolved-name" in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env
    assert "HYPER_LEARNING_AGENT_ID" not in env

def test_reinstall_refreshes_stale_readonly_skill_purpose(_dirs) -> None:
    """A copied skill without --resolve-purpose must not stay that way after upgrade."""
    claude, _, _ = _dirs
    skill_path = claude / "skills" / "hyper-learning" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        "python3 -m hyperstruck.ide.hook prompt --readonly --emit text --goal \"$ARGUMENTS\"\n"
    )

    install.install(validate=False)

    refreshed = skill_path.read_text()
    assert "--readonly" in refreshed
    assert "--resolve-purpose agent_loop" in refreshed


def test_copy_skills_replaces_a_directory_symlink(tmp_path, monkeypatch) -> None:
    source = tmp_path / "bundled"
    skill = source / "hyper-learning"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("new")
    target_dir = tmp_path / "skills"
    linked = tmp_path / "linked-skill"
    linked.mkdir()
    (linked / "reference.md").write_text("stale")
    dest = target_dir / "hyper-learning"
    dest.parent.mkdir()
    dest.symlink_to(linked, target_is_directory=True)
    monkeypatch.setattr(install, "_skills_resource_dir", lambda: source)
    install._copy_skills(target_dir, install.Report())
    assert dest.is_dir()
    assert not dest.is_symlink()
    assert (dest / "SKILL.md").read_text() == "new"
    assert not (dest / "reference.md").exists()
    assert (linked / "reference.md").read_text() == "stale"


def test_ensure_durable_venv_creates_and_syncs(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    venv_dir = home / "venv"
    monkeypatch.setenv("HYPER_HOME", str(home))
    monkeypatch.setenv("HYPER_IDE_VENV", str(venv_dir))
    monkeypatch.setattr(install, "_ensure_durable_venv", _REAL_ENSURE_DURABLE_VENV)
    synced: list[Path] = []

    def fake_sync(report: install.Report, path: Path) -> None:
        synced.append(path)
        report.did(f"Installed hyperstruck into durable venv ({path})")

    monkeypatch.setattr(install, "_sync_package_into_venv", fake_sync)
    monkeypatch.setattr(install, "_durable_venv_importable", lambda report, path: True)
    report = install.Report()
    result = install._ensure_durable_venv(report)
    assert result is True
    assert install._venv_python(venv_dir).is_file()
    assert synced == [venv_dir]
    assert any("Created durable IDE venv" in a for a in report.actions)
