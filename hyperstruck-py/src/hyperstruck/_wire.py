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
    thread_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON body the platform expects."""
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "steps": [asdict(step) for step in self.steps],
            "outcome": asdict(self.outcome),
            "source_framework": self.source_framework,
            "thread_id": self.thread_id,
        }


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
    ``agent_id``): a distillation job stands outside the resolve/observe/reinforce loop, so
    there is no wrapping envelope. ``run_id`` must be namespaced ``distill:``.
    """

    agent_id: str
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

    def to_payload(self) -> dict[str, Any]:
        """Serialise to the JSON body the platform expects."""
        return {
            "agent_id": self.agent_id,
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


@dataclass(frozen=True)
class ResolvedContext:
    """The bound learnings for a goal, as returned by resolve.

    ``injected_text`` is the rendered block to prepend to the model call (rendered
    server-side); ``offered_learning_ids`` are the IDs offered, for client-side
    visibility and the injection-fidelity metric.
    """

    injected_text: str | None = None
    offered_learning_ids: tuple[str, ...] = ()

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ResolvedContext:
        return cls(
            injected_text=data.get("injected_text"),
            offered_learning_ids=tuple(data.get("offered_learning_ids") or ()),
        )
