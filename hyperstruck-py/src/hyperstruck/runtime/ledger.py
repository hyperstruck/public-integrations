"""What one run recorded: the two shelves offered to it, and what it then did.

``/resolve`` returns advice and claims, and the boundary render-confirms both: an item
refused by the trust floor or cut by the token budget appears in neither the block nor
the offered ids, so a shelf's offer is what it delivered. Open obligations ride the claims
shelf as owed claims and have no shelf of their own.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


class LedgerStateError(RuntimeError):
    """A lifecycle call arrived out of order.

    The LangGraph seat never needed this: the framework's hook ordering enforced the
    sequence, and the state was three flat booleans that could not be reached wrongly. A
    public ``open``/``record``/``close`` surface hands that ordering to the caller, so
    what was structurally impossible becomes an ordinary mistake and has to be named
    rather than absorbed. Absorbing it would mean recording steps against a closed run
    and reporting a smaller episode than the one that happened.
    """


class LedgerClosedError(LedgerStateError):
    """The run is closed and cannot record anything further."""


@dataclass(frozen=True)
class Shelf:
    """One shelf's offer to a run: the rendered block and the ids behind it."""

    name: str
    text: str | None
    offered_ids: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not self.offered_ids and not self.text


def render_confirmed_shelf(
    name: str, text: str | None, offered_ids: Iterable[str]
) -> Shelf:
    """A shelf whose offer the boundary guarantees was rendered."""
    return Shelf(name=name, text=text, offered_ids=tuple(offered_ids))


@dataclass
class _PlannedCall:
    """A tool call the model planned, captured before the tool runs."""

    call_id: str
    name: str
    args: Mapping[str, Any]


@dataclass
class _Outcome:
    """A tool's result, captured after it runs and joined to its plan by id."""

    call_id: str
    name: str
    result: Any = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


@dataclass
class RunLedger:
    """Everything one run records, from open to close."""

    run_id: str
    goal: str

    advice: Shelf | None = None
    facts: Shelf | None = None

    is_resolved: bool = False
    # Latched separately from ``is_resolved``, which latches either way so a failure never
    # re-triggers retrieval. That makes it useless for telling a fault from a cold corpus,
    # and those two are exactly what the boundary is being told apart.
    is_resolve_failed: bool = False
    # Set where the block reaches a model call, not where it is resolved: a run can
    # resolve and then never call a model, and the boundary is told which happened.
    is_injected: bool = False

    planned: dict[str, _PlannedCall] = field(default_factory=dict)
    outcomes: dict[str, _Outcome] = field(default_factory=dict)
    call_order: list[str] = field(default_factory=list)

    model_call_count: int = 0
    is_closed: bool = False

    # ---- lifecycle -------------------------------------------------------

    def _require_open(self) -> None:
        if self.is_closed:
            raise LedgerClosedError(
                f"run {self.run_id} is closed; recording against it would report a "
                "smaller episode than the one that happened"
            )

    def close(self) -> None:
        """Close the run once. A second close is a caller fault, not a no-op.

        Silently allowing it would hide a double-close in a retry or a finally block,
        and the second close is the one that would send a duplicate episode.
        """
        if self.is_closed:
            raise LedgerClosedError(f"run {self.run_id} is already closed")
        self.is_closed = True

    # ---- recording -------------------------------------------------------

    def record_offer(
        self,
        *,
        advice: Shelf,
        facts: Shelf,
    ) -> None:
        """Record what the recall offered, both shelves at once.

        Both are required rather than defaulted, so a caller cannot record one and leave
        the other silently missing with every test still passing.
        """
        self._require_open()
        self.advice = advice
        self.facts = facts
        self.is_resolved = True

    def record_resolve_failed(self) -> None:
        """A resolve that raised. Distinct from one that returned nothing."""
        self._require_open()
        self.is_resolved = True
        self.is_resolve_failed = True

    def record_model_call(self) -> None:
        """One model call happened, whatever it planned.

        Counted apart from :meth:`record_planned_calls`, which the adapters skip entirely
        when a response asked for no tools. Folded together, the final answer of every run
        went uncounted and the figure diverged from the TypeScript seat's, which counts
        every call. It is a count of calls, so it counts calls.
        """
        self._require_open()
        self.model_call_count += 1

    def record_planned_calls(
        self, calls: Sequence[tuple[str, str, Mapping[str, Any]]]
    ) -> None:
        """Capture what one model call planned, as (id, name, args) triples."""
        self._require_open()
        for call_id, name, args in calls:
            if call_id in self.planned:
                continue
            self.planned[call_id] = _PlannedCall(call_id, name, args)
            self.call_order.append(call_id)

    def record_outcome(
        self, call_id: str, name: str, *, result: Any = None, error: str | None = None
    ) -> None:
        """Capture what actually happened for one planned call."""
        self._require_open()
        self.outcomes[call_id] = _Outcome(call_id, name, result=result, error=error)

    # ---- reading ---------------------------------------------------------

    @property
    def steps(self) -> list[dict[str, Any]]:
        """The join: only calls present in both streams become steps.

        A call the model planned and the runtime never ran is not evidence about
        anything, and recording it as a step would teach the corpus from an obligation
        rather than from an outcome. A result arriving for a call that was never planned
        is the same defect from the other side and is equally dropped: it means the two
        streams came from different runs.
        """
        joined = []
        for call_id in self.call_order:
            outcome = self.outcomes.get(call_id)
            if outcome is None:
                continue
            plan = self.planned[call_id]
            joined.append(
                {
                    "id": call_id,
                    "name": plan.name,
                    "args": dict(plan.args),
                    "status": "failed" if outcome.is_error else "completed",
                    "result": outcome.result,
                    "error": outcome.error,
                }
            )
        return joined

    @property
    def offered_any(self) -> bool:
        """Whether any shelf put anything forward."""
        return any(
            shelf is not None and shelf.offered_ids
            for shelf in (self.advice, self.facts)
        )
