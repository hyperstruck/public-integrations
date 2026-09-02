"""The middleware loop, driven against a fake LearningClient port."""

from __future__ import annotations

import asyncio

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
    def __init__(
        self,
        injected_text: str | None = "LEARNINGS",
        ids=("l1", "l2"),
        injected_facts_text: str | None = None,
        claim_ids=(),
    ) -> None:
        self.injected_text = injected_text
        self.ids = tuple(ids)
        self.injected_facts_text = injected_facts_text
        self.claim_ids = tuple(claim_ids)
        self.resolved: list[str] = []
        self.resolved_tools: list[tuple] = []
        self.observed: list[Episode] = []
        self.reinforced: list[tuple[Episode, bool]] = []
        self.receipts: list[str | None] = []
        self.deliveries: list[bool | None] = []
        self.recall_outcomes: list[str | None] = []

    async def resolve(self, *, identity, run_id, goal, available_tools=(), max_learnings=8, model_context_window=None):
        self.resolved.append(run_id)
        self.resolved_tools.append(tuple(available_tools))
        return ResolvedContext(
            injected_text=self.injected_text,
            injected_facts_text=self.injected_facts_text,
            offered_learning_ids=self.ids,
            offered_claim_ids=self.claim_ids,
        )

    async def observe(self, *, identity, episode) -> None:
        self.observed.append(episode)

    async def reinforce(
        self,
        *,
        identity,
        episode,
        is_org_promotion_allowed=False,
        context_receipt=None,
        is_delivered=None,
        recall_outcome=None,
    ) -> None:
        self.receipts.append(context_receipt)
        self.deliveries.append(is_delivered)
        self.recall_outcomes.append(recall_outcome)
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
    # This host injects the block itself, so it reports delivery rather than leaving the
    # run indistinguishable from a client too old to say. It still sends no receipt, so
    # it still credits nothing: the only artefact it could offer is its own claim.
    assert fake.deliveries == [True]
    # The reason travels with it: the boolean alone cannot tell an empty corpus from a
    # resolve that failed, and both would read as a client too old to answer.
    assert fake.recall_outcomes == ["delivered"]
    assert fake.receipts == [None]
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


def test_the_seat_reports_a_failed_resolve_apart_from_an_empty_corpus() -> None:
    """A fault and a cold start are the two this field exists to tell apart.

    `is_resolved` latches on the failure path too, so classifying on it alone reported
    every network error, 500 and timeout as "the corpus had nothing", which is the
    ordinary case an operator would rightly ignore.
    """
    from hyperstruck.langgraph.ledger import InvokeLedger
    from hyperstruck.langgraph.middleware import _recall_outcome

    def ledger(**state) -> InvokeLedger:
        made = InvokeLedger(run_id="r", goal="g", agent_id=None, org_id=None)
        for key, value in state.items():
            setattr(made, key, value)
        return made

    assert _recall_outcome(ledger(is_injected=True)) == "delivered"
    assert (
        _recall_outcome(ledger(is_resolved=True, is_resolve_failed=True))
        == "resolve_failed"
    )
    assert _recall_outcome(ledger(is_resolved=True)) == "resolve_empty"
    assert (
        _recall_outcome(ledger(is_resolved=True, injected_text="RULE"))
        == "recall_unclaimed"
    )
    # A run offered facts and no rules was offered something. Classifying on the
    # advice half alone reported it as a corpus with nothing in it, which is the
    # opposite repair from "the block was built and never reached the model".
    assert (
        _recall_outcome(ledger(is_resolved=True, injected_facts_text="FACTS"))
        == "recall_unclaimed"
    )
    assert _recall_outcome(ledger()) == "recall_missing"


async def test_facts_are_injected_alongside_rules_and_both_id_sets_recorded() -> None:
    """The composed block reaches the model and the ledger keeps the halves apart."""
    fake = FakeLearningClient(injected_facts_text="FACTS", claim_ids=("c9",))
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))

    captured = {}

    async def handler(req):
        captured["req"] = req
        return "ok"

    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("x")]), handler)

    injected = captured["req"].messages[0]
    assert isinstance(injected, SystemMessage)
    assert injected.content == "LEARNINGS\n\nFACTS"

    ledger = LEDGERS.get(state[RUN_ID_STATE_KEY])
    assert ledger.injected_text == "LEARNINGS"
    assert ledger.injected_facts_text == "FACTS"
    assert ledger.offered_learning_ids == ("l1", "l2")
    assert ledger.offered_claim_ids == ("c9",)
    assert mw.stats.learnings_injected == 2
    assert mw.stats.facts_injected == 1


async def test_a_facts_only_resolve_still_injects() -> None:
    """The regression this item exists for: facts alone reached no LangGraph agent.

    The middleware gated injection on the advice half, so a run whose corpus held
    facts and no applicable rule was shown nothing at all.
    """
    fake = FakeLearningClient(
        injected_text=None, ids=(), injected_facts_text="FACTS", claim_ids=("c9",)
    )
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))

    captured = {}

    async def handler(req):
        captured["req"] = req
        return "ok"

    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("x")]), handler)

    injected = captured["req"].messages[0]
    assert isinstance(injected, SystemMessage)
    assert injected.content == "FACTS"
    assert LEDGERS.get(state[RUN_ID_STATE_KEY]).is_injected is True
    assert mw.stats.facts_injected == 1
    assert mw.stats.learnings_injected == 0

    # The behaviour this change actually alters at the wire: what the boundary is
    # told. Before it, a facts-only run arrived as an empty corpus that was never
    # shown, which is the reading that makes a supply problem look like a delivery one.
    await mw.aafter_agent(state, None)
    assert fake.deliveries == [True]
    assert fake.recall_outcomes == ["delivered"]


async def test_a_resolve_holding_neither_half_injects_nothing() -> None:
    fake = FakeLearningClient(injected_text=None, ids=())
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))

    captured = {}

    async def handler(req):
        captured["req"] = req
        return "ok"

    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("x")]), handler)
    assert not isinstance(captured["req"].messages[0], SystemMessage)
    assert LEDGERS.get(state[RUN_ID_STATE_KEY]).is_injected is False


async def test_the_composed_block_is_reused_on_a_later_model_call() -> None:
    """A multi-step loop keeps both halves in view without resolving again."""
    fake = FakeLearningClient(injected_facts_text="FACTS", claim_ids=("c9",))
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))

    seen = []

    async def handler(req):
        seen.append(req)
        return "ok"

    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("x")]), handler)
    await mw.awrap_model_call(Req(state=state, messages=[HumanMessage("y")]), handler)

    assert len(seen) == 2
    for req in seen:
        assert isinstance(req.messages[0], SystemMessage)
        assert req.messages[0].content == "LEARNINGS\n\nFACTS"
    assert fake.resolved == [state[RUN_ID_STATE_KEY]], "resolved once, reused after"
    # Counted per run, not per model call: two calls showed one offer.
    assert mw.stats.learnings_injected == 2
    assert mw.stats.facts_injected == 1


class _SlowResolveClient(FakeLearningClient):
    """A client whose resolve outlives the run, with a teardown that is not instant."""

    async def resolve(self, *, identity, run_id, goal, available_tools=(), max_learnings=8, model_context_window=None):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.05)
            raise
        raise AssertionError("unreachable")


async def test_a_run_ending_before_any_model_call_does_not_wait_on_its_prefetch() -> None:
    """The prefetch is cancelled at run end, not left to write onto a popped ledger."""
    fake = _SlowResolveClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))
    ledger = LEDGERS.get(state[RUN_ID_STATE_KEY])
    task = ledger.resolve_task

    await mw.aafter_agent(state, None)

    assert task.done(), "the prefetch is joined, not left running past the report"
    assert fake.recall_outcomes == ["recall_missing"]
    assert mw.stats.errors == 0, "a cancelled prefetch is not an error"
    assert mw.stats.learnings_injected == 0
    assert mw.stats.facts_injected == 0


async def test_cancelling_the_run_end_hook_is_not_swallowed_by_the_join() -> None:
    """An abnormally terminated run is never observed, which the join must not break.

    Awaiting the prefetch inside a `suppress` swallows a cancellation delivered to
    `aafter_agent` itself just as readily as the task's own, so the hook would run on
    and report a half-run. Verified against that shape: it observed the run.
    """
    fake = _SlowResolveClient()
    mw = HyperstruckLearningMiddleware(agent_name="bot", client=fake)
    state = {"messages": [HumanMessage("x")]}
    state.update(await mw.abefore_agent(state, None))

    hook = asyncio.ensure_future(mw.aafter_agent(state, None))
    await asyncio.sleep(0)
    hook.cancel()

    with pytest.raises(asyncio.CancelledError):
        await hook
    assert fake.observed == [], "an abnormally terminated run is never observed"
    assert mw.stats.runs_observed == 0
