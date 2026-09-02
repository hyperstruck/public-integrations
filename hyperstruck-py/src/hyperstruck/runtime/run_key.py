"""Which model calls belong to the same run, and how confident we are about it.

The model-layer seat's hooks fire once per model call, not once per episode, so the seat
has to answer a question the LangGraph seat never had to: which calls are the same run.
Getting it wrong is not an inefficiency. Two concurrent conversations sharing one wrapped
client would have one run's block matched against the other's params.

**We do not invent a correlation key.** The observability layer most customers already run
has one. OpenTelemetry's GenAI conventions define an ``invoke_agent`` span above the model
spans, and ``gen_ai.conversation.id`` as an identifier for a conversation, session or
thread, meant for keeping a multi-turn session traceable as a unit. Reading theirs also
means our run report lines up against their own incident rather than sitting beside it.

**We do not depend on a tracer either.** OpenTelemetry's own client design principles say a
library should depend only on the API, which is a safe no-op without an SDK and carries no
transitive dependencies, so taking that dependency would be sanctioned and cheap. It would
also serve exactly one tracer. Customers run Datadog and Sentry too, and each would be
another dependency and another release to wait for. So the rung is a *resolver*: the
shipped default guard-imports the OpenTelemetry API and anything else is three lines the
customer writes today. The optional ``[otel]`` extra only pins the API version for someone
who would rather state the capability in a lockfile than discover it at import.

The ladder is ordered by how much the answer can be trusted, and the run report always says
which rung answered, because an inferred key is a fact about the report's reliability that
the reader is entitled to.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

# Set by the seat's own ``withRun``/``run()`` wrapper. A ContextVar rather than a
# thread-local because the runtimes this seat targets are asyncio-shaped, and a
# thread-local is shared by every task on the loop, which is the same cross-run leak this
# module exists to prevent.
_CURRENT_RUN: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "hyperstruck_current_run", default=None
)


@dataclass(frozen=True)
class RunKey:
    """A run's correlation key and where it came from.

    ``source`` is reported rather than kept internal. "The key came from your trace
    context" and "we guessed from the message history" license different amounts of
    confidence in everything downstream of it, and a report that presents both the same
    way is the one that gets trusted when it should not be.
    """

    key: str
    source: str
    is_inferred: bool


RunKeyResolver = Callable[[], RunKey | None]


def current_context_run_key() -> RunKey | None:
    """The key set by this seat's own run wrapper. Exact, and requires one wrapper."""
    key = _CURRENT_RUN.get()
    if key is None:
        return None
    return RunKey(key=key, source="context", is_inferred=False)


def set_current_run(key: str) -> contextvars.Token[str | None]:
    """Bind a run key for the current context. The token restores the previous one."""
    return _CURRENT_RUN.set(key)


def reset_current_run(token: contextvars.Token[str | None]) -> None:
    _CURRENT_RUN.reset(token)


def otel_run_key() -> RunKey | None:
    """The active OpenTelemetry trace, when the API is installed and a span is recording.

    Guarded rather than depended upon, for the reason in the module docstring. The import
    is one function wide and any failure falls to the next rung, so a breaking change in
    the API costs correlation quality and never correctness.

    A non-recording span is treated as absent. The API returns an invalid no-op span when
    no SDK is configured, and its all-zero trace id would otherwise become a single shared
    run key for every concurrent run in the process, which is precisely the collision this
    module exists to prevent.
    """
    try:
        from opentelemetry import trace as _trace
    except Exception:
        return None
    try:
        span = _trace.get_current_span()
        context = span.get_span_context()
        if not context.is_valid:
            return None
        return RunKey(
            key=f"{context.trace_id:032x}", source="trace", is_inferred=False
        )
    except Exception:
        return None


# The explicit wrapper first, the trace second. Ordered by how much each rung can be
# trusted *as a run boundary*, which is not the same as how precise its identifier is: a
# trace context supplies a key and never an end, while the wrapper supplies both and is the
# only rung exact in both directions. With the trace first, a caller who wrapped their run
# explicitly had that wrapper ignored whenever a span happened to be recording, and two
# concurrent handles inside one trace collided on a single key.
DEFAULT_RESOLVERS: tuple[RunKeyResolver, ...] = (current_context_run_key, otel_run_key)


def resolve_run_key(
    resolvers: Sequence[RunKeyResolver] = DEFAULT_RESOLVERS,
) -> RunKey:
    """The best available key, or a minted one that says it was minted.

    Falling back to a fresh identifier rather than to a shared default is deliberate: a
    process-wide constant would silently merge every unattributed run into one, and a
    merged run reports a receipt for a block another run was shown. A unique key loses
    correlation across calls, which the report says out loud; a shared one loses
    correctness, which it could not.
    """
    for resolver in resolvers:
        try:
            key = resolver()
        except Exception:
            continue
        if key is not None:
            return key
    return RunKey(key=uuid.uuid4().hex, source="minted", is_inferred=True)
