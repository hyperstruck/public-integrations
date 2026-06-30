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
