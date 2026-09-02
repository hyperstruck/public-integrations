"""The public package must never import the engine, and its neutral half never the IDE.

A clean install of ``hyperstruck`` (and the LangGraph host) must pull in zero
``hyperstruck_core`` modules: the learning logic lives on the platform, and the
package is a thin client.

The second direction matters for the same reason and was not pinned: the vendored
contract reader is framework-neutral and is read by every host, so an import reaching
down into the editor hook makes a LangGraph user carry the hook and takes its
diagnostics' labelling with it.
"""

from __future__ import annotations

import sys


def test_importing_hyperstruck_does_not_import_core() -> None:
    # Drop any engine modules a sibling test may have imported.
    for name in list(sys.modules):
        if name == "hyperstruck_core" or name.startswith("hyperstruck_core."):
            del sys.modules[name]

    import hyperstruck  # noqa: F401
    import hyperstruck.ide  # noqa: F401
    import hyperstruck.ide.hook  # noqa: F401
    import hyperstruck.ide.install  # noqa: F401
    import hyperstruck.langgraph  # noqa: F401

    leaked = [
        name
        for name in sys.modules
        if name == "hyperstruck_core" or name.startswith("hyperstruck_core.")
    ]
    assert leaked == [], f"public package imported engine modules: {leaked}"


def test_the_neutral_layer_does_not_import_the_ide_adapter() -> None:
    # Snapshot and restore: a sibling test imports inside its body and compares enum
    # members with `is`, so leaving fresh module objects behind reddens it under any
    # collection order but the alphabetical one that happens to run ide/ first.
    saved = dict(sys.modules)
    try:
        for name in list(sys.modules):
            if name == "hyperstruck" or name.startswith("hyperstruck."):
                del sys.modules[name]

        import hyperstruck.contracts  # noqa: F401
        import hyperstruck.langgraph  # noqa: F401

        leaked = [
            name
            for name in sys.modules
            if name == "hyperstruck.ide" or name.startswith("hyperstruck.ide.")
        ]
    finally:
        sys.modules.clear()
        sys.modules.update(saved)
    assert leaked == [], f"the framework-neutral layer imported the IDE adapter: {leaked}"
