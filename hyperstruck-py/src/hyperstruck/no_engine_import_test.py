"""The public package must never import the engine.

A clean install of ``hyperstruck`` (and the LangGraph host) must pull in zero
``hyperstruck_core`` modules: the learning logic lives on the platform, and the
package is a thin client.
"""

from __future__ import annotations

import sys


def test_importing_hyperstruck_does_not_import_core() -> None:
    # Drop any engine modules a sibling test may have imported.
    for name in list(sys.modules):
        if name == "hyperstruck_core" or name.startswith("hyperstruck_core."):
            del sys.modules[name]

    import hyperstruck  # noqa: F401
    import hyperstruck.langgraph  # noqa: F401

    leaked = [name for name in sys.modules if name == "hyperstruck_core" or name.startswith("hyperstruck_core.")]
    assert leaked == [], f"public package imported engine modules: {leaked}"
