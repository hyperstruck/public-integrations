"""The closed sets this client sends, held against what the boundary publishes."""

from __future__ import annotations

from hyperstruck._wire import (
    DECLINE_REASONS,
    REASON_NO_GOAL,
    REASON_READONLY_CLOSE,
    published_decline_reasons,
)


def test_every_published_reason_is_one_this_client_knows() -> None:
    """The vendored list is the boundary's own. A reason on it that this client cannot
    name is a decline it can never send, which is a silent gap rather than an error."""
    assert published_decline_reasons() <= DECLINE_REASONS


def test_a_reason_the_boundary_already_accepts_is_published() -> None:
    assert REASON_READONLY_CLOSE in published_decline_reasons()


def test_a_reason_can_be_defined_here_before_the_boundary_takes_it() -> None:
    """This is the whole point of publishing separately from defining.

    A refused decline is not a degraded diagnostic: it leaves the run open holding its
    resolve reservation until the retention sweep, and this client reaches a user's
    machine on a different schedule from the API it talks to. So the code names the
    reason, and the caller checks whether it may send it yet.
    """
    assert REASON_NO_GOAL in DECLINE_REASONS
    assert published_decline_reasons() < DECLINE_REASONS
