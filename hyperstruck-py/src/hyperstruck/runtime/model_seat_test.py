"""The wrapped model clients: what they inject, what they capture, and what they survive.

The fakes here are duck-typed on purpose, exactly as the wrappers are. Typing them against
the real SDKs would test that this package can import ``anthropic`` and ``openai``, which
it deliberately cannot, and would miss the shape that actually matters in a deployment: a
customer's vendored or gateway-fronted client returning plain dicts.
"""

from __future__ import annotations

import asyncio

from types import SimpleNamespace
from typing import Any

import pytest

from hyperstruck._wire import ResolvedContext
from hyperstruck.identity import AgentIdentity
from hyperstruck.runtime.model_seat import wrap_anthropic, wrap_openai
from hyperstruck.runtime.run import RunSeat
from hyperstruck.runtime.run_key import RunKey

IDENTITY = AgentIdentity(agent_name="support-bot")
ADVICE = "Relevant learnings from prior runs (hyperstruck):\n- prefer the bulk endpoint"


class FakeBoundary:
    def __init__(self, context: ResolvedContext | None = None) -> None:
        self._context = context if context is not None else ResolvedContext()
        self.reinforced: list[dict[str, Any]] = []
        self.declined: list[dict[str, Any]] = []
        self.observed: list[Any] = []

    async def resolve(self, **kwargs: Any) -> ResolvedContext:
        return self._context

    async def observe(self, *, identity: Any, episode: Any) -> None:
        self.observed.append(episode)

    async def reinforce(self, **kwargs: Any) -> None:
        self.reinforced.append(kwargs)

    async def decline(self, **kwargs: Any) -> None:
        self.declined.append(kwargs)


class FakeAnthropic:
    """One fixed run key, so every call of a test lands on the same run."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses
        self.sent: list[dict[str, Any]] = []
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return self._responses.pop(0)


class SyncAnthropic:
    def __init__(self) -> None:
        self.messages = SimpleNamespace(create=lambda **kwargs: None)


class FakeOpenAI:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses
        self.sent: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return self._responses.pop(0)


def _seat(boundary: FakeBoundary, *, grace: float = 0.0) -> RunSeat:
    key = RunKey(key="fixed", source="context", is_inferred=False)
    return RunSeat(
        client=boundary,
        identity=IDENTITY,
        run_key_resolvers=(lambda: key,),
        # Zero by default here, not in production: these tests are about what the seat does
        # when the window has elapsed, and waiting a real minute for each would say nothing
        # extra. The window's own behaviour, that a further call inside it continues the
        # run, has its own test below with a real one.
        close_grace_seconds=grace,
    )


async def _settle() -> None:
    """Let the seat's own grace-window timer fire.

    The close is driven by the seat rather than by the caller, which is the whole point:
    leaving the sweep to the customer would make the documented default attachment point
    earn no credit for anyone who did not read that paragraph.
    """
    for _ in range(8):
        await asyncio.sleep(0)


def _anthropic_tool_use(call_id: str = "t1") -> dict[str, Any]:
    return {"content": [{"type": "tool_use", "id": call_id, "name": "search", "input": {"q": "x"}}]}


def _results(*blocks: dict[str, Any]) -> dict[str, Any]:
    """The user turn a customer's loop sends back carrying tool results."""
    return {
        "role": "user",
        "content": [{"type": "tool_result", **block} for block in blocks],
    }


def _anthropic_answer() -> dict[str, Any]:
    return {"content": [{"type": "text", "text": "done"}]}


def _openai_tool_use(call_id: str = "t1") -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": call_id,
                            "function": {"name": "search", "arguments": '{"q": "x"}'},
                        }
                    ]
                }
            }
        ]
    }


def _openai_answer() -> dict[str, Any]:
    return {"choices": [{"message": {"content": "done"}}]}


async def test_the_block_goes_into_the_system_prompt_and_not_a_synthetic_user_turn() -> None:
    """A user turn the customer did not write changes what their own loop sees.

    The seat must be invisible to everything except the model.
    """
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeAnthropic([_anthropic_answer()])
    wrap_anthropic(client, _seat(boundary))

    await client.messages.create(
        model="claude-opus-5",
        system="You are terse.",
        messages=[{"role": "user", "content": "find the renewal"}],
    )
    sent = client.sent[0]
    assert sent["system"].startswith(ADVICE)
    assert sent["system"].endswith("You are terse.")
    assert sent["messages"] == [{"role": "user", "content": "find the renewal"}]


async def test_a_system_block_list_is_prepended_to_rather_than_stringified() -> None:
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeAnthropic([_anthropic_answer()])
    wrap_anthropic(client, _seat(boundary))

    await client.messages.create(
        system=[{"type": "text", "text": "You are terse."}],
        messages=[{"role": "user", "content": "g"}],
    )
    assert client.sent[0]["system"][0] == {"type": "text", "text": ADVICE}


async def test_an_unreadable_system_shape_is_left_alone_rather_than_corrupted() -> None:
    """No recall is better than a prompt we mangled on the way past."""
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeAnthropic([_anthropic_answer()])
    wrap_anthropic(client, _seat(boundary))

    sentinel = object()
    await client.messages.create(system=sentinel, messages=[{"role": "user", "content": "g"}])
    assert client.sent[0]["system"] is sentinel


async def test_openai_injection_sits_after_the_customers_own_system_message() -> None:
    """Demoting their instruction to give our block a better position changes their agent."""
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeOpenAI([_openai_answer()])
    wrap_openai(client, _seat(boundary))

    await client.chat.completions.create(
        model="gpt",
        messages=[
            {"role": "system", "content": "You are terse."},
            {"role": "user", "content": "find the renewal"},
        ],
    )
    roles = [m["role"] for m in client.sent[0]["messages"]]
    assert roles == ["system", "system", "user"]
    assert client.sent[0]["messages"][0]["content"] == "You are terse."
    assert client.sent[0]["messages"][1]["content"] == ADVICE


async def test_one_recall_is_spent_however_many_times_the_call_is_retried() -> None:
    """A retried send must show the model the block it was shown the first time.

    Rate limits and overloads routinely make the SDK's own retry resend the same logical
    call, so the hook firing several times for one logical step is ordinary rather than
    exceptional.
    """
    resolves = 0

    class Counting(FakeBoundary):
        async def resolve(self, **kwargs: Any) -> ResolvedContext:
            nonlocal resolves
            resolves += 1
            return ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",))

    boundary = Counting()
    client = FakeAnthropic([_anthropic_tool_use(), _anthropic_tool_use(), _anthropic_answer()])
    wrap_anthropic(client, _seat(boundary))

    for _ in range(3):
        await client.messages.create(messages=[{"role": "user", "content": "g"}])
    assert resolves == 1
    assert {sent["system"] for sent in client.sent} == {ADVICE}


async def test_a_tool_outcome_is_harvested_from_the_next_request() -> None:
    """A model-layer seat never sees a tool run, only the result fed back to the model.

    Exact for any loop that returns results, and blind to a tool whose result the customer
    never shows it, which the ledger's join then drops rather than guessing at.
    """
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    seat = _seat(boundary)
    client = FakeAnthropic([_anthropic_tool_use("t1"), _anthropic_tool_use("t2"), _anthropic_answer()])
    wrap_anthropic(client, seat)

    await client.messages.create(messages=[{"role": "user", "content": "g"}])
    await client.messages.create(
        messages=[
            {"role": "user", "content": "g"},
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "found it"}
                ],
            },
        ]
    )
    await client.messages.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "found it"},
                    {"type": "tool_result", "tool_use_id": "t2", "content": "and this"},
                ],
            }
        ]
    )
    await _settle()
    episode = boundary.observed[0]
    assert [step.id for step in episode.steps] == ["t1", "t2"]
    assert episode.steps[0].result == "found it"


async def test_a_tool_result_marked_an_error_is_recorded_as_a_failure() -> None:
    """A failure recovered from is the highest-signal turn the corpus can learn from.

    Two steps, and deliberately: one is a turn that did a single thing, which the corpus
    cannot contrast against anything, so the gate declines it.
    """
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeAnthropic(
        [_anthropic_tool_use("t1"), _anthropic_tool_use("t2"), _anthropic_answer()]
    )
    wrap_anthropic(client, _seat(boundary))

    await client.messages.create(messages=[{"role": "user", "content": "g"}])
    await client.messages.create(
        messages=[_results({"tool_use_id": "t1", "content": "429 rate limited", "is_error": True})]
    )
    await client.messages.create(
        messages=[
            _results(
                {"tool_use_id": "t1", "content": "429 rate limited", "is_error": True},
                {"tool_use_id": "t2", "content": "retried and found it"},
            )
        ]
    )
    await _settle()
    steps = boundary.observed[0].steps
    assert [step.status for step in steps] == ["failed", "completed"]
    assert steps[0].error == "429 rate limited"


async def test_a_run_that_did_one_thing_declines_rather_than_teaching_from_it() -> None:
    """One material step is a turn the corpus cannot contrast against anything."""
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeAnthropic([_anthropic_tool_use("t1"), _anthropic_answer()])
    wrap_anthropic(client, _seat(boundary))

    await client.messages.create(messages=[{"role": "user", "content": "g"}])
    await client.messages.create(messages=[_results({"tool_use_id": "t1", "content": "ok"})])
    await _settle()
    assert boundary.observed == []
    await _settle()
    assert boundary.declined[0]["reason"] == "below_material_threshold"


async def test_the_run_closes_when_the_model_stops_asking_for_tools() -> None:
    """The only terminal signal a model-layer seat gets, and the report says as much.

    A customer wanting an exact boundary uses the explicit run handle, which is what it is
    for rather than a fallback.
    """
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    seat = _seat(boundary)
    client = FakeOpenAI([_openai_tool_use("t1"), _openai_tool_use("t2"), _openai_answer()])
    wrap_openai(client, seat)

    await client.chat.completions.create(messages=[{"role": "user", "content": "g"}])
    await client.chat.completions.create(
        messages=[{"role": "tool", "tool_call_id": "t1", "content": "ok"}]
    )
    assert len(seat.runs) == 1
    await client.chat.completions.create(
        messages=[
            {"role": "tool", "tool_call_id": "t1", "content": "ok"},
            {"role": "tool", "tool_call_id": "t2", "content": "ok"},
        ]
    )
    await _settle()
    assert len(seat.runs) == 0
    await _settle()
    assert boundary.reinforced
    assert "prefer the bulk endpoint" in boundary.reinforced[0]["context_receipt"]


async def test_the_receipt_is_located_against_the_params_as_they_were_sent() -> None:
    """The commercial point of attaching here at all: an artefact we did not author."""
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    client = FakeAnthropic(
        [_anthropic_tool_use("t1"), _anthropic_tool_use("t2"), _anthropic_answer()]
    )
    wrap_anthropic(client, _seat(boundary))

    await client.messages.create(messages=[{"role": "user", "content": "g"}])
    await client.messages.create(messages=[_results({"tool_use_id": "t1", "content": "ok"})])
    await client.messages.create(
        messages=[
            _results(
                {"tool_use_id": "t1", "content": "ok"},
                {"tool_use_id": "t2", "content": "ok"},
            )
        ]
    )
    await _settle()
    assert boundary.reinforced[0]["is_delivered"] is True
    assert boundary.reinforced[0]["recall_outcome"] == "delivered"
    assert "prefer the bulk endpoint" in boundary.reinforced[0]["context_receipt"]


async def test_a_boundary_that_is_down_never_breaks_the_customers_model_call() -> None:
    """A learning client that can break a model call is a learning client they remove."""

    class Broken(FakeBoundary):
        async def resolve(self, **kwargs: Any) -> ResolvedContext:
            raise RuntimeError("boundary down")

    client = FakeAnthropic([_anthropic_answer()])
    wrap_anthropic(client, _seat(Broken()))
    response = await client.messages.create(messages=[{"role": "user", "content": "g"}])
    assert response == _anthropic_answer()
    assert "system" not in client.sent[0]


async def test_a_malformed_argument_blob_still_records_the_step() -> None:
    """A model can emit invalid JSON, and the step still happened."""
    boundary = FakeBoundary()
    seat = _seat(boundary)
    broken = _openai_tool_use("t1")
    broken["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{not json"
    client = FakeOpenAI([broken, _openai_tool_use("t2"), _openai_answer()])
    wrap_openai(client, seat)

    await client.chat.completions.create(messages=[{"role": "user", "content": "g"}])
    await client.chat.completions.create(
        messages=[{"role": "tool", "tool_call_id": "t1", "content": "ok"}]
    )
    await client.chat.completions.create(
        messages=[
            {"role": "tool", "tool_call_id": "t1", "content": "ok"},
            {"role": "tool", "tool_call_id": "t2", "content": "ok"},
        ]
    )
    await _settle()
    assert boundary.observed[0].steps[0].args == {}


async def test_the_tool_roster_is_read_from_either_sdks_shape() -> None:
    """The server reads restraint from what was available and declined."""
    boundary = FakeBoundary()
    seat = _seat(boundary)
    client = FakeOpenAI([_openai_tool_use("t1"), _openai_tool_use("t2"), _openai_answer()])
    wrap_openai(client, seat)

    await client.chat.completions.create(
        messages=[{"role": "user", "content": "g"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "look things up",
                    "parameters": {"properties": {"q": {"type": "string"}}},
                },
            }
        ],
    )
    await client.chat.completions.create(
        messages=[{"role": "tool", "tool_call_id": "t1", "content": "ok"}]
    )
    await client.chat.completions.create(
        messages=[
            {"role": "tool", "tool_call_id": "t1", "content": "ok"},
            {"role": "tool", "tool_call_id": "t2", "content": "ok"},
        ]
    )
    await _settle()
    roster = boundary.observed[0].available_tools
    assert [tool.name for tool in roster] == ["search"]
    assert roster[0].category is None, "a guess would look like a declaration"


async def test_wrapping_a_synchronous_client_refuses_rather_than_capturing_nothing() -> None:
    """It would otherwise appear to work while recording not one run."""
    with pytest.raises(TypeError, match="async client only"):
        wrap_anthropic(SyncAnthropic(), _seat(FakeBoundary()))


async def test_wrapping_something_that_is_not_a_model_client_says_so() -> None:
    with pytest.raises(TypeError, match="does not look like"):
        wrap_openai(object(), _seat(FakeBoundary()))


async def test_everything_else_on_the_client_still_reaches_it() -> None:
    """A drop-in replacement rather than a facade the customer has to learn."""
    client = FakeAnthropic([])
    client.api_key = "sk-test"
    wrapped = wrap_anthropic(client, _seat(FakeBoundary()))
    assert wrapped.api_key == "sk-test"


async def test_the_adapter_stamps_its_own_provenance_on_the_episode() -> None:
    """The platform tells surfaces apart by this field, so it must name this one.

    Not "hyperstruck-core": the package deliberately never imports the engine, and naming
    the engine here would attribute a foreign customer's episode to it.
    """
    boundary = FakeBoundary()
    client = FakeOpenAI([_openai_tool_use("t1"), _openai_tool_use("t2"), _openai_answer()])
    wrap_openai(client, _seat(boundary))

    await client.chat.completions.create(messages=[{"role": "user", "content": "g"}])
    await client.chat.completions.create(
        messages=[{"role": "tool", "tool_call_id": "t1", "content": "ok"}]
    )
    await client.chat.completions.create(
        messages=[
            {"role": "tool", "tool_call_id": "t1", "content": "ok"},
            {"role": "tool", "tool_call_id": "t2", "content": "ok"},
        ]
    )
    await _settle()
    assert boundary.observed[0].source_framework == "openai-sdk"


async def test_a_caller_who_named_their_own_surface_keeps_it() -> None:
    """Their name is a decision; the adapter's is a fallback."""
    boundary = FakeBoundary()
    seat = RunSeat(
        client=boundary,
        identity=IDENTITY,
        run_key_resolvers=(lambda: RunKey(key="fixed", source="context", is_inferred=False),),
        source_framework="mono-agent-service",
        close_grace_seconds=0.0,
    )
    client = FakeAnthropic([_anthropic_answer()])
    wrap_anthropic(client, seat)
    await client.messages.create(messages=[{"role": "user", "content": "g"}])
    await _settle()
    assert boundary.declined[0]["source_framework"] == "mono-agent-service"


async def test_every_model_call_is_counted_including_the_one_that_asked_for_no_tools() -> None:
    """The count is of calls, so it counts calls.

    `record_planned_calls` did the counting and the adapters skip it entirely when a
    response asks for no tools, so the final answer of every run went uncounted and the
    figure diverged from the TypeScript seat's.
    """
    boundary = FakeBoundary()
    seat = _seat(boundary)
    client = FakeOpenAI([_openai_tool_use("t1"), _openai_tool_use("t2"), _openai_answer()])
    wrap_openai(client, seat)
    await client.chat.completions.create(messages=[{"role": "user", "content": "g"}])
    await client.chat.completions.create(
        messages=[{"role": "tool", "tool_call_id": "t1", "content": "ok"}]
    )
    await client.chat.completions.create(
        messages=[
            {"role": "tool", "tool_call_id": "t1", "content": "ok"},
            {"role": "tool", "tool_call_id": "t2", "content": "ok"},
        ]
    )
    await _settle()
    assert boundary.reinforced
    report = seat_report(seat)
    assert report is not None
    assert report.model_call_count == 3, f"counted {report.model_call_count} of 3 calls"


def seat_report(seat: RunSeat):
    """The last report the seat emitted, for a test that did not register a sink."""
    return getattr(seat, "_last_report", None)


class _FakeStreamManager:
    """What ``AsyncAnthropic.messages.stream`` returns: an async context manager."""

    def __init__(self, events: list[str], final: dict[str, Any]) -> None:
        self.events = events
        self._final = final
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> Any:
        self.entered = True
        return self

    async def __aexit__(self, *_: Any) -> None:
        self.exited = True

    async def get_final_message(self) -> dict[str, Any]:
        return self._final

    async def __aiter__(self):  # pragma: no cover - iterated in the test below
        for event in self.events:
            yield event


class _FakeStreamingAnthropic:
    def __init__(self, finals: list[dict[str, Any]]) -> None:
        self._finals = list(finals)
        self.sent: list[dict[str, Any]] = []
        self.managers: list[_FakeStreamManager] = []
        self.messages = SimpleNamespace(create=self._create, stream=self._stream)

    async def _create(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return self._finals.pop(0)

    def _stream(self, **kwargs: Any) -> _FakeStreamManager:
        self.sent.append(kwargs)
        manager = _FakeStreamManager(["a", "b"], self._finals.pop(0))
        self.managers.append(manager)
        return manager


async def test_a_streaming_run_is_captured_rather_than_silently_dropped() -> None:
    """Before this the seat wrapped only the buffered call, so a customer who streams got
    nothing at all: no injection, no episode, no run, and no error to explain it."""
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    seat = _seat(boundary)
    client = _FakeStreamingAnthropic(
        [_anthropic_tool_use("t1"), _anthropic_tool_use("t2"), _anthropic_answer()]
    )
    wrap_anthropic(client, seat)

    async with client.messages.stream(messages=[{"role": "user", "content": "g"}]):
        pass
    async with client.messages.stream(
        messages=[_results({"tool_use_id": "t1", "content": "ok"})]
    ):
        pass
    async with client.messages.stream(
        messages=[
            _results(
                {"tool_use_id": "t1", "content": "ok"},
                {"tool_use_id": "t2", "content": "ok"},
            )
        ]
    ):
        pass
    await _settle()

    assert boundary.reinforced, "a streamed run reached neither observe nor reinforce"
    assert "prefer the bulk endpoint" in boundary.reinforced[0]["context_receipt"]
    assert len(boundary.observed[0].steps) == 2


async def test_a_streamed_call_still_receives_the_injected_block() -> None:
    boundary = FakeBoundary(ResolvedContext(injected_text=ADVICE, offered_learning_ids=("l1",)))
    seat = _seat(boundary)
    client = _FakeStreamingAnthropic([_anthropic_answer()])
    wrap_anthropic(client, seat)
    async with client.messages.stream(messages=[{"role": "user", "content": "g"}]):
        pass
    assert "prefer the bulk endpoint" in str(client.sent[0].get("system"))


async def test_the_customer_s_own_stream_object_is_handed_back_untouched() -> None:
    """A seat that buffered a stream to inspect it would remove the one property a
    customer chose streaming for."""
    boundary = FakeBoundary()
    seat = _seat(boundary)
    client = _FakeStreamingAnthropic([_anthropic_answer()])
    wrap_anthropic(client, seat)
    async with client.messages.stream(messages=[{"role": "user", "content": "g"}]) as stream:
        assert stream is client.managers[0]
        assert stream.entered is True
    assert client.managers[0].exited is True


async def test_wrapping_the_same_client_twice_does_not_nest_two_seats() -> None:
    """Nested, every model call would open two runs, inject twice, and write two episodes
    for one turn."""
    boundary = FakeBoundary()
    seat = _seat(boundary)
    client = FakeAnthropic([_anthropic_answer()])
    wrap_anthropic(client, seat)
    wrap_anthropic(client, seat)
    await client.messages.create(messages=[{"role": "user", "content": "g"}])
    await _settle()
    assert len(boundary.declined) + len(boundary.observed) == 1
