"""Guards on the goal tagging: what it cuts, and that it cuts the string that is sent."""

from __future__ import annotations

import pytest

from hyperstruck.ide.constants import SOURCE_CLAUDE_CODE, SOURCE_CURSOR
from hyperstruck.ide.prompt_spans import (
    MAX_SPANS,
    ORIGIN_HARNESS,
    ORIGIN_USER_PROSE,
    principal_prose,
    prompt_spans,
)
from hyperstruck.ide.receipt import marker

_COMMAND_TURN = (
    "<local-command-caveat>Caveat: generated while running local commands.</local-command-caveat>\n"
    "<command-name>/clear</command-name>\n"
    "<command-message>clear</command-message>\n"
    "<command-args></command-args>\n"
)


@pytest.mark.parametrize(
    "goal",
    [
        "Fix the failing test.",
        _COMMAND_TURN,
        _COMMAND_TURN + "Now fix the failing test.",
        "<task-notification>done</task-notification>Then carry on.",
        "before <system-reminder>x</system-reminder> after",
        f"{marker('run-1')}\nrecalled text\n\nFix the test.",
        "<task-notification>truncated mid-block, no closer",
        "",
    ],
)
def test_the_spans_concatenate_back_to_the_goal(goal: str) -> None:
    """Contiguous by construction, because a gap is counted against the client.

    Text left between client spans is labelled by the boundary's own set and counted as a
    gap, which is the signal for a client that missed something. A client that gapped on
    ordinary prose would make that number say nothing.
    """
    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    assert "".join(span.text for span in spans) == goal


def test_an_undeclared_host_is_not_told_another_hosts_markup() -> None:
    """Nothing, rather than one prose span over everything.

    Cursor has no declared envelope. Claiming the whole turn is prose would be an
    assertion this client cannot make, and it would stop the boundary's own closed set
    from being consulted at all for the origins it does know.
    """
    assert prompt_spans(_COMMAND_TURN, SOURCE_CURSOR) == ()


def test_the_command_envelope_is_harness_and_the_prose_beside_it_is_not() -> None:
    goal = _COMMAND_TURN + "Now fix the failing test."

    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    harness = [span.text for span in spans if span.origin == ORIGIN_HARNESS]
    prose = "".join(span.text for span in spans if span.origin == ORIGIN_USER_PROSE)
    assert "<command-name>/clear</command-name>" in harness
    assert "<local-command-caveat>" not in prose
    assert prose.strip() == "Now fix the failing test."


def test_a_turn_that_is_only_the_envelope_carries_no_prose_at_all() -> None:
    """The case that motivated the whole item: a slash command is nothing but markup.

    Measured over 4,024 real prompt turns, 405 were exactly this shape and every one of
    them reached a producer as a goal the person had supposedly typed.
    """
    spans = prompt_spans(_COMMAND_TURN, SOURCE_CLAUDE_CODE)

    prose = "".join(s.text for s in spans if s.origin == ORIGIN_USER_PROSE)
    assert prose.strip() == ""
    assert any(span.origin == ORIGIN_HARNESS for span in spans)


def test_an_unclosed_marker_runs_to_the_end_because_the_prompt_was_clipped() -> None:
    """The host closes every marker it opens, so an open one means the text was cut.

    Ending the span at the opener instead would hand the block's own body back as prose,
    which is the text the block exists to keep out.
    """
    goal = "<task-notification>\n<task-id>b92gu43oq</task-id>\nstill going"

    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    assert [(s.text, s.origin) for s in spans] == [(goal, ORIGIN_HARNESS)]


def test_this_clients_own_run_marker_is_cut_whatever_the_host_is() -> None:
    """Minted by ``receipt.marker``, so it is knowledge rather than a copied string."""
    goal = f"{marker('run-7')}\nsome recalled advice"

    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    assert spans[0].text == "<!-- hyperstruck-run: run-7 -->"
    assert spans[0].origin == ORIGIN_HARNESS


def test_every_span_declares_this_client_as_the_labeller() -> None:
    """The boundary counts spans by labeller, so the source is not a caller field."""
    spans = prompt_spans(_COMMAND_TURN, SOURCE_CLAUDE_CODE)

    assert {span.source for span in spans} == {"client"}


def test_the_utterance_is_the_prose_and_nothing_the_host_wrote() -> None:
    """The field is the only evidence for a rule no tool result could have revealed.

    So a value carrying the host's own envelope would let machine text authorise a standing
    order, which is the threat the whole span mechanism exists for.
    """
    goal = _COMMAND_TURN + "We use British English in this repository."

    utterance = principal_prose(prompt_spans(goal, SOURCE_CLAUDE_CODE))

    assert utterance == "We use British English in this repository."
    assert "<command-name>" not in (utterance or "")


def test_an_undeclared_host_yields_no_utterance_at_all() -> None:
    """No tagging, no claim. The boundary refuses one it cannot place in tagged prose anyway."""
    goal = _COMMAND_TURN + "We use British English in this repository."

    assert principal_prose(prompt_spans(goal, SOURCE_CURSOR)) is None


def test_a_turn_that_is_entirely_host_markup_yields_no_utterance() -> None:
    """A notification-only turn has no principal in it, so it must not report one."""
    assert principal_prose(prompt_spans(_COMMAND_TURN, SOURCE_CLAUDE_CODE)) is None


def test_prose_split_by_markup_comes_back_joined_in_order() -> None:
    """Two prose stretches around a system reminder are one utterance, not the first one."""
    goal = "Use British English <system-reminder>x</system-reminder> in every file."

    utterance = principal_prose(prompt_spans(goal, SOURCE_CLAUDE_CODE))

    assert utterance == "Use British English  in every file."


def test_the_utterance_is_a_substring_of_the_tagged_prose_by_construction() -> None:
    """The boundary's containment check is what this has to satisfy, so it is asserted here.

    Written as the boundary's own test rather than as an equality, because the two live in
    different repositories' worth of code and the property between them is containment.
    """
    goal = f"{marker('run-1')}\nrecalled text\n\nAlways run the linter." + _COMMAND_TURN
    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    prose = "".join(s.text for s in spans if s.origin == ORIGIN_USER_PROSE)
    utterance = principal_prose(spans)

    assert utterance
    assert " ".join(utterance.split()) in " ".join(prose.split())


def test_a_goal_that_cuts_past_the_platform_bound_abstains_rather_than_422s() -> None:
    """The platform refuses more than MAX_SPANS and a 4xx is terminal to the flush retry.

    Driven from the real shape rather than a synthetic one: repeated Claude Code command blocks
    are what produced 255 spans on an ordinary 8,000-character goal.
    """
    goal = _COMMAND_TURN * 40

    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    assert len(prompt_spans(_COMMAND_TURN, SOURCE_CLAUDE_CODE)) * 40 > MAX_SPANS
    assert spans == ()


def test_a_goal_inside_the_bound_is_still_cut() -> None:
    """The abstention has to be the exception, or the labelling is off for everybody."""
    assert prompt_spans(_COMMAND_TURN * 2, SOURCE_CLAUDE_CODE) != ()


def test_the_opener_search_does_not_rescan_the_goal_for_every_span() -> None:
    """Eight declared markers times sixty-four spans is the walk squared on the worst goals.

    Asserted on the number of scans rather than on wall clock, which is not a property of the
    code. A marker absent from the goal is looked for once and remembered absent.
    """
    scans = {"n": 0}
    real_find = str.find

    class _CountingStr(str):
        def find(self, *args: object) -> int:  # type: ignore[override]
            scans["n"] += 1
            return real_find(self, *args)  # type: ignore[arg-type]

    goal = _CountingStr(_COMMAND_TURN * 8)
    spans = prompt_spans(goal, SOURCE_CLAUDE_CODE)

    # Two scans per span memoised against nine without. Bounded between the two, so the guard
    # fails on the rescan rather than on an off-by-one.
    assert scans["n"] < len(spans) * 4
