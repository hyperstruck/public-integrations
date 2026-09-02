"""The Microsoft Agent Framework seat: a thin shim over the shared core.

Agent Framework exposes a provider-agnostic ``AIContextProvider`` with ``invoking`` and
``invoked`` hooks, which is the same two halves this seat needs and is a first-class
pluggable extension point rather than a memory-specific bolt-on. Our LangGraph seat is the
same shape. A customer already invested in a framework's memory interface plugs us in
where they expect to.

**It is a shim, and that is the whole design.** Everything of consequence lives in
:class:`~hyperstruck.runtime.run.RunSeat`: the ledger, the receipt, the declaration
registry, the reinforce-versus-decline table. What is here is the translation between one
framework's vocabulary and the core's, and nothing else. The two shipped seats grew their
own copies of that loop and the differences turned out to be accidents rather than
decisions, which is the mistake this package exists not to repeat.

**Where it sits, and the honest cost of that.** A context provider runs *above* the
composition stack: it is handed the messages the agent assembled, not the params the model
was sent, so what it can observe is what the agent intended rather than what survived
trimming, summarisation and guardrails on the way down. It therefore records no receipt,
exactly as the LangGraph seat does not, and for the same stated reason: the only artefact
it could return is the block it built itself, and echoing that back asserts the very thing
a receipt exists to prove. A customer who wants credit attaches at the model layer as well,
which composes: the provider supplies the exact run boundary and the model seat supplies
the receipt.

There is no framework dependency here. The protocol is duck-typed against the two hook
names, so a vendored build, a version bump that adds a field, and a customer's own
subclass all work, and this package's one-runtime-dependency property holds.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from hyperstruck._wire import ToolSpec
from hyperstruck.runtime.run import HyperstruckRun, RunReport, RunSeat
from hyperstruck.runtime.run_key import RunKey

logger = logging.getLogger(__name__)

# The key prefix for a run the framework gave no thread id. Such a run cannot be looked up
# by thread on the way out, so ``invoked`` takes the oldest one instead: without a thread
# there is nothing to correlate on, and one invocation at a time is the only reading
# available. Prefixed rather than bare so a thread genuinely named this cannot collide.
_UNTHREADED = "hyperstruck-unthreaded:"

# What this seat reports itself as. Not "agent-framework" alone: the platform's host tuple
# is a claim about whether an acceptance record exists, and this seat has none to offer, so
# the name says which surface produced the episode without implying the receipt lane admits
# it.
SOURCE_FRAMEWORK = "agent-framework"

# The rung a provider-supplied boundary occupies. Exact, because the framework tells us
# where the run starts and ends rather than us inferring it from traffic shape.
PROVIDER_SOURCE = "context"


def _text_of(message: Any) -> str:
    """The plain text of one framework message, however it carries it.

    Duck-typed rather than matched against a class, because the framework's message type
    has changed shape across releases and a seat that names one of them stops working on
    the next. A shape this cannot read contributes nothing, which costs the run its goal
    and never its correctness.
    """
    text = getattr(message, "text", None)
    if isinstance(text, str) and text.strip():
        return text
    contents = getattr(message, "contents", None) or getattr(message, "content", None)
    if isinstance(contents, str):
        return contents
    if isinstance(contents, Iterable):
        parts = [
            part
            for item in contents
            if isinstance(part := getattr(item, "text", None), str) and part
        ]
        if parts:
            return "\n".join(parts)
    return ""


def _latest_user_goal(messages: Sequence[Any]) -> str:
    """The latest human turn, which is what a run with no declared goal is about.

    Read from the newest backwards. An agent's own scratch turns sit after the human's, and
    taking the first user message would key a long session on whatever started it rather
    than on what this invocation is for.
    """
    for message in reversed(list(messages)):
        role = getattr(message, "role", None)
        name = getattr(role, "value", role)
        if isinstance(name, str) and name.lower() in {"user", "human"}:
            text = _text_of(message).strip()
            if text:
                return text
    return ""


def _tool_specs(tools: Any) -> tuple[ToolSpec, ...]:
    """The roster the agent had, as the boundary expects it.

    The roster rather than the tools that ran: the server reads restraint from what was
    available and declined, so a roster derived from the calls would only ever hold tools
    that fired, and a run that deliberately held off would be indistinguishable from one
    with nothing to hold off from.
    """
    if not tools:
        return ()
    specs: list[ToolSpec] = []
    for tool in tools:
        name = getattr(tool, "name", None)
        if not isinstance(name, str) or not name:
            continue
        parameters = getattr(tool, "input_schema", None) or getattr(
            tool, "parameters", None
        )
        specs.append(
            ToolSpec(
                name=name,
                description=str(getattr(tool, "description", "") or ""),
                parameters=parameters if isinstance(parameters, dict) else None,
            )
        )
    return tuple(specs)


def _function_calls(messages: Sequence[Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Tool calls the agent planned, as ``(id, name, args)`` triples."""
    calls: list[tuple[str, str, dict[str, Any]]] = []
    for message in messages:
        contents = getattr(message, "contents", None) or ()
        if isinstance(contents, str):
            continue
        for item in contents:
            call_id = getattr(item, "call_id", None)
            name = getattr(item, "name", None)
            if not isinstance(call_id, str) or not isinstance(name, str):
                continue
            arguments = getattr(item, "arguments", None)
            calls.append((call_id, name, arguments if isinstance(arguments, dict) else {}))
    return calls


def _function_results(messages: Sequence[Any]) -> list[tuple[str, Any, bool]]:
    """Tool outcomes, as ``(call_id, result, is_error)`` triples."""
    results: list[tuple[str, Any, bool]] = []
    for message in messages:
        contents = getattr(message, "contents", None) or ()
        if isinstance(contents, str):
            continue
        for item in contents:
            call_id = getattr(item, "call_id", None)
            if not isinstance(call_id, str):
                continue
            if not hasattr(item, "result") and not hasattr(item, "exception"):
                continue
            exception = getattr(item, "exception", None)
            results.append((call_id, getattr(item, "result", None), exception is not None))
    return results


class HyperstruckContextProvider:
    """An ``AIContextProvider`` over the shared run seat.

    Constructed with a seat and dropped into an agent's ``context_providers``. The
    framework calls :meth:`invoking` before each run and :meth:`invoked` after it, which
    is the exact boundary the run-key ladder's inference rung has to guess at, so this
    attachment point keys and closes runs precisely.

    ``thread_id`` is read from the framework's own thread when it offers one, so a
    multi-turn session is one thread server-side rather than a series of unrelated runs.
    """

    def __init__(
        self,
        seat: RunSeat,
        *,
        on_report: Callable[[RunReport], None] | None = None,
    ) -> None:
        self._seat = seat
        self._seat.declare_host(SOURCE_FRAMEWORK)
        self._on_report = on_report
        # Keyed by the framework's own thread where it names one, so two threads served by
        # one provider instance never share a run. Falls back to a per-invocation key, which
        # loses cross-turn correlation and never correctness.
        self._runs: dict[str, HyperstruckRun] = {}

    async def invoking(
        self,
        messages: Any = (),
        *,
        thread_id: str | None = None,
        tools: Any = None,
        **_: Any,
    ) -> Any:
        """Open the run and return the recalled context for this invocation.

        The return value is deliberately a plain object carrying ``instructions`` rather
        than the framework's own ``Context`` type: constructing theirs would make this
        package depend on the framework, which is the thing the shim exists to avoid. The
        framework reads the attribute, so a duck-typed carrier is what it needs.
        """
        key = thread_id or f"{_UNTHREADED}{uuid.uuid4().hex}"
        run = self._seat.open(
            _latest_user_goal(messages if isinstance(messages, Sequence) else []),
            _tool_specs(tools),
            thread_id=thread_id,
            run_key=RunKey(key=key, source=PROVIDER_SOURCE, is_inferred=False),
        )
        self._runs[key] = run
        block = await self._seat.before_model_call(run)
        # Recorded as injected here and nowhere else. The provider hands the block to the
        # agent, which is the last point this seat can observe, and it is deliberately not
        # the same claim the model seat makes: what the agent was given is not what the
        # model was sent, and only the model seat can tell them apart.
        if block:
            run.ledger.is_injected = True
        return _RecalledContext(instructions=block)

    def _pop_unthreaded(self) -> HyperstruckRun | None:
        """The oldest run opened without a thread id, or ``None``."""
        for key in list(self._runs):
            if key.startswith(_UNTHREADED):
                return self._runs.pop(key)
        return None

    async def invoked(
        self,
        request_messages: Any = (),
        response_messages: Any = (),
        *,
        thread_id: str | None = None,
        invoke_exception: BaseException | None = None,
        **_: Any,
    ) -> None:
        """Record what the invocation did, then close the run.

        Always closes. A run left neither reinforced nor declined is indistinguishable from
        a host that stopped writing back, and it sits open holding its resolve reservation
        until the server's reclaim sweep notices.
        """
        # Popped by the key ``invoking`` actually stored under. A run opened without a
        # thread id was keyed on a minted identifier and looked up here under "", so it was
        # never found, never closed and never credited: it sat open holding its resolve
        # reservation until the server's reclaim sweep noticed.
        run = self._runs.pop(thread_id, None) if thread_id else self._pop_unthreaded()
        if run is None:
            # Every open run is registered under its key, so this means either two
            # ``invoked`` calls for one invocation or an ``invoked`` with no ``invoking``.
            # Both are the framework's ordering, not ours, and neither is worth taking the
            # host's run down for.
            logger.debug("Hyperstruck: invoked with no open run for thread %r", thread_id)
            return
        try:
            messages = [
                *(request_messages if isinstance(request_messages, Sequence) else []),
                *(response_messages if isinstance(response_messages, Sequence) else []),
            ]
            self._seat.record_planned_calls(run, _function_calls(messages))
            for call_id, result, is_error in _function_results(messages):
                self._seat.record_step(
                    run,
                    call_id,
                    "",
                    result=None if is_error else result,
                    error=str(result) if is_error else None,
                )
        except Exception as exc:  # noqa: BLE001 - never break the host's invocation
            logger.warning("Hyperstruck: could not read the invocation's steps: %s", exc)
        report = await self._seat.close(run, is_success=invoke_exception is None)
        if self._on_report is not None:
            try:
                self._on_report(report)
            except Exception as exc:  # noqa: BLE001 - a customer callback is not our loop
                logger.warning("Hyperstruck: run report callback raised: %s", exc)

    # The framework's provider protocol also names a thread-lifecycle hook. Nothing is owed
    # to it here: this seat's state is per invocation and is dropped on close, so there is
    # no per-thread resource for it to release.
    async def thread_created(self, thread_id: str | None = None) -> None:  # noqa: ARG002
        return None


class _RecalledContext:
    """What the provider hands back: instructions to prepend, and nothing else.

    A plain carrier rather than the framework's ``Context``, so this module imports nothing
    from it. The framework reads ``instructions``; anything it does not read costs nothing
    to omit and would cost a dependency to supply.
    """

    __slots__ = ("instructions",)

    def __init__(self, instructions: str | None) -> None:
        self.instructions = instructions


__all__ = [
    "HyperstruckContextProvider",
    "PROVIDER_SOURCE",
    "SOURCE_FRAMEWORK",
]
