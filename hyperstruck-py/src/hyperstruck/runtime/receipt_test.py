"""What the receipt must observe rather than assert."""

from __future__ import annotations

from hyperstruck.runtime.receipt import (
    DELIVERED_REFORMATTED,
    DELIVERED_VERBATIM,
    UNRESOLVED,
    flatten_params,
    locate_receipt,
)

ADVICE = "Relevant learnings from prior runs (hyperstruck):\n- prefer the bulk endpoint\n- retry once on 429"
FACTS = "Facts recalled about entities in this task (hyperstruck):\nNorthwind Clinics Pty Ltd:\n- billing runs monthly"


def _shelves(advice: str | None = ADVICE, facts: str | None = FACTS):
    return [
        ("advice", advice, ("l1", "l2")),
        ("facts", facts, ("c1",)),
    ]


def test_the_receipt_is_a_slice_of_what_was_sent_not_of_what_we_built() -> None:
    """The distinction the whole lane rests on: an observation, not an echo.

    A receipt built by remembering what we sent would report our block intact whatever the
    host did to it. This one is assembled from the payload's own rendering of the lines we
    authored, in payload order, so it is evidence about the host's stack rather than about
    our own intentions.

    It carries our lines and nothing else, including nothing the host interleaved between
    them. That is the disclosure bound, and it is enforced by construction rather than
    promised: an earlier version took the span from the first match to the last and
    returned everything inside it, and a probe of that version produced a receipt carrying
    a patient record, a card number and a password. See the exposure test below.
    """
    sent = f"You are a helpful agent.\n{ADVICE}\n[host note]\n{FACTS}\nUser: hello"
    location = locate_receipt(sent, _shelves())
    assert location.text is not None
    # Every line of ours survived the journey and every one of them is in the artefact.
    for line in ADVICE.splitlines() + FACTS.splitlines():
        assert line in location.text
    assert "[host note]" not in location.text
    assert "You are a helpful agent." not in location.text
    assert "User: hello" not in location.text


def test_the_receipt_never_carries_content_sitting_between_two_of_our_lines() -> None:
    """The disclosure bound, probed the way the fault was found.

    A model quoting one of our advice lines back is the ordinary case for an agent
    restating guidance it was given. It puts a match early and our real block late, and a
    first-match-to-last-match span swallows every message in between.
    """
    sensitive = (
        "PATIENT: Jane Doe, DOB 1971-04-02\n"
        "card 4111111111111111\n"
        "password hunter2"
    )
    sent = "\n".join(
        [
            "- prefer the bulk endpoint",  # the model restating our guidance
            sensitive,
            ADVICE,
            FACTS,
        ]
    )
    location = locate_receipt(sent, _shelves())
    assert location.text is not None
    for secret in ("PATIENT", "Jane Doe", "4111111111111111", "hunter2", "1971-04-02"):
        assert secret not in location.text


def test_an_echo_elsewhere_in_the_history_does_not_credit_a_shelf() -> None:
    """Exposure is never asserted from the model's own output.

    A tool result or a model turn repeating one of our lines is not evidence that the
    system block survived. Treating it as evidence would be a positive claim of exposure
    drawn from the very text the block was supposed to influence.
    """
    filler = "\n".join(f"chatter {index}" for index in range(30))
    sent = f"{filler}\n- prefer the bulk endpoint\n{filler}"
    location = locate_receipt(sent, _shelves())
    advice = next(shelf for shelf in location.shelves if shelf.name == "advice")
    # One line of a three-line block, found alone and far from anything else of ours.
    assert advice.outcome != DELIVERED_VERBATIM
    assert advice.lines_found < advice.lines_expected


def test_a_block_that_never_arrived_yields_no_receipt_rather_than_an_empty_one() -> None:
    """An empty string would read as an exposure that matched nothing.

    That is a different claim from "the block never reached the model", and reporting the
    second as the first is what would credit a trimming middleware's victim as a run that
    simply had nothing worth crediting.
    """
    location = locate_receipt("You are a helpful agent.\nUser: hello", _shelves())
    assert location.text is None
    assert location.is_present is False
    assert location.outcome == UNRESOLVED


def test_a_rewrapped_block_reads_as_delivered_not_as_a_drop() -> None:
    """Reflowing to the host's own column width still showed the model the learning.

    Reading that as a drop would be a positive claim of non-exposure drawn from formatting
    alone, which is the one thing this lane must never assert.
    """
    reflowed = (
        "Relevant learnings from prior runs   (hyperstruck):\n"
        "  * prefer the bulk endpoint\n"
        "  * retry once on 429"
    )
    location = locate_receipt(reflowed, _shelves(facts=None))
    advice = location.shelves[0]
    assert advice.outcome == DELIVERED_REFORMATTED
    assert advice.missing_lines == ()


def test_a_block_sent_untouched_is_verbatim() -> None:
    location = locate_receipt(f"prefix\n{ADVICE}\nsuffix", _shelves(facts=None))
    assert location.shelves[0].outcome == DELIVERED_VERBATIM


def test_a_dropped_line_is_named_so_the_customer_can_see_their_own_trimmer() -> None:
    """This is the whole local value of the report: no support ticket needed."""
    trimmed = "Relevant learnings from prior runs (hyperstruck):\n- prefer the bulk endpoint"
    location = locate_receipt(trimmed, _shelves(facts=None))
    advice = location.shelves[0]
    assert advice.outcome == DELIVERED_REFORMATTED
    assert advice.missing_lines == ("retry once on 429",)
    assert advice.lines_found == 2
    assert advice.lines_expected == 3


def test_the_run_outcome_is_the_worst_shelf_not_the_best() -> None:
    """A run that delivered its advice and lost its facts has something wrong with it."""
    sent = f"prefix\n{ADVICE}\nsuffix"
    location = locate_receipt(sent, _shelves())
    assert location.shelves[0].outcome == DELIVERED_VERBATIM
    assert location.shelves[1].outcome == UNRESOLVED
    assert location.outcome == UNRESOLVED


def test_an_empty_shelf_does_not_drag_the_run_outcome_down() -> None:
    """A shelf the corpus had nothing for is not a shelf that went missing."""
    location = locate_receipt(f"prefix\n{ADVICE}", _shelves(facts=None))
    assert location.outcome == DELIVERED_VERBATIM


def test_a_marker_is_stripped_as_a_token_and_never_as_a_character_class() -> None:
    """``lstrip("-* ")`` eats the minus off a value and the line never matches again."""
    block = "- range = -5 to -10"
    location = locate_receipt("* range = -5 to -10", [("advice", block, ("l1",))])
    assert location.shelves[0].outcome == DELIVERED_REFORMATTED
    assert location.shelves[0].missing_lines == ()


def test_flattening_walks_shapes_rather_than_naming_a_providers_schema() -> None:
    params = {
        "model": "claude-opus-5",
        "messages": [
            {"role": "system", "content": ADVICE},
            {"role": "user", "content": [{"type": "text", "text": "hello"}]},
        ],
    }
    flattened = flatten_params(params)
    assert "prefer the bulk endpoint" in flattened
    assert "hello" in flattened


def test_a_shape_flattening_cannot_read_contributes_nothing() -> None:
    """The fail-safe direction: unreadable params look like a block that did not arrive.

    An exposure this seat cannot evidence must never be asserted, so an object it cannot
    walk yields no receipt rather than a receipt it cannot stand behind.
    """

    class Opaque:
        pass

    assert flatten_params(Opaque()) == ""
