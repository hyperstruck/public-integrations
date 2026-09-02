"""The OpenTelemetry adapter, best effort only.

The GenAI semantic conventions define agent, workflow, tool and model spans, and auto
instrumentation exists for most stacks, so deriving an episode passively is attractive. It
is not the contract, and the reason is dated rather than vague: every ``gen_ai.*``
attribute still carries the Development stability badge, and the conventions were moved out
of the main semantic-conventions repository into a dedicated one in June 2026 with no
published stabilisation timeline. Attribute names can therefore change without a major
version bump.

So the mapping is pinned here in one place, documented as best effort, and **no contract
test depends on it**. A customer with no instrumentation loses correlation quality, never
correctness.

The trace rung itself lives in :mod:`hyperstruck.runtime.run_key`, because it is the one
every seat gets by default. What lives here is the rung below it, which reads an attribute
off a live span, and that is a different kind of claim: reading a span's attributes back is
not part of the OpenTelemetry API's public surface, so a provider is free not to expose it.
Opting into it is therefore the customer's decision about their own instrumentation rather
than a library's about everyone's.
"""

from __future__ import annotations

from collections.abc import Sequence

from hyperstruck.runtime.run_key import DEFAULT_RESOLVERS, RunKey, RunKeyResolver

# The attribute naming a conversation, session or thread, meant for keeping a multi-turn
# session traceable as a unit. Pinned as a constant so the day it is renamed is a one-line
# change with a reader who knows why it is here.
CONVERSATION_ID_ATTRIBUTE = "gen_ai.conversation.id"

# What the report calls a run keyed this way. Distinct from "trace": a conversation id keys
# a multi-turn session and a trace id keys one operation, and a reader deciding how much to
# trust a correlation is entitled to know which of the two answered.
CONVERSATION_SOURCE = "conversation"


def conversation_run_key() -> RunKey | None:
    """``gen_ai.conversation.id`` off the active span, when the host set one.

    Guarded at every step and returning ``None`` rather than raising, for the reason in the
    module docstring: losing this rung costs correlation quality and never correctness,
    which is the whole basis on which the adapter is best effort.

    The recording check matters as much here as it does for the trace rung. A non-recording
    span carries no attributes, and treating its absent conversation id as an answer would
    put every concurrent run in the process under one key, which is precisely the collision
    the ladder exists to prevent.
    """
    try:
        from opentelemetry import trace as _trace
    except Exception:
        return None
    try:
        span = _trace.get_current_span()
        if not span.get_span_context().is_valid:
            return None
        # Not on the API's Span protocol; a provider that does not expose it falls through
        # to the next rung rather than taking the run down.
        attributes = getattr(span, "attributes", None)
        if attributes is None:
            return None
        value = attributes.get(CONVERSATION_ID_ATTRIBUTE)
        if not isinstance(value, str) or not value:
            return None
        return RunKey(key=value, source=CONVERSATION_SOURCE, is_inferred=False)
    except Exception:
        return None


def resolvers_with_conversation(
    base: Sequence[RunKeyResolver] = DEFAULT_RESOLVERS,
) -> tuple[RunKeyResolver, ...]:
    """The ladder with the conversation rung inserted below the trace rung.

    Below trace and above this seat's own wrapper, because a customer who set both meant
    the trace to be the finer of the two: a conversation spans a session and a trace spans
    one operation within it.

    Not the shipped default. A resolver that reads a span attribute the API does not
    promise should be opted into by a customer who knows their own instrumentation, rather
    than switched on for everyone by a library.
    """
    rungs = tuple(base)
    if not rungs:
        return (conversation_run_key,)
    return (rungs[0], conversation_run_key, *rungs[1:])


__all__ = [
    "CONVERSATION_ID_ATTRIBUTE",
    "CONVERSATION_SOURCE",
    "conversation_run_key",
    "resolvers_with_conversation",
]
