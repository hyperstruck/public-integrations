"""The vendored contracts parse, and say what the code that reads them expects."""

from __future__ import annotations

import json

from pathlib import Path

import pytest

from hyperstruck.contracts import published_names, published_shape
from hyperstruck.ide.debug import debug as hook_debug


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


class TestPublishedShape:
    """The scalar-constraint sibling of :func:`published_names`.

    Its degradation matters more than its happy path. Every caller asks "how must I bound
    this value before sending it", so an empty answer has to make the caller withhold. A
    caller that read a missing bound as "no bound" would turn a packaging fault into the
    leak the bound exists to prevent.
    """

    def test_the_published_constraints_are_read(self, tmp_path) -> None:
        contract = tmp_path / "c.json"
        contract.write_text(
            json.dumps({"operand_shape": {"max_words": 8, "word_pattern": "^a$"}})
        )

        assert published_shape(contract, "operand_shape") == {
            "max_words": 8,
            "word_pattern": "^a$",
        }

    @pytest.mark.parametrize(
        "content",
        [
            '{"operand_shape": []}',
            '{"operand_shape": "eight"}',
            '{"other": {}}',
            "not json",
        ],
        ids=["a_list", "a_string", "a_missing_key", "unparseable"],
    )
    def test_anything_that_is_not_a_mapping_yields_empty(
        self, tmp_path, content: str
    ) -> None:
        contract = tmp_path / "c.json"
        contract.write_text(content)

        assert published_shape(contract, "operand_shape") == {}

    def test_a_missing_file_yields_empty_rather_than_raising(self, tmp_path) -> None:
        """These are read on the paths that finalise a turn, inside a hook that fails open
        by contract, so an exception would surface nowhere at all."""
        assert published_shape(tmp_path / "absent.json", "operand_shape") == {}

    def test_a_non_scalar_member_is_dropped_rather_than_passed_through(
        self, tmp_path
    ) -> None:
        """A caller compiling a pattern or comparing a length against a nested object
        raises, and raises in the same place nothing can see it."""
        contract = tmp_path / "c.json"
        contract.write_text(
            json.dumps(
                {"operand_shape": {"max_words": 8, "nested": {"a": 1}, "list": [1]}}
            )
        )

        assert published_shape(contract, "operand_shape") == {"max_words": 8}


def test_the_neutral_layers_breadcrumb_is_not_tagged_as_the_hooks(
    monkeypatch, capsys, tmp_path
) -> None:
    """The channel is the whole reason the diagnostic moved out of the IDE package.

    A LangGraph host reading ``[hyperstruck-hook]`` against a contract it degraded goes
    looking for an editor hook it never installed, which is the state the move fixed and
    which nothing else here would notice.
    """
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
    contract = tmp_path / "c.json"
    contract.write_text("not json at all")

    assert published_shape(contract, "operand_shape") == {}
    written = capsys.readouterr().err
    assert "[hyperstruck]" in written
    assert "[hyperstruck-hook]" not in written


def test_the_hooks_breadcrumb_stays_tagged_as_the_hooks(monkeypatch, capsys) -> None:
    """The other half of the same split: moving the primitive must not relabel the hook."""
    monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")

    hook_debug("a hook breadcrumb")

    assert "[hyperstruck-hook]" in capsys.readouterr().err
