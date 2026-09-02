"""The run-scoped core: one object per run, attachable from any runtime.

Every seat we ship is a thin adapter over this. The LangGraph middleware and the IDE hook
each grew their own version of the same loop, and the differences between them turned out
to be accidents rather than decisions: only one of them declines, only one of them handles
the third shelf, and neither can produce a receipt. This module is the one loop, and a new
host is the adapter that feeds it.

    open(goal, tools)      -> prefetch POST /resolve, hold the three blocks
    (model call)           -> replay the block, locate it in the params as sent
    record_step(...)       -> join planned calls against actual outcomes
    close(outcome)         -> POST /observe, then /reinforce with the receipt, or /decline

**The block is computed once and replayed.** Rate limits and overloads routinely make a
customer's own retry logic, or the SDK's built-in retry, resend the same logical call, so
the model-layer hook fires several times for one logical step. Recomputing would show the
model a different block on the second send and spend a second recall against the run's
budget. Receipt location, by contrast, runs on **every** send: a mid-run trim is exactly
what it exists to catch, and the latest location wins.

**Lifecycle is guarded rather than assumed.** The LangGraph ledger's three flat booleans
were only ever safe because the framework's hook ordering enforced the sequence. A public
surface hands that ordering to the caller, so close-before-open, double close and a step
recorded after close are defined here rather than left undefined.

**Nothing here breaks the host's run.** Resolve fails open, the write path is scheduled
rather than awaited, and every callback the customer registered is called inside a guard.
A seat that dies when we do is a seat they remove.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from hyperstruck._wire import (
    DEFAULT_MAX_LEARNINGS,
    Episode,
    ObligationClosureResult,
    ReinforceResult,
    ReportedObligationOutcome,
    ResolvedContext,
    StepRecord,
    TerminalOutcome,
    ToolSpec,
    combine_injection_blocks,
    is_unpublished_decline_reason,
)
from hyperstruck.identity import AgentIdentity
from hyperstruck.runtime.declarations import DeclarationRegistry, join
from hyperstruck.runtime.ledger import (
    LedgerClosedError,
    RunLedger,
    Shelf,
    offered_and_delivered_shelf,
    render_confirmed_shelf,
)
from hyperstruck.runtime.receipt import ReceiptLocation, locate_receipt
from hyperstruck.runtime.run_key import DEFAULT_RESOLVERS, RunKey, resolve_run_key
from hyperstruck.runtime.scanning import scan_and_scrub
from hyperstruck.turn_gate import decline_reason, should_observe

logger = logging.getLogger(__name__)

# Provenance stamped on every episode this seat produces, when no adapter names itself.
# Not "hyperstruck-core": this package deliberately never imports the engine, and naming
# the engine here would attribute a foreign customer's episode to it in the one field the
# platform uses to tell surfaces apart.
SOURCE_FRAMEWORK = "hyperstruck-runtime"

# The boundary's closed vocabulary for why a recall did not reach the model. String
# literals rather than an import of ``hyperstruck.ide.recall``: that enum carries a dozen
# editor-specific states (transcript reads, warm stashes) that no neutral host can be in,
# and the neutral layer may not import the IDE adapter in any case. These five are the
# members a host-neutral seat can actually reach, and they are the boundary's own names.
OUTCOME_DELIVERED = "delivered"
OUTCOME_RESOLVE_FAILED = "resolve_failed"
OUTCOME_RESOLVE_EMPTY = "resolve_empty"
OUTCOME_RECALL_UNCLAIMED = "recall_unclaimed"
OUTCOME_RECALL_MISSING = "recall_missing"

# How long a run may sit untouched before it counts as abandoned. Measured from the last
# ledger touch rather than from open, so a long run that is still working is never a
# candidate while an opened-and-forgotten one ages out. Thirty minutes is above any
# plausible agent turn and far below the point at which the cap fills in a real deployment.
DEFAULT_RUN_TTL_SECONDS = 30 * 60

# Bound on live runs. Inherited from the LangGraph registry, whose own comment warns that
# the eviction victim can be a live in-flight run. Pairing it with the TTL above is what
# turns that warning into a rule: abandoned entries go first, and evicting a live one is a
# warning rather than routine housekeeping.
DEFAULT_MAX_LIVE_RUNS = 2048

# How long the seat waits after a tool-free assistant answer before closing the run.
#
# The model layer gets no episode-end event, so this is the only terminal signal it has, and
# it has to be a window rather than an edge: a customer's loop that answers, is asked a
# follow-up, and answers again is one episode, and closing on the first answer would make it
# two. A further call under the same key inside the window continues the run.
#
# The honest cost is stated rather than hidden: a grace-window close posts credit up to one
# window late. Sixty seconds is long enough to cover a human reading an answer and replying,
# and short enough that a batch host's credit is not held up materially.
DEFAULT_CLOSE_GRACE_SECONDS = 60.0

# How long close() will wait for a cancelled prefetch to unwind. Short, because nothing is
# owed to a resolve nobody will read.
_RESOLVE_JOIN_TIMEOUT = 1.0

# The step kind this seat records. The observe/decline rule is shared across hosts and the
# vocabulary is not: the IDE seat distinguishes an edit from a search because its transcript
# does, while everything a model-layer seat sees is a tool the runtime actually ran. So this
# seat has one kind and it is material, and a host that wants a finer vocabulary passes its
# own ``material_kinds`` and stamps its own kinds.
TOOL_CALL_KIND = "tool_call"
DEFAULT_MATERIAL_KINDS = frozenset({TOOL_CALL_KIND})


def recall_outcome(
    *,
    is_injected: bool,
    is_resolve_failed: bool,
    is_resolved: bool,
    is_offered: bool,
) -> str:
    """Why the recall did not reach the model, in the boundary's own vocabulary.

    Sent beside the delivery boolean because the boolean alone is the half-answer the
    field exists to remove: without it a run whose corpus was empty is indistinguishable
    from one whose resolve failed, and both look like a client too old to say. Collapsing
    ``resolve_failed`` into ``resolve_empty`` is the specific failure the taxonomy exists
    to prevent, because it makes a broken deployment read exactly like a cold corpus.

    Takes four booleans rather than a ledger, because the LangGraph seat holds the same
    four on a different object and this is the one rule for both. Passing the ledger would
    have left the shared rule reachable from exactly one of the two seats that needs it.
    """
    if is_injected:
        return OUTCOME_DELIVERED
    if is_resolve_failed:
        return OUTCOME_RESOLVE_FAILED
    if not is_resolved:
        # The run ended with the prefetch still in flight. Not a fault: the run was short.
        return OUTCOME_RECALL_MISSING
    return OUTCOME_RESOLVE_EMPTY if not is_offered else OUTCOME_RECALL_UNCLAIMED


def _outcome_kwarg(
    outcomes: Sequence[ReportedObligationOutcome],
) -> dict[str, Any]:
    """The ``obligation_outcomes`` keyword, passed only when there is something to report.

    This seat drives whatever client it was handed, including one a customer wrote against
    the ``LearningClient`` port before the parameter existed. Omitting it when empty means
    such a client is called exactly as it was; a host that does report outcomes against one
    gets its ``TypeError``, which is the honest answer, since that client cannot carry them.
    """
    if not outcomes:
        return {}
    return {"obligation_outcomes": tuple(outcomes)}


def _read_write_result(
    value: Any,
) -> tuple[tuple[dict[str, str], ...], tuple[ObligationClosureResult, ...]]:
    """Read what a reinforce or decline returned, whatever shape the client returns it in.

    A client written against an earlier version of the port returns the presence verdicts as a
    bare sequence, or nothing at all. Reading a field off that would raise outside the write
    guard, which is the one thing this seat promises never to do to a host run.
    """
    if isinstance(value, ReinforceResult):
        return tuple(value.presence_outcomes), tuple(value.obligation_closures)
    if isinstance(value, (tuple, list)):
        return tuple(item for item in value if isinstance(item, dict)), ()
    return (), ()


def ledger_recall_outcome(ledger: RunLedger) -> str:
    """:func:`recall_outcome` read off this seat's own ledger."""
    return recall_outcome(
        is_injected=ledger.is_injected,
        is_resolve_failed=ledger.is_resolve_failed,
        is_resolved=ledger.is_resolved,
        is_offered=ledger.offered_any,
    )


@dataclass(frozen=True)
class RunReport:
    """What happened to one run, in the same shape on every channel that carries it.

    The same report reaches the structured log line, the callback registered at wrap time,
    and the handle a caller may be holding, and it is never a subset on any of them. A
    customer who moves between attachment points must not silently lose a field, which is
    the failure mode a "the handle has more" design has.

    Several fields exist only so that nothing is withheld silently. ``withheld`` names the
    declarations that were dropped and the configuration that would release them,
    ``recall_outcome`` distinguishes a broken boundary from a cold corpus, and
    ``run_key_source`` says which rung of the ladder answered, because an inferred key is a
    fact about this report's own reliability that its reader is entitled to.
    """

    run_id: str
    goal: str
    run_key_source: str
    is_run_key_inferred: bool
    recall_outcome: str
    receipt_outcome: str
    is_receipt_sent: bool
    shelves: tuple[dict[str, Any], ...]
    step_count: int
    model_call_count: int
    disposition: str
    close_trigger: str | None = None
    # The boundary's own verdict per offered id, once the reinforce has drained. Empty until
    # then, and empty against a deployment that does not return it. Present here as well as
    # in the TypeScript report because the promise is one report shape across every channel
    # *and* both languages; a field in one and not the other makes a customer who moves
    # between them lose it silently, which is the failure the promise exists to prevent.
    presence_outcomes: tuple[dict[str, str], ...] = ()
    # What the boundary did with each reported outcome, per id. Empty on the
    # asynchronous write path and when the run reported none.
    obligation_closures: tuple[ObligationClosureResult, ...] = ()
    decline_reason: str | None = None
    withheld: tuple[str, ...] = ()
    is_evicted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "run_key_source": self.run_key_source,
            "is_run_key_inferred": self.is_run_key_inferred,
            "recall_outcome": self.recall_outcome,
            "receipt_outcome": self.receipt_outcome,
            "is_receipt_sent": self.is_receipt_sent,
            "shelves": [dict(shelf) for shelf in self.shelves],
            "step_count": self.step_count,
            "model_call_count": self.model_call_count,
            "disposition": self.disposition,
            "close_trigger": self.close_trigger,
            "presence_outcomes": [dict(outcome) for outcome in self.presence_outcomes],
            "obligation_closures": [
                closure.to_dict() for closure in self.obligation_closures
            ],
            "decline_reason": self.decline_reason,
            "withheld": list(self.withheld),
            "is_evicted": self.is_evicted,
        }


# What a run's close did with it: the three terminal dispositions plus the one that is not
# a close at all. An evicted run reaches none of the boundary's terminal endpoints, and
# that is deliberate rather than an omission, see ``RunRegistry.sweep``.
DISPOSITION_REINFORCED = "reinforced"
# The run was worth learning from and was sent, but no receipt went with it. Distinct from
# the two below, which are failures rather than a weaker success, and which used to be
# indistinguishable from it in the one field a reader consults.
DISPOSITION_OBSERVED = "observed"
# The write-back raised. The episode may or may not have landed.
DISPOSITION_WRITE_FAILED = "write_failed"
# The turn was declined, and the only honest reason for it is one the boundary has not
# published, so nothing was sent rather than a refused decline leaving the run open.
DISPOSITION_WITHHELD = "withheld"
DISPOSITION_DECLINED = "declined"
DISPOSITION_EVICTED = "evicted"

# Why the close fired, reported beside the rung that keyed the run. A customer reading a
# late or a missing reinforcement can then see which of the two happened without asking.
CLOSE_TRIGGER_EXPLICIT = "explicit"
CLOSE_TRIGGER_NO_TOOL_CALLS = "no_tool_calls_grace"
CLOSE_TRIGGER_PROCESS_EXIT = "process_exit"
CLOSE_TRIGGER_ABANDONED = "abandoned_ttl"


@dataclass
class HyperstruckRun:
    """One run, from open through every model call to close.

    Held by the registry rather than by the seat, so one wrapped client serving many
    concurrent runs never lets two of them share state. Constructed through
    :meth:`RunSeat.open` rather than directly.
    """

    run_id: str
    identity: AgentIdentity
    goal: str
    key: RunKey
    tools: tuple[ToolSpec, ...] = ()
    thread_id: str | None = None

    ledger: RunLedger = field(init=False)
    resolve_task: asyncio.Task[None] | None = None
    injection_block: str | None = None
    receipt: ReceiptLocation | None = None
    # The most complete receipt this run ever saw, which is the evidence that goes on the
    # wire, and the least complete, which is the fidelity the run report shows. See
    # ``RunSeat.after_model_call`` for why one artefact cannot be both.
    best_receipt: ReceiptLocation | None = None
    worst_receipt: ReceiptLocation | None = None
    report: RunReport | None = None
    withheld: tuple[str, ...] = ()
    last_touched: float = field(default_factory=time.monotonic)
    # Set when a model answered without asking for another tool, cleared when a further
    # call arrives under the same key. The grace window runs from this moment.
    closable_at: float | None = None
    close_task: asyncio.Task[None] | None = None

    def __post_init__(self) -> None:
        self.ledger = RunLedger(run_id=self.run_id, goal=self.goal)

    def touch(self) -> None:
        """Mark the run as still active, for the abandonment sweep."""
        self.last_touched = time.monotonic()

    @property
    def is_closed(self) -> bool:
        return self.ledger.is_closed


class RunRegistry:
    """The live runs of one process, bounded by a cap and aged by a TTL.

    The cap alone was the LangGraph registry's design and its own comment warned that the
    victim can be a live in-flight run. That was tolerable when the graph's hook ordering
    decided concurrency; a public surface makes concurrency the customer's choice, so the
    cap is paired with a TTL and the two answer different questions. The TTL reclaims runs
    nobody will ever close. The cap is the backstop, and reaching it is a warning.
    """

    def __init__(
        self,
        *,
        max_size: int = DEFAULT_MAX_LIVE_RUNS,
        ttl_seconds: float = DEFAULT_RUN_TTL_SECONDS,
    ) -> None:
        self._runs: OrderedDict[str, HyperstruckRun] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def register(self, run: HyperstruckRun) -> list[HyperstruckRun]:
        """Add a run, returning any that were displaced or evicted to make room for it.

        A run already live under this key is *displaced*, and it is returned rather than
        dropped. Every other way a run leaves this registry produces a report; this path
        used to produce none, so a second run opened under a key still held by a live one
        (two overlapping invocations on one framework thread, say) silently orphaned the
        first: never closed, never declined, holding its resolve reservation until the
        server's reclaim sweep noticed.
        """
        displaced = self._runs.get(run.key.key)
        evicted: list[HyperstruckRun] = []
        if displaced is not None and displaced is not run and not displaced.is_closed:
            logger.warning(
                "Hyperstruck: run %s was displaced by a second run under the same key "
                "(%s); reporting it rather than dropping it",
                displaced.run_id,
                run.key.key,
            )
            evicted.append(displaced)
        self._runs[run.key.key] = run
        self._runs.move_to_end(run.key.key)
        evicted.extend(self.sweep())
        while len(self._runs) > self._max_size:
            _, victim = self._runs.popitem(last=False)
            logger.warning(
                "Hyperstruck run registry full (%d) with no abandoned run to reclaim; "
                "evicted live run %s and its learning capture is lost",
                self._max_size,
                victim.run_id,
            )
            evicted.append(victim)
        return evicted

    def sweep(self, now: float | None = None) -> list[HyperstruckRun]:
        """Drop runs untouched for longer than the TTL, and return them.

        Abandoned means no activity for the TTL, measured from the last touch. A run that
        is still working is touched by every model call and every step, so it is never a
        candidate however long it has been open.
        """
        moment = time.monotonic() if now is None else now
        abandoned = [
            run
            for run in self._runs.values()
            if moment - run.last_touched > self._ttl_seconds
        ]
        for run in abandoned:
            self._runs.pop(run.key.key, None)
            logger.info(
                "Hyperstruck run %s aged out after %.0fs untouched; reporting it as "
                "evicted rather than declining it",
                run.run_id,
                moment - run.last_touched,
            )
        return abandoned

    def get(self, key: str | None) -> HyperstruckRun | None:
        """The live run under one correlation key, or ``None``.

        Keyed on the correlation key rather than on the run id, and the two are no longer
        the same string. A stable key (a trace, a conversation id) names a *series* of
        runs, and giving each of them the same run id would have the platform dedupe the
        second turn's episode against the first and drop it silently, which is the worst
        shape a fault can have: the customer sees a corpus that stops filling and no error
        anywhere. The key correlates; the run id identifies.
        """
        if not key:
            return None
        run = self._runs.get(key)
        if run is not None:
            self._runs.move_to_end(key)
            run.touch()
        return run

    def pop(self, key: str | None) -> HyperstruckRun | None:
        if not key:
            return None
        return self._runs.pop(key, None)

    def closable(self, grace: float, now: float | None = None) -> list[HyperstruckRun]:
        """Runs whose grace window has elapsed since a tool-free assistant answer."""
        moment = time.monotonic() if now is None else now
        return [
            run
            for run in self._runs.values()
            if run.closable_at is not None and moment - run.closable_at >= grace
        ]

    def all(self) -> list[HyperstruckRun]:
        """Every live run, for a process-exit flush."""
        return list(self._runs.values())

    def __len__(self) -> int:
        return len(self._runs)


ReportSink = Callable[[RunReport], None]


class RunSeat:
    """The host-neutral seat: one per wrapped client, many runs.

    The API key binds here, at construction, and one seat is therefore one tenant. Tenancy
    is never derived from a run key: a missed inference would then be a cross-tenant leak
    rather than a lost attribution, and those are not the same class of mistake.
    """

    def __init__(
        self,
        *,
        client: Any,
        identity: AgentIdentity,
        declarations: DeclarationRegistry | None = None,
        on_report: ReportSink | None = None,
        max_learnings: int = DEFAULT_MAX_LEARNINGS,
        material_kinds: frozenset[str] = DEFAULT_MATERIAL_KINDS,
        source_framework: str = SOURCE_FRAMEWORK,
        run_key_resolvers: Sequence[Callable[[], RunKey | None]] = DEFAULT_RESOLVERS,
        registry: RunRegistry | None = None,
        scanner: Any = None,
        close_grace_seconds: float = DEFAULT_CLOSE_GRACE_SECONDS,
    ) -> None:
        self._client = client
        self._identity = identity
        self._declarations = declarations or DeclarationRegistry()
        self._on_report = on_report
        self._max_learnings = max_learnings
        self._material_kinds = material_kinds
        self._source_framework = source_framework
        self._resolvers = tuple(run_key_resolvers)
        # Off unless a customer passes one. Origin declaration is the primary mechanism
        # and this is the secondary net over free text, which is where origin labelling
        # under-delivers because one label covers arbitrary content.
        self._scanner = scanner
        self.close_grace_seconds = close_grace_seconds
        # ``is not None`` rather than ``or``: the registry defines ``__len__``, so an empty
        # one is falsy and a caller's own registry would be silently swapped for a fresh
        # default at exactly the moment it holds no runs, which is every process start.
        self.runs = registry if registry is not None else RunRegistry()
        # The key of the run the inference rung last opened, so a continuation can find it.
        self._inferred_key: str | None = None
        # The last report emitted, for a host with no sink registered that still wants to
        # look at what happened. The report reaches the log line and the callback either
        # way; this is a convenience, not a fourth channel.
        self._last_report: RunReport | None = None

    def declare_host(self, name: str) -> None:
        """Let an adapter stamp its own provenance, without overriding a caller's.

        Only when the framework is still the default, so a customer who named their own
        surface keeps it: their name is a decision and the adapter's is a fallback.
        """
        if self._source_framework == SOURCE_FRAMEWORK:
            self._source_framework = name

    # -- lifecycle ---------------------------------------------------------

    def open(
        self,
        goal: str,
        tools: Sequence[ToolSpec] = (),
        *,
        thread_id: str | None = None,
        run_key: RunKey | None = None,
    ) -> HyperstruckRun:
        """Start a run and fire its resolve prefetch.

        The prefetch is scheduled rather than awaited so its round-trip overlaps whatever
        the host does between opening a run and its first model call. A hosted resolve ran
        p50 11.6s and p99 18.7s in production, so awaiting it here would put that tail
        straight into the customer's own latency.
        """
        key = run_key or resolve_run_key(self._resolvers)
        # Read the subject declaration off the roster's own schemas. Without this the
        # registry only ever holds what a caller registered by hand, so the annotation a
        # customer already wrote for their own API documentation would be read by nobody
        # and every run would fall back to structural salience, which is the fragmented
        # entity problem the subject key exists to fix. ``register_tools`` adds only a
        # subject and never fabricates an argument label, so it cannot make an undeclared
        # tool look declared.
        self._declarations.register_tools(tools)
        # A discriminator, because a correlation key can be stable across turns while a run
        # id must not be. The platform dedupes writes by run id, so a second turn under one
        # conversation id would otherwise have its episode dropped as a duplicate of the
        # first, silently and with nothing to diagnose from.
        run = HyperstruckRun(
            run_id=f"{self._identity.agent_name}:{key.key}:{uuid.uuid4().hex[:8]}",
            identity=self._identity,
            goal=goal,
            key=key,
            tools=tuple(tools),
            thread_id=thread_id,
        )
        for evicted in self.runs.register(run):
            self._emit(
                self._build_report(
                    evicted,
                    DISPOSITION_EVICTED,
                    is_evicted=True,
                    trigger=CLOSE_TRIGGER_ABANDONED,
                )
            )
        # Guarded exactly as ``mark_closable`` is. ``open`` is reachable from synchronous
        # host code (a context provider's constructor path, a caller wiring a run up before
        # entering its loop), and raising there would break the host's own start-up for a
        # prefetch that is an optimisation. With no loop the recall simply resolves on the
        # first ``before_model_call`` instead.
        try:
            run.resolve_task = asyncio.ensure_future(self._prefetch(run))
        except RuntimeError:
            run.resolve_task = None
        return run

    def for_call(
        self,
        goal: str,
        tools: Sequence[ToolSpec] = (),
        *,
        is_continuation: bool = False,
    ) -> HyperstruckRun:
        """The run this model call belongs to, opening one if the ladder names a new key.

        The model-layer hooks fire once per model call rather than once per episode, so
        every call has to answer "which run is this" before it can do anything else. The
        ladder answers it, and the same key maps to the same run id, so a second call of
        the same run finds the run the first one opened.

        Getting this wrong is not an inefficiency. Two concurrent conversations sharing one
        wrapped client would have one run's block matched against the other's params, which
        is why the ladder puts inference last and why the report always says which rung
        answered.
        """
        key = resolve_run_key(self._resolvers)
        # Rung 4 of the ladder, and the reason it exists. Every rung above supplies a key
        # stable across the calls of one episode; minting supplies one that is not, so a
        # customer with no tracer and no explicit wrapper got a fresh run per model call, no
        # joined steps, and a decline every turn. That is the configuration both quick
        # starts document, so the documented default captured nothing at all.
        #
        # The adapter tells us whether this call shows a conversation already in progress (a
        # prior assistant turn, or tool results fed back). If it does, and nothing better
        # than a minted key is available, this call belongs to the run the last one opened.
        # It is still reported as inferred, because it is.
        if key.is_inferred and is_continuation and self._inferred_key is not None:
            if self.runs.get(self._inferred_key) is not None:
                key = RunKey(key=self._inferred_key, source="inferred", is_inferred=True)
        existing = self.runs.get(key.key)
        if existing is not None:
            # A further call under the same key continues the run rather than letting the
            # grace window close it. Cancelled here rather than checked at fire time so a
            # long-lived session does not accumulate one pending timer per turn.
            existing.closable_at = None
            if existing.close_task is not None:
                existing.close_task.cancel()
                existing.close_task = None
            # The roster can arrive on a later call than the first, since a customer may
            # bind tools partway through a loop. Recorded when it does, because a run with
            # an empty roster makes restraint unreadable server-side.
            if tools and not existing.tools:
                existing.tools = tuple(tools)
                self._declarations.register_tools(tools)
            return existing
        opened = self.open(goal, tools, run_key=key)
        # Remembered only for the minted rung: every other rung re-derives the same key on
        # the next call, and carrying one of theirs would let a stale run outlive its
        # context.
        if key.is_inferred:
            self._inferred_key = key.key
        return opened

    async def before_model_call(self, run: HyperstruckRun) -> str | None:
        """The block to inject on this model call, awaited off the prefetch once.

        Returns the same string on every call of the run. A retried send must show the
        model the block it was shown the first time, or the receipt it produces evidences
        something other than what happened.
        """
        run.touch()
        if not run.ledger.is_resolved and run.resolve_task is not None:
            try:
                await run.resolve_task
            except Exception:  # noqa: BLE001 - fail open; already counted in the task
                pass
        return run.injection_block

    def record_model_call(self, run: HyperstruckRun) -> None:
        """One model call happened. Counted here so a tool-free answer counts too."""
        run.touch()
        if not run.ledger.is_closed:
            run.ledger.record_model_call()

    def after_model_call(self, run: HyperstruckRun, sent_payload: Any) -> None:
        """Locate our block in the params as they were actually sent.

        Runs on every send rather than once, because a mid-run trim is precisely the thing
        the receipt exists to catch.

        **What "as sent" bounds, said plainly.** The payload here is the composed params at
        this seat's own position, which is below every middleware the customer arranged and
        above the SDK's own serialisation. So the receipt evidences what survived their
        composition stack, which is the claim the spec makes and the class of loss it names
        (a trimmer, a summariser, a guardrail emptying the block). It does not and cannot
        evidence what a gateway did to the request afterwards: nothing at this layer can see
        past the call it makes. A seat that claimed otherwise would be asserting an exposure
        it never observed, which is the one thing this lane must never do.
        """
        run.touch()
        if run.injection_block is None:
            return
        text = (
            sent_payload
            if isinstance(sent_payload, str)
            else _flatten(sent_payload)
        )
        located = locate_receipt(text, self._shelf_inputs(run))
        run.receipt = located

        # Two different facts, and collapsing them is what produced a run reporting
        # `delivered` with no receipt at all.
        #
        # **Delivery is monotone across the run.** "Did the recall reach the model" is
        # answered once and stays answered: a block the model was shown on call one was
        # shown, whatever call three did. So the flag latches on the first located block.
        #
        # **The evidence has to survive with it.** ``run.receipt`` is overwritten on every
        # send, because the latest location is what describes what the model was *last*
        # shown. Pairing a latching flag with a last-write-wins artefact meant a run whose
        # final call was trimmed sent ``is_delivered=True`` and ``context_receipt=None``,
        # which is exactly the pair these fields exist to separate, and which the platform
        # escalates to a warning as a client defect. So the best receipt the run ever saw is
        # kept alongside the latest one, and that is what goes on the wire.
        #
        # **The trim is still reported**, through ``worst_receipt`` below, which is the
        # customer-facing diagnostic and the thing a mid-run trim exists to surface. The
        # wire gets the evidence; the report gets the fidelity.
        if located.is_present:
            run.ledger.is_injected = True
            if run.best_receipt is None or _is_better(located, run.best_receipt):
                run.best_receipt = located
        if run.worst_receipt is None or _is_worse(located, run.worst_receipt):
            run.worst_receipt = located

    def record_planned_calls(
        self, run: HyperstruckRun, calls: Sequence[tuple[str, str, Mapping[str, Any]]]
    ) -> None:
        run.touch()
        run.ledger.record_planned_calls(calls)

    def record_step(
        self,
        run: HyperstruckRun,
        call_id: str,
        name: str,
        *,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        run.touch()
        run.ledger.record_outcome(call_id, name, result=result, error=error)

    def mark_closable(self, run: HyperstruckRun) -> None:
        """The model answered without asking for another tool: start the grace window.

        A mark rather than a close, and the seat starts its own timer rather than leaving
        the sweep to the customer. Leaving it to them would make the documented default
        attachment point earn no credit for anyone who did not read that paragraph, which is
        the exact failure the grace window exists to close.

        Outside a running loop there is nothing to schedule onto, and that is not an error:
        a synchronous host closes at process exit through :meth:`flush_all`, and raising
        here would break a model call over a bookkeeping detail.
        """
        run.touch()
        run.closable_at = time.monotonic()
        if run.close_task is not None:
            run.close_task.cancel()
        try:
            run.close_task = asyncio.ensure_future(self._close_after_grace(run))
        except RuntimeError:
            run.close_task = None

    async def _close_after_grace(self, run: HyperstruckRun) -> None:
        """Wait out the window, then close unless a further call continued the run."""
        try:
            await asyncio.sleep(self.close_grace_seconds)
        except asyncio.CancelledError:
            return
        if run.closable_at is None or run.is_closed:
            return
        try:
            await self.close(run, trigger=CLOSE_TRIGGER_NO_TOOL_CALLS)
        except Exception as exc:  # noqa: BLE001 - a background close is never the host's problem
            logger.warning("Hyperstruck: grace-window close failed for %s: %s", run.run_id, exc)

    async def sweep(self, now: float | None = None) -> list[RunReport]:
        """Close what the window has finished with and report what aged out.

        The timer above is the normal path; this is for a host that would rather drive the
        sweep itself, and it also reclaims runs the TTL has abandoned. Safe to call on a
        timer and safe to never call.
        """
        reports: list[RunReport] = []
        for run in self.runs.closable(self.close_grace_seconds, now):
            report = await self._close_if_open(run, CLOSE_TRIGGER_NO_TOOL_CALLS)
            if report is not None:
                reports.append(report)
        for abandoned in self.runs.sweep(now):
            report = self._build_report(
                abandoned,
                DISPOSITION_EVICTED,
                is_evicted=True,
                trigger=CLOSE_TRIGGER_ABANDONED,
            )
            self._emit(report)
            reports.append(report)
        return reports

    async def flush_all(self) -> list[RunReport]:
        """Close every live run. For a process-exit flush, with synchronous writes.

        Process exit is the one moment a fire-and-forget queue loses everything it holds, so
        a host that wants its last runs credited pairs this with the client's synchronous
        write mode. Without both, the episodes are dropped at teardown with no error
        anywhere.
        """
        reports: list[RunReport] = []
        for run in self.runs.all():
            report = await self._close_if_open(run, CLOSE_TRIGGER_PROCESS_EXIT)
            if report is not None:
                reports.append(report)
        return reports

    async def _close_if_open(
        self, run: HyperstruckRun, trigger: str
    ) -> RunReport | None:
        """Close one run, tolerating the case where something else closed it first.

        Both bulk paths above walk a snapshot and await inside the loop, and ``close``
        itself awaits the prefetch. That await is a point at which a *sibling* run's own
        grace timer can fire and close the run this loop is about to reach. A second close
        is a caller fault by design and raises, so without this guard one raced run would
        take down the whole sweep and lose the reports of every run still queued behind it.

        The guard is here rather than in ``close``, deliberately: a double close from a
        caller's own retry or ``finally`` is still a fault worth naming, and absorbing it
        there would hide the duplicate episode that fault would have sent.
        """
        if run.is_closed:
            return None
        try:
            return await self.close(run, trigger=trigger)
        except Exception as exc:  # noqa: BLE001 - one raced run must not lose the rest
            logger.warning(
                "Hyperstruck: bulk close (%s) failed for %s: %s", trigger, run.run_id, exc
            )
            return None

    async def close(
        self,
        run: HyperstruckRun,
        *,
        is_success: bool = True,
        trigger: str = CLOSE_TRIGGER_EXPLICIT,
        obligation_outcomes: Sequence[ReportedObligationOutcome] = (),
    ) -> RunReport:
        """End the run: observe and reinforce, or decline, and report either way.

        Always terminal. A run left neither reinforced nor declined is indistinguishable
        from a host that stopped writing back, and it sits open holding its resolve
        reservation until the server's reclaim sweep notices.

        ``obligation_outcomes`` reports what the turn did with the obligations it was offered.
        They ride the close rather than taking a call of their own, and either leg carries
        them, because a turn that resolved an obligation and learned nothing is still a turn
        that resolved an obligation. What became of each is on the report's
        ``obligation_closures``.
        """
        self.runs.pop(run.key.key)
        # Never the task we are running on. ``_close_after_grace`` calls straight into
        # here, so cancelling ``close_task`` unconditionally cancels *this* coroutine
        # mid-close: the run is popped from the registry, the write never goes out, and the
        # default attachment point reinforces nothing while looking like it closed.
        if run.close_task is not None:
            if run.close_task is not asyncio.current_task():
                run.close_task.cancel()
            run.close_task = None
        await self._join_prefetch(run)
        run.ledger.close()

        steps = run.ledger.steps
        # The gate reads a kind, and this seat has exactly one. Stamped here rather than in
        # the ledger, because the ledger records what happened and the vocabulary that
        # grades it belongs to the host.
        graded = [{**step, "kind": TOOL_CALL_KIND} for step in steps]
        is_worth_observing = should_observe(graded, self._material_kinds)
        outcome = ledger_recall_outcome(run.ledger)

        if is_worth_observing:
            report = await self._reinforce(
                run,
                steps,
                is_success=is_success,
                outcome=outcome,
                trigger=trigger,
                obligation_outcomes=obligation_outcomes,
            )
        else:
            report = await self._decline(
                run,
                steps,
                outcome=outcome,
                trigger=trigger,
                obligation_outcomes=obligation_outcomes,
            )
        run.report = report
        self._emit(report)
        return report

    # -- write path --------------------------------------------------------

    async def _reinforce(
        self,
        run: HyperstruckRun,
        steps: list[dict[str, Any]],
        *,
        is_success: bool,
        outcome: str,
        trigger: str,
        obligation_outcomes: Sequence[ReportedObligationOutcome] = (),
    ) -> RunReport:
        episode = self._build_episode(run, steps, is_success=is_success)
        # The best the run saw, not the last. A receipt is evidence that the model was
        # shown the block, and the run's own last call is not the only moment that could
        # have happened in.
        evidence = run.best_receipt or run.receipt
        receipt = evidence.text if evidence is not None else None
        try:
            await self._client.observe(identity=run.identity, episode=episode)
            result = await self._client.reinforce(
                identity=run.identity,
                episode=episode,
                is_org_promotion_allowed=self._declarations.is_fully_declared(
                    step["name"] for step in steps
                ),
                context_receipt=receipt,
                is_delivered=run.ledger.is_injected,
                recall_outcome=outcome,
                **_outcome_kwarg(obligation_outcomes),
            )
        except Exception as exc:  # noqa: BLE001 - never break the host run
            logger.warning(
                "Hyperstruck: write-back failed for run %s: %s", run.run_id, exc,
                exc_info=True,
            )
            return self._build_report(run, DISPOSITION_WRITE_FAILED, trigger=trigger)
        presence, closures = _read_write_result(result)
        return self._build_report(
            run,
            DISPOSITION_REINFORCED if receipt else DISPOSITION_OBSERVED,
            is_receipt_sent=receipt is not None,
            presence=presence,
            closures=closures,
            trigger=trigger,
        )

    async def _decline(
        self,
        run: HyperstruckRun,
        steps: list[dict[str, Any]],
        *,
        outcome: str,
        trigger: str,
        obligation_outcomes: Sequence[ReportedObligationOutcome] = (),
    ) -> RunReport:
        reason = decline_reason(
            [{**step, "kind": TOOL_CALL_KIND} for step in steps],
            is_worth_learning_from=False,
            is_goalless=not run.goal.strip(),
            is_offer_empty=not run.ledger.offered_any,
        )
        # A decline reason the boundary has not published is refused behind
        # ``extra="forbid"``, and a refused decline leaves the run open holding its
        # resolve reservation, which is worse than saying less. Withhold and say so.
        # The rule itself lives in ``_wire``: three client paths choose a decline
        # reason and re-deriving it here is what let them drift apart.
        if is_unpublished_decline_reason(reason):
            withheld = (
                f"decline_reason={reason} (the boundary has not published this reason; "
                "upgrade the platform deploy to release it)",
            )
            run.withheld = run.withheld + withheld
            return self._build_report(
                run, DISPOSITION_WITHHELD, decline=None, trigger=trigger
            )
        try:
            result = await self._client.decline(
                identity=run.identity,
                run_id=run.run_id,
                reason=reason,
                is_delivered=run.ledger.is_injected,
                recall_outcome=outcome,
                source_framework=self._source_framework,
                **_outcome_kwarg(obligation_outcomes),
            )
        except Exception as exc:  # noqa: BLE001 - never break the host run
            logger.warning(
                "Hyperstruck: decline failed for run %s: %s", run.run_id, exc,
                exc_info=True,
            )
            # Not `declined`. The run is still open server-side holding its resolve
            # reservation, and a report saying otherwise is the one that stops anyone
            # looking.
            return self._build_report(
                run, DISPOSITION_WRITE_FAILED, decline=reason, trigger=trigger
            )
        _, closures = _read_write_result(result)
        return self._build_report(
            run,
            DISPOSITION_DECLINED,
            decline=reason,
            closures=closures,
            trigger=trigger,
        )

    # -- internals ---------------------------------------------------------

    async def _prefetch(self, run: HyperstruckRun) -> None:
        """Resolve once and hold the rendered blocks. Fail open on anything."""
        try:
            context = await self._client.resolve(
                identity=run.identity,
                run_id=run.run_id,
                goal=run.goal,
                available_tools=run.tools,
                max_learnings=self._max_learnings,
                source_framework=self._source_framework,
            )
        except Exception as exc:  # noqa: BLE001 - fail open, never break the run
            logger.warning(
                "Hyperstruck: resolve failed for run %s: %s", run.run_id, exc,
                exc_info=True,
            )
            run.ledger.record_resolve_failed()
            return
        # Inside a guard, not after one. A response that violates a shelf invariant raises
        # here, and unguarded that left ``is_resolved`` False, which the taxonomy reads as
        # ``recall_missing``: "not a fault, the run was short". A boundary returning a
        # malformed offer was therefore indistinguishable from a short run, which is the
        # collapse the taxonomy exists to prevent.
        try:
            run.ledger.record_offer(**_shelves_from(context))
            run.injection_block = combine_injection_blocks(
                context.injected_text,
                context.injected_facts_text,
                context.injected_obligations_text,
            )
        except Exception as exc:  # noqa: BLE001 - fail open, and say which fault it was
            logger.warning(
                "Hyperstruck: resolve returned an unusable offer for run %s: %s",
                run.run_id,
                exc,
                exc_info=True,
            )
            if not run.ledger.is_closed and not run.ledger.is_resolved:
                run.ledger.record_resolve_failed()

    async def _join_prefetch(self, run: HyperstruckRun) -> None:
        """Wait out the prefetch before reporting, cancelling it if still in flight.

        ``asyncio.wait`` rather than awaiting the task: awaiting inside a suppress
        swallows a cancellation delivered to *this* coroutine as readily as one raised by
        the task, so an abnormally terminated run would continue past here and be observed.
        """
        task = run.resolve_task
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.wait({task}, timeout=_RESOLVE_JOIN_TIMEOUT)

    def _shelf_inputs(
        self, run: HyperstruckRun
    ) -> list[tuple[str, str | None, tuple[str, ...]]]:
        return [
            (shelf.name, shelf.text, shelf.offered_ids)
            for shelf in (
                run.ledger.advice,
                run.ledger.facts,
                run.ledger.obligations,
            )
            if shelf is not None
        ]

    def _build_episode(
        self, run: HyperstruckRun, steps: list[dict[str, Any]], *, is_success: bool
    ) -> Episode:
        records: list[StepRecord] = []
        completed = 0
        failed = 0
        withheld: list[str] = list(run.withheld)
        # The one-hop join's left-hand side: values this run's earlier steps returned, with
        # the label their tool declared. Built as the steps are walked and never carried
        # between runs, because the claim it supports is "this value came out of that tool
        # in this episode" and nothing weaker would be true.
        prior_outputs: dict[str, str] = {}
        for step in steps:
            if step["status"] == "failed":
                failed += 1
            else:
                completed += 1
            declared, dropped = self._declarations.declaration_for(
                step["name"], step["args"]
            )
            withheld.extend(dropped)
            # A value the agent copied out of an earlier result keeps that result's label.
            # One hop, escalate only, and checked against this run's own recorded outputs
            # rather than across the call graph, which we cannot see from a hook and could
            # not claim soundly if we could.
            escalated = self._declarations.propagate(
                step["name"], step["args"], prior_outputs
            )
            if escalated:
                # Joined, not overwritten. ``declaration_for`` has already stamped every
                # undeclared argument with the restrictive default, and ``propagate``
                # computes its own baseline from the registry alone, which does not hold
                # that default. Merging its answer over the stamp therefore *lowered* an
                # undeclared argument from secret to whatever the earlier tool declared,
                # which is the exact inversion the lattice exists to make impossible, and
                # the report announced it as an escalation while doing it.
                declared = dict(declared or {})
                before = dict(declared.get("args") or {})
                stamped = dict(before)
                for key, label in escalated.items():
                    stamped[key] = join(stamped.get(key), label) or label
                declared["args"] = stamped
                # Reported only where the stamp actually moved. Testing "the joined value
                # equals the propagated label" also fires when an undeclared argument was
                # already `secret` and the propagated label is `secret` too, which names an
                # earlier tool as the cause of a label the restrictive default had already
                # set, and so points the customer at the wrong remedy.
                escalated = {
                    k: v for k, v in escalated.items() if stamped[k] != before.get(k)
                }
            if escalated:
                withheld.append(
                    f"{step['name']}: {len(escalated)} argument(s) "
                    f"({', '.join(sorted(escalated))}) escalated to match a value an "
                    "earlier tool in this run returned"
                )
            # Result and error together, because they share an origin exactly: the same
            # tool, the same call, the same step. Covering one and not the other was an
            # inconsistency rather than a decision, and a stack trace carrying a customer
            # record is an ordinary thing for a failing tool to return.
            scanned = scan_and_scrub(
                {"result": step["result"], "error": step["error"]}, self._scanner
            )
            if not scanned.is_clean:
                withheld.append(f"{step['name']}: {scanned.describe()}")
            scanned_payload = scanned.payload
            step_result = (
                scanned_payload.get("result")
                if isinstance(scanned_payload, dict)
                else step["result"]
            )
            step_error = (
                scanned_payload.get("error")
                if isinstance(scanned_payload, dict)
                else step["error"]
            )
            records.append(
                StepRecord(
                    id=step["id"],
                    name=step["name"],
                    args=step["args"],
                    status=step["status"],
                    result=step_result,
                    error=step_error,
                    declared_sensitivity=declared,
                )
            )
            # Recorded after this step's own stamp, so a step can never escalate against
            # itself, and from the scrubbed payload, so a value the scanner removed cannot
            # be reintroduced into the join table it was removed from the wire for.
            self._declarations.record_outputs(prior_outputs, step["name"], step_result)
        # Scanned before the withheld list is snapshotted: it can add a line of its own,
        # and an entry appended after the snapshot never reaches the report.
        available_tools = self._scanned_tools(run.tools, withheld)
        run.withheld = tuple(dict.fromkeys(withheld))
        return Episode(
            run_id=run.run_id,
            goal=run.goal,
            steps=tuple(records),
            outcome=TerminalOutcome(
                is_success=is_success and failed == 0,
                total_steps=len(records),
                completed_steps=completed,
                failed_steps=failed,
            ),
            source_framework=self._source_framework,
            thread_id=run.thread_id,
            # The roster the agent had, not the tools it happened to call. The server
            # reads restraint from what was available and declined, so a roster derived
            # from the steps would only ever hold tools that ran.
            #
            # Scanned as well, because it goes to the platform and is stored alongside the
            # learning. ``ToolSpec``'s own docstring says "Pre-redact: these are stored
            # alongside the learning" and nothing enforced it: a JSON Schema carries
            # `description`, `default` and `examples`, and an example is routinely a real
            # value. The goal is deliberately *not* scanned; its origin is the principal,
            # which is the case origin labelling handles and the scanner is not for.
            available_tools=available_tools,
        )

    def _scanned_tools(
        self, tools: tuple[ToolSpec, ...], withheld: list[str]
    ) -> tuple[ToolSpec, ...]:
        """The roster with its schemas scanned, since they reach the platform verbatim."""
        if self._scanner is None or not tools:
            return tools
        scanned: list[ToolSpec] = []
        for tool in tools:
            result = scan_and_scrub(
                {"parameters": tool.parameters, "returns": tool.returns}, self._scanner
            )
            if result.is_clean or not isinstance(result.payload, dict):
                scanned.append(tool)
                continue
            withheld.append(f"{tool.name} (schema): {result.describe()}")
            scanned.append(
                ToolSpec(
                    name=tool.name,
                    description=tool.description,
                    category=tool.category,
                    parameters=result.payload.get("parameters"),
                    returns=result.payload.get("returns"),
                )
            )
        return tuple(scanned)

    def _build_report(
        self,
        run: HyperstruckRun,
        disposition: str,
        *,
        decline: str | None = None,
        is_receipt_sent: bool = False,
        is_evicted: bool = False,
        presence: tuple[dict[str, str], ...] = (),
        closures: tuple[ObligationClosureResult, ...] = (),
        trigger: str | None = None,
    ) -> RunReport:
        # The worst the run saw, because the reader's question is whether anything went
        # wrong on the way to the model, and a run that delivered twice and was trimmed on
        # the third call has something wrong with it.
        receipt = run.worst_receipt or run.receipt
        return RunReport(
            run_id=run.run_id,
            goal=run.goal,
            run_key_source=run.key.source,
            is_run_key_inferred=run.key.is_inferred,
            recall_outcome=ledger_recall_outcome(run.ledger),
            receipt_outcome=receipt.outcome if receipt is not None else "unresolved",
            is_receipt_sent=is_receipt_sent,
            shelves=tuple(
                {
                    "name": shelf.name,
                    "outcome": shelf.outcome,
                    "offered_ids": list(shelf.offered_ids),
                    "lines_expected": shelf.lines_expected,
                    "lines_found": shelf.lines_found,
                    "missing_lines": list(shelf.missing_lines),
                }
                for shelf in (receipt.shelves if receipt is not None else ())
            ),
            step_count=len(run.ledger.steps),
            model_call_count=run.ledger.model_call_count,
            disposition=disposition,
            close_trigger=trigger,
            presence_outcomes=presence,
            obligation_closures=closures,
            decline_reason=decline,
            withheld=run.withheld,
            is_evicted=is_evicted,
        )

    def _emit(self, report: RunReport) -> None:  # noqa: D401
        """Publish the report on every channel, and never let one break the others.

        The log line is on by default and unconditional, because a customer who registered
        nothing must still be able to find out what happened to their run. The callback is
        how a service routes the report into its own observability, and a callback that
        raises is the customer's bug, not a reason to lose the run.
        """
        self._last_report = report
        logger.info("hyperstruck.run %s", report.to_dict())
        if self._on_report is None:
            return
        try:
            self._on_report(report)
        except Exception as exc:  # noqa: BLE001 - a customer callback is not our loop
            logger.warning(
                "Hyperstruck: run report callback raised for %s: %s", report.run_id, exc
            )


def _located_lines(receipt: ReceiptLocation) -> int:
    """How much of our block one location found, for comparing two of them."""
    return sum(shelf.lines_found for shelf in receipt.shelves)


def _is_better(candidate: ReceiptLocation, against: ReceiptLocation) -> bool:
    return _located_lines(candidate) > _located_lines(against)


def _is_worse(candidate: ReceiptLocation, against: ReceiptLocation) -> bool:
    return _located_lines(candidate) < _located_lines(against)


def _shelves_from(context: ResolvedContext) -> dict[str, Shelf]:
    """The three shelves as the boundary described them, each with its own promise."""
    return {
        "advice": render_confirmed_shelf(
            "advice", context.injected_text, context.offered_learning_ids
        ),
        "facts": render_confirmed_shelf(
            "facts", context.injected_facts_text, context.offered_claim_ids
        ),
        "obligations": offered_and_delivered_shelf(
            "obligations",
            context.injected_obligations_text,
            context.offered_obligation_ids,
            context.delivered_obligation_ids or None,
        ),
    }


def _flatten(params: Any) -> str:
    from hyperstruck.runtime.receipt import flatten_params

    return flatten_params(params)


def new_run_id(agent_name: str) -> str:
    """A run id for a caller that wants one without opening a seat."""
    return f"{agent_name}:{uuid.uuid4().hex}"


__all__ = [
    "CLOSE_TRIGGER_ABANDONED",
    "CLOSE_TRIGGER_EXPLICIT",
    "CLOSE_TRIGGER_NO_TOOL_CALLS",
    "CLOSE_TRIGGER_PROCESS_EXIT",
    "DISPOSITION_DECLINED",
    "DISPOSITION_EVICTED",
    "DISPOSITION_OBSERVED",
    "DISPOSITION_REINFORCED",
    "DISPOSITION_WITHHELD",
    "DISPOSITION_WRITE_FAILED",
    "HyperstruckRun",
    "LedgerClosedError",
    "RunRegistry",
    "RunReport",
    "RunSeat",
    "ledger_recall_outcome",
    "recall_outcome",
]
