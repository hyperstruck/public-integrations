"""Per-invoke recorder for the LangGraph learning middleware.

This is the thin client analogue of the platform's offer log: it records what one
``invoke()`` did, so a finished run can be shipped as an episode. Unlike the
server, it derives no eligibility and holds no learning objects: born-this-run
exclusion, supersession collapse, and attribution all run server-side. The client
only records, joins tool decisions to outcomes by tool-call id, and projects the
run onto an :class:`~hyperstruck._wire.Episode`.

A single registered middleware serves many concurrent invokes, so the ledger is
never stored on the instance: each invoke owns one ``InvokeLedger`` in a
process-global, bounded registry keyed by a per-invoke run id, correlated across
hooks through a small state channel. The registry is bounded so an abnormally
terminated run (whose end hook never fires to evict it) cannot leak memory.
"""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from hyperstruck._wire import Episode, StepRecord, TerminalOutcome

logger = logging.getLogger(__name__)

# State channel carrying the per-invoke run id. Small and JSON-serialisable, so it
# threads across every middleware hook (and survives a checkpointer) while the
# heavyweight ledger stays in the in-memory registry.
RUN_ID_STATE_KEY = "hyperstruck_run_id"

# Bound on the live-ledger registry: an invoke that terminates abnormally never
# reaches the end hook that evicts its ledger, so the registry self-evicts the
# oldest entries past this bound rather than growing without limit.
_MAX_LIVE_LEDGERS = 2048


@dataclass
class _PlannedCall:
    """A tool call the model planned, captured before the tool runs."""

    tool_call_id: str
    name: str
    args: Mapping[str, Any]


@dataclass
class _ToolOutcome:
    """A tool's result, captured around the tool call and joined by id."""

    tool_call_id: str
    name: str
    result: Any = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


@dataclass
class InvokeLedger:
    """Everything one ``invoke()`` records for learning capture."""

    run_id: str
    agent_id: str
    org_id: str | None
    goal: str
    thread_id: str | None = None

    is_resolved: bool = False
    # Set where the block actually reaches a model call, not where it is resolved: a run
    # can resolve and then never call a model, and the boundary is told which happened.
    is_injected: bool = False
    # The rendered injection block (rendered server-side), reused on every later
    # model call of the run. ``None`` means nothing to inject.
    injected_text: str | None = None
    offered_learning_ids: tuple[str, ...] = ()
    # The in-flight resolve prefetch, awaited at the first model call. Stored here
    # (not on the instance) so concurrent invokes stay isolated.
    resolve_task: asyncio.Task[None] | None = None

    # Tool-call-id join: planned calls keyed by id, outcomes keyed by id.
    planned_calls: dict[str, _PlannedCall] = field(default_factory=dict)
    outcomes: dict[str, _ToolOutcome] = field(default_factory=dict)
    call_order: list[str] = field(default_factory=list)

    model_call_count: int = 0
    non_tool_decision_count: int = 0

    # ---- recording (called from the middleware hooks) -------------------

    def record_injection(self, injected_text: str | None, offered_learning_ids: tuple[str, ...]) -> None:
        """Record the resolve result: the rendered block and the offered ids."""
        self.injected_text = injected_text
        self.offered_learning_ids = offered_learning_ids
        self.is_resolved = True

    def record_planned_tool_calls(self, message: AIMessage) -> None:
        """Capture an AIMessage's planned tool calls (by id) as pending decisions."""
        self.model_call_count += 1
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            self.non_tool_decision_count += 1
            return
        for call in tool_calls:
            tool_call_id = call.get("id") or ""
            if not tool_call_id or tool_call_id in self.planned_calls:
                continue
            self.planned_calls[tool_call_id] = _PlannedCall(
                tool_call_id=tool_call_id,
                name=call.get("name", ""),
                args=call.get("args", {}) or {},
            )
            self.call_order.append(tool_call_id)

    def record_tool_outcome(self, tool_call_id: str, name: str, message: Any) -> None:
        """Join a tool's outcome onto its planned call by tool-call id."""
        if not tool_call_id:
            return
        error: str | None = None
        result: Any = None
        if isinstance(message, ToolMessage):
            result = message.content
            if getattr(message, "status", None) == "error":
                error = str(message.content)
        else:  # a Command or other return; record what we can
            result = getattr(message, "content", None)
        self.outcomes[tool_call_id] = _ToolOutcome(tool_call_id=tool_call_id, name=name, result=result, error=error)

    # ---- read (called once at invoke end) -------------------------------

    def build_episode(
        self,
        *,
        source_framework: str,
        tool_sensitivity: Mapping[str, Mapping[str, str]] | None = None,
    ) -> Episode:
        """Project the joined trace onto an :class:`Episode`.

        Only tool calls that actually ran (a planned call joined to an outcome)
        become steps. ``tool_sensitivity`` attaches producer-declared sensitivity
        labels so client-side redaction strips them before the wire and the
        platform's floor reads a declared fact rather than guessing.
        """
        steps: list[StepRecord] = []
        completed = 0
        failed = 0
        for tool_call_id in self.call_order:
            planned = self.planned_calls.get(tool_call_id)
            step_outcome = self.outcomes.get(tool_call_id)
            if planned is None or step_outcome is None:
                continue  # planned but never completed -> not an executed step
            if step_outcome.is_error:
                failed += 1
            else:
                completed += 1
            declared = None
            if tool_sensitivity and planned.name in tool_sensitivity:
                declared = {"args": dict(tool_sensitivity[planned.name])}
            steps.append(
                StepRecord(
                    id=tool_call_id,
                    name=planned.name,
                    args=dict(planned.args),
                    status="failed" if step_outcome.is_error else "completed",
                    result=step_outcome.result,
                    error=step_outcome.error,
                    declared_sensitivity=declared,
                )
            )

        terminal_outcome = TerminalOutcome(
            is_success=failed == 0,
            total_steps=len(steps),
            completed_steps=completed,
            failed_steps=failed,
        )
        return Episode(
            run_id=self.run_id,
            goal=self.goal,
            steps=tuple(steps),
            outcome=terminal_outcome,
            source_framework=source_framework,
            thread_id=self.thread_id,
        )

    def is_fully_declared(self, tool_sensitivity: Mapping[str, Mapping[str, str]]) -> bool:
        """Whether every foreign tool the run used carries a sensitivity declaration.

        Gates the cross-tenant org promotion: an undeclared (or empty-declared)
        foreign tool keeps the run's learnings agent-private. A run with no tool
        calls has nothing foreign to gate.
        """
        tool_names = {p.name for p in self.planned_calls.values()}
        if not tool_names:
            return True
        return all(tool_sensitivity.get(name) for name in tool_names)


class LedgerRegistry:
    """Process-global, bounded registry of live per-invoke ledgers.

    Keyed by run id so concurrent invokes never clobber each other. Bounded
    LRU-by-access so an abnormally terminated invoke, whose end hook never fires
    to evict its ledger, cannot leak memory. Eviction is by last access (every
    hook reads via ``get``), so the victim is a stale abandoned run, not a
    long-running invoke still touching its ledger.
    """

    def __init__(self, max_size: int = _MAX_LIVE_LEDGERS) -> None:
        self._ledgers: OrderedDict[str, InvokeLedger] = OrderedDict()
        self._max_size = max_size

    def register(self, ledger: InvokeLedger) -> None:
        self._ledgers[ledger.run_id] = ledger
        self._ledgers.move_to_end(ledger.run_id)
        while len(self._ledgers) > self._max_size:
            _, evicted = self._ledgers.popitem(last=False)
            # The bound exists to reclaim abandoned ledgers; if the victim was
            # resolved it is an in-flight run whose capture is being lost under
            # load, which is worth surfacing rather than dropping silently.
            if evicted.is_resolved:
                logger.warning(
                    "Hyperstruck ledger registry full (%d); evicted a live run %s, its learning capture is lost",
                    self._max_size,
                    evicted.run_id,
                )

    def get(self, run_id: str | None) -> InvokeLedger | None:
        if not run_id:
            return None
        ledger = self._ledgers.get(run_id)
        if ledger is not None:
            self._ledgers.move_to_end(run_id)
        return ledger

    def pop(self, run_id: str | None) -> InvokeLedger | None:
        if not run_id:
            return None
        return self._ledgers.pop(run_id, None)

    def __len__(self) -> int:
        return len(self._ledgers)


# The single process-global registry the middleware shares across all invokes.
LEDGERS = LedgerRegistry()
