"""Wire types crossing the boundary to the Hyperstruck platform.

Plain, JSON-serialisable value types with no Core dependency. The platform owns
the authoritative contract; these mirror only what the client must send and
receive. Deliberately minimal: the resolve response carries the rendered
injection block and the offered learning IDs, never full ``Learning`` objects, so
corpus internals stay server-side.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from hyperstruck.contracts import published_names

# Default cap on learnings resolved/injected per run, shared by the client and the
# middleware so the two defaults cannot drift.
DEFAULT_MAX_LEARNINGS = 8

# Server default when the client omits max_learnings on distill. Keep the client
# field optional and omit the wire key unless the caller overrides, so a client
# release can land before the API knows the field.
DEFAULT_DISTILL_MAX_LEARNINGS = 10
DISTILL_MIN_LEARNINGS = 1
DISTILL_MAX_LEARNINGS = 50

# Why a turn ended with nothing worth learning. The boundary validates against this
# exact set and rejects anything else, so the two must not drift.
REASON_NO_TOOL_CALLS = "no_tool_calls"
REASON_BELOW_MATERIAL_THRESHOLD = "below_material_threshold"
# No path in this client emits this any more: the recording path provably cannot reach it
# (see _decline_reason), and the read-only close that used to borrow it now names itself.
# Kept because it stays valid on the wire for a host driving the loop by hand, which the
# hyper-learning skill documents.
REASON_EMPTY_OFFER = "empty_offer"
REASON_UNEVIDENCED_OUTCOME = "unevidenced_outcome"
# A read-only recall closing itself. It has no outcome to reinforce against, so it is not
# a turn that was judged not worth learning from: there was never a judgement to make. It
# is its own reason because the daily credit alert reported it as lost credit while it
# borrowed REASON_BELOW_MATERIAL_THRESHOLD and REASON_EMPTY_OFFER. Only the first of those
# is also sent by the recording path, and one shared reason was enough to make the two
# populations indistinguishable in the one column that should have separated them.
REASON_READONLY_CLOSE = "readonly_close"
# A turn the host started without ever handing this client a prompt. It is not a turn
# that did too little, which is what every reason above reports: its steps may be
# entirely material. What it has no account of is what it was trying to do, and a goal
# is what an extracted rule is transferable *against*, so observing it asks the corpus
# to generalise from an episode with nothing to generalise about.
REASON_NO_GOAL = "no_goal"
DECLINE_REASONS = frozenset(
    {
        REASON_NO_TOOL_CALLS,
        REASON_BELOW_MATERIAL_THRESHOLD,
        REASON_EMPTY_OFFER,
        REASON_UNEVIDENCED_OUTCOME,
        REASON_READONLY_CLOSE,
        REASON_NO_GOAL,
    }
)

_DECLINE_CONTRACT = Path(__file__).parent / "published_decline_reasons.json"


def is_unpublished_decline_reason(reason: str) -> bool:
    """Whether this reason must be withheld rather than sent.

    The boundary refuses a reason it does not know, and a refused decline is not a
    degraded diagnostic: it leaves the run open holding its resolve reservation until
    the retention sweep.

    Keyed on whether the reason is published, never on which reason it is. Both client
    paths read ``reason == REASON_NO_GOAL and ...`` while no_goal was the only
    unpublished member, so publishing it would have left both gates permanently false
    and the next reason added with no gate at all, in branches that still looked
    guarded.

    ``published and`` is not a formality. ``published_names`` degrades a missing,
    truncated or wrong-shaped contract file to an EMPTY set by design, and under a
    per-reason key that cost one reason while the rest still went out. Under a property
    key an empty set would withhold EVERY decline, so one corrupt JSON file in a wheel
    would stop any run closing, fleet-wide, and the hook fails open so it would surface
    nowhere. ``wire_value`` reasons this out at length for the recall half: an unreadable
    contract is not an empty one, and reading it as one turns a loud packaging fault into
    a silent data-integrity one. Sending optimistically is strictly no worse, because a
    genuinely unpublished reason is refused and the run is left open either way, while a
    published-but-locally-unreadable one declines cleanly.

    Lives here rather than in either caller because there are THREE client paths that
    choose a decline reason and only two were re-keyed when this was first fixed; the
    third, ``ide/hook.py``, staged whatever ``turn_gate`` returned with no publication
    gate at all, while gating the recall outcome beside it. Re-deriving the rule is what
    let them drift.
    """
    published = published_decline_reasons()
    return bool(published) and reason not in published


def published_decline_reasons() -> frozenset[str]:
    """The decline reasons the boundary accepts, as published by it.

    A reason it does not know is refused outright, and a refused decline leaves the run
    open holding its resolve reservation until the retention sweep, so a reason is only
    ever sent once it appears here.
    """
    return published_names(_DECLINE_CONTRACT, "reasons")


@dataclass(frozen=True)
class ToolSpec:
    """A tool the agent has available, as the platform's resolve expects it."""

    name: str
    description: str = ""
    # Only the server's own categories are read: "read_only", "write",
    # "destructive", "external", "delegation". Of those, "write", "destructive"
    # and "external" are the side-effectful ones, and declaring at least one is
    # what makes a run holding off from an act legible at all. A near-miss such
    # as "read" is treated as declaring nothing.
    category: str | None = None
    # The tool's declared schemas, used to fingerprint its shape. Pre-redact:
    # these are stored alongside the learning.
    parameters: dict[str, Any] | None = None
    returns: dict[str, Any] | None = None


@dataclass(frozen=True)
class StepRecord:
    """One executed tool call: a planned decision joined to its outcome by id."""

    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    status: Literal["completed", "failed", "skipped"] = "completed"
    result: Any = None
    error: str | None = None
    # The runtime decided this act must not happen. Valid only with ``status``
    # of ``"skipped"`` and no ``error``; the three together are what the server
    # reads as a refusal. ``"skipped"`` on its own is not one, and sending it
    # alone makes the whole run read as having acted.
    is_refused: bool = False
    # Per-argument sensitivity labels declared for this tool, e.g.
    # ``{"args": {"ssn": "pii"}}``. Drives client-side redaction before the wire.
    #
    # A section may also be a bare string, of which ``subject`` is the one the server
    # reads: the argument key naming the entity this step's result is about. The
    # boundary has accepted that shape since core-platform #427 and Core consumes it
    # through ``resolve_subject_arg_key``; this type was the only thing left stopping a
    # published client from sending it. Without it every foreign caller falls to
    # structural salience, which is the fallback rung operating as the only rung, and
    # the cost is entity fragmentation: the same company arriving under two names
    # accumulates two dossiers and neither reaches the stability the read side gates on.
    declared_sensitivity: dict[str, dict[str, bool | str | int] | str] | None = None


@dataclass(frozen=True)
class TerminalOutcome:
    """The run's terminal result."""

    is_success: bool
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    # The answer this run actually gave its principal, verbatim: the composed output the person was
    # shown, not the reasoning that produced it. Sent, the agent's own commitments in it ("I'll
    # confirm the volumes by Friday") are recorded on the obligation shelf and offered back to the
    # agent when they come due. Omitted, nothing else changes.
    #
    # Populate it only from the composed output. A tool result put here is stored under a provenance
    # class that says the AGENT bound itself, which turns retrieved content into a promise.
    final_output: str | None = None


def _drop_defaults(payload: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Strip keys still at the value that means "the caller said nothing".

    Every field on this wire is added to the API model before it is added here,
    but a client is upgraded on the customer's schedule and an API is upgraded on
    ours, so the two orders both happen. The API forbids extra keys, and a 4xx is
    terminal to the flush retry, so a field emitted unconditionally does not
    degrade against an older API: it drops those episodes permanently. Omitting a
    default-valued field costs nothing and removes that whole class of failure.
    """
    return {k: v for k, v in payload.items() if k not in defaults or v != defaults[k]}


def _step_payload(step: StepRecord) -> dict[str, Any]:
    return _drop_defaults(asdict(step), {"is_refused": False})


def _tool_payload(tool: ToolSpec) -> dict[str, Any]:
    return _drop_defaults(
        asdict(tool), {"category": None, "parameters": None, "returns": None}
    )


@dataclass(frozen=True)
class EpisodeSpan:
    """One contiguous stretch of the goal, with the origin this client asserts for it.

    ``source`` is who decided, and it is a fixed ``"client"`` rather than a caller field: the
    platform counts spans by labeller, and a value the caller could set would make that count
    a claim about whatever the caller wrote instead of about who did the work.
    """

    text: str
    origin: str
    source: str = "client"


@dataclass(frozen=True)
class Episode:
    """A finished foreign run, ready to ship to observe / reinforce."""

    run_id: str
    goal: str
    steps: tuple[StepRecord, ...] = ()
    outcome: TerminalOutcome = field(
        default_factory=lambda: TerminalOutcome(is_success=True)
    )
    source_framework: str = "langgraph"
    # Populate only from a human-input channel. Model output, tool results and retrieved
    # documents must never reach this: the guarantee it carries is about which writer can
    # set it, not about what it contains, so a host that fills it from anything else has
    # silently handed authority to whatever wrote the text.
    principal_utterance: str | None = None
    thread_id: str | None = None
    # When this run actually spoke, as an aware instant. Left unset the server stamps its own
    # arrival, which is receipt time: fine for learning decay, wrong for the own-output obligation
    # lane, whose anchor kind `run_clock` exists precisely to be distinguishable FROM receipt. A
    # hook that staged a turn and flushed it after a laptop sleep would otherwise date "by Friday"
    # from the flush rather than from the answer.
    occurred_at: datetime | None = None
    # The tools the agent had available during this run. Left empty, the server
    # writes an empty capability fingerprint and cannot read restraint at all,
    # so a run that deliberately held off is indistinguishable from one that had
    # nothing to hold off from.
    available_tools: tuple[ToolSpec, ...] = ()
    # How this client cut the goal into prose and machine markup.
    spans: tuple[EpisodeSpan, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON body the platform expects."""
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "goal": self.goal,
            "steps": [_step_payload(step) for step in self.steps],
            # Defaults dropped, for the reason ``_drop_defaults`` gives: the API model forbids extra
            # keys and a 4xx is terminal to the flush retry, so a field emitted unconditionally does
            # not degrade against an older API, it drops those episodes permanently.
            "outcome": _drop_defaults(asdict(self.outcome), {"final_output": None}),
            "source_framework": self.source_framework,
            "thread_id": self.thread_id,
        }
        # Omitted when unset, on the same rule as the two fields below: the API model forbids
        # extra keys and a 4xx is terminal to the flush retry, so an unconditional emit drops
        # every episode permanently against an API that predates the field.
        if self.occurred_at is not None:
            payload["occurred_at"] = self.occurred_at.isoformat()
        # Same rule as ``principal_utterance`` below, and for the same reason: an
        # API that predates this field forbids it outright, so emitting it when
        # the caller declared no roster would 422 every write for anyone who
        # upgrades this package before the deploy lands. Sending it only when it
        # carries something keeps an upgraded client working against an older API.
        if self.available_tools:
            payload["available_tools"] = [
                _tool_payload(tool) for tool in self.available_tools
            ]
        # Same rule, load-bearing here: a platform predating this field forbids it, and a 4xx is
        # terminal to the flush retry.
        if self.spans:
            payload["spans"] = [asdict(span) for span in self.spans]
        # Omitted entirely when unset. The API model forbids extra keys and rejects a
        # forbidden one even with a null value, so emitting it unconditionally would 422
        # every write for anyone who upgrades this package before the API deploy lands,
        # and a 4xx is terminal to the flush retry, so those episodes are dropped for good.
        if self.principal_utterance:
            payload["principal_utterance"] = self.principal_utterance
        return payload


@dataclass(frozen=True)
class EvidenceItem:
    """One piece of corpus evidence for distillation (a content step, not a tool call)."""

    id: str

    content: str

    label: str = ""

    role: Literal["support", "contrast", "neutral"] = "neutral"

    status: Literal["completed", "failed"] = "completed"

    source_ref: str | None = None
    # The entity this item is about, e.g. an account or product name. Given, it is the name the
    # facts are filed under, so two spellings of one company do not become two entities and never
    # accumulate corroboration. Omitted, the entity is read from the prose.
    # Optional caller hints: emails, Slack ids, or other surface forms that name a
    # person in this item. The platform also harvests those from the content.

    subject: str | None = None
    # Where the item came from: ``provenance`` carries ``source_class``, ``source_id`` (the system
    # the item came from, not the item's own reference) and an optional RFC 3339 ``source_time``
    # for when its facts became true. To say what the item is *about*, use ``subject`` above.

    declared_sensitivity: dict[str, Any] | None = None

    identity_markers: tuple[str, ...] = ()
    # What this item is about, and where it came from. ``subject`` names the field carrying the
    # entity, so two spellings of one company do not become two entities; ``provenance`` carries
    # ``source_class``, ``source_id`` (the system the item came from, not the item's own
    # reference) and an optional RFC 3339 ``source_time`` for when its facts became true.

    # Typed obligations this item already carries, written verbatim with no LLM involved: they
    # are stored directly on the obligation shelf as ``provenance_class=user_directed`` and never
    # enter this item's extraction. Up to 8 per item, 50 across a request. ``ObligationDue.at``
    # must already be an aware ISO-8601 instant: the server refuses a relative date such as
    # "next Friday" on this path rather than resolving it, so pre-resolve it before sending.
    obligations: tuple[Obligation, ...] = ()
    # What your connector knows about this document; shapes under ``RecordContextModel``.
    # Send the whole set each time, and addresses as ``email``: keyed, never kept.
    record_context: dict[str, Any] | None = None


def _evidence_payload(item: EvidenceItem) -> dict[str, Any]:
    payload = _drop_defaults(
        asdict(item),
        {"identity_markers": (), "obligations": (), "record_context": None},
    )
    # Not asdict's own nested conversion: Obligation/ObligationParty/ObligationDue each drop
    # their own None fields through to_payload(), and asdict() would instead emit every field,
    # including the ones the caller left unset.
    if item.obligations:
        payload["obligations"] = [o.to_payload() for o in item.obligations]
    return payload


@dataclass(frozen=True)
class DistillOutcome:
    """The corpus job's terminal verdict."""

    is_success: bool
    summary: str | None = None


@dataclass(frozen=True)
class DistillJob:
    """A corpus distillation job, ready to ship to ``POST /distill``.

    Unlike an ``Episode`` this is the whole flat request body (it carries its own
    ``agent_name``): a distillation job stands outside the resolve/observe/reinforce loop, so
    there is no wrapping envelope. ``run_id`` must be namespaced ``distill:``.
    """

    agent_name: str
    run_id: str
    goal: str
    evidence: tuple[EvidenceItem, ...]
    outcome: DistillOutcome = field(
        default_factory=lambda: DistillOutcome(is_success=True)
    )
    org_id: str | None = None
    evaluation: str | None = None
    synthesis_notes: str | None = None
    source_framework: str = "api:distill"
    occurred_at: str | None = None
    max_learnings: int | None = None

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON body the platform expects."""
        payload: dict[str, Any] = {
            "agent_name": self.agent_name,
            "org_id": self.org_id,
            "run_id": self.run_id,
            "goal": self.goal,
            "evidence": [_evidence_payload(item) for item in self.evidence],
            "outcome": asdict(self.outcome),
            "evaluation": self.evaluation,
            "synthesis_notes": self.synthesis_notes,
            "source_framework": self.source_framework,
            "occurred_at": self.occurred_at,
        }
        # Omit unless the caller set an override; the server applies its default.
        if self.max_learnings is not None:
            payload["max_learnings"] = self.max_learnings
        return payload


@dataclass(frozen=True)
class ObligationParty:
    """One side of an obligation: a role the host names (``AE``, ``agent``), a party by name, or
    a registry entity id. A name is resolved, and minted if new, on the server."""

    role: str | None = None
    entity: str | None = None
    entity_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            k: v
            for k, v in (
                ("role", self.role),
                ("entity", self.entity),
                ("entity_id", self.entity_id),
            )
            if v is not None
        }


@dataclass(frozen=True)
class ObligationDue:
    """When an obligation falls due: an aware ISO-8601 instant, its IANA zone, and whether the
    caller meant the day or the instant. A ``date`` due is overdue after the end of that day in
    its zone; naive instants are refused by the server rather than assumed UTC."""

    at: str
    tz: str | None = None
    precision: str = "date"

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"at": self.at, "precision": self.precision}
        if self.tz is not None:
            payload["tz"] = self.tz
        return payload


@dataclass(frozen=True)
class Obligation:
    """A directed obligation, ready to ship to ``POST /agents/{agent_id}/obligations``.

    Stands outside the resolve/observe/reinforce loop like a distillation job: the host hands
    the agent something it owes, and the server holds it, dedupes it, bounds it and expires it.
    The outcome comes back typed rather than as a status code, because a refusal is a fact the
    host should read, not an error.
    """

    statement: str
    owed_by: ObligationParty
    owed_to: ObligationParty
    subject: ObligationParty | None = None
    due: ObligationDue | None = None
    not_before: str | None = None
    lead_days: int | None = None
    premises: tuple[str, ...] = ()
    due_from_claim_id: str | None = None
    expires_at: str | None = None
    timezone: str | None = None
    provenance: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "statement": self.statement,
            "owed_by": self.owed_by.to_payload(),
            "owed_to": self.owed_to.to_payload(),
        }
        if self.subject is not None:
            payload["subject"] = self.subject.to_payload()
        if self.due is not None:
            payload["due"] = self.due.to_payload()
        for key, value in (
            ("not_before", self.not_before),
            ("lead_days", self.lead_days),
            ("due_from_claim_id", self.due_from_claim_id),
            ("expires_at", self.expires_at),
            ("timezone", self.timezone),
            ("provenance", self.provenance),
        ):
            if value is not None:
                payload[key] = value
        if self.premises:
            payload["premises"] = list(self.premises)
        return payload


OBLIGATION_OUTCOMES: frozenset[str] = frozenset(
    {
        "written",
        "deduped",
        "suppressed",
        "evicted_then_written",
        "refused_capacity",
        "refused_invalid",
    }
)


@dataclass(frozen=True)
class ObligationOutcome:
    """What became of a held obligation: its id when it landed or already existed, the typed
    outcome, the row an over-allowance write evicted, and the reason for a refusal."""

    outcome: str
    id: str | None = None
    evicted_id: str | None = None
    reason: str | None = None

    @property
    def is_held(self) -> bool:
        return self.outcome in {"written", "deduped", "evicted_then_written"}

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ObligationOutcome:
        return cls(
            outcome=str(data.get("outcome") or "refused_invalid"),
            id=data.get("id"),
            evicted_id=data.get("evicted_id"),
            reason=data.get("reason"),
        )


@dataclass(frozen=True)
class ObligationClosure:
    """How an obligation ended, for the item-level verbs and for a loop-level outcomes list.

    ``expected_version`` is optional and is the version the caller last read. Left out, the shelf's
    own open-status guard still applies, so a row that has already closed is refused; the token is
    for a caller that read a row, decided something about it, and wants to be told if it moved
    since. It is a body field rather than an ``If-Match`` header because the commonest caller holds
    a bare id from ``offered_obligation_ids`` and no version at all.
    """

    outcome: str
    kept_basis: str | None = None
    dropped_reason: str | None = None
    note: str | None = None
    expected_version: int | None = None

    def __post_init__(self) -> None:
        if self.outcome not in {"kept", "dropped"}:
            raise ValueError(
                "an obligation closes as kept or dropped; use cancel to withdraw the record"
            )
        if self.outcome == "kept" and not self.kept_basis:
            raise ValueError(
                "closing as kept needs a kept_basis: reported, evidenced or declared"
            )
        if self.outcome == "dropped" and not self.dropped_reason:
            raise ValueError(
                "closing as dropped needs a dropped_reason: not_an_obligation, no_longer_applies, wont_do or duplicate"
            )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"outcome": self.outcome}
        for name, value in (
            ("kept_basis", self.kept_basis),
            ("dropped_reason", self.dropped_reason),
            ("note", self.note),
            ("expected_version", self.expected_version),
        ):
            if value is not None:
                payload[name] = value
        return payload

    def to_outcome_payload(self, obligation_id: str) -> dict[str, Any]:
        """The same closure as one entry in a loop-level ``obligation_outcomes`` list.

        ``expected_version`` is deliberately dropped: the run lock serialises the loop-level path,
        so there is no race for a token to guard and the server does not accept one.
        """
        payload = self.to_payload()
        payload.pop("expected_version", None)
        return {"id": obligation_id, **payload}


@dataclass(frozen=True)
class ReportedObligationOutcome:
    """One obligation a turn resolved, reported with the reinforce or decline that ends the run.

    The loop-level alternative to the item-level verbs, for the host that took the due-set block,
    acted on it, and holds a handful of ids from ``offered_obligation_ids``. A POST per obligation
    on top of the reinforce it is already sending would be a round trip per row for no added
    safety, since the run lock serialises this path. That is also why there is no
    ``expected_version`` here and why the server accepts none: there is no race for a token to
    guard, and a host reporting what its own turn did is not racing anybody.
    """

    id: str
    outcome: str
    kept_basis: str | None = None
    dropped_reason: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        self._closure()

    def _closure(self) -> ObligationClosure:
        """The item-level closure this reports, which is where the coherence rules live.

        Built rather than restated, so "kept needs a basis, dropped needs a reason" exists in one
        place and the two paths cannot come to disagree about what a coherent closure is.
        """
        return ObligationClosure(
            outcome=self.outcome,
            kept_basis=self.kept_basis,
            dropped_reason=self.dropped_reason,
            note=self.note,
        )

    def to_payload(self) -> dict[str, Any]:
        return self._closure().to_outcome_payload(self.id)


CLOSURE_APPLIED = "applied"
# The only transient disposition, and the only one worth sending again.
CLOSURE_BUSY = "busy"


@dataclass(frozen=True)
class ObligationClosureResult:
    """What the boundary did with one reported outcome, per id.

    A batch of outcomes can partly apply, and until this existed every mix of applied, ignored
    and unknown ids came back as the same 202. ``status`` is the row's status after the call,
    and None where there was no row this call read.
    """

    id: str
    disposition: str
    status: str | None = None

    @property
    def is_applied(self) -> bool:
        return self.disposition == CLOSURE_APPLIED

    @property
    def is_retryable(self) -> bool:
        return self.disposition == CLOSURE_BUSY

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "disposition": self.disposition, "status": self.status}


@dataclass(frozen=True)
class ReinforceResult:
    """What a reinforce or a decline read back: the presence verdicts and the closure results.

    A named return rather than a bare sequence, because two unrelated answers now come back from
    one call and because a developer looks for a value at the call they made. A closure result
    reachable only through the run report would be invisible to exactly the host that reported
    the closure.

    Both halves are empty on the asynchronous write path, where the response arrives after the
    caller has gone, and empty against a deployment that returns neither, which is what both
    clients degrade to.
    """

    presence_outcomes: tuple[dict[str, str], ...] = ()
    obligation_closures: tuple[ObligationClosureResult, ...] = ()


def combine_injection_blocks(
    advice: str | None, facts: str | None, obligations: str | None = None
) -> str | None:
    """Place the advice, fact and obligation blocks adjacently, for a host that wants no choice.

    Lives beside :class:`ResolvedContext` because every surface needs it: the halves are
    returned separately so a host *may* place them apart, which leaves each host that
    does not care to re-derive the same join. Takes the two blocks rather than the
    context, since a host replaying a stashed turn holds the strings without the object.

    ``obligations`` is last and optional. Last because it is the shortest and the most
    time-sensitive of the three, so a reader meets it after the framing rather than instead
    of it; optional because an older stash holds two strings and a replay of it must not
    become a call this function refuses.

    The blank line between them is this client's own convention, not the boundary's:
    Core's ``InjectionBlocks.injected_text`` joins the same two halves with a single
    newline. Nothing depends on the separator (the receipt matcher is anchored per
    fragment and explicitly does not require the halves to be adjacent), so the two are
    allowed to differ, but neither is "the" documented placement and this one must not
    be cited as though it were.
    """
    parts = [block for block in (advice, facts, obligations) if block]
    if not parts:
        return None
    return "\n\n".join(parts)


@dataclass(frozen=True)
class ResolvedContext:
    """The bound learnings for a goal, as returned by resolve.

    ``injected_text`` is the rendered advice block to prepend to the model call
    (rendered server-side); ``offered_learning_ids`` are the IDs offered, for
    client-side visibility and the injection-fidelity metric.

    ``injected_facts_text`` is the block of facts the agent established about
    entities it has already investigated, returned separately so a host can place
    it where its model treats it best and keep the advice half in a cached prompt
    prefix. A host that wants no choice injects the two adjacently.
    ``offered_claim_ids`` names the facts that block carries.

    ``injected_obligations_text`` is the third block: the few open obligations that
    bear on this moment, by their dates, by an entity the goal bound, or because
    what one rested on has changed. It is advisory and every line says so; it is
    not a task list to execute. ``offered_obligation_ids`` names what the shelf
    admitted, which can be more than the block carries when the block's token
    budget cut the tail, and ``delivered_obligation_ids`` names the subset the block
    actually rendered. The two are held apart because the shelf escalates on
    deliveries: an obligation admitted by selection and then cut by the budget was
    shown to no model and must never be escalated for being ignored. Advice and facts
    need no such pair, because their offer is render-confirmed and the two sets
    coincide by construction.

    Every fact and obligation field is empty against a server that predates it,
    and against a deployment holding no claims or no obligations for the agent.
    """

    injected_text: str | None = None
    injected_facts_text: str | None = None
    injected_obligations_text: str | None = None
    offered_learning_ids: tuple[str, ...] = ()
    offered_claim_ids: tuple[str, ...] = ()
    offered_obligation_ids: tuple[str, ...] = ()
    # What the obligation block actually carried, which the offered set deliberately
    # over-states. Empty against a server that predates the field, and that reads as
    # nothing delivered rather than as everything delivered: over-reporting is what
    # escalates an obligation no model was ever shown, and under-reporting only forgoes
    # credit. The two are not the same size of mistake, so the absent case takes the
    # side that cannot harm anyone.
    delivered_obligation_ids: tuple[str, ...] = ()

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ResolvedContext:
        return cls(
            injected_text=data.get("injected_text"),
            injected_facts_text=data.get("injected_facts_text"),
            injected_obligations_text=data.get("injected_obligations_text"),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
            offered_claim_ids=tuple(data.get("offered_claim_ids") or ()),
            offered_obligation_ids=tuple(data.get("offered_obligation_ids") or ()),
            delivered_obligation_ids=tuple(data.get("delivered_obligation_ids") or ()),
        )
