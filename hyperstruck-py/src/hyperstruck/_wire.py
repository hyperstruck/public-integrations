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
REASON_EMPTY_OFFER = "empty_offer"
DECLINE_REASONS = frozenset(
    {REASON_NO_TOOL_CALLS, REASON_BELOW_MATERIAL_THRESHOLD, REASON_EMPTY_OFFER}
)


@dataclass(frozen=True)
class ToolSpec:
    """A tool the agent has available, as the platform's resolve expects it."""

    name: str
    description: str = ""


@dataclass(frozen=True)
class StepRecord:
    """One executed tool call: a planned decision joined to its outcome by id."""

    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    status: Literal["completed", "failed"] = "completed"
    result: Any = None
    error: str | None = None
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

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON body the platform expects."""
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "goal": self.goal,
            "steps": [asdict(step) for step in self.steps],
            "outcome": asdict(self.outcome),
            "source_framework": self.source_framework,
            "thread_id": self.thread_id,
        }
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
