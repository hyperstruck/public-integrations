"""The ladder, and the two failure directions it must not have."""

from __future__ import annotations

from hyperstruck.runtime.run_key import (
    RunKey,
    current_context_run_key,
    otel_run_key,
    reset_current_run,
    resolve_run_key,
    set_current_run,
)


def test_the_context_rung_answers_when_the_wrapper_set_a_key() -> None:
    token = set_current_run("run-abc")
    try:
        key = current_context_run_key()
        assert key == RunKey(key="run-abc", source="context", is_inferred=False)
    finally:
        reset_current_run(token)

    assert current_context_run_key() is None


def test_a_higher_rung_wins_over_a_lower_one() -> None:
    """Ordering is the whole point: an exact key must never lose to a guessed one."""
    token = set_current_run("run-abc")
    try:
        resolved = resolve_run_key(
            [lambda: RunKey(key="t", source="trace", is_inferred=False),
             current_context_run_key]
        )
        assert resolved.source == "trace"
    finally:
        reset_current_run(token)


def test_a_resolver_that_raises_falls_through_rather_than_failing_the_run() -> None:
    """A tracer misbehaving must cost correlation quality, never the customer's run."""

    def boom() -> RunKey | None:
        raise RuntimeError("tracer exploded")

    resolved = resolve_run_key([boom, lambda: RunKey("k", "context", False)])

    assert resolved.key == "k"


def test_the_last_resort_mints_a_unique_key_and_says_it_did() -> None:
    """A shared default would merge every unattributed run into one.

    That is the one failure with a correctness cost: a merged run reports a receipt for
    a block another run was shown. Losing correlation is recoverable and is reported.
    """
    first = resolve_run_key([])
    second = resolve_run_key([])

    assert first.key != second.key
    assert first.is_inferred is True
    assert first.source == "minted"


def test_otel_is_absent_or_invalid_rather_than_all_zeroes() -> None:
    """A no-op span's trace id is all zeroes and would become one key for every run.

    Whether the API is installed here or not, the only acceptable answers are a valid
    trace or nothing at all.
    """
    key = otel_run_key()

    assert key is None or key.key != "0" * 32
