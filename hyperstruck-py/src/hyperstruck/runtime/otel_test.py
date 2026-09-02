"""The conversation rung is best effort, and its failure mode is loss of quality only."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from hyperstruck.runtime.otel import (
    CONVERSATION_ID_ATTRIBUTE,
    conversation_run_key,
    resolvers_with_conversation,
)
from hyperstruck.runtime.run_key import RunKey, resolve_run_key


class _Context:
    def __init__(self, *, is_valid: bool) -> None:
        self.is_valid = is_valid


class _Span:
    def __init__(self, *, is_valid: bool = True, attributes: Any = None) -> None:
        self._context = _Context(is_valid=is_valid)
        if attributes is not None:
            self.attributes = attributes

    def get_span_context(self) -> _Context:
        return self._context


@pytest.fixture
def fake_otel(monkeypatch: pytest.MonkeyPatch):
    """Install a stand-in for the OpenTelemetry API, since we take no dependency on it."""

    def install(span: Any) -> None:
        package = ModuleType("opentelemetry")
        trace = ModuleType("opentelemetry.trace")
        trace.get_current_span = lambda: span  # type: ignore[attr-defined]
        package.trace = trace  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "opentelemetry", package)
        monkeypatch.setitem(sys.modules, "opentelemetry.trace", trace)

    return install


def test_with_no_tracer_installed_the_rung_answers_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    assert conversation_run_key() is None


def test_the_conversation_id_is_read_when_the_host_set_one(fake_otel: Any) -> None:
    fake_otel(_Span(attributes={CONVERSATION_ID_ATTRIBUTE: "session-42"}))
    key = conversation_run_key()
    assert key == RunKey(key="session-42", source="conversation", is_inferred=False)


def test_a_non_recording_span_is_treated_as_absent(fake_otel: Any) -> None:
    # Its all-zero context would otherwise become one shared key for every concurrent run
    # in the process, which is precisely the collision the ladder exists to prevent.
    fake_otel(_Span(is_valid=False, attributes={CONVERSATION_ID_ATTRIBUTE: "session-42"}))
    assert conversation_run_key() is None


def test_a_provider_that_exposes_no_attributes_falls_through(fake_otel: Any) -> None:
    fake_otel(_Span())
    assert conversation_run_key() is None


def test_an_empty_or_non_string_conversation_id_is_not_an_answer(fake_otel: Any) -> None:
    fake_otel(_Span(attributes={CONVERSATION_ID_ATTRIBUTE: ""}))
    assert conversation_run_key() is None
    fake_otel(_Span(attributes={CONVERSATION_ID_ATTRIBUTE: 7}))
    assert conversation_run_key() is None


def test_an_api_that_raises_costs_correlation_quality_and_never_the_run(
    fake_otel: Any,
) -> None:
    class _Exploding:
        def get_span_context(self) -> Any:
            raise RuntimeError("the tracer changed shape")

    fake_otel(_Exploding())
    assert conversation_run_key() is None


def test_the_conversation_rung_sits_below_trace_and_above_the_seat_s_own_wrapper() -> None:
    def trace() -> RunKey | None:
        return None

    def context() -> RunKey | None:
        return None

    ladder = resolvers_with_conversation((trace, context))
    assert ladder[0] is trace
    assert ladder[1] is conversation_run_key
    assert ladder[2] is context


def test_an_empty_base_ladder_still_yields_a_usable_one() -> None:
    assert resolvers_with_conversation(()) == (conversation_run_key,)


def test_a_trace_rung_that_answered_wins_over_the_conversation_rung(fake_otel: Any) -> None:
    fake_otel(_Span(attributes={CONVERSATION_ID_ATTRIBUTE: "session-42"}))
    ladder = resolvers_with_conversation(
        (lambda: RunKey(key="trace-1", source="trace", is_inferred=False),)
    )
    assert resolve_run_key(ladder).source == "trace"


def test_the_conversation_rung_answers_when_the_trace_rung_did_not(fake_otel: Any) -> None:
    fake_otel(_Span(attributes={CONVERSATION_ID_ATTRIBUTE: "session-42"}))
    ladder = resolvers_with_conversation((lambda: None,))
    key = resolve_run_key(ladder)
    assert key.key == "session-42"
    assert key.source == "conversation"


def test_the_rung_is_not_in_the_shipped_default_ladder() -> None:
    # Reading a span attribute is not part of the API's promised surface, so opting into it
    # is the customer's decision about their own instrumentation, not a library's about
    # everyone's.
    from hyperstruck.runtime.run_key import DEFAULT_RESOLVERS

    assert conversation_run_key not in DEFAULT_RESOLVERS


def test_the_pinned_attribute_name_is_the_conventions_own() -> None:
    # Pinned in one place precisely because the conventions are still Development and the
    # name can change without a major version bump.
    assert CONVERSATION_ID_ATTRIBUTE == "gen_ai.conversation.id"


def test_a_stand_in_span_object_is_all_the_adapter_needs(fake_otel: Any) -> None:
    # The adapter is duck-typed rather than depending on the API's types, so a tracer that
    # is not OpenTelemetry can be plugged in with a resolver of three lines.
    fake_otel(
        SimpleNamespace(
            get_span_context=lambda: SimpleNamespace(is_valid=True),
            attributes={CONVERSATION_ID_ATTRIBUTE: "from-another-tracer"},
        )
    )
    assert conversation_run_key() is not None
