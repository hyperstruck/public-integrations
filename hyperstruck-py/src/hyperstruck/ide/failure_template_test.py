"""Reading a failure's own name, and refusing anything that would not be an operand."""

from __future__ import annotations

import pytest

from hyperstruck.ide.failure_template import (
    MAX_SCANNED_CHARS,
    MAX_SIGNATURE_CHARS,
    failure_signature,
)
from hyperstruck.ide.host_vocabularies import failure_framing

CLAUDE = failure_framing("claude-code")


class TestItReadsTheNameAFailureLeadsWith:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "ModuleNotFoundError: No module named 'pytest_asyncio'",
                "ModuleNotFoundError",
            ),
            ("ls: /Users/someone/secret-project: No such file", "ls"),
            ("KeyError: 'space_id'", "KeyError"),
            (
                "json.decoder.JSONDecodeError: Expecting value",
                "json.decoder.JSONDecodeError",
            ),
            ("AttributeError: 'Foo' object has no attribute 'bar'", "AttributeError"),
            ("TimeoutError(30)", "TimeoutError"),
        ],
    )
    def test_the_leading_identifier_is_the_operand(
        self, text: str, expected: str
    ) -> None:
        assert failure_signature(text, is_host_labelled=True) == expected

    def test_two_runs_of_the_same_failure_yield_the_same_operand(self) -> None:
        """The whole point: an equality test can only fire if the operand recurs."""
        assert failure_signature(
            "ModuleNotFoundError: No module named 'httpx'", is_host_labelled=True
        ) == failure_signature(
            "ModuleNotFoundError: No module named 'pydantic'", is_host_labelled=True
        )

    def test_different_failures_stay_distinguishable(self) -> None:
        assert failure_signature("KeyError: 'a'", is_host_labelled=True) != (
            failure_signature("TypeError: 'a'", is_host_labelled=True)
        )

    def test_a_labelled_field_holding_more_than_the_name_yields_nothing(self) -> None:
        """``stderr`` is a stream, not a message. Reading its last line was the same
        positional guess the framed path was corrected for, and it leaked the same way.
        """
        assert (
            failure_signature(
                "running tests...\nAssertionError: nope", is_host_labelled=True
            )
            is None
        )


class TestTheHostsOwnFramingIsRemovedFirst:
    def test_a_framed_failure_yields_its_real_name(self) -> None:
        """Without stripping the frame the operand is 'Error' for 65% of all Claude Code
        failures, which is the degenerate gate reached by a different route."""
        assert (
            failure_signature("Error: ModuleNotFoundError: No module named 'x'", CLAUDE)
            == "ModuleNotFoundError"
        )

    def test_a_bare_framing_line_yields_nothing_rather_than_the_frame(self) -> None:
        assert failure_signature("Error: Exit code 1", CLAUDE) is None

    def test_an_undeclared_host_strips_nothing(self) -> None:
        """Abstain on undeclared, like every other host table: another host's framing is
        not a fact about this one."""
        assert failure_signature("Error: boom", is_host_labelled=True) == "Error"


class TestItRefusesWhatTheBoundaryWouldRefuse:
    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   \n ",
            "User rejected tool use",
            "--- 42 ---",
            "no such file or directory",
        ],
        ids=["empty", "blank", "a_sentence", "punctuation", "prose"],
    )
    def test_anything_that_is_not_a_single_token_reports_nothing(
        self, text: str
    ) -> None:
        """The boundary admits an operand only if it matches ``^[A-Za-z0-9_.-]+$``, so
        sending a phrase costs the gate silently. Refusing here keeps the two ends
        describing the same value."""
        assert failure_signature(text, is_host_labelled=True) is None

    def test_the_operand_carries_no_path_quoted_value_or_sentence(self) -> None:
        """The token class drops the tail of a line, so a path, a quoted value or a
        sentence cannot ride along with the name. It is not what keeps the operand safe:
        a username and a hostname are that same class, which is why the line it is read
        from is chosen by the host's own label or frame and never by position."""
        signature = failure_signature(
            "ls: /Users/tlynch/dev/secret-repo: No such file or directory",
            is_host_labelled=True,
        )

        assert signature == "ls"

    def test_an_over_long_head_reports_nothing(self) -> None:
        assert (
            failure_signature(
                "A" * (MAX_SIGNATURE_CHARS + 1) + ": boom", is_host_labelled=True
            )
            is None
        )


class TestNothingIsDerivedFromTextTheHostDidNotCallAnError:
    def test_an_unlabelled_unframed_result_yields_nothing(self) -> None:
        """A failed call's whole result is also how a tool's OUTPUT arrives, and shape alone
        cannot tell an error message from a file's contents. So provenance decides: either
        the text came from a field meaning "this is the error", or the host's own framing
        was present. Without that, a read whose body happened to be one token would put a
        line of someone's file on the wire as the operand."""
        assert failure_signature("RAW_FILE_BODY_LINE") is None

    def test_only_the_framed_line_is_read(self) -> None:
        """Any later line is the command's own output, which cannot be told apart from a
        file's contents. Both looser rules were tried and both leaked."""
        assert failure_signature("Error: KeyError: 'x'", CLAUDE) == "KeyError"
        assert failure_signature("Error: Exit code 1\nKeyError: 'x'", CLAUDE) is None

    def test_an_error_labelled_field_needs_no_framing(self) -> None:
        """Cursor puts the message in stderr, which already means "this is the error"."""
        assert (
            failure_signature("pytest: command not found", is_host_labelled=True)
            == "pytest"
        )


class TestALabelledFieldIsAClaimAboutTheFieldNotAboutEachLineInIt:
    """A stream that happens to be called ``stderr`` is still a stream.

    These are the payloads that shipped a username, an internal hostname and an
    environment variable name as gate operands under the last-line rule. Nothing about
    their *shape* refuses them, so only the position rule can.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "root:*:0:0:System\ntlynch:*:501:20:Thomas Lynch:/Users/tlynch:/bin/zsh",
            "fetching\ninternal.corp.example.com",
            "connecting\nDATABASE_PASSWORD_PROD",
            "cat /etc/hosts\n10.0.3.4-db-prod-01.internal",
        ],
        ids=["username", "hostname", "env_var", "host_entry"],
    )
    def test_a_multi_line_stream_yields_nothing(self, text: str) -> None:
        assert failure_signature(text, is_host_labelled=True) is None

    def test_a_field_holding_only_the_name_still_works(self) -> None:
        """The rule costs coverage, not the case it exists to serve."""
        assert (
            failure_signature("pytest: command not found", is_host_labelled=True)
            == "pytest"
        )

    def test_a_field_too_long_to_read_whole_yields_nothing(self) -> None:
        """The scan is bounded so a huge result cannot sit between the user and their next
        keystroke, and a bound that clipped a stream down to one line would reinstate the
        leak. Not seeing the whole field is itself a reason to abstain."""
        assert (
            failure_signature(
                "KeyError: 'x'\n" + "A" * MAX_SCANNED_CHARS, is_host_labelled=True
            )
            is None
        )


class TestTheFrameLeadsTheResultOrItIsNotTheFrame:
    def test_a_frame_further_down_is_the_tools_own_output(self) -> None:
        """A tool can print ``Error:`` itself. Scanning every line for a frame made that
        line's own content the operand, which is the leak by another door: three of the
        four routes into this reach it without the frame having been checked elsewhere.
        """
        assert (
            failure_signature(
                "some output\nError: bastion.corp.internal: timeout", CLAUDE
            )
            is None
        )

    def test_the_frame_on_the_first_line_still_reads(self) -> None:
        assert failure_signature("Error: KeyError: 'space_id'", CLAUDE) == "KeyError"
