"""Informative-turn gating and tool classification."""

from __future__ import annotations

import pytest

from hyperstruck.ide import registration
from hyperstruck.ide.constants import (
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    STEP_KIND_ACT,
    STEP_KIND_COMMAND,
    STEP_KIND_EDIT,
    STEP_KIND_READ,
)
from hyperstruck.ide.gating import classify_tool, recovered_from_failure, should_observe


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))


class TestClassificationAsksDeclarationsAndNeverGuesses:
    @pytest.mark.parametrize(
        ("source", "name", "expected"),
        [
            (SOURCE_CLAUDE_CODE, "Bash", STEP_KIND_COMMAND),
            (SOURCE_CLAUDE_CODE, "Edit", STEP_KIND_EDIT),
            (SOURCE_CLAUDE_CODE, "Read", STEP_KIND_READ),
            (SOURCE_CURSOR, "run_terminal_cmd", STEP_KIND_COMMAND),
            (SOURCE_CURSOR, "edit_file", STEP_KIND_EDIT),
            (SOURCE_CURSOR, "read_file", STEP_KIND_READ),
        ],
    )
    def test_a_hosts_own_tool_takes_the_kind_that_host_declares(
        self, source: str, name: str, expected: str
    ) -> None:
        assert classify_tool(name, source) == expected

    def test_a_registered_tool_takes_its_stored_verdict(self) -> None:
        """Judged once out of band, because a tool event carries no annotations and every
        hook is a fresh subprocess."""
        registration.register(
            SOURCE_CLAUDE_CODE,
            [
                {"name": "mcp__docs__search", "annotations": {"readOnlyHint": True}},
                {"name": "mcp__slack__post", "annotations": {"readOnlyHint": False}},
            ],
        )

        assert classify_tool("mcp__docs__search", SOURCE_CLAUDE_CODE) == STEP_KIND_READ
        assert classify_tool("mcp__slack__post", SOURCE_CLAUDE_CODE) == STEP_KIND_ACT

    def test_the_hosts_own_declaration_outranks_a_stored_verdict(self) -> None:
        """A host event knows its own tool; a registration is a snapshot that can age."""
        registration.register(
            SOURCE_CLAUDE_CODE,
            [{"name": "Bash", "annotations": {"readOnlyHint": True}}],
        )

        assert classify_tool("Bash", SOURCE_CLAUDE_CODE) == STEP_KIND_COMMAND

    def test_an_unknown_tool_is_material_rather_than_read_only(self) -> None:
        """The reversal that is the point of the item.

        The critic and the spend cap backstop over-inclusion; nothing backstops
        over-exclusion, and a registration gap is invisible. Under the old default every
        MCP tool fell to a kind the observe gate refuses.
        """
        assert classify_tool("mystery_tool", SOURCE_CLAUDE_CODE) == STEP_KIND_ACT
        assert classify_tool("mcp__anything__at_all") == STEP_KIND_ACT
        assert classify_tool(None) == STEP_KIND_ACT

    def test_an_undeclared_host_says_nothing_about_another_hosts_tools(self) -> None:
        """Abstain on undeclared, like the status vocabularies: inheriting is the cliff."""
        assert classify_tool("Bash", "some-other-editor") == STEP_KIND_ACT

    def test_a_lookup_miss_performs_no_work(self, monkeypatch) -> None:
        """It runs once per tool call inside the editor's hook, in a fresh subprocess."""
        monkeypatch.setattr(
            registration,
            "register",
            lambda *_a, **_k: pytest.fail("classification triggered a registration"),
        )

        assert classify_tool("never_seen", SOURCE_CLAUDE_CODE) == STEP_KIND_ACT


def _step(kind: str, status: str = "completed") -> dict:
    return {"kind": kind, "status": status}


def test_should_observe_material_threshold() -> None:
    assert should_observe([_step("edit"), _step("command")]) is True
    assert (
        should_observe([_step("edit")]) is False
    )  # one material step is below the gate
    assert should_observe([_step("read"), _step("read")]) is False
    assert should_observe([]) is False


def test_should_observe_failure_recovery_always() -> None:
    steps = [_step("command", "failed"), _step("command", "completed")]
    assert recovered_from_failure(steps) is True
    assert should_observe(steps) is True


def test_no_recovery_when_failure_is_last() -> None:
    steps = [_step("command", "completed"), _step("command", "failed")]
    assert recovered_from_failure(steps) is False
