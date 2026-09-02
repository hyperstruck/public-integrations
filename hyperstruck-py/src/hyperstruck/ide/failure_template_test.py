"""What a failure is allowed to say its name is, and what licenses it saying so."""

from __future__ import annotations

import re

import pytest

from hyperstruck.ide.failure_template import (
    MAX_SCANNED_CHARS,
    _MASK,
    ProvenanceTier,
    failure_signature,
)
from hyperstruck.ide.host_vocabularies import host_authored_framing
from hyperstruck.ide.step_result import published_operand_shape

CLAUDE = host_authored_framing("claude-code")
SHAPE = published_operand_shape()

TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "/app/run.py", line 3, in <module>\n'
    "    import missing\n"
    "ModuleNotFoundError: No module named 'missing'"
)


def signature(text: str, framing=CLAUDE, shape=SHAPE):
    return failure_signature(text, framing, shape=shape)


class TestAFrameConsumingTheWholeLineIsNotAMessage:
    """The defect that made the shipped rule derive an operand on 0 of 2,509 failures.

    Claude Code leads a failed Bash result with ``Exit code 1`` as the *entire* first line.
    The rule stripped the frame, was left with an empty string, and returned nothing before
    ever reaching the error on line two. It fired only when the frame and the failure's name
    shared a line, which real results never do.
    """

    @pytest.mark.parametrize("frame", ["Exit code 1", "Error:", "<tool_use_error>"])
    def test_a_bare_frame_is_not_a_host_message(self, frame: str) -> None:
        tier, operand = signature(frame)

        assert (tier, operand) == (ProvenanceTier.UNLICENSED, None)

    def test_the_error_on_the_next_line_is_reached_instead(self) -> None:
        """The whole point of the empty-remainder rule: the result falls through to the
        language tier, where its traceback is actually readable."""
        tier, operand = signature(f"Exit code 1\n{TRACEBACK}")

        assert (tier, operand) == (
            ProvenanceTier.LANGUAGE_RUNTIME,
            "ModuleNotFoundError",
        )


class TestTheFrameLeadsTheResultOrItIsNotTheFrame:
    def test_a_frame_further_down_is_the_tools_own_output(self) -> None:
        """Scanning every line for a frame lets a tool's own output supply one, so a step
        printing the host's framing inside its output could name its own operand."""
        tier, operand = signature("listing\n<tool_use_error>bastion.corp: down")

        assert (tier, operand) == (ProvenanceTier.UNLICENSED, None)

    def test_the_frame_on_the_first_line_still_reads(self) -> None:
        tier, operand = signature("<tool_use_error>File has not been read yet.")

        assert (tier, operand) == (
            ProvenanceTier.HOST_MESSAGE,
            "File has not been read yet",
        )


class TestOnlyAHostsOwnProtocolFrameLicensesAMessage:
    """A generic envelope names no author, and masking cannot rescue what follows one.

    ``internal.corp.example.com``, ``tlynch`` and ``DATABASE_PASSWORD_PROD`` all match the
    boundary's own word pattern, so mask-by-refusal leaves every one of them intact. The
    only thing that keeps them out is refusing to read under a frame that is an envelope
    around a program's output rather than an introduction to the host's own words.
    """

    @pytest.mark.parametrize(
        "text",
        [
            "internal.corp.example.com: Connection refused",
            "tlynch: permission denied",
            "DATABASE_PASSWORD_PROD: not set",
        ],
    )
    @pytest.mark.parametrize("envelope", ["Error: ", "Exit code 1\n"])
    def test_nothing_is_read_under_a_generic_envelope(
        self, envelope: str, text: str
    ) -> None:
        tier, operand = signature(f"{envelope}{text}")

        assert (tier, operand) == (ProvenanceTier.UNLICENSED, None)

    @pytest.mark.parametrize(
        "text",
        [
            "internal.corp.example.com: Connection refused",
            "tlynch: permission denied",
            "DATABASE_PASSWORD_PROD: not set",
        ],
    )
    def test_the_same_text_under_a_protocol_frame_is_masked_not_dropped(
        self, text: str
    ) -> None:
        """The host tier does read these, and that is safe for a different reason: the host
        composes its messages from a fixed vocabulary, so this shape does not arise under a
        protocol frame. Pinned so the asymmetry is visible rather than assumed, and so the
        day it stops holding is a red test rather than a silent leak."""
        tier, _ = signature(f"<tool_use_error>{text}")

        assert tier is ProvenanceTier.HOST_MESSAGE


class TestTheSentenceCutKeepsWhatIsNotASentenceEnd:
    """``MAX_GATE_VALUE_WORDS`` is 8, so an uncut protocol message is refused for length.

    The cut is what makes the tier yield anything at all, and the lookbehind is what stops
    it cutting inside a version, a filename or a dotted attribute path.
    """

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "File has not been read yet. Read it first before writing to it.",
                "File has not been read yet",
            ),
            (
                "String to replace not found in file.",
                "String to replace not found in file",
            ),
        ],
    )
    def test_a_message_is_cut_at_its_first_sentence(
        self, text: str, expected: str
    ) -> None:
        assert signature(f"<tool_use_error>{text}")[1] == expected

    @pytest.mark.parametrize(
        ("unbroken", "expected"),
        [
            ("v1.2.3 is unsupported", "<*> is unsupported"),
            ("__init__.py is missing", "<*> is missing"),
            ("Object.assign failed", "<*> failed"),
        ],
    )
    def test_a_period_inside_a_token_is_not_a_sentence_end(
        self, unbroken: str, expected: str
    ) -> None:
        """The words after the period survive, which is the whole assertion: none of these
        puts a lowercase letter, a closing paren or a closing bracket immediately before a
        period that whitespace then follows, so the lookbehind refuses to cut.

        All three are then masked, by the separate rule underneath: each carries a dot or an
        underscore, so each is an identifier rather than a word of the host's prose. Spelling
        the masked form out here rather than asserting the raw text keeps the two rules
        legible as two, and the trailing words are what prove the cut did not fire: a cut that
        had fired would drop ``is unsupported`` entirely, and no masking change can disguise
        that.
        """
        assert signature(f"<tool_use_error>{unbroken}")[1] == expected

    def test_a_message_too_long_to_bound_is_refused(self) -> None:
        assert (
            signature("<tool_use_error>one two three four five six seven eight nine")[1]
            is None
        )


class TestMaskingIsByRefusalAndIsDeterministic:
    def test_a_word_the_boundary_refuses_becomes_a_mask(self) -> None:
        tier, operand = signature(
            "<tool_use_error>Blocked: sleep 120 followed by: cat /private/tmp/x"
        )

        assert tier is ProvenanceTier.HOST_MESSAGE
        assert operand == "Blocked sleep 120 followed by cat <*>"

    def test_a_message_that_is_all_mask_says_nothing_and_is_refused(self) -> None:
        assert signature("<tool_use_error>/one/path /two/path")[1] is None

    def test_the_same_message_masks_identically_every_time(self) -> None:
        """The boundary's support floors count distinct runs of the same operand, so a
        machine-dependent mask would never accumulate support anywhere."""
        text = "<tool_use_error>File /Users/someone/x.py has been modified since read."

        assert (
            signature(text)[1]
            == signature(text)[1]
            == "File <*> has been modified since read"
        )


class TestAnUnreadableContractWithholdsRatherThanUnbounds:
    """Empty is the safe degradation, and here it is the only safe one.

    Every bound the masking applies comes from the vendored contract. A caller that read a
    missing bound as "no bound" would ship the unmasked message, which is the leak the bound
    exists to prevent, so an unreadable shape abstains instead.
    """

    @pytest.mark.parametrize(
        "shape", [{}, None, {"max_words": 8}, {"word_pattern": "^a$"}]
    )
    def test_an_incomplete_shape_yields_nothing(self, shape) -> None:
        assert (
            signature("<tool_use_error>File has not been read yet.", shape=shape)[1]
            is None
        )

    def test_an_uncompilable_pattern_yields_nothing_rather_than_raising(self) -> None:
        """This runs inside a hook that fails open by contract, so an exception would
        surface nowhere at all and cost the episode instead."""
        broken = dict(SHAPE) | {"word_pattern": "((("}

        assert (
            signature("<tool_use_error>File has not been read yet.", shape=broken)[1]
            is None
        )


class TestTheScanIsBounded:
    def test_nothing_is_read_past_the_character_bound(self) -> None:
        """This runs in a per-tool-call subprocess on unclipped raw output, so an unbounded
        scan would put a multi-megabyte ``cat`` between the user and their next keystroke."""
        buried = ("noise\n" * MAX_SCANNED_CHARS) + TRACEBACK

        assert signature(buried)[1] is None

    def test_a_deep_traceback_is_not_amputated(self) -> None:
        """A twenty-line cap used to sit beside the character bound, and a language block ends
        with its exception line, so the cap removed exactly the part carrying the name. Every
        traceback of six frames or more abstained. Ten frames is twenty-two lines and well
        inside the character bound, so it must resolve."""
        frames = "".join(
            f'  File "/app/m{n}.py", line {n}, in f{n}\n    call_{n}()\n' for n in range(10)
        )
        deep = f"Traceback (most recent call last):\n{frames}KeyError: 'k'"

        assert len(deep.splitlines()) > 20
        assert signature(deep) == (ProvenanceTier.LANGUAGE_RUNTIME, "KeyError")

    def test_empty_and_blank_text_yield_nothing(self) -> None:
        for text in ("", "   \n  \n", "\n"):
            assert signature(text) == (ProvenanceTier.UNLICENSED, None)


class TestTheResidualThisCannotClose:
    """The exposure that survives every rule tried here, pinned rather than described.

    Three rules have been tried on this path: position, then grammar, then structural masking.
    Each closed the cases it was shown and left the class open, because a username, a hostname
    and an environment variable name are the same shape as an ordinary word and as an
    exception class name. Separating them by meaning would be a lexicon.

    These assertions are deliberately the uncomfortable direction: they assert that untrusted
    tokens ARE emitted. That is what stops the residual being quietly forgotten, and it is what
    turns red the day someone believes they have closed it, so the claim gets checked rather
    than assumed. What bounds these values is the boundary's k-anonymity floors, which is a
    property of the population and not of any of these strings.
    """

    @pytest.mark.parametrize(
        ("text", "emitted"),
        [
            ("<tool_use_error>Blocked: ssh bastion", "Blocked ssh bastion"),
            ("<tool_use_error>Blocked: curl vault-prod-eu", "Blocked curl vault-prod-eu"),
            (
                "<tool_use_error>Environment variable PGPASSWORD is not set",
                "Environment variable PGPASSWORD is not set",
            ),
            ("<tool_use_error>User tlynch is not permitted", "User tlynch is not permitted"),
        ],
        ids=["a_hostname", "a_hyphenated_host", "an_env_var", "a_username"],
    )
    def test_an_undotted_bare_token_still_reaches_the_operand(
        self, text: str, emitted: str
    ) -> None:
        assert signature(text)[1] == emitted

    def test_a_truncated_traceback_can_present_an_arbitrary_exception_line(self) -> None:
        """The language tier's residual, and the narrower of the two.

        The block rule bounds the read to the frames the banner licenses, but the line that
        ends that run is whatever occupies the slot. A traceback truncated exactly there, with
        other output interleaved, puts an arbitrary line in it. Measured over 1,744 real
        production-reachable failures this shape does not occur: it is adversarial rather than
        natural, which is why it is a stated residual and not a blocker.
        """
        truncated = (
            "Traceback (most recent call last):\n"
            '  File "app.py", line 1, in <module>\n'
            "tlynch: permission denied"
        )

        assert signature(truncated) == (ProvenanceTier.LANGUAGE_RUNTIME, "tlynch")

    @pytest.mark.parametrize(
        "identifier", ["internal.corp.example.com", "DATABASE_PASSWORD_PROD"]
    )
    def test_what_the_word_rule_does_close_stays_closed(self, identifier: str) -> None:
        """The half that is genuinely bounded: a dot or an underscore is masked.

        Membership here is decided by mutation, not by plausibility. A leading slash and an
        angle-bracketed token both look like they belong and neither does: the boundary's own
        ``word_pattern`` refuses both and is checked first, so each stayed masked with this
        client rule deleted entirely and would have read as a proof of it while being none.
        The angle-bracket case moved to the test below when the boundary tightened it.
        """
        operand = signature(f"<tool_use_error>Blocked: cat {identifier}")[1]

        assert operand is not None
        assert identifier not in operand

    def test_an_angle_bracketed_token_is_closed_by_the_boundarys_own_pattern(self) -> None:
        """``<secret.txt>`` was the client's to close under contract version 1 and is the
        boundary's under version 2, which narrowed the bracketed alternative to at most eight
        letters. Asserted against the vendored pattern rather than the client rule, because
        deleting the client rule leaves this green and it would otherwise read as coverage of
        a rule it no longer exercises.
        """
        word = re.compile(published_operand_shape()["word_pattern"])

        assert not word.match("<secret.txt>")
        assert word.match(_MASK)
