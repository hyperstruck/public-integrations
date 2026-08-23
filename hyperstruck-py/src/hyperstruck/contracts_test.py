"""The vendored contracts parse, and say what the code that reads them expects."""

from __future__ import annotations

from pathlib import Path

import pytest

from hyperstruck.contracts import published_names


def test_a_contract_publishes_the_names_under_its_own_key(tmp_path: Path) -> None:
    contract = tmp_path / "c.json"
    contract.write_text('{"description": "why", "names": ["a", "b"]}')

    assert published_names(contract, "names") == {"a", "b"}


@pytest.mark.parametrize(
    "content",
    [
        None,
        "not json at all",
        '{"other_key": []}',
        '{"names": 7}',
        '{"names": "error_type"}',
        '{"names": {"error_type": true}}',
    ],
    ids=["absent", "corrupt", "wrong_key", "wrong_type", "string", "mapping"],
)
def test_an_unreadable_contract_publishes_nothing_rather_than_taking_the_turn_with_it(
    tmp_path: Path, content: str | None
) -> None:
    """These are read on the paths that finalise a turn, and the hook fails open by
    contract, so an exception here would lose the whole episode and surface nowhere.

    Empty is the safe degradation in both directions by construction: every caller asks
    "may I send this value", so an empty answer withholds it and keeps the behaviour the
    client had before the value existed.

    A string and a mapping are here because they are the shapes that do *not* raise:
    ``frozenset`` iterates them happily and yields characters or keys, which is non-empty
    and matches nothing, so the caller withholds every value and never learns why.
    """
    contract = tmp_path / "c.json"
    if content is not None:
        contract.write_text(content)

    assert published_names(contract, "names") == frozenset()
