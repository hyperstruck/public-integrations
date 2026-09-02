"""What one run recorded: three shelves offered to it, and what it then did.

Two things separate this from the LangGraph seat's ledger it is lifted from.

**Three shelves, not two.** ``/resolve`` returns advice, facts and obligations, and every
client we ship has handled two. The parsing for the third already existed and the ledger
simply never called it, which is the quietest possible way for a shelf to go missing.

**Offered and delivered are separate sets, per shelf.** For advice and facts the boundary
render-confirms its offer: an item refused by the trust floor or cut by the token budget
appears in neither list, so the two sets coincide and the distinction costs nothing. For
obligations it deliberately does not. ``offered_obligation_ids`` names everything the
selection admitted, including one the block's budget then cut, because the shelf escalates
on deliveries and an obligation no model was shown must not be escalated for being
ignored. Collapsing the two would produce a scoring fault on the server that is invisible
from here, which is the worst shape a fault can have, so the ledger refuses to represent
them as one thing even for the shelves where they happen to agree.
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
    """One shelf's offer to a run, and what the block actually carried.

    ``is_render_confirmed`` is not decoration. It records whether the boundary promises
    that everything offered was rendered, which is true of advice and facts and false of
    obligations. A reader that needs "what was the model actually shown" must use
    ``delivered_ids`` on every shelf; the flag exists so a reader that needs "what did the
    shelf put forward" can tell the two questions apart rather than guessing from whether
    the lists happen to match on the run in front of it.
    """

    name: str
    text: str | None
    offered_ids: tuple[str, ...]
    delivered_ids: tuple[str, ...]
    is_render_confirmed: bool

    def __post_init__(self) -> None:
        extra = set(self.delivered_ids) - set(self.offered_ids)
        if extra:
            raise ValueError(
                f"{self.name}: delivered ids that were never offered: {sorted(extra)}. "
                "Delivered is a subset of offered by construction; a difference here "
                "means the two were read from different responses."
            )
        if self.is_render_confirmed and set(self.delivered_ids) != set(self.offered_ids):
            raise ValueError(
                f"{self.name} is render-confirmed, so its offered and delivered sets "
                "must agree. They do not, which means either the boundary changed its "
                "promise or this shelf was constructed with the wrong flag."
            )

    @property
    def is_empty(self) -> bool:
        return not self.offered_ids and not self.text


def render_confirmed_shelf(
    name: str, text: str | None, offered_ids: Iterable[str]
) -> Shelf:
    """A shelf whose offer the boundary guarantees was rendered."""
    ids = tuple(offered_ids)
    return Shelf(
        name=name,
        text=text,
        offered_ids=ids,
        delivered_ids=ids,
        is_render_confirmed=True,
    )


def offered_and_delivered_shelf(
    name: str,
    text: str | None,
    offered_ids: Iterable[str],
    delivered_ids: Iterable[str] | None,
) -> Shelf:
    """A shelf that offers more than it delivers, and says which is which.

    ``delivered_ids`` of ``None`` means the boundary did not report a delivered set, which
    is what an older deployment does. That is recorded as nothing delivered rather than as
    everything delivered: over-reporting a delivery is what causes an obligation nobody
    saw to be escalated for being ignored, and under-reporting only forgoes credit.
    """
    return Shelf(
        name=name,
        text=text,
        offered_ids=tuple(offered_ids),
        delivered_ids=tuple(delivered_ids or ()),
        is_render_confirmed=False,
    )


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
    obligations: Shelf | None = None

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
        obligations: Shelf,
    ) -> None:
        """Record what the recall offered, all three shelves at once.

        All three are required rather than defaulted. A default would let a caller record
        two and silently reproduce the missing-shelf fault this ledger exists to end,
        with every test still passing, which is how it survived this long.
        """
        self._require_open()
        self.advice = advice
        self.facts = facts
        self.obligations = obligations
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
        """Whether any shelf put anything forward, which is not the same as delivered."""
        return any(
            shelf is not None and shelf.offered_ids
            for shelf in (self.advice, self.facts, self.obligations)
        )

    @property
    def delivered_any(self) -> bool:
        return any(
            shelf is not None and shelf.delivered_ids
            for shelf in (self.advice, self.facts, self.obligations)
        )
