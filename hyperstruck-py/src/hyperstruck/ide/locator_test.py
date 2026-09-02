"""The client's locator builder against its own vendored golden cases.

Cross-checked against the pinned Core install directly in
``api/locator_client_parity_test.py`` (core-platform only, since this package cannot
depend on Core); this file is what ships and runs wherever the client itself is tested.
"""

from __future__ import annotations

import json
from pathlib import Path

from hyperstruck.ide import locator

_CASES = json.loads((Path(__file__).parent / "locator_golden_cases.json").read_text())


def test_every_golden_case() -> None:
    for case in _CASES:
        got = locator.locator_from_parts(
            case["remote"], case["commit"], case["tree"], case["path"], max_chars=case["max_chars"]
        )
        assert got == case["expected"], case["name"]


def test_credentials_never_reach_the_locator() -> None:
    got = locator.locator_from_parts("https://user:s3cr3t@github.com/acme/api.git", "a" * 40)
    assert got is not None
    assert "s3cr3t" not in got
    assert "user" not in got
