"""The middleware loop, driven against a fake LearningClient port."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from hyperstruck._wire import Episode, ResolvedContext
from hyperstruck.identity import AgentIdentity
from hyperstruck.langgraph import middleware as mw_module
from hyperstruck.langgraph.ledger import LEDGERS, RUN_ID_STATE_KEY
from hyperstruck.langgraph.middleware import (
    HyperstruckLearningMiddleware,
    assert_innermost,
)


class FakeLearningClient:
    def __init__(self, injected_text: str | None = "LEARNINGS", ids=("l1", "l2")) -> None:
        self.injected_text = injected_text
        self.ids = tuple(ids)
        self.resolved: list[str] = []
        self.resolved_tools: list[tuple] = []
        self.observed: list[Episode] = []
        self.reinforced: list[tuple[Episode, bool]] = []

    async def resolve(self, *, identity, run_id, goal, available_tools=(), max_learnings=8, model_context_window=None):
        self.resolved.append(run_id)
        self.resolved_tools.append(tuple(available_tools))
        return ResolvedContext(injected_text=self.injected_text, offered_learning_ids=self.ids)

    async def observe(self, *, identity, episode) -> None:
        self.observed.append(episode)

    async def reinforce(self, *, identity, episode, is_org_promotion_allowed=False) -> None:
        self.reinforced.append((episode, is_org_promotion_allowed))


class Req:
    def __init__(self, state, messages, tools=None, tool_call=None) -> None:
        self.state = state
        self.messages = messages
        self.tools = tools
        self.tool_call = tool_call

    def override(self, messages):
        return Req(self.state, messages, self.tools, self.tool_call)


def test_requires_identity() -> None:
    with pytest.raises(ValueError, match="identity"):
        HyperstruckLearningMiddleware(client=FakeLearningClient())


async def test_full_loop_resolves_injects_records_and_writes() -> None:
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", org_id="org", client=fake)

    state = {"messages": [HumanMessage("look up the account")]}
    delta = await mw.abefore_agent(state, None)
    state.update(delta)
    run_id = state[RUN_ID_STATE_KEY]
    assert run_id.startswith("bot:")

    # Model call: prefetched resolve is awaited and injected.
    captured = {}

    async def handler(req):
        captured["req"] = req
        return "model-out"

    req = Req(state=state, messages=[HumanMessage("look up the account")])
    await mw.awrap_model_call(req, handler)
    injected = captured["req"].messages[0]
    assert isinstance(injected, SystemMessage)
    assert injected.content == "LEARNINGS"
    assert fake.resolved == [run_id]

    # Model plans a tool call.
    ai = AIMessage(content="", tool_calls=[{"id": "c1", "name": "lookup", "args": {"id": 7}}])
    await mw.aafter_model({**state, "messages": [ai]}, None)

    # Tool runs; outcome joined by id.
    tool_req = Req(state=state, messages=[], tool_call={"id": "c1", "name": "lookup"})

    async def tool_handler(req):
        return ToolMessage(content="found", tool_call_id="c1")

    await mw.awrap_tool_call(tool_req, tool_handler)
    assert mw.stats.tool_calls == 1

    # Invoke end: observe + reinforce, episode has the joined step.
    await mw.aafter_agent(state, None)
    assert len(fake.observed) == 1
    assert fake.observed[0].steps[0].id == "c1"
    assert len(fake.reinforced) == 1
    assert mw.stats.runs_observed == 1
    assert LEDGERS.get(run_id) is None  # popped at end


async def test_resolve_failure_fails_open() -> None:
    class FailingClient(FakeLearningClient):
        async def resolve(self, **kwargs):
            raise RuntimeError("platform down")

    fake = FailingClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))

    captured = {}

    async def handler(req):
        captured["req"] = req
        return "ok"

    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("x")]), handler)
    # No injection, run proceeds, error counted.
    assert not isinstance(captured["req"].messages[0], SystemMessage)
    assert mw.stats.errors == 1


async def test_cancelled_run_is_not_observed() -> None:
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))
    # Simulate cancellation: aafter_agent never fires.
    assert fake.observed == []
    assert mw.stats.runs_started == 1
    assert mw.stats.runs_observed == 0
    # The skip is visible: started but not observed and not in flight (we pop here).
    LEDGERS.pop(state[RUN_ID_STATE_KEY])
    assert mw.stats.runs_incomplete(live=0) == 1


async def test_tool_aware_resolve_passes_registered_tools() -> None:
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(
        agent_name="bot", client=fake, tools=["search", {"name": "db", "description": "query the db"}]
    )
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))
    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("x")]), lambda req: _noop(req))
    tool_names = {t.name for t in fake.resolved_tools[0]}
    assert tool_names == {"search", "db"}


async def _noop(req):
    return "ok"


class DrainableClient(FakeLearningClient):
    """A fake client that records whether the middleware drained/closed it."""

    def __init__(self) -> None:
        super().__init__()
        self.drained = 0
        self.closed = 0

    async def drain(self, timeout: float = 30.0) -> None:
        self.drained += 1

    async def aclose(self) -> None:
        self.closed += 1


async def test_aclose_drains_the_client() -> None:
    fake = DrainableClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    await mw.aclose()
    assert fake.closed == 1


async def test_async_context_drains_on_exit() -> None:
    fake = DrainableClient()
    async with HyperstruckLearningMiddleware(agent_name="bot", client=fake) as mw:
        assert isinstance(mw, HyperstruckLearningMiddleware)
    assert fake.closed == 1


async def test_drain_is_noop_when_client_has_no_drain() -> None:
    # A custom client without drain/aclose must not raise.
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    await mw.drain()
    await mw.aclose()


def test_assert_innermost_passes_when_last() -> None:
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    other = object()
    assert_innermost([other, mw], mw)  # innermost (last): no raise


def test_assert_innermost_raises_when_not_last() -> None:
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    other = object()
    with pytest.raises(ValueError, match="innermost"):
        assert_innermost([mw, other], mw)


async def test_per_invoke_identity_override(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLearningClient()
    mw = HyperstruckLearningMiddleware(agent_name="default-bot", client=fake)
    override = AgentIdentity(agent_name="tenant-2-bot", org_id="org-2")

    def fake_config(key):
        return override if key == mw_module.IDENTITY_CONFIG_KEY else None

    monkeypatch.setattr(mw_module, "_config_value", fake_config)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))
    assert state[RUN_ID_STATE_KEY].startswith("tenant-2-bot:")
