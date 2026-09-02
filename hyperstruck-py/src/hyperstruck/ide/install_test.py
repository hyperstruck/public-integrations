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
        "HYPER_SPACE_ID",
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
        "postToolUseFailure",
        "stop",
    }
    assert "--inject" in cursor_cfg["hooks"]["postToolUse"][0]["command"]
    assert "prompt" in cursor_cfg["hooks"]["beforeSubmitPrompt"][0]["command"]
    expected = _expected_hook_python(venv_dir)
    assert expected in cmds[0]
    assert sys.executable not in cmds[0]
    assert expected in cursor_cfg["hooks"]["beforeSubmitPrompt"][0]["command"]
    assert not (cursor / "rules" / "hyperstruck-learning.mdc").exists()


def test_claude_code_reports_its_session_start_so_a_compaction_opens_a_new_window(
    _dirs,
) -> None:
    claude, _, _ = _dirs
    install.install(validate=False)

    commands = _claude_cmds(claude, "SessionStart")

    assert len(commands) == 1
    parts = shlex.split(commands[0])
    assert parts[parts.index("-m") + 1 :] == [
        "hyperstruck.ide.hook",
        "session-start",
        "--source",
        "claude-code",
    ]


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
    assert len(claude_cmds) == 5
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


def test_claude_code_reports_a_failed_call_as_well_as_a_successful_one(_dirs) -> None:
    """Claude Code keeps a failed call for its own event; unregistered, it is never seen.

    Installed twice over settings that already hold someone else's hook on that event, to
    show an upgrade adds ours once and touches nothing it did not write.
    """
    claude, _, _ = _dirs
    theirs = {"matcher": "Bash", "hooks": [{"type": "command", "command": "their-hook"}]}
    (claude / "settings.json").write_text(
        json.dumps({"hooks": {"PostToolUseFailure": [theirs]}})
    )

    install.install(validate=False)
    install.install(validate=False)

    hooks = json.loads((claude / "settings.json").read_text())["hooks"]
    assert hooks["PostToolUseFailure"][0] == theirs
    (ours,) = hooks["PostToolUseFailure"][1:]
    assert ours["matcher"] == "*"
    assert ours["hooks"][0]["command"] == hooks["PostToolUse"][0]["hooks"][0]["command"]

    install.uninstall()
    assert _claude_cmds(claude, "PostToolUseFailure") == ["their-hook"]


def test_cursor_reports_a_failed_call_to_a_capture_hook(_dirs) -> None:
    """Cursor's shell capture has no exit status; its failure event is the only signal."""
    _, cursor, _ = _dirs

    install.install(validate=False)
    install.install(validate=False)

    hooks = json.loads((cursor / "hooks.json").read_text())["hooks"]
    (entry,) = hooks["postToolUseFailure"]
    assert "hyperstruck.ide.hook tool --source cursor" in entry["command"]
    assert "--inject" not in entry["command"]

    install.uninstall()
    hooks = json.loads((cursor / "hooks.json").read_text()).get("hooks", {})
    assert not hooks.get("postToolUseFailure")


def _older_cursor_install(cursor: Path) -> None:
    """A hooks file as an earlier client left it: shell capture wired beside someone else's."""
    install.install(validate=False)
    path = cursor / "hooks.json"
    config = json.loads(path.read_text())
    ours = config["hooks"]["postToolUseFailure"][0]["command"]
    config["hooks"]["afterShellExecution"] = [
        {"command": "their-audit-hook"},
        {"command": ours + " --kind command"},
    ]
    path.write_text(json.dumps(config))


def test_reinstalling_stops_capturing_cursor_shell_calls_from_the_shell_event(
    _dirs,
) -> None:
    """Shell calls are recorded from the tool events; a leftover entry would record nothing."""
    _, cursor, _ = _dirs
    _older_cursor_install(cursor)

    install.install(validate=False)

    hooks = json.loads((cursor / "hooks.json").read_text())["hooks"]
    assert hooks["afterShellExecution"] == [{"command": "their-audit-hook"}]


def test_uninstalling_an_older_cursor_install_removes_its_shell_capture(_dirs) -> None:
    _, cursor, _ = _dirs
    _older_cursor_install(cursor)

    install.uninstall()

    hooks = json.loads((cursor / "hooks.json").read_text())["hooks"]
    assert hooks["afterShellExecution"] == [{"command": "their-audit-hook"}]


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
        lambda key, base, **_kwargs: [{"id": _AGENT_UUID, "name": "only-agent"}],
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
        lambda key, base, **_kwargs: [
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
        lambda key, base, **_kwargs: [
            {"id": _AGENT_UUID, "name": "chosen"},
            {"id": "22222222-2222-4222-8222-222222222222", "name": "b"},
        ],
    )
    install.install(api_key="k", agent_name="chosen", validate=False)
    env = (install.env_file()).read_text()
    assert "HYPER_AGENT_NAME=chosen" in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env


def test_unverified_agent_name_not_persisted_when_missing_from_page(
    _dirs, monkeypatch
) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base, **_kwargs: [
            {"id": _AGENT_UUID, "name": "a"},
            {"id": "22222222-2222-4222-8222-222222222222", "name": "b"},
        ],
    )
    report = install.install(api_key="k", agent_name="chosen", validate=False)
    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME" not in env
    assert "HYPER_AGENT_ID" not in env
    assert any("No agent named 'chosen'" in warning for warning in report.warnings)


def test_agent_id_overwrites_stale_name(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base, **_kwargs: [{"id": _AGENT_UUID, "name": "a"}],
    )
    install.install(
        api_key="k",
        agent_name="chosen",
        agent_id=_AGENT_UUID,
        validate=False,
    )
    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME=a" in env
    assert "HYPER_AGENT_NAME=chosen" not in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env


def test_unverified_name_does_not_autowire_single_other_agent(
    _dirs, monkeypatch
) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base, **_kwargs: [{"id": _AGENT_UUID, "name": "a"}],
    )
    report = install.install(api_key="k", agent_name="chosen", validate=False)
    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME" not in env
    assert "HYPER_AGENT_ID" not in env
    assert any("No agent named 'chosen'" in warning for warning in report.warnings)


def test_explicit_agent_uuid_resolves_name(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(
        install,
        "_list_agents",
        lambda key, base, **_kwargs: [{"id": _AGENT_UUID, "name": "resolved-name"}],
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
        lambda key, base, **_kwargs: [{"id": _AGENT_UUID, "name": "resolved-name"}],
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
        lambda key, base, **_kwargs: [{"id": _AGENT_UUID, "name": "resolved-name"}],
    )
    path = install.env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"HYPER_API_KEY=k\nHYPER_LEARNING_AGENT_ID={_AGENT_UUID}\n")

    install.install(validate=False)

    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME=resolved-name" in env
    assert f"HYPER_AGENT_ID={_AGENT_UUID}" in env
    assert "HYPER_LEARNING_AGENT_ID" not in env


_SPACE_UUID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def test_space_id_is_persisted_and_passed_to_list(_dirs, monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _capture(key: str, base: str | None, **kwargs: object) -> list[dict[str, str]]:
        seen["key"] = key
        seen["base"] = base
        seen.update(kwargs)
        return [{"id": _AGENT_UUID, "name": "space-agent"}]

    monkeypatch.setattr(install, "_list_agents", _capture)
    install.install(api_key="k", space_id=_SPACE_UUID, validate=False)
    env = install.env_file().read_text()
    assert f"HYPER_SPACE_ID={_SPACE_UUID}" in env
    assert seen["space_id"] == _SPACE_UUID
    assert seen.get("q") is None


def test_space_id_from_env_narrows_name_lookup(_dirs, monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _capture(key: str, base: str | None, **kwargs: object) -> list[dict[str, str]]:
        seen.update(kwargs)
        return [{"id": _AGENT_UUID, "name": "chosen"}]

    monkeypatch.setattr(install, "_list_agents", _capture)
    monkeypatch.setenv("HYPER_SPACE_ID", _SPACE_UUID)
    install.install(api_key="k", agent_name="chosen", validate=False)
    assert seen["space_id"] == _SPACE_UUID
    assert seen["q"] == "chosen"
    assert f"HYPER_SPACE_ID={_SPACE_UUID}" in install.env_file().read_text()


def test_empty_space_list_warns(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(install, "_list_agents", lambda key, base, **_kwargs: [])
    report = install.install(api_key="k", space_id=_SPACE_UUID, validate=False)
    assert any("empty page" in warning for warning in report.warnings)
    assert f"HYPER_SPACE_ID={_SPACE_UUID}" in install.env_file().read_text()


def test_unverified_agent_name_not_persisted_on_empty_space(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(install, "_list_agents", lambda key, base, **_kwargs: [])
    report = install.install(
        api_key="k",
        agent_name="chosen",
        space_id=_SPACE_UUID,
        validate=False,
    )
    env = install.env_file().read_text()
    assert "HYPER_AGENT_NAME" not in env
    assert "HYPER_AGENT_ID" not in env
    assert f"HYPER_SPACE_ID={_SPACE_UUID}" in env
    assert any("No agent named 'chosen'" in warning for warning in report.warnings)


def test_list_failure_warns_and_is_not_an_empty_space(_dirs, monkeypatch) -> None:
    monkeypatch.setattr(install, "_list_agents", lambda key, base, **_kwargs: None)
    report = install.install(api_key="k", space_id=_SPACE_UUID, validate=False)
    assert any("Could not list agents" in warning for warning in report.warnings)
    assert not any("empty page" in warning for warning in report.warnings)


def test_invalid_space_id_is_ignored(_dirs, monkeypatch) -> None:
    seen: dict[str, object] = {}

    def _capture(key: str, base: str | None, **kwargs: object) -> list[dict[str, str]]:
        seen.update(kwargs)
        return [{"id": _AGENT_UUID, "name": "only-agent"}]

    monkeypatch.setattr(install, "_list_agents", _capture)
    report = install.install(api_key="k", space_id="not-a-uuid", validate=False)
    assert seen["space_id"] is None
    assert any("not a UUID" in warning for warning in report.warnings)
    assert "HYPER_SPACE_ID" not in install.env_file().read_text()


def test_invalid_space_id_in_env_file_is_removed(_dirs, monkeypatch) -> None:
    path = install.env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HYPER_API_KEY=k\nHYPER_SPACE_ID=not-a-uuid\n")
    seen: dict[str, object] = {}

    def _capture(key: str, base: str | None, **kwargs: object) -> list[dict[str, str]]:
        seen.update(kwargs)
        return [{"id": _AGENT_UUID, "name": "only-agent"}]

    monkeypatch.setattr(install, "_list_agents", _capture)
    report = install.install(validate=False)
    assert seen["space_id"] is None
    assert any("not a UUID" in warning for warning in report.warnings)
    assert "HYPER_SPACE_ID" not in path.read_text()


def test_list_agents_sends_space_id_and_q(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {"items": [{"id": _AGENT_UUID, "name": "chosen"}]}

    def _get(
        url: str,
        *,
        params: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> _Response:
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("httpx.get", _get)
    items = install._list_agents(
        "k",
        "https://api.example.test",
        space_id=_SPACE_UUID,
        q="chosen",
    )
    assert items == [{"id": _AGENT_UUID, "name": "chosen"}]
    assert captured["url"] == "https://api.example.test/agents"
    assert captured["params"] == {
        "limit": 50,
        "space_id": _SPACE_UUID,
        "q": "chosen",
    }


def test_list_agents_asks_for_test_agents_only_when_told_to(monkeypatch) -> None:
    sent: list[dict[str, object]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {"items": []}

    def _get(url: str, *, params: dict[str, object], **_kwargs: object) -> _Response:
        sent.append(params)
        return _Response()

    monkeypatch.setattr("httpx.get", _get)
    install._list_agents("k", "https://api.example.test")
    install._list_agents("k", "https://api.example.test", include_test=True)
    assert "test" not in sent[0]
    assert sent[1]["test"] == "include"


def test_an_explicit_agent_name_or_id_is_checked_against_test_agents_too(
    _dirs, monkeypatch
) -> None:
    seen: list[dict[str, object]] = []

    def _capture(key: str, base: str | None, **kwargs: object) -> list[dict[str, str]]:
        seen.append(kwargs)
        return [{"id": _AGENT_UUID, "name": "chosen"}]

    monkeypatch.setattr(install, "_list_agents", _capture)
    install.install(api_key="k", validate=False)
    install.install(api_key="k", agent_name="chosen", validate=False)
    install.install(api_key="k", agent_id=_AGENT_UUID, validate=False)
    assert [bool(kwargs.get("include_test")) for kwargs in seen] == [False, True, True]


def test_reinstall_refreshes_stale_readonly_skill_purpose(_dirs) -> None:
    """A copied skill without --resolve-purpose must not stay that way after upgrade."""
    claude, _, _ = _dirs
    skill_path = claude / "skills" / "hyper-learning" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        'python3 -m hyperstruck.ide.hook prompt --readonly --emit text --goal "$ARGUMENTS"\n'
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


def _real_durable_venv(tmp_path, monkeypatch) -> tuple[Path, install.Report]:
    venv_dir = tmp_path / "home" / "venv"
    monkeypatch.setattr(install, "_ensure_durable_venv", _REAL_ENSURE_DURABLE_VENV)
    monkeypatch.setattr(install, "_sync_package_into_venv", lambda report, path: None)
    monkeypatch.setattr(install, "_durable_venv_importable", lambda report, path: True)
    return venv_dir, install.Report()


def test_homebrew_cellar_base_maps_to_stable_opt_path(tmp_path) -> None:
    rest = Path("Frameworks/Python.framework/Versions/3.14/bin/python3.14")
    cellar = tmp_path / "Cellar" / "python@3.14" / "3.14.7" / rest
    opt = tmp_path / "opt" / "python@3.14" / rest
    cellar.parent.mkdir(parents=True)
    cellar.touch()
    opt.parent.mkdir(parents=True)
    opt.touch()
    assert install._stable_base_python(cellar) == opt

    opt.unlink()
    assert install._stable_base_python(cellar) == cellar
    plain = tmp_path / "usr" / "bin" / "python3"
    assert install._stable_base_python(plain) == plain


def test_ensure_durable_venv_builds_from_stable_base(tmp_path, monkeypatch) -> None:
    venv_dir, report = _real_durable_venv(tmp_path, monkeypatch)
    seen: list[Path] = []

    def stable(base: Path) -> Path:
        seen.append(base)
        return base

    monkeypatch.setattr(install, "_stable_base_python", stable)
    monkeypatch.setattr(sys, "_base_executable", sys.executable)
    assert install._ensure_durable_venv(report) is True
    assert seen == [Path(sys.executable)]
    assert install._interpreter_starts(install._venv_python(venv_dir))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell stub")
def test_broken_durable_venv_is_rebuilt_with_clear(tmp_path, monkeypatch) -> None:
    venv_dir, report = _real_durable_venv(tmp_path, monkeypatch)
    python = install._venv_python(venv_dir)
    python.parent.mkdir(parents=True)
    # Stands in for an interpreter whose Homebrew release was removed.
    python.write_text("#!/bin/sh\nexit 1\n")
    python.chmod(0o755)
    (venv_dir / "marker").write_text("stale")

    assert install._ensure_durable_venv(report) is True
    assert install._interpreter_starts(python)
    assert not (venv_dir / "marker").exists()
    assert any("Rebuilt durable IDE venv" in a for a in report.actions)
    home = next(
        line
        for line in (venv_dir / "pyvenv.cfg").read_text().splitlines()
        if line.startswith("home")
    )
    assert "/Cellar/" not in home
    for entry in python.parent.iterdir():
        if entry.is_symlink():
            assert "/Cellar/" not in str(entry.readlink())


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink")
def test_dangling_durable_python_link_is_rebuilt(tmp_path, monkeypatch) -> None:
    venv_dir, report = _real_durable_venv(tmp_path, monkeypatch)
    python = install._venv_python(venv_dir)
    python.parent.mkdir(parents=True)
    python.symlink_to(tmp_path / "removed" / "python3")

    assert install._ensure_durable_venv(report) is True
    assert install._interpreter_starts(python)
    assert any("Rebuilt durable IDE venv" in a for a in report.actions)


def test_healthy_durable_venv_is_left_alone(tmp_path, monkeypatch) -> None:
    venv_dir, report = _real_durable_venv(tmp_path, monkeypatch)
    assert install._ensure_durable_venv(report) is True
    (venv_dir / "marker").write_text("keep")

    again = install.Report()
    assert install._ensure_durable_venv(again) is True
    assert (venv_dir / "marker").read_text() == "keep"
    assert not any("durable IDE venv at" in a for a in again.actions)


def _wrapper(tmp_path: Path, name: str = "hyperstruck-learning-hook.sh") -> Path:
    """A person's own script that logs a failure and then runs the hook, as on a real machine."""
    script = tmp_path / name
    script.write_text(
        '#!/usr/bin/env bash\n"$PY" -P -m hyperstruck.ide.hook "$@" 2>"$err"\n'
    )
    script.chmod(0o755)
    return script


def _write_wrapped_settings(claude: Path, script: Path, **extra: list) -> None:
    def group(args: str, matcher: str | None = None) -> dict:
        entry = {"type": "command", "command": f"{script} {args}"}
        return {"hooks": [entry], **({"matcher": matcher} if matcher else {})}

    hooks = {
        "PostToolUse": [group("tool --source claude-code", "*")],
        "UserPromptSubmit": [group("prompt --source claude-code")],
        "Stop": [group("stop --source claude-code")],
    }
    for event, groups in extra.items():
        hooks[event] = hooks.get(event, []) + groups
    (claude / "settings.json").write_text(json.dumps({"hooks": hooks}))


def _all_commands(claude: Path) -> list[str]:
    hooks = json.loads((claude / "settings.json").read_text()).get("hooks", {})
    return [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]


def test_uninstall_removes_entries_that_run_our_hook_through_a_wrapper_script(
    _dirs, tmp_path
) -> None:
    """Only a script that runs our hook is ours; anything else beside it stays wired."""
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    audit = tmp_path / "audit.sh"
    audit.write_text("#!/bin/sh\nlogger stop\n")
    oversized = tmp_path / "oversized.sh"
    oversized.write_text("hyperstruck.ide.hook\n" + "#" * (64 * 1024))
    missing = tmp_path / "missing.sh"
    others = [f"{audit} stop", f"{oversized} stop", f"{missing} stop"]
    _write_wrapped_settings(
        claude,
        script,
        Stop=[{"hooks": [{"type": "command", "command": c}]} for c in others],
    )

    install.uninstall()

    assert _all_commands(claude) == others
    assert script.exists()


def _wired(claude: Path) -> dict:
    hooks = json.loads((claude / "settings.json").read_text())["hooks"]
    return {
        event: [(g.get("matcher"), [h["command"] for h in g["hooks"]]) for g in groups]
        for event, groups in hooks.items()
    }


def test_install_wires_every_claude_event_through_the_wrapper_it_finds(
    _dirs, tmp_path
) -> None:
    """The person's script stays in front of the hook, and every event the hook needs is there."""
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    _write_wrapped_settings(claude, script)

    install.install(validate=False)

    assert _wired(claude) == {
        "SessionStart": [(None, [f"{script} session-start --source claude-code"])],
        "UserPromptSubmit": [(None, [f"{script} prompt --source claude-code"])],
        "PostToolUse": [("*", [f"{script} tool --source claude-code"])],
        "PostToolUseFailure": [("*", [f"{script} tool --source claude-code"])],
        "Stop": [(None, [f"{script} stop --source claude-code"])],
    }


def test_installing_twice_through_a_wrapper_changes_nothing_the_second_time(
    _dirs, tmp_path
) -> None:
    claude, _, _ = _dirs
    _write_wrapped_settings(claude, _wrapper(tmp_path))
    install.install(validate=False)
    first = (claude / "settings.json").read_text()

    install.install(validate=False)

    assert (claude / "settings.json").read_text() == first


def test_a_foreign_entry_beside_the_wrapper_is_kept(_dirs, tmp_path) -> None:
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    audit = {"hooks": [{"type": "command", "command": "/usr/local/bin/audit stop"}]}
    _write_wrapped_settings(claude, script, Stop=[audit])

    install.install(validate=False)

    assert _wired(claude)["Stop"] == [
        (None, ["/usr/local/bin/audit stop"]),
        (None, [f"{script} stop --source claude-code"]),
    ]


def test_uninstall_after_a_wrapper_install_leaves_no_entry_of_ours(
    _dirs, tmp_path
) -> None:
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    _write_wrapped_settings(claude, script)
    install.install(validate=False)

    install.uninstall()

    assert _all_commands(claude) == []
    assert script.exists()


def test_a_wrapper_named_from_home_keeps_its_tilde(_dirs, tmp_path, monkeypatch) -> None:
    """The shell must still expand the path, so the tilde is written as the person wrote it."""
    claude, _, _ = _dirs
    monkeypatch.setenv("HOME", str(tmp_path))
    _wrapper(tmp_path)
    _write_wrapped_settings(claude, Path("~/hyperstruck-learning-hook.sh"))

    install.install(validate=False)

    assert _wired(claude)["PostToolUseFailure"] == [
        ("*", ["~/hyperstruck-learning-hook.sh tool --source claude-code"])
    ]


def test_the_report_names_the_wrapper_it_kept(_dirs, tmp_path) -> None:
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    _write_wrapped_settings(claude, script)

    report = install.install(validate=False)

    assert any(f"through your wrapper {script}" in a for a in report.actions)


def test_one_script_per_event_with_fixed_arguments_is_left_as_it_was(_dirs, tmp_path) -> None:
    """Such a script ignores what it is passed, so rewiring every event through one breaks them."""
    claude, _, _ = _dirs
    hooks = {}
    for event, sub in (("UserPromptSubmit", "prompt"), ("Stop", "stop"), ("PostToolUse", "tool")):
        script = tmp_path / f"{sub}.sh"
        script.write_text(f"#!/bin/sh\nexec py -P -m hyperstruck.ide.hook {sub} --source claude-code\n")
        hooks[event] = [{"hooks": [{"type": "command", "command": str(script)}]}]
    (claude / "settings.json").write_text(json.dumps({"hooks": hooks}))
    before = (claude / "settings.json").read_text()

    report = install.install(validate=False)

    assert (claude / "settings.json").read_text() == before
    assert any(
        all(f"{sub}.sh" in w for sub in ("prompt", "stop", "tool")) for w in report.warnings
    )


def test_two_different_wrappers_are_left_as_they_were(_dirs, tmp_path) -> None:
    claude, _, _ = _dirs
    first = _wrapper(tmp_path, "logs.sh")
    second = _wrapper(tmp_path, "audits.sh")
    _write_wrapped_settings(
        claude,
        first,
        Stop=[{"hooks": [{"type": "command", "command": f"{second} stop --source claude-code"}]}],
    )
    before = (claude / "settings.json").read_text()

    report = install.install(validate=False)

    assert (claude / "settings.json").read_text() == before
    assert any(str(first) in w and str(second) in w for w in report.warnings)


def test_the_wrapper_is_written_back_in_the_persons_own_words(_dirs, tmp_path) -> None:
    claude, _, _ = _dirs
    folder = tmp_path / "my hooks"
    folder.mkdir()
    _wrapper(folder)
    _write_wrapped_settings(claude, Path(f'"{folder}/hyperstruck-learning-hook.sh"'))

    install.install(validate=False)

    assert _wired(claude)["Stop"] == [
        (None, [f'"{folder}/hyperstruck-learning-hook.sh" stop --source claude-code'])
    ]


@pytest.mark.parametrize(
    "prefix",
    [
        '"$HOME"/hyperstruck-learning-hook.sh',
        "LOG=1 {home}/hyperstruck-learning-hook.sh",
        "bash {home}/hyperstruck-learning-hook.sh",
    ],
)
def test_a_wrapper_named_the_way_a_shell_reads_it_is_kept_word_for_word(
    _dirs, tmp_path, monkeypatch, prefix
) -> None:
    claude, _, _ = _dirs
    monkeypatch.setenv("HOME", str(tmp_path))
    _wrapper(tmp_path)
    written = prefix.format(home=tmp_path)
    _write_wrapped_settings(claude, Path(written))

    install.install(validate=False)

    assert _wired(claude)["PostToolUseFailure"] == [
        ("*", [f"{written} tool --source claude-code"])
    ]


def test_a_wrapper_named_by_a_bare_word_on_path_is_recognised(_dirs, tmp_path, monkeypatch) -> None:
    claude, _, _ = _dirs
    _wrapper(tmp_path, "hyper-hook")
    monkeypatch.setenv("PATH", f"{tmp_path}:{__import__('os').environ['PATH']}")
    _write_wrapped_settings(claude, Path("hyper-hook"))

    install.install(validate=False)

    assert _wired(claude)["SessionStart"] == [
        (None, ["hyper-hook session-start --source claude-code"])
    ]


def test_a_single_script_with_fixed_arguments_is_left_as_it_was(_dirs, tmp_path) -> None:
    claude, _, _ = _dirs
    script = tmp_path / "tool.sh"
    script.write_text("#!/bin/sh\nexec py -P -m hyperstruck.ide.hook tool --source claude-code\n")
    group = {"matcher": "*", "hooks": [{"type": "command", "command": str(script)}]}
    (claude / "settings.json").write_text(json.dumps({"hooks": {"PostToolUse": [group]}}))
    before = (claude / "settings.json").read_text()

    report = install.install(validate=False)

    assert (claude / "settings.json").read_text() == before
    assert any(str(script) in w for w in report.warnings)


@pytest.mark.parametrize(
    "mention", ['echo "$(date) $@" >> "$HOME/hook.log"', "# usage: prompt.sh $@"]
)
def test_a_fixed_script_that_only_mentions_its_arguments_elsewhere_is_left_as_it_was(
    _dirs, tmp_path, mention
) -> None:
    claude, _, _ = _dirs
    script = tmp_path / "prompt.sh"
    script.write_text(
        f"#!/bin/sh\n{mention}\nexec py -P -m hyperstruck.ide.hook prompt --source claude-code\n"
    )
    command = f"{script} prompt --source claude-code"
    group = {"hooks": [{"type": "command", "command": command}]}
    (claude / "settings.json").write_text(json.dumps({"hooks": {"UserPromptSubmit": [group]}}))
    before = (claude / "settings.json").read_text()

    install.install(validate=False)

    assert (claude / "settings.json").read_text() == before


def test_a_foreign_entry_under_an_unknown_users_home_is_left_alone(_dirs) -> None:
    """Resolving ``~name/`` for a user who does not exist must not stop install or uninstall."""
    claude, _, _ = _dirs
    foreign = "~nosuchuser-hyperstruck-test/bin/notify.sh stop"
    group = {"hooks": [{"type": "command", "command": foreign}]}
    (claude / "settings.json").write_text(json.dumps({"hooks": {"Stop": [group]}}))

    install.install(validate=False)
    assert foreign in _all_commands(claude)

    install.uninstall()
    assert _all_commands(claude) == [foreign]


def test_a_wrapper_option_named_like_a_hook_event_stays_part_of_the_wrapper(
    _dirs, tmp_path
) -> None:
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    _write_wrapped_settings(claude, Path(f"{script} --mode tool"))

    install.install(validate=False)

    assert _wired(claude)["Stop"] == [
        (None, [f"{script} --mode tool stop --source claude-code"])
    ]


def test_a_wrapper_wired_without_the_hooks_arguments_is_left_as_it_was(_dirs, tmp_path) -> None:
    """Where its own words end cannot be told, so nothing is rewritten around a guess."""
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    group = {"hooks": [{"type": "command", "command": f"LOG=1 bash {script}"}]}
    (claude / "settings.json").write_text(json.dumps({"hooks": {"Stop": [group]}}))
    before = (claude / "settings.json").read_text()

    report = install.install(validate=False)

    assert (claude / "settings.json").read_text() == before
    assert any(str(script) in w for w in report.warnings)


def _shared_group_settings(claude: Path, script: Path) -> None:
    """A person's own command and the wrapper written into one group, by hand."""
    group = {
        "matcher": "Bash",
        "hooks": [
            {"type": "command", "command": "/usr/local/bin/lint.sh"},
            {"type": "command", "command": f"{script} tool --source claude-code"},
        ],
    }
    (claude / "settings.json").write_text(json.dumps({"hooks": {"PostToolUse": [group]}}))


def test_install_keeps_a_persons_command_that_shares_the_wrappers_group(_dirs, tmp_path) -> None:
    claude, _, _ = _dirs
    script = _wrapper(tmp_path)
    _shared_group_settings(claude, script)

    install.install(validate=False)

    assert _wired(claude)["PostToolUse"] == [
        ("Bash", ["/usr/local/bin/lint.sh"]),
        ("*", [f"{script} tool --source claude-code"]),
    ]


def test_uninstall_keeps_a_persons_command_that_shares_the_wrappers_group(
    _dirs, tmp_path
) -> None:
    claude, _, _ = _dirs
    _shared_group_settings(claude, _wrapper(tmp_path))

    install.uninstall()

    assert _wired(claude)["PostToolUse"] == [("Bash", ["/usr/local/bin/lint.sh"])]
