"""What a step reports about its outcome, and what it refuses to."""

from __future__ import annotations

import json
import re

import pytest

from hyperstruck.ide import step_result
from hyperstruck.ide.constants import (
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    SOURCE_OPENHANDS,
)
from hyperstruck.ide.failure_template import ProvenanceTier
from hyperstruck.ide.step_result import (
    GATE_FIELD,
    gate_bearing_result,
    published_fields,
    published_operand_shape,
)

CLAUDE = SOURCE_CLAUDE_CODE
CURSOR = SOURCE_CURSOR

# A real CPython traceback, which is what a language grammar licenses reading a name from.
# Fixtures below use this wherever an operand is expected, because after the tiering it is
# provenance and not string shape that decides, and a bare ``Name: message`` line is exactly
# the shape that no longer yields anything.
TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "/app/run.py", line 3, in <module>\n'
    "    import missing\n"
    "{name}: No module named 'missing'"
)

# A stream: several lines, of which one carries an identifier. No tier may pick a line out
# of these, because none of them is authored by anyone the client can name.
MULTI_LINE_LEAKS = [
    pytest.param(
        "root:*:0:0:System\ntlynch:*:501:20:Thomas Lynch:/Users/tlynch:/bin/zsh",
        id="a_username",
    ),
    pytest.param("fetching\ninternal.corp.example.com", id="an_internal_host"),
    pytest.param(
        "boom\nsk-ant-api03-DEADBEEFdeadbeefDEADBEEFdeadbeef", id="a_credential"
    ),
    pytest.param("connecting\nDATABASE_PASSWORD_PROD", id="an_env_var_name"),
]

# One line, holding an identifier and a message. Every positional rule this module has had
# returned the identifier from these, and the tiering is what stops it: a generic envelope
# names no author, so what follows one belongs to no tier at all.
SINGLE_LINE_LEAKS = [
    pytest.param(
        "internal.corp.example.com: Connection refused", id="an_internal_host"
    ),
    pytest.param("tlynch: permission denied", id="a_username"),
    pytest.param("DATABASE_PASSWORD_PROD: not set", id="an_env_var_name"),
]

# The payload shapes that reach an operand, one per provenance the client can see. Kept
# beside the fixtures so a test covering "every way in" cannot silently cover fewer.
PAYLOAD_SHAPES = [
    pytest.param(lambda t: {"tool_response": f"Error: {t}"}, CLAUDE, id="framed"),
    pytest.param(lambda t: {"stderr": t}, CURSOR, id="stderr"),
    pytest.param(lambda t: {"error": t}, CURSOR, id="error"),
]


@pytest.fixture
def _floor_enforced(monkeypatch) -> None:
    """The boundary admitting an operand on its support, which is what turns it on."""
    monkeypatch.setattr(step_result, "is_operand_admitted_on_support", lambda: True)


class TestOnlyALicensedTierIsSent:
    """Provenance decides, and a tier is withdrawn by removing its grammar.

    A separate boolean gate over the matched tier used to sit here and has been removed: it
    could never refuse anything, because a tier that matches nothing produces no candidate.
    What replaced it is that an unlicensed result yields no operand at all, which is asserted
    below against the shapes that used to defeat every positional rule.
    """

    @pytest.mark.parametrize("text", SINGLE_LINE_LEAKS)
    @pytest.mark.parametrize(("payload_for", "source"), PAYLOAD_SHAPES)
    def test_a_generic_envelope_names_no_author_so_nothing_is_read_under_one(
        self, payload_for, source: str, text: str, _floor_enforced
    ) -> None:
        """The three values every earlier rule shipped, refused by the rule itself.

        ``Error:`` and ``Exit code N`` are envelopes around whatever the program printed, so
        the text after one is the program's own and belongs to no tier. Masking cannot save
        it: ``internal.corp.example.com``, ``tlynch`` and ``DATABASE_PASSWORD_PROD`` all match
        the boundary's own word pattern and survive masking intact.
        """
        assert (
            gate_bearing_result(payload_for(text), is_error=True, source=source) is None
        )

    @pytest.mark.parametrize("source", [CLAUDE, CURSOR, "", SOURCE_OPENHANDS])
    def test_a_host_message_tier_needs_that_hosts_declared_protocol_frame(
        self, source: str, _floor_enforced
    ) -> None:
        """The licence is per host and per frame, so a host nobody has read the protocol of
        gets the abstention rather than a guess."""
        reported = gate_bearing_result(
            {"tool_response": "<tool_use_error>File has not been read yet."},
            is_error=True,
            source=source,
        )

        assert (reported is not None) is (source == CLAUDE)

    def test_the_tier_a_result_resolves_to_is_the_one_its_grammar_licenses(
        self, _floor_enforced
    ) -> None:
        """The tier is the decision, so it is asserted directly rather than through a gate."""
        from hyperstruck.ide.failure_template import failure_signature
        from hyperstruck.ide.host_vocabularies import host_authored_framing

        framing = host_authored_framing(CLAUDE)
        shape = published_operand_shape()

        assert failure_signature(
            "<tool_use_error>File has not been read yet.", framing, shape=shape
        )[0] is ProvenanceTier.HOST_MESSAGE
        assert failure_signature(
            TRACEBACK.format(name="KeyError"), framing, shape=shape
        )[0] is ProvenanceTier.LANGUAGE_RUNTIME
        assert failure_signature(
            "Error: tlynch: permission denied", framing, shape=shape
        )[0] is ProvenanceTier.UNLICENSED


class TestOnlyAFailureReports:
    def test_a_successful_step_reports_nothing(self, _floor_enforced) -> None:
        """A gate recognises a dead end, and a step that succeeded is not one."""
        assert (
            gate_bearing_result({"tool_response": {"stdout": "ok"}}, is_error=False)
            is None
        )

    def test_a_failure_reports_the_name_it_failed_under(self, _floor_enforced) -> None:
        reported = gate_bearing_result(
            {"tool_response": TRACEBACK.format(name="ModuleNotFoundError")},
            is_error=True,
            source=CLAUDE,
        )

        assert reported == {GATE_FIELD: "ModuleNotFoundError"}

    def test_a_labelled_field_is_read_only_when_a_grammar_recognises_it(
        self, _floor_enforced
    ) -> None:
        """``stderr`` says the text is an error; it does not say who wrote it.

        So the field name licenses nothing on its own, and the same field yields an operand
        only when what is inside it is something a declared grammar recognises. A one-line
        field holding a bare ``name: message`` is the shape that used to yield its leading
        token whatever the token was, and it now yields nothing.
        """
        assert (
            gate_bearing_result(
                {"exit_code": 127, "stderr": "pytest: command not found"}, is_error=True
            )
            is None
        )
        assert gate_bearing_result(
            {"exit_code": 1, "stderr": TRACEBACK.format(name="AssertionError")},
            is_error=True,
        ) == {GATE_FIELD: "AssertionError"}

    def test_a_failure_with_nothing_to_say_reports_nothing(
        self, _floor_enforced
    ) -> None:
        """Anchored, or the abstention answers for the empty-text rule and hides a crash.

        Deleting the empty-lines guard from ``failure_signature`` left every client test
        green while this test took ``_floor_enforced`` alone. Anchored, that deletion raises
        ``IndexError``, which is what would have reached the hook.
        """
        assert gate_bearing_result({"tool_response": ""}, is_error=True) is None
        assert gate_bearing_result({"tool_response": "   \n "}, is_error=True) is None
        assert gate_bearing_result({}, is_error=True) is None

    def test_the_undocumented_second_field_name_is_read_too(
        self, _floor_enforced
    ) -> None:
        """The host's result field is undocumented and observed under two names; reading
        only one costs every failure silently, with nothing anywhere to see."""
        assert gate_bearing_result(
            {"tool_result": TRACEBACK.format(name="KeyError")},
            is_error=True,
            source=CLAUDE,
        ) == {GATE_FIELD: "KeyError"}


class TestTheOperandIsWithheldUntilTheBoundaryPromisesToRefuseSingletons:
    """The guarantee is published now, so what is pinned is the mechanism, not the answer."""

    def test_the_guarantee_the_boundary_now_enforces_is_published(self) -> None:
        assert step_result.is_operand_admitted_on_support() is True

    def test_nothing_is_reported_when_the_guarantee_is_absent(
        self, tmp_path, monkeypatch
    ) -> None:
        """72.7% of shape-derived operands are singletons, quasi-identifiers and dead gates
        at once, so a boundary that has not promised to refuse them must be sent none.

        Anchored on purpose, so the floor check is the only thing withholding. Without it
        the ``None`` could come from a tier refusing and the floor consultation could be
        deleted outright with the whole suite still green."""
        withdrawn = tmp_path / "gate_published_fields.json"
        withdrawn.write_text(
            json.dumps(
                {"fields": sorted(published_fields()), "enforced_guarantees": []}
            )
        )
        monkeypatch.setattr(step_result, "_CONTRACT", withdrawn)
        assert step_result.is_operand_admitted_on_support() is False
        assert (
            gate_bearing_result(
                {"tool_response": TRACEBACK.format(name="KeyError")},
                is_error=True,
                source=CLAUDE,
            )
            is None
        )


class TestTheOperandIsOneTheBoundaryCanActuallyAdmit:
    """An operand the boundary refuses is a value sent to be silently dropped.

    Both shapes are asserted against the *vendored* patterns rather than against literals
    written here, because a literal copy is a third place the bound lives and the one that
    never moves when the boundary's does.
    """

    HOST_MESSAGES = [
        "<tool_use_error>File has not been read yet. Read it first before writing.",
        "<tool_use_error>String to replace not found in file.",
        "Output does not match required schema: /challenges: must be array",
    ]
    RUNTIME_FAILURES = [
        TRACEBACK.format(name="ModuleNotFoundError"),
        TRACEBACK.format(name="FileNotFoundError"),
    ]

    # Every qualified exception name the boundary's entropy ceiling refuses. They are here
    # rather than in RUNTIME_FAILURES because they do not survive it, and the two members
    # above clear 3.5 bits per character by 0.13 and 0.09: a fixture picked from that margin
    # reads as coverage of the language tier while testing only its easiest input.
    REFUSED_QUALIFIED_NAMES = [
        "asyncio.TimeoutError",
        "json.JSONDecodeError",
        "subprocess.CalledProcessError",
        "hyperstruck_core.harness.capture.EmptyCaptureError",
    ]

    @pytest.mark.parametrize("text", HOST_MESSAGES + RUNTIME_FAILURES)
    def test_every_operand_matches_the_boundarys_own_phrase_shape(
        self, text: str, _floor_enforced
    ) -> None:
        reported = gate_bearing_result(
            {"tool_response": text}, is_error=True, source=CLAUDE
        )

        assert reported is not None
        phrase = published_operand_shape()["phrase_pattern"]
        assert re.fullmatch(phrase, reported[GATE_FIELD])

    @pytest.mark.parametrize("text", RUNTIME_FAILURES)
    def test_a_language_runtime_name_is_a_single_token(
        self, text: str, _floor_enforced
    ) -> None:
        """A runtime's error name is the class name and never the message, so it is bounded
        by the stricter of the two shapes rather than by the phrase shape a host message
        needs."""
        reported = gate_bearing_result(
            {"tool_response": text}, is_error=True, source=CLAUDE
        )

        assert reported is not None
        token = published_operand_shape()["token_pattern"]
        assert re.fullmatch(token, reported[GATE_FIELD])

    @pytest.mark.parametrize("name", REFUSED_QUALIFIED_NAMES)
    def test_a_qualified_exception_name_is_refused_by_the_entropy_ceiling(
        self, name: str, _floor_enforced
    ) -> None:
        """Pinned in the uncomfortable direction: these are names the tier reads correctly
        and the contract then throws away.

        Entropy per character is the wrong instrument for a dotted name, because the dots
        and the case changes that make it *more* readable are what push it over. The tier
        is not at fault and neither is this client, which mirrors the published bound so the
        value is refused here rather than silently at the boundary. Filed against Core as
        ``platform-followups.md`` #120; when that lands, these move into RUNTIME_FAILURES
        and this test goes with them. Until then the loss is asserted rather than assumed,
        so nobody reads the language tier's coverage as including qualified names.
        """
        assert (
            gate_bearing_result(
                {"tool_response": TRACEBACK.format(name=name)},
                is_error=True,
                source=CLAUDE,
            )
            is None
        )


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
            {"tool_response": TRACEBACK.format(name="KeyError")},
            is_error=True,
            source=CLAUDE,
        )

        assert reported is not None
        assert set(reported) == {GATE_FIELD}

    def test_an_exit_status_is_never_emitted_as_the_operand(
        self, _floor_enforced
    ) -> None:
        """Measured over 1,181 real failures carrying one, 86.3% were ``1``, which means no
        more than 'something went wrong'. It is the degenerate gate by another route."""
        reported = gate_bearing_result(
            {"tool_response": "Exit code 1\n" + TRACEBACK.format(name="TimeoutError")},
            is_error=True,
            source=CLAUDE,
        )

        assert reported == {GATE_FIELD: "TimeoutError"}
        assert "error_code" not in reported


class TestTheOperandIsNeverReadFromAToolsOutput:
    """The property the module claims, attacked with the payloads that broke it.

    Program output gives no reliable position for the failure's name, and that is true of
    every way it arrives: a host that concatenates stdout and stderr into one string, and a
    field named ``stderr`` or ``error``, which is a claim about the field and not about each
    line inside it. Reading the last line, and then reading the line after the frame, each
    shipped a username, an internal hostname and a credential in testing.
    """

    @pytest.mark.parametrize("output", MULTI_LINE_LEAKS)
    def test_no_line_of_a_framed_result_can_become_the_operand(
        self, _floor_enforced, output: str
    ) -> None:
        """Anchored, so this pins the rule refusing to spill past a frame into the
        program's own output, not the emit policy in front of it."""
        reported = gate_bearing_result(
            {"tool_response": f"Error: Exit code 1\n{output}"},
            is_error=True,
            source=CLAUDE,
        )

        assert reported is None

    @pytest.mark.parametrize("output", MULTI_LINE_LEAKS)
    @pytest.mark.parametrize("field", ["stderr", "error"])
    def test_no_line_of_a_labelled_field_can_become_the_operand(
        self, _floor_enforced, field: str, output: str
    ) -> None:
        """Anchored for the same reason as its twin above, and that symmetry is the point.

        An earlier round anchored only the framed half. This half then asserted ``None`` for
        a reason with nothing to do with the rule under test.
        """
        reported = gate_bearing_result(
            {"exit_code": 1, field: output}, is_error=True, source=CURSOR
        )

        assert reported is None

    def test_a_host_message_never_reaches_past_its_own_first_line(
        self, _floor_enforced
    ) -> None:
        """The frame leads the result or it is not the envelope.

        Scanning every line for a protocol frame would let a tool's own output supply one,
        so a step printing the host's framing inside its output could name its own operand.
        """
        assert (
            gate_bearing_result(
                {
                    "tool_response": (
                        "listing files\n<tool_use_error>internal.corp.example.com refused"
                    )
                },
                is_error=True,
                source=CLAUDE,
            )
            is None
        )

    def test_the_first_labelled_field_answers_rather_than_all_of_them_joined(
        self, _floor_enforced
    ) -> None:
        """Each field separately means "this is the error"; their concatenation means only
        "here is everything", and the operand would come from whichever came last."""
        text = step_result._failure_text(
            {"error": "KeyError: 'space_id'", "stderr": "cleaning up\ntlynch"}
        )

        assert text == "KeyError: 'space_id'"

    def test_a_value_the_scrubber_changed_is_dropped_rather_than_shipped_redacted(
        self, _floor_enforced, monkeypatch
    ) -> None:
        """Scrubbing after validating let a redacted value through that no longer matched
        the shape it was validated against, so the boundary refused it silently. And a value
        the scrubber touched is a credential, not a failure's name: redacted, it is still a
        quasi-identifier, just wearing a mask.

        The scrubber is driven directly because masking now reaches credentials first: every
        natural payload that used to arrive here has a digit or an underscore in it, which
        the boundary's word pattern refuses, so it is already a mask by the time this guard
        runs. That makes the guard unreachable from input rather than unnecessary, and an
        unreachable guard with no test is the one that gets deleted as dead.
        """
        monkeypatch.setattr(step_result, "scrub_secrets", lambda value: "[REDACTED]")

        assert (
            gate_bearing_result(
                {"tool_response": TRACEBACK.format(name="KeyError")},
                is_error=True,
                source=CLAUDE,
            )
            is None
        )


class TestADeniedCallIsNotAFailureOfTheThingItWouldHaveDone:
    """A rule learned from a denial is a rule about permission settings.

    213 of 2,509 host-declared failures on the reference corpus are denials rather than
    failures: the user rejected the call, automode was unavailable or blocked it, or the
    turn was interrupted. Excluding them on the host's own ``toolDenialKind`` is the right
    fix and needs a field whose presence in a ``PostToolUse`` payload is unproven, since a
    denied tool never executes and the hook may not fire for one at all. That is settled at
    the end-to-end gate rather than guessed at here.

    What is pinned meanwhile is the **residual**, measured rather than argued: of the four
    denial classes, only ``automode-blocked`` reaches a tier at all. The other three carry
    no declared frame, or overrun the word cap once cut, so they abstain for reasons that
    have nothing to do with being denials. Pinning it is what stops the residual growing
    silently: a later frame or a raised cap could quietly admit the other three, and this
    goes red rather than the corpus filling with rules about permission prompts.

    The one that does reach a tier leaks a command *shape* and not an identity, its paths
    are masked, and all but one instance on the reference corpus is a singleton the
    boundary's recurrence floor withholds.
    """

    DENIALS_THAT_ABSTAIN = [
        pytest.param(
            "The user doesn't want to proceed with this tool use. The tool use was "
            "rejected (eg. if it was a file edit, the new_string was NOT written).",
            id="user_rejected",
        ),
        pytest.param(
            "<tool_use_error>The user doesn't want to proceed with this tool use.",
            id="user_rejected_framed",
        ),
        pytest.param("No automode available", id="automode_unavailable"),
        pytest.param("The user interrupted this tool call.", id="interrupted"),
    ]

    @pytest.mark.parametrize("text", DENIALS_THAT_ABSTAIN)
    def test_three_of_the_four_denial_classes_reach_no_tier(
        self, text: str, _floor_enforced
    ) -> None:
        assert (
            gate_bearing_result({"tool_response": text}, is_error=True, source=CLAUDE)
            is None
        )

    def test_the_one_that_does_reach_a_tier_carries_a_shape_and_not_an_identity(
        self, _floor_enforced
    ) -> None:
        """The accepted residual, spelled out rather than described.

        Blocking a measured 20-point coverage improvement on this is the wrong trade, and
        hiding it would be worse, so it is written down as an assertion that fails if it
        ever becomes more than this.
        """
        reported = gate_bearing_result(
            {
                "tool_response": (
                    "<tool_use_error>Blocked: sleep 120 followed by: "
                    "cat /Users/someone/secret/notes.txt"
                )
            },
            is_error=True,
            source=CLAUDE,
        )

        assert reported == {GATE_FIELD: "Blocked sleep 120 followed by cat <*>"}


class TestEachWayOfReportingNothingSaysWhichOneItWas:
    """Four abstentions that look identical from outside and mean opposite things.

    Nothing asserted any of these lines, and one of them was wrong for two of the four:
    a value a tier read correctly and the contract then refused was reported as no tier
    having licensed the failure, which is the common by-design case. Reading a bound
    refusal as an abstention is how a working tier is measured as an absent one.
    """

    def _lines(self, capsys) -> str:
        return capsys.readouterr().err

    def test_no_tier_licensed_it_says_so(
        self, monkeypatch, capsys, _floor_enforced
    ) -> None:
        monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")

        assert (
            gate_bearing_result(
                {"tool_response": "fetching\ninternal.corp.example.com"},
                is_error=True,
                source=CLAUDE,
            )
            is None
        )
        assert "no provenance tier licensed this failure" in self._lines(capsys)

    def test_a_bound_refusing_a_licensed_value_is_not_reported_as_no_tier(
        self, monkeypatch, capsys, _floor_enforced
    ) -> None:
        monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")

        assert (
            gate_bearing_result(
                {"tool_response": TRACEBACK.format(name="asyncio.TimeoutError")},
                is_error=True,
                source=CLAUDE,
            )
            is None
        )
        written = self._lines(capsys)
        assert "refused by the published bounds" in written
        assert ProvenanceTier.LANGUAGE_RUNTIME.value in written
        assert "no provenance tier licensed" not in written

    def test_the_guarantee_being_unpublished_says_so(
        self, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")
        monkeypatch.setattr(step_result, "is_operand_admitted_on_support", lambda: False)

        assert (
            gate_bearing_result(
                {"tool_response": TRACEBACK.format(name="KeyError")},
                is_error=True,
                source=CLAUDE,
            )
            is None
        )
        written = self._lines(capsys)
        assert "publishes no support-floor guarantee" in written
        assert "no provenance tier licensed" not in written

    @pytest.mark.parametrize(
        "text",
        ["<tool_use_error>/etc/passwd", "<tool_use_error>1 2 3"],
        ids=["every_word_masked", "too_few_letters"],
    )
    def test_the_clients_own_masking_is_not_reported_as_a_published_bound(
        self, text: str, monkeypatch, capsys, _floor_enforced
    ) -> None:
        """The host tier masks under a rule deliberately tighter than the boundary's.

        Reporting that rule's refusal as the contract's is the same mislabel as reporting a
        bound refusal as an abstention, one branch over, and it was introduced by the fix
        for the first one.
        """
        monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")

        assert (
            gate_bearing_result(
                {"tool_response": text}, is_error=True, source=CLAUDE
            )
            is None
        )
        written = self._lines(capsys)
        assert "did not survive this client's masking" in written
        assert "refused by the published bounds" not in written
        assert "no provenance tier licensed" not in written

    def test_a_successful_step_says_nothing_at_all(
        self, monkeypatch, capsys, _floor_enforced
    ) -> None:
        """A step with no dead end to recognise is not an abstention and owes no line."""
        monkeypatch.setenv("HYPER_HOOK_DEBUG", "1")

        assert (
            gate_bearing_result(
                {"tool_response": "ok"}, is_error=False, source=CLAUDE
            )
            is None
        )
        assert self._lines(capsys) == ""


class TestTheBoundsThisClientDoesNotMirrorAreSafeToOmit:
    """Eight of the boundary's eleven published keys are applied here. Three are not.

    "Mirroring three of ten was a silent implementation, not a partial one" is the reason
    ``_admissible`` exists, so the three omissions need a stated reason rather than an
    absence, and a reason that fails loudly when the boundary moves underneath it. Each
    test below asserts the property that makes the omission safe, so a contract that
    changed it reddens here instead of silently disagreeing with the boundary.
    """

    def test_the_only_normalisation_published_is_one_the_operand_already_satisfies(
        self,
    ) -> None:
        """``strip`` is not applied because nothing this client builds can carry padding.

        If the boundary ever publishes a normalisation that transforms rather than trims,
        the support floors count a value this client never produced, and every operand
        stops accumulating.
        """
        assert published_operand_shape()["normalisation"] == "strip"

        for text in TestTheOperandIsOneTheBoundaryCanActuallyAdmit.HOST_MESSAGES + [
            TRACEBACK.format(name="KeyError")
        ]:
            reported = gate_bearing_result(
                {"tool_response": text}, is_error=True, source=CLAUDE
            )
            if reported is not None:
                assert reported[GATE_FIELD] == reported[GATE_FIELD].strip()

    def test_the_language_tier_can_only_produce_values_the_token_pattern_admits(
        self,
    ) -> None:
        """``token_pattern`` is not applied because the grammar is strictly narrower.

        The anchor reads a name matching ``^[A-Za-z_][A-Za-z0-9_.]*``, which is a subset of
        the published ``^[A-Za-z0-9_.-]+$``, so applying it would refuse nothing.
        """
        token = re.compile(published_operand_shape()["token_pattern"])

        for name in ["KeyError", "ModuleNotFoundError", "_Private", "A1"]:
            assert token.fullmatch(name)

    def test_no_operand_this_client_builds_is_numeric(self) -> None:
        """``max_numeric_magnitude`` is not applied because it bounds a numeric operand.

        Both tiers build a name or a masked phrase, never a bare number: the language
        anchor's pattern must open with a letter or underscore, and a phrase that masked
        every word is refused outright. ``max_digits``, which is mirrored, bounds the rest.
        """
        for text in TestTheOperandIsOneTheBoundaryCanActuallyAdmit.HOST_MESSAGES + [
            TRACEBACK.format(name="KeyError")
        ]:
            reported = gate_bearing_result(
                {"tool_response": text}, is_error=True, source=CLAUDE
            )
            if reported is not None:
                with pytest.raises(ValueError):
                    float(reported[GATE_FIELD])
