"""The per-invoke recorder: tool-call join, episode projection, declaration gate."""

from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from hyperstruck.langgraph.ledger import InvokeLedger


def _ledger() -> InvokeLedger:
    return InvokeLedger(run_id="bot:1", agent_id="bot", org_id="org", goal="g")


def test_planned_calls_and_non_tool_decisions() -> None:
    ledger = _ledger()
    ledger.record_planned_tool_calls(AIMessage(content="", tool_calls=[{"id": "c1", "name": "search", "args": {"q": "x"}}]))
    ledger.record_planned_tool_calls(AIMessage(content="final answer"))
    assert ledger.model_call_count == 2
    assert ledger.non_tool_decision_count == 1
    assert "c1" in ledger.planned_calls


def test_build_episode_includes_only_completed_steps() -> None:
    ledger = _ledger()
    ledger.record_planned_tool_calls(
        AIMessage(
            content="",
            tool_calls=[
                {"id": "c1", "name": "search", "args": {"q": "x"}},
                {"id": "c2", "name": "write", "args": {}},
            ],
        )
    )
    ledger.record_tool_outcome("c1", "search", ToolMessage(content="hit", tool_call_id="c1"))
    # c2 planned but never produced an outcome -> excluded from the episode.
    episode = ledger.build_episode(source_framework="langgraph")
    assert len(episode.steps) == 1
    assert episode.steps[0].id == "c1"
    assert episode.outcome.completed_steps == 1
    assert episode.outcome.is_success is True


def test_failed_tool_marks_step_failed() -> None:
    ledger = _ledger()
    ledger.record_planned_tool_calls(AIMessage(content="", tool_calls=[{"id": "c1", "name": "search", "args": {}}]))
    ledger.record_tool_outcome("c1", "search", ToolMessage(content="boom", tool_call_id="c1", status="error"))
    episode = ledger.build_episode(source_framework="langgraph")
    assert episode.steps[0].status == "failed"
    assert episode.outcome.failed_steps == 1
    assert episode.outcome.is_success is False


def test_declared_sensitivity_attached() -> None:
    ledger = _ledger()
    ledger.record_planned_tool_calls(AIMessage(content="", tool_calls=[{"id": "c1", "name": "lookup", "args": {"ssn": "x"}}]))
    ledger.record_tool_outcome("c1", "lookup", ToolMessage(content="ok", tool_call_id="c1"))
    episode = ledger.build_episode(source_framework="langgraph", tool_sensitivity={"lookup": {"ssn": "pii"}})
    assert episode.steps[0].declared_sensitivity == {"args": {"ssn": "pii"}}


def test_is_fully_declared() -> None:
    ledger = _ledger()
    ledger.record_planned_tool_calls(AIMessage(content="", tool_calls=[{"id": "c1", "name": "lookup", "args": {}}]))
    assert ledger.is_fully_declared({"lookup": {"ssn": "pii"}}) is True
    assert ledger.is_fully_declared({"lookup": {}}) is False  # empty declaration does not unlock
    assert ledger.is_fully_declared({}) is False


def test_no_tool_calls_is_fully_declared() -> None:
    ledger = _ledger()
    assert ledger.is_fully_declared({}) is True


def test_record_injection_holds_the_two_halves_apart() -> None:
    ledger = _ledger()
    ledger.record_injection("RULES", ("l1",), "FACTS", ("c1",))

    assert ledger.injected_text == "RULES"
    assert ledger.injected_facts_text == "FACTS"
    assert ledger.offered_learning_ids == ("l1",)
    assert ledger.offered_claim_ids == ("c1",)
    assert ledger.is_resolved is True


def test_injection_block_composes_whichever_halves_arrived() -> None:
    """The fact half alone is still something to show, which is the whole point."""
    both = _ledger()
    both.record_injection("RULES", ("l1",), "FACTS", ("c1",))
    assert both.injection_block == "RULES\n\nFACTS"

    facts_only = _ledger()
    facts_only.record_injection(None, (), "FACTS", ("c1",))
    assert facts_only.injection_block == "FACTS"

    rules_only = _ledger()
    rules_only.record_injection("RULES", ("l1",), None, ())
    assert rules_only.injection_block == "RULES"

    empty = _ledger()
    empty.record_injection(None, (), None, ())
    assert empty.injection_block is None
