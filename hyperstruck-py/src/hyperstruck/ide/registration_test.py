"""The registration store: what it translates, what it withholds, and what it forgets."""

from __future__ import annotations

import time

import pytest

from hyperstruck.ide import registration
from hyperstruck.ide.constants import (
    REGISTRATION_TTL_SECONDS,
    SOURCE_CLAUDE_CODE,
    STEP_KIND_ACT,
    STEP_KIND_READ,
)

SOURCE = SOURCE_CLAUDE_CODE


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))


class TestItTranslatesAndNeverInfers:
    @pytest.mark.parametrize(
        ("declaration", "expected"),
        [
            ({"annotations": {"readOnlyHint": True}}, STEP_KIND_READ),
            ({"annotations": {"readOnlyHint": False}}, STEP_KIND_ACT),
            ({"annotations": {"destructiveHint": True}}, STEP_KIND_ACT),
            ({"category": "read_only"}, STEP_KIND_READ),
            ({"category": "write"}, STEP_KIND_ACT),
            ({"category": "destructive"}, STEP_KIND_ACT),
            ({"category": "external"}, STEP_KIND_ACT),
            ({"category": "delegation"}, STEP_KIND_ACT),
            ({}, STEP_KIND_ACT),
        ],
    )
    def test_a_closed_vocabulary_maps_onto_a_closed_vocabulary(
        self, declaration: dict, expected: str
    ) -> None:
        """Read-only is the only verdict that takes a tool out of the material set, so it
        is the only thing asked about; everything else acts."""
        registration.register(SOURCE, [{"name": "t"} | declaration])

        assert registration.registered_kind(SOURCE, "t") == expected

    def test_an_act_is_never_recorded_as_a_command(self) -> None:
        """The execution oracle reads the trailing ``command`` step as the turn's verdict,
        and an unrelated API call is not a verdict on anything."""
        registration.register(SOURCE, [{"name": "mcp__slack__post"}])

        assert registration.registered_kind(SOURCE, "mcp__slack__post") != "command"

    def test_a_tool_with_no_name_is_not_recorded(self) -> None:
        registration.register(SOURCE, [{"annotations": {"readOnlyHint": True}}])

        assert registration.registered_kind(SOURCE, "") is None


class TestThePaletteIsAllOrNothing:
    def test_a_complete_registration_sends_the_palette(self) -> None:
        registration.register(
            SOURCE,
            [{"name": "mcp__docs__search", "annotations": {"readOnlyHint": True}}],
            declared_servers=["docs"],
            registered_servers=["docs"],
        )

        palette = registration.palette(SOURCE)

        assert palette is not None
        assert [tool.name for tool in palette] == ["mcp__docs__search"]
        assert palette[0].category == "read_only"

    def test_a_partial_registration_sends_nothing_and_keeps_its_verdicts(self) -> None:
        """A null palette fails open; a partial one is read as tools the agent lacks, so
        it suppresses exactly the MCP-targeted rules classification exists to earn."""
        registration.register(
            SOURCE,
            [{"name": "mcp__docs__search"}],
            declared_servers=["docs", "slack"],
            registered_servers=["docs"],
        )

        assert registration.palette(SOURCE) is None
        assert (
            registration.registered_kind(SOURCE, "mcp__docs__search") == STEP_KIND_ACT
        )

    def test_an_empty_tool_set_sends_nothing(self) -> None:
        """An empty list would reach the server as a run with no tools at all."""
        registration.register(SOURCE, [], declared_servers=[], registered_servers=[])

        assert registration.palette(SOURCE) is None

    def test_an_unregistered_host_sends_nothing(self) -> None:
        assert registration.palette("never-registered") is None
        assert registration.registered_kind("never-registered", "t") is None


class TestTheWindowShipsWhereverItIsKnown:
    def test_it_ships_even_when_the_palette_is_withheld(self) -> None:
        """It bounds how much comes back; it cannot make a rule ineligible."""
        registration.register(
            SOURCE,
            [{"name": "t"}],
            declared_servers=["docs", "slack"],
            registered_servers=["docs"],
            model_context_window=200_000,
        )

        assert registration.palette(SOURCE) is None
        assert registration.context_window(SOURCE) == 200_000

    @pytest.mark.parametrize("declared", [None, 0, -1, "200000"])
    def test_an_undeclared_window_stays_absent_rather_than_guessed(
        self, declared: object
    ) -> None:
        registration.register(SOURCE, [{"name": "t"}], model_context_window=declared)

        assert registration.context_window(SOURCE) is None


class TestAStaleRegistrationIsForgotten:
    def test_a_registration_past_its_ttl_says_nothing(self, monkeypatch) -> None:
        """A removed tool degrades safely, since unregistered already means material. A
        tool whose declaration changed is the residual risk, and this bounds it."""
        registration.register(
            SOURCE,
            [{"name": "t", "annotations": {"readOnlyHint": True}}],
            declared_servers=[],
            registered_servers=[],
            model_context_window=200_000,
        )
        expired = time.time() + REGISTRATION_TTL_SECONDS + 1
        monkeypatch.setattr(registration.time, "time", lambda: expired)

        assert registration.registered_kind(SOURCE, "t") is None
        assert registration.palette(SOURCE) is None
        assert registration.context_window(SOURCE) is None
