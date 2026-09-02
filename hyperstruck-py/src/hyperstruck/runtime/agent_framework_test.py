"""The Agent Framework shim translates one vocabulary into the core's, and nothing else."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from hyperstruck._wire import Episode, ResolvedContext
from hyperstruck.identity import AgentIdentity
from hyperstruck.runtime.agent_framework import (
    SOURCE_FRAMEWORK,
    HyperstruckContextProvider,
)
from hyperstruck.runtime.run import RunReport, RunSeat

IDENTITY = AgentIdentity(agent_name="agent")


@dataclass
class _Text:
    text: str


@dataclass
class _Call:
    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Result:
    call_id: str
    result: Any = None
    exception: BaseException | None = None


@dataclass
class _Message:
    role: str
    contents: list[Any] = field(default_factory=list)
    text: str = ""


@dataclass
class _Tool:
    name: str
    description: str = ""
    input_schema: dict[str, Any] | None = None


class FakeClient:
    def __init__(self, context: ResolvedContext | None = None) -> None:
        self.context = context or ResolvedContext()
        self.observed: list[Episode] = []
        self.reinforced: list[dict[str, Any]] = []
        self.declined: list[dict[str, Any]] = []
        self.resolve_calls: list[dict[str, Any]] = []

    async def resolve(self, **kwargs: Any) -> ResolvedContext:
        self.resolve_calls.append(kwargs)
        return self.context

    async def observe(self, *, identity: Any, episode: Episode) -> None:  # noqa: ARG002
        self.observed.append(episode)

    async def reinforce(self, **kwargs: Any) -> None:
        self.reinforced.append(kwargs)

    async def decline(self, **kwargs: Any) -> None:
        self.declined.append(kwargs)


def _provider(
    client: FakeClient,
) -> tuple[HyperstruckContextProvider, RunSeat, list[RunReport]]:
    reports: list[RunReport] = []
    seat = RunSeat(client=client, identity=IDENTITY, on_report=reports.append)
    return HyperstruckContextProvider(seat), seat, reports


@pytest.mark.asyncio
async def test_the_recalled_block_is_returned_as_instructions() -> None:
    client = FakeClient(
        ResolvedContext(injected_text="- check the currency", offered_learning_ids=("a1",))
    )
    provider, _, _ = _provider(client)
    context = await provider.invoking(
        [_Message(role="user", text="reconcile the invoice")], thread_id="t1"
    )
    assert context.instructions == "- check the currency"


@pytest.mark.asyncio
async def test_the_goal_is_the_latest_human_turn_not_the_first() -> None:
    client = FakeClient()
    provider, _, _ = _provider(client)
    await provider.invoking(
        [
            _Message(role="user", text="set up the workspace"),
            _Message(role="assistant", text="done"),
            _Message(role="user", text="now reconcile the March invoices"),
        ],
        thread_id="t1",
    )
    assert client.resolve_calls[0]["goal"] == "now reconcile the March invoices"


@pytest.mark.asyncio
async def test_a_message_shape_the_shim_cannot_read_costs_the_goal_and_not_the_run() -> None:
    client = FakeClient()
    provider, _, reports = _provider(client)
    await provider.invoking([object()], thread_id="t1")
    await provider.invoked(thread_id="t1")
    assert len(reports) == 1


@pytest.mark.asyncio
async def test_the_roster_the_agent_had_reaches_the_episode() -> None:
    client = FakeClient()
    provider, _, _ = _provider(client)
    await provider.invoking(
        [_Message(role="user", text="go")],
        thread_id="t1",
        tools=[_Tool(name="search"), _Tool(name="never_called")],
    )
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "search"), _Call("2", "write")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "found"), _Result("2", "ok")])
        ],
        thread_id="t1",
    )
    assert [tool.name for tool in client.observed[0].available_tools] == [
        "search",
        "never_called",
    ]


@pytest.mark.asyncio
async def test_planned_calls_join_their_outcomes_into_steps() -> None:
    client = FakeClient()
    provider, _, _ = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "search"), _Call("2", "write")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "found"), _Result("2", "ok")])
        ],
        thread_id="t1",
    )
    assert len(client.observed[0].steps) == 2
    assert client.observed[0].steps[0].status == "completed"


@pytest.mark.asyncio
async def test_a_tool_that_raised_is_recorded_as_failed() -> None:
    client = FakeClient()
    provider, _, _ = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "write"), _Call("2", "write")])
        ],
        response_messages=[
            _Message(
                role="tool",
                contents=[
                    _Result("1", "denied", exception=RuntimeError("denied")),
                    _Result("2", "ok"),
                ],
            )
        ],
        thread_id="t1",
    )
    assert client.observed[0].steps[0].status == "failed"
    # A failure followed by a success is the prime learning, so the turn is kept.
    assert len(client.reinforced) == 1


@pytest.mark.asyncio
async def test_a_call_whose_result_never_came_back_is_dropped_rather_than_guessed() -> None:
    client = FakeClient()
    provider, _, _ = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(
        request_messages=[_Message(role="assistant", contents=[_Call("1", "search")])],
        thread_id="t1",
    )
    assert client.reinforced == []
    assert client.declined[0]["reason"] == "no_tool_calls"


@pytest.mark.asyncio
async def test_the_run_closes_even_when_the_invocation_raised() -> None:
    client = FakeClient()
    provider, _, reports = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(thread_id="t1", invoke_exception=RuntimeError("agent failed"))
    assert len(reports) == 1
    assert len(client.declined) == 1


@pytest.mark.asyncio
async def test_two_threads_served_by_one_provider_never_share_a_run() -> None:
    client = FakeClient()
    provider, seat, reports = _provider(client)
    await provider.invoking([_Message(role="user", text="left")], thread_id="t1")
    await provider.invoking([_Message(role="user", text="right")], thread_id="t2")
    assert len(seat.runs) == 2
    await provider.invoked(thread_id="t1")
    await provider.invoked(thread_id="t2")
    assert sorted(report.goal for report in reports) == ["left", "right"]


@pytest.mark.asyncio
async def test_a_second_invoked_for_one_invocation_is_not_a_second_close() -> None:
    client = FakeClient()
    provider, _, reports = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(thread_id="t1")
    await provider.invoked(thread_id="t1")
    assert len(reports) == 1


@pytest.mark.asyncio
async def test_this_seat_sends_no_receipt_because_it_sits_above_the_composition_stack() -> None:
    # It is handed the messages the agent assembled, not the params the model was sent, so
    # the only artefact it could return is the block it built itself. Echoing that back
    # asserts the very thing a receipt exists to prove.
    client = FakeClient(
        ResolvedContext(injected_text="- check the currency", offered_learning_ids=("a1",))
    )
    provider, _, _ = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "a"), _Call("2", "b")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "ok"), _Result("2", "ok")])
        ],
        thread_id="t1",
    )
    assert client.reinforced[0]["context_receipt"] is None
    # Delivery is still reported: the block did reach the agent, and that is a different
    # claim from the receipt, which is about what reached the model.
    assert client.reinforced[0]["is_delivered"] is True
    assert client.reinforced[0]["recall_outcome"] == "delivered"


@pytest.mark.asyncio
async def test_the_provider_names_its_own_host_without_overriding_a_caller_s() -> None:
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY)
    provider = HyperstruckContextProvider(seat)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "a"), _Call("2", "b")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "ok"), _Result("2", "ok")])
        ],
        thread_id="t1",
    )
    assert client.observed[0].source_framework == SOURCE_FRAMEWORK

    named_client = FakeClient()
    named_seat = RunSeat(
        client=named_client, identity=IDENTITY, source_framework="mine"
    )
    named = HyperstruckContextProvider(named_seat)
    await named.invoking([_Message(role="user", text="go")], thread_id="t1")
    await named.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "a"), _Call("2", "b")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "ok"), _Result("2", "ok")])
        ],
        thread_id="t1",
    )
    assert named_client.observed[0].source_framework == "mine"


@pytest.mark.asyncio
async def test_the_thread_id_reaches_the_episode_so_a_session_is_one_thread() -> None:
    client = FakeClient()
    provider, _, _ = _provider(client)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "a"), _Call("2", "b")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "ok"), _Result("2", "ok")])
        ],
        thread_id="t1",
    )
    assert client.observed[0].thread_id == "t1"


@pytest.mark.asyncio
async def test_a_report_callback_that_raises_does_not_break_the_invocation() -> None:
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY)

    def explode(_: RunReport) -> None:
        raise RuntimeError("customer bug")

    provider = HyperstruckContextProvider(seat, on_report=explode)
    await provider.invoking([_Message(role="user", text="go")], thread_id="t1")
    await provider.invoked(thread_id="t1")
    assert len(client.declined) == 1


@pytest.mark.asyncio
async def test_an_invocation_with_no_thread_id_is_still_closed() -> None:
    """Every other test here supplies one, so the fallback path was never exercised.

    Before the fix, `invoking` keyed the run on a minted identifier and `invoked` looked it
    up under the empty string, so the run was never found, never closed and never credited:
    it sat open holding its resolve reservation until the server's reclaim sweep noticed.
    """
    client = FakeClient()
    provider, seat, reports = _provider(client)
    await provider.invoking([_Message(role="user", text="go")])
    assert len(seat.runs) == 1
    await provider.invoked(
        request_messages=[
            _Message(role="assistant", contents=[_Call("1", "a"), _Call("2", "b")])
        ],
        response_messages=[
            _Message(role="tool", contents=[_Result("1", "ok"), _Result("2", "ok")])
        ],
    )
    assert len(reports) == 1
    assert len(seat.runs) == 0
    assert len(client.reinforced) == 1


@pytest.mark.asyncio
async def test_two_unthreaded_invocations_close_in_the_order_they_opened() -> None:
    """Without a thread there is nothing to correlate on, so oldest-first is the only
    reading available and it is the one that keeps a long run from being closed by a short
    one that started after it."""
    client = FakeClient()
    provider, seat, reports = _provider(client)
    await provider.invoking([_Message(role="user", text="first")])
    await provider.invoking([_Message(role="user", text="second")])
    await provider.invoked()
    await provider.invoked()
    assert [report.goal for report in reports] == ["first", "second"]
    assert len(seat.runs) == 0
