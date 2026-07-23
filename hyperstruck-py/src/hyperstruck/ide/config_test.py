"""Auth/config loading and ambient-agent resolution."""

from __future__ import annotations

import os

import pytest

from hyperstruck.ide import config
from hyperstruck.ide.constants import env_file


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))
    for var in (
        "HYPER_API_KEY",
        "HYPER_BASE_URL",
        "HYPER_AGENT_NAME",
        "HYPER_AGENT_ID",
        "HYPER_LEARNING_AGENT_NAME",
        "HYPER_LEARNING_AGENT_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_load_env_populates_missing(monkeypatch) -> None:
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "HYPER_API_KEY=secret\nHYPER_AGENT_NAME=agent-x\n# a comment\n",
        encoding="utf-8",
    )
    config.load_env()
    assert os.environ["HYPER_API_KEY"] == "secret"
    assert os.environ["HYPER_AGENT_NAME"] == "agent-x"


def test_load_env_migrates_legacy_name_pin(monkeypatch) -> None:
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HYPER_AGENT_ID=agent-x\n", encoding="utf-8")
    config.load_env()
    assert os.environ["HYPER_AGENT_NAME"] == "agent-x"
    assert "HYPER_AGENT_ID" not in os.environ


def test_load_env_keeps_uuid_as_rest_id(monkeypatch) -> None:
    agent_uuid = "11111111-1111-4111-8111-111111111111"
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"HYPER_AGENT_ID={agent_uuid}\n", encoding="utf-8")
    config.load_env()
    assert os.environ["HYPER_AGENT_ID"] == agent_uuid
    assert os.environ.get("HYPER_AGENT_NAME") is None


def test_load_env_migrates_legacy_learning_uuid_as_rest_id(monkeypatch) -> None:
    agent_uuid = "11111111-1111-4111-8111-111111111111"
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"HYPER_LEARNING_AGENT_ID={agent_uuid}\n", encoding="utf-8")
    config.load_env()
    assert os.environ["HYPER_AGENT_ID"] == agent_uuid
    assert os.environ.get("HYPER_AGENT_NAME") is None


def test_load_env_does_not_override_real_env(monkeypatch) -> None:
    monkeypatch.setenv("HYPER_AGENT_NAME", "from-shell")
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HYPER_AGENT_NAME=from-file\n", encoding="utf-8")
    config.load_env()
    assert os.environ["HYPER_AGENT_NAME"] == "from-shell"


def test_configured_agent_name_precedence(monkeypatch) -> None:
    assert config.configured_agent_name() is None
    monkeypatch.setenv("HYPER_AGENT_NAME", "pinned")
    assert config.configured_agent_name() == "pinned"
    monkeypatch.setenv("HYPER_LEARNING_AGENT_NAME", "loop-specific")
    assert config.configured_agent_name() == "loop-specific"


def test_configured_agent_id_requires_uuid(monkeypatch) -> None:
    assert config.configured_agent_id() is None
    monkeypatch.setenv("HYPER_AGENT_ID", "not-a-uuid")
    assert config.configured_agent_id() is None
    agent_uuid = "22222222-2222-4222-8222-222222222222"
    monkeypatch.setenv("HYPER_AGENT_ID", agent_uuid)
    assert config.configured_agent_id() == agent_uuid
