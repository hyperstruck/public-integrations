"""What a step reports about its outcome, and what it refuses to."""

from __future__ import annotations

import pytest

from hyperstruck.ide import step_result
from hyperstruck.ide.step_result import (
    GATE_FIELD,
    gate_bearing_result,
    published_fields,
)

CLAUDE = "claude-code"
CURSOR = "cursor"

# The payloads that shipped a username, an internal hostname, a credential and an
# environment variable name as gate operands in testing, under two successive position
# rules. Every entry-shape test takes all four, so a rule fixed on one path cannot pass
# for the other.
LEAKS = [
    "root:*:0:0:System\ntlynch:*:501:20:Thomas Lynch:/Users/tlynch:/bin/zsh",
    "fetching\ninternal.corp.example.com",
    "boom\nsk-ant-api03-DEADBEEFdeadbeefDEADBEEFdeadbeef",
    "connecting\nDATABASE_PASSWORD_PROD",
]
LEAK_IDS = ["a_username", "an_internal_host", "a_credential", "an_env_var_name"]


@pytest.fixture
def _floor_enforced(monkeypatch) -> None:
    """The boundary admitting an operand on its support, which is what turns it on."""
    monkeypatch.setattr(step_result, "is_operand_admitted_on_support", lambda: True)


class TestOnlyAFailureReports:
    def test_a_successful_step_reports_nothing(self, _floor_enforced) -> None:
        """A gate recognises a dead end, and a step that succeeded is not one."""
        assert (
            gate_bearing_result({"tool_response": {"stdout": "ok"}}, is_error=False)
            is None
        )

    def test_a_failure_reports_the_name_it_failed_under(self, _floor_enforced) -> None:
        reported = gate_bearing_result(
            {"tool_response": "Error: ModuleNotFoundError: No module named 'x'"},
            is_error=True,
            source=CLAUDE,
        )

        assert reported == {GATE_FIELD: "ModuleNotFoundError"}

    def test_a_cursor_failure_is_read_from_its_structured_fields(
        self, _floor_enforced
    ) -> None:
        reported = gate_bearing_result(
            {"exit_code": 127, "stderr": "pytest: command not found"}, is_error=True
        )

        assert reported == {GATE_FIELD: "pytest"}

    def test_a_failure_with_nothing_to_say_reports_nothing(
        self, _floor_enforced
    ) -> None:
        assert gate_bearing_result({"tool_response": ""}, is_error=True) is None
        assert gate_bearing_result({}, is_error=True) is None

    def test_the_undocumented_second_field_name_is_read_too(
        self, _floor_enforced
    ) -> None:
        """The host's result field is undocumented and observed under two names; reading
        only one costs every failure silently, with nothing anywhere to see."""
        assert gate_bearing_result(
            {"tool_result": "Error: KeyError: 'x'"}, is_error=True, source=CLAUDE
        ) == {GATE_FIELD: "KeyError"}


class TestTheOperandIsWithheldUntilTheBoundaryPromisesToRefuseSingletons:
    def test_nothing_is_reported_while_the_guarantee_is_unpublished(self) -> None:
        """The contract file has said this all along and nothing read it, so the client
        shipped the operands anyway. 72.7% of them are singletons, which are quasi-identifiers
        and dead gates at once, and 'leaks nothing by construction' turned out to be a claim
        about a masking rule rather than a property."""
        assert step_result.is_operand_admitted_on_support() is False
        assert (
            gate_bearing_result(
                {"tool_response": "Error: KeyError: 'x'"}, is_error=True, source=CLAUDE
            )
            is None
        )


class TestTheOperandIsOneTheBoundaryCanActuallyAdmit:
    def test_every_operand_matches_the_boundarys_own_token_shape(
        self, _floor_enforced
    ) -> None:
        """The boundary admits an operand only if it matches ``^[A-Za-z0-9_.-]+$``. A richer
        masked phrase covers far more failures and is refused there, so it waits on a
        boundary change rather than being sent to be silently dropped."""
        import re

        for text in (
            "Error: ModuleNotFoundError: No module named 'x'",
            "Error: ls: /nope: No such file or directory",
            "Error: json.decoder.JSONDecodeError: Expecting value",
        ):
            reported = gate_bearing_result(
                {"tool_response": text}, is_error=True, source=CLAUDE
            )
            assert reported is not None
            assert re.fullmatch(r"[A-Za-z0-9_.-]+", reported[GATE_FIELD])


class TestTheReportedNameIsOneTheServerReads:
    def test_the_emitted_field_is_published(self) -> None:
        """A name outside this list yields no gate and no error, which is why it is asserted."""
        assert GATE_FIELD in published_fields()

    def test_status_is_never_emitted(self, _floor_enforced) -> None:
        """A gate on "failed" fires on every failure of that tool.

        Emitting it would move the server's gate count off zero while every gate derived
        meant nothing, which is worse than the zero: the measurement would read as satisfied
        without the thing it measures having changed.
        """
        reported = gate_bearing_result(
            {"tool_response": "Error: KeyError: 'x'"}, is_error=True, source=CLAUDE
        )

        assert reported is not None
        assert set(reported) == {GATE_FIELD}

    def test_an_exit_status_is_never_emitted_as_the_operand(
        self, _floor_enforced
    ) -> None:
        """Measured over 1,181 real failures carrying one, 86.3% were ``1``, which means no
        more than 'something went wrong'. It is the degenerate gate by another route."""
        reported = gate_bearing_result(
            {"exit_code": 1, "stderr": "boom"}, is_error=True
        )

        assert reported == {GATE_FIELD: "boom"}
        assert "error_code" not in reported


class TestTheOperandIsNeverReadFromAToolsOutput:
    """The property the module claims, attacked with the payloads that broke it.

    Program output gives no reliable position for the failure's name, and that is true of
    every way it arrives: a host that concatenates stdout and stderr into one string, and a
    field named ``stderr`` or ``error``, which is a claim about the field and not about each
    line inside it. Reading the last line, and then reading the line after the frame, each
    shipped a username, an internal hostname and a credential in testing.

    Both entry shapes take the same payloads and the same assertion. The earlier version
    parameterised only the framed one, so the identical payloads shipped through the
    labelled one for a release while a test named for the whole property passed.
    """

    @pytest.mark.parametrize("output", LEAKS, ids=LEAK_IDS)
    def test_no_line_of_a_framed_result_can_become_the_operand(
        self, _floor_enforced, output: str
    ) -> None:
        reported = gate_bearing_result(
            {"tool_response": f"Error: Exit code 1\n{output}"},
            is_error=True,
            source=CLAUDE,
        )

        assert reported is None

    @pytest.mark.parametrize("output", LEAKS, ids=LEAK_IDS)
    @pytest.mark.parametrize("field", ["stderr", "error"])
    def test_no_line_of_a_labelled_field_can_become_the_operand(
        self, _floor_enforced, field: str, output: str
    ) -> None:
        reported = gate_bearing_result(
            {"exit_code": 1, field: output}, is_error=True, source=CURSOR
        )

        assert reported is None

    def test_the_first_labelled_field_answers_rather_than_all_of_them_joined(
        self, _floor_enforced
    ) -> None:
        """Each field separately means "this is the error"; their concatenation means only
        "here is everything", and the operand would come from whichever came last."""
        reported = gate_bearing_result(
            {"error": "KeyError: 'space_id'", "stderr": "cleaning up\ntlynch"},
            is_error=True,
            source=CURSOR,
        )

        assert reported == {GATE_FIELD: "KeyError"}

    def test_a_value_the_scrubber_changed_is_dropped_rather_than_shipped_redacted(
        self, _floor_enforced
    ) -> None:
        """Scrubbing after validating let a redacted value through that no longer matched the
        shape it was validated against, so the boundary refused it silently. And a value the
        scrubber touched is a credential, not a failure's name: redacted, it is still a
        quasi-identifier, just wearing a mask."""
        reported = gate_bearing_result(
            {"stderr": "sk-ant-api03-DEADBEEFdeadbeefDEADBEEFdeadbeef: bad key"},
            is_error=True,
        )

        assert reported is None
