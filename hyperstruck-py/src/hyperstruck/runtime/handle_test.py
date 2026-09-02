"""The explicit handle closes the run on every path, and binds its key while it runs."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from hyperstruck._wire import Episode, ResolvedContext
from hyperstruck.identity import AgentIdentity
from hyperstruck.runtime.handle import hyperstruck_run
from hyperstruck.runtime.run import RunReport, RunSeat
from hyperstruck.runtime.run_key import resolve_run_key

IDENTITY = AgentIdentity(agent_name="agent")


class FakeClient:
    def __init__(self) -> None:
        self.observed: list[Episode] = []
        self.declined: list[dict[str, Any]] = []

    async def resolve(self, **_: Any) -> ResolvedContext:
        return ResolvedContext()

    async def observe(self, *, identity: Any, episode: Episode) -> None:  # noqa: ARG002
        self.observed.append(episode)

    async def reinforce(self, **_: Any) -> None:
        return None

    async def decline(self, **kwargs: Any) -> None:
        self.declined.append(kwargs)


def _seat(client: FakeClient) -> tuple[RunSeat, list[RunReport]]:
    reports: list[RunReport] = []
    return (
        RunSeat(client=client, identity=IDENTITY, on_report=reports.append),
        reports,
    )


def _two_steps(seat: RunSeat, run: Any) -> None:
    seat.record_planned_calls(run, [("1", "search", {}), ("2", "write", {})])
    seat.record_step(run, "1", "search", result="found")
    seat.record_step(run, "2", "write", result="ok")


@pytest.mark.asyncio
async def test_the_handle_closes_the_run_and_reports_an_exact_key() -> None:
    client = FakeClient()
    seat, reports = _seat(client)
    async with hyperstruck_run(seat, "reconcile the invoice") as run:
        assert not run.is_closed
    assert len(reports) == 1
    assert reports[0].run_key_source == "context"
    assert reports[0].is_run_key_inferred is False
    assert len(seat.runs) == 0


@pytest.mark.asyncio
async def test_a_raising_body_still_closes_the_run_as_unsuccessful() -> None:
    client = FakeClient()
    seat, reports = _seat(client)
    with pytest.raises(RuntimeError, match="host blew up"):
        async with hyperstruck_run(seat, "g") as run:
            _two_steps(seat, run)
            raise RuntimeError("host blew up")
    assert len(reports) == 1
    assert client.observed[0].outcome.is_success is False


@pytest.mark.asyncio
async def test_a_cancelled_body_still_closes_the_run() -> None:
    # A cancellation is not an ordinary exception and is the path most likely to leave a
    # run open holding its resolve reservation, which the server can only reclaim by sweep.
    client = FakeClient()
    seat, reports = _seat(client)

    async def body() -> None:
        async with hyperstruck_run(seat, "g"):
            await asyncio.sleep(3600)

    task = asyncio.ensure_future(body())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(reports) == 1
    assert len(seat.runs) == 0


@pytest.mark.asyncio
async def test_the_key_is_bound_for_the_body_and_restored_after() -> None:
    client = FakeClient()
    seat, _ = _seat(client)
    before = resolve_run_key().source
    async with hyperstruck_run(seat, "g") as run:
        key = resolve_run_key()
        assert key.source == "context"
        assert run.run_id.startswith(f"agent:{key.key}:")
    assert resolve_run_key().source == before


@pytest.mark.asyncio
async def test_a_model_call_inside_the_handle_joins_the_handle_s_run() -> None:
    client = FakeClient()
    seat, _ = _seat(client)
    async with hyperstruck_run(seat, "reconcile the invoice") as run:
        # ``for_call`` is what the model seat uses per call. Inside the handle it must find
        # the handle's run rather than opening one beside it.
        assert seat.for_call("something else inferred") is run
    assert client.observed == [] or client.observed[0].goal == "reconcile the invoice"


@pytest.mark.asyncio
async def test_two_concurrent_handles_keep_their_runs_apart() -> None:
    client = FakeClient()
    seat, reports = _seat(client)

    async def one(goal: str, delay: float) -> None:
        async with hyperstruck_run(seat, goal):
            await asyncio.sleep(delay)

    await asyncio.gather(one("left", 0.01), one("right", 0))
    assert sorted(report.goal for report in reports) == ["left", "right"]
    assert reports[0].run_id != reports[1].run_id


@pytest.mark.asyncio
async def test_a_body_that_closed_the_run_itself_is_not_closed_twice() -> None:
    client = FakeClient()
    seat, reports = _seat(client)
    async with hyperstruck_run(seat, "g") as run:
        await seat.before_model_call(run)
        await seat.close(run)
    assert len(reports) == 1


@pytest.mark.asyncio
async def test_the_handle_s_own_callback_gets_the_same_report_the_seat_emits() -> None:
    client = FakeClient()
    seat, reports = _seat(client)
    handed: list[RunReport] = []
    async with hyperstruck_run(seat, "g", on_report=handed.append):
        pass
    assert handed == reports


@pytest.mark.asyncio
async def test_the_roster_reaches_the_episode_from_the_handle() -> None:
    from hyperstruck._wire import ToolSpec

    client = FakeClient()
    seat, _ = _seat(client)
    async with hyperstruck_run(seat, "g", [ToolSpec(name="search")]) as run:
        _two_steps(seat, run)
    assert [tool.name for tool in client.observed[0].available_tools] == ["search"]
