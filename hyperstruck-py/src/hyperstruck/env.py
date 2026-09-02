"""Shared environment-variable resolution for the package.

The API key and base URL are read from the same env vars by the client, the MCP
credential seam, the CLI, and the server config, so the variable names and the
"first non-empty wins" lookup live here once rather than being reinvented in each.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

# The env vars the API key and base URL are read from (HYPER_* are legacy aliases).
API_KEY_ENV_VARS = ("HYPERSTRUCK_API_KEY", "HYPER_API_KEY")
BASE_URL_ENV_VARS = ("HYPERSTRUCK_BASE_URL", "HYPER_BASE_URL")

# Here rather than beside the client so a caller can read a deadline without
# importing the httpx-backed client module.
RESOLVE_TIMEOUT_ENV = "HYPER_RESOLVE_TIMEOUT"
WRITE_TIMEOUT_ENV = "HYPER_WRITE_TIMEOUT"

# The one switch for every diagnostic channel. Off by default so the hook loop stays silent
# and fails open; on, it lets a user tell "hook never fired" apart from "fired but no agent
# / empty resolve / network down", which otherwise all produce identical empty output. The
# name still says HOOK because it is what users already set and what the install docs carry;
# renaming it would silence them.
DEBUG_ENV = "HYPER_HOOK_DEBUG"

# Values of DEBUG_ENV that count as "off" (anything else enables debug).
DEBUG_OFF_VALUES = frozenset({"", "0", "false", "no", "off"})


def first_env(
    names: Sequence[str], env: Mapping[str, str] | None = None
) -> str | None:
    """Return the value of the first set, non-empty variable in ``names``."""
    environ = env if env is not None else os.environ
    for name in names:
        value = environ.get(name)
        if value:
            return value
    return None


def env_float(name: str, default: float) -> float:
    """Return ``name`` parsed as a float, falling back to ``default``.

    An unset, empty or unparseable value yields the default rather than raising:
    a malformed deadline must not stop a host from starting.
    """
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
