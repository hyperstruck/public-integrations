"""Auth/config loading and ambient-agent resolution for the IDE loop.

The agent a turn reads from and writes to is the *customer's configured agent
name* for the learning boundary, not anything derived from the git repo. REST
skills that call ``/agents/{agent_id}/...`` use ``HYPER_AGENT_ID`` (hosted agent
UUID) instead — see :func:`configured_agent_id`.

Selection is dynamic where an LLM can do it (the skills list agents and pick the
one fitting the task) and deterministic where it cannot (the ambient hook reads
``HYPER_AGENT_NAME``). The installer resolves both name and UUID once when
possible, so the hot path is a cheap env read.
"""

from __future__ import annotations

import os
from uuid import UUID

from hyperstruck.ide.constants import (
    AGENT_ID_ENV_VARS,
    AGENT_NAME_ENV_VARS,
    env_file,
)

_API_KEY_VARS = ("HYPER_API_KEY", "HYPERSTRUCK_API_KEY")
_BASE_URL_VARS = ("HYPER_BASE_URL", "HYPERSTRUCK_BASE_URL")
_TIMEOUT_VARS = ("HYPER_RESOLVE_TIMEOUT", "HYPER_WRITE_TIMEOUT")
_LOADABLE = (
    *AGENT_NAME_ENV_VARS,
    *AGENT_ID_ENV_VARS,
    *_API_KEY_VARS,
    *_BASE_URL_VARS,
    *_TIMEOUT_VARS,
)

# Legacy single var: if it holds a UUID it maps to HYPER_AGENT_ID; otherwise to name.
_LEGACY_AGENT_ENV = "HYPER_AGENT_ID"
_LEGACY_LOOP_AGENT_ENV = "HYPER_LEARNING_AGENT_ID"


def _looks_like_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _parse_env_value(value: str) -> str:
    """Parse a dotenv RHS: strip quotes and trailing inline comments.

    Hand-authored ``.env`` files often wrap secrets as ``KEY="value"`` or add
    ``KEY="value" # note``. Leaving quotes or comment text in the Bearer token
    yields HTTP 401 Invalid API key from Core. Quoted content keeps interior
    ``#``; unquoted values trim at the first whitespace-hash comment marker.
    """
    value = value.strip()
    if not value:
        return value
    if value[0] in "\"'":
        quote = value[0]
        end = value.find(quote, 1)
        if end != -1:
            return value[1:end]
        return value
    comment_at = value.find(" #")
    if comment_at != -1:
        return value[:comment_at].rstrip()
    return value


def load_env() -> None:
    """Load ``~/.hyperstruck/.env`` into ``os.environ`` without overriding it.

    A hook process does not inherit the user's shell dotenv, so the loop's auth
    and configured agent live in this file and are loaded at hook start. A value
    already present in the real environment wins, so an explicit export is never
    clobbered. Legacy ``HYPER_AGENT_ID`` / ``HYPER_LEARNING_AGENT_ID`` values are
    split into ``HYPER_AGENT_NAME`` vs ``HYPER_AGENT_ID`` when unambiguous.
    Values are parsed dotenv-style (strip surrounding quotes and trailing
    `` #`` comments).
    """
    path = env_file()
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    parsed: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed[key.strip()] = _parse_env_value(value)
    _apply_legacy_agent_env(parsed)
    for key, value in parsed.items():
        if key in _LOADABLE and not os.environ.get(key):
            os.environ[key] = value


def _apply_legacy_agent_env(parsed: dict[str, str]) -> None:
    """Map deprecated env keys onto ``HYPER_AGENT_NAME`` / ``HYPER_AGENT_ID``."""
    loop_legacy = parsed.pop(_LEGACY_LOOP_AGENT_ENV, None)
    if loop_legacy:
        if _looks_like_uuid(loop_legacy):
            parsed.setdefault("HYPER_AGENT_ID", loop_legacy)
        elif "HYPER_AGENT_NAME" not in parsed:
            parsed["HYPER_AGENT_NAME"] = loop_legacy

    single_legacy = parsed.get(_LEGACY_AGENT_ENV)
    if not single_legacy:
        return
    if "HYPER_AGENT_NAME" not in parsed and not _looks_like_uuid(single_legacy):
        parsed["HYPER_AGENT_NAME"] = single_legacy
        parsed.pop(_LEGACY_AGENT_ENV, None)
    elif "HYPER_AGENT_ID" not in parsed and _looks_like_uuid(single_legacy):
        parsed["HYPER_AGENT_ID"] = single_legacy


def configured_agent_name() -> str | None:
    """The ambient loop's boundary agent **name**, or ``None`` if unset."""
    for var in AGENT_NAME_ENV_VARS:
        value = (os.environ.get(var) or "").strip()
        if value:
            return value
    return None


def configured_agent_id() -> str | None:
    """The hosted agent **UUID** for REST skill calls, or ``None`` if unset."""
    for var in AGENT_ID_ENV_VARS:
        value = (os.environ.get(var) or "").strip()
        if value and _looks_like_uuid(value):
            return value
    return None
