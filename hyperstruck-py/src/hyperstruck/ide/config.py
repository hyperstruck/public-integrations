"""Auth/config loading and ambient-agent resolution for the IDE loop.

The agent a turn reads from and writes to is the *customer's configured agent*,
not anything derived from the git repo: Claude Code and Cursor are general agent
platforms, so binding identity to a repo would be too narrow. Selection is
dynamic where an LLM can do it (the skills list the customer's agents and pick the
one fitting the task) and deterministic where it cannot (the ambient hook reads a
single configured agent). The installer resolves that ambient agent once, so the
hot path is a cheap env read.
"""

from __future__ import annotations

import os

from hyperstruck.ide.constants import AGENT_ID_ENV_VARS, env_file

_API_KEY_VARS = ("HYPER_API_KEY", "HYPERSTRUCK_API_KEY")
_BASE_URL_VARS = ("HYPER_BASE_URL", "HYPERSTRUCK_BASE_URL")
_TIMEOUT_VARS = ("HYPER_RESOLVE_TIMEOUT", "HYPER_WRITE_TIMEOUT")
_LOADABLE = (*AGENT_ID_ENV_VARS, *_API_KEY_VARS, *_BASE_URL_VARS, *_TIMEOUT_VARS)


def load_env() -> None:
    """Load ``~/.hyperstruck/.env`` into ``os.environ`` without overriding it.

    A hook process does not inherit the user's shell dotenv, so the loop's auth
    and configured agent live in this file and are loaded at hook start. A value
    already present in the real environment wins, so an explicit export is never
    clobbered.
    """
    path = env_file()
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in _LOADABLE and not os.environ.get(key):
            os.environ[key] = value.strip()


def configured_agent_id() -> str | None:
    """The ambient loop's agent id from the environment, or ``None`` if unset.

    ``None`` means the loop has no agent to learn into (no configured default and
    not a single-agent tenant), so the hook fails open and does nothing until the
    installer or the user sets one. The skills still select an agent per task.
    """
    for var in AGENT_ID_ENV_VARS:
        value = (os.environ.get(var) or "").strip()
        if value:
            return value
    return None
