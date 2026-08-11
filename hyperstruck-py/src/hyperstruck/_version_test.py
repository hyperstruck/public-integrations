"""The version is declared twice, so the two declarations must not drift.

A bump applied to one and not the other is invisible to every test and to the
package's own behaviour, and surfaces only as a reinstall that silently does
nothing because pip already has that version.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from hyperstruck._version import __version__

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_declared_version_matches_the_packaging_metadata() -> None:
    with _PYPROJECT.open("rb") as handle:
        declared = tomllib.load(handle)["project"]["version"]
    assert declared == __version__
