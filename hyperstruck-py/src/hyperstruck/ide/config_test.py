"""Auth/config loading and ambient-agent resolution."""

from __future__ import annotations

import pytest

from hyperstruck.ide import config
from hyperstruck.ide.constants import env_file


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))
    for var in (
        "HYPER_API_KEY",
        "HYPER_BASE_URL",
        "HYPER_AGENT_ID",
        "HYPER_LEARNING_AGENT_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_load_env_populates_missing(monkeypatch) -> None:
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "HYPER_API_KEY=secret\nHYPER_AGENT_ID=agent-x\n# a comment\n", encoding="utf-8"
    )
    config.load_env()
    import os

    assert os.environ["HYPER_API_KEY"] == "secret"
    assert os.environ["HYPER_AGENT_ID"] == "agent-x"


def test_load_env_does_not_override_real_env(monkeypatch) -> None:
    monkeypatch.setenv("HYPER_AGENT_ID", "from-shell")
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HYPER_AGENT_ID=from-file\n", encoding="utf-8")
    config.load_env()
    import os

    assert os.environ["HYPER_AGENT_ID"] == "from-shell"


def test_configured_agent_id_precedence(monkeypatch) -> None:
    assert config.configured_agent_id() is None
    monkeypatch.setenv("HYPER_AGENT_ID", "pinned")
    assert config.configured_agent_id() == "pinned"
    monkeypatch.setenv("HYPER_LEARNING_AGENT_ID", "loop-specific")
    assert config.configured_agent_id() == "loop-specific"
