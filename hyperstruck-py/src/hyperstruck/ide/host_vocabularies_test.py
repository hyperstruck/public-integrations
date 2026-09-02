"""What each host declares about itself, and what it refuses to say about others."""

from __future__ import annotations

import pytest

from hyperstruck.ide.constants import (
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    SOURCE_OPENHANDS,
    STATUS_COMPLETED,
    STEP_KIND_COMMAND,
    STEP_KIND_EDIT,
    STEP_KIND_READ,
)
from hyperstruck.ide.host_vocabularies import declared_kind, vocabulary_for
from hyperstruck.ide.outcome import TurnOutcome


class TestATerminalStatusMeansWhatItsHostSaysItMeans:
    @pytest.mark.parametrize(
        "source", [SOURCE_CLAUDE_CODE, SOURCE_CURSOR, SOURCE_OPENHANDS]
    )
    def test_a_declared_host_classifies_its_own_statuses(self, source: str) -> None:
        vocabulary = vocabulary_for(source)

        assert vocabulary.classify(STATUS_COMPLETED) is TurnOutcome.SUCCESS
        assert vocabulary.classify("aborted") is TurnOutcome.FAILURE

    def test_an_undeclared_status_abstains_rather_than_counting_as_success(
        self,
    ) -> None:
        """The defect this table was written for: membership decided failure and
        non-membership decided *success*, so a CI run killed by a ``timeout`` was
        credited."""
        assert (
            vocabulary_for(SOURCE_CLAUDE_CODE).classify("timeout")
            is TurnOutcome.UNEVIDENCED
        )

    def test_an_undeclared_host_abstains_on_everything(self) -> None:
        """A real cliff, and the safe direction: a host is declared in the same change
        that adds the host, rather than inheriting another host's meanings."""
        vocabulary = vocabulary_for("some-other-editor")

        assert vocabulary.classify(STATUS_COMPLETED) is TurnOutcome.UNEVIDENCED
        assert vocabulary.classify("failed") is TurnOutcome.UNEVIDENCED


class TestAHostsOwnToolsAreDeclaredByExactName:
    @pytest.mark.parametrize(
        ("source", "name", "expected"),
        [
            (SOURCE_CLAUDE_CODE, "Bash", STEP_KIND_COMMAND),
            (SOURCE_CLAUDE_CODE, "Write", STEP_KIND_EDIT),
            (SOURCE_CLAUDE_CODE, "Grep", STEP_KIND_READ),
            (SOURCE_CURSOR, "run_terminal_cmd", STEP_KIND_COMMAND),
            (SOURCE_CURSOR, "search_replace", STEP_KIND_EDIT),
            (SOURCE_CURSOR, "codebase_search", STEP_KIND_READ),
        ],
    )
    def test_a_declared_tool_takes_its_declared_kind(
        self, source: str, name: str, expected: str
    ) -> None:
        assert declared_kind(source, name) == expected

    @pytest.mark.parametrize("name", ["bash", "BASH", "Bash ", "EditFile", "my_edit"])
    def test_a_name_is_matched_whole_and_never_read_for_what_it_suggests(
        self, name: str
    ) -> None:
        """The whole difference from the substring table this replaces, which gave
        ``EditFile`` an edit verdict on the strength of four characters."""
        assert declared_kind(SOURCE_CLAUDE_CODE, name) is None

    def test_a_host_says_nothing_about_another_hosts_tools(self) -> None:
        assert declared_kind(SOURCE_CURSOR, "Bash") is None
        assert declared_kind(SOURCE_CLAUDE_CODE, "run_terminal_cmd") is None

    def test_an_undeclared_host_declares_no_tools(self) -> None:
        assert declared_kind("some-other-editor", "Bash") is None

    def test_no_declaration_claims_a_kind_that_is_not_a_step_kind(self) -> None:
        """A kind the gate does not know silently drops the step out of every set."""
        known = {STEP_KIND_COMMAND, STEP_KIND_EDIT, STEP_KIND_READ}
        for source in (SOURCE_CLAUDE_CODE, SOURCE_CURSOR):
            for name in ("Bash", "Write", "Grep", "run_terminal_cmd", "read_file"):
                kind = declared_kind(source, name)
                assert kind is None or kind in known
