"""Wire types crossing the boundary to the Hyperstruck platform.

Plain, JSON-serialisable value types with no Core dependency. The platform owns
the authoritative contract; these mirror only what the client must send and
receive. Deliberately minimal: the resolve response carries the rendered
injection block and the offered learning IDs, never full ``Learning`` objects, so
corpus internals stay server-side.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

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
DECLINE_REASONS = frozenset(
    {
        REASON_NO_TOOL_CALLS,
        REASON_BELOW_MATERIAL_THRESHOLD,
        REASON_EMPTY_OFFER,
        REASON_UNEVIDENCED_OUTCOME,
        REASON_READONLY_CLOSE,
    }
)


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
    declared_sensitivity: dict[str, dict[str, str]] | None = None


@dataclass(frozen=True)
class TerminalOutcome:
    """The run's terminal result."""

    is_success: bool
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0


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
    # The tools the agent had available during this run. Left empty, the server
    # writes an empty capability fingerprint and cannot read restraint at all,
    # so a run that deliberately held off is indistinguishable from one that had
    # nothing to hold off from.
    available_tools: tuple[ToolSpec, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON body the platform expects."""
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "goal": self.goal,
            "steps": [_step_payload(step) for step in self.steps],
            "outcome": asdict(self.outcome),
            "source_framework": self.source_framework,
            "thread_id": self.thread_id,
        }
        # Same rule as ``principal_utterance`` below, and for the same reason: an
        # API that predates this field forbids it outright, so emitting it when
        # the caller declared no roster would 422 every write for anyone who
        # upgrades this package before the deploy lands. Sending it only when it
        # carries something keeps an upgraded client working against an older API.
        if self.available_tools:
            payload["available_tools"] = [
                _tool_payload(tool) for tool in self.available_tools
            ]
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
    subject: str | None = None
    # Where the item came from: ``provenance`` carries ``source_class``, ``source_id`` (the system
    # the item came from, not the item's own reference) and an optional RFC 3339 ``source_time``
    # for when its facts became true. To say what the item is *about*, use ``subject`` above.
    declared_sensitivity: dict[str, Any] | None = None


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
            "evidence": [asdict(item) for item in self.evidence],
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

    Both fact fields are empty against a server that predates them, and against a
    deployment holding no claims for the agent.
    """

    injected_text: str | None = None
    injected_facts_text: str | None = None
    offered_learning_ids: tuple[str, ...] = ()
    offered_claim_ids: tuple[str, ...] = ()

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ResolvedContext:
        return cls(
            injected_text=data.get("injected_text"),
            injected_facts_text=data.get("injected_facts_text"),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
            offered_claim_ids=tuple(data.get("offered_claim_ids") or ()),
        )
