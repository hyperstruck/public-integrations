"""The documented default attachment point: a wrapped model client.

This is the load-bearing decision of the whole seat. Attaching at the model layer means
running below every other middleware the customer composed, after trimming, after
summarisation, after guardrails. What this sees is the prompt as it actually goes on the
wire, and two problems the LangGraph seat documents as unavoidable dissolve because of it.

The ordering hazard that seat guards with a runtime ``assert_innermost`` becomes structural:
there is no layer below to be wrong about. And, commercially, an honest receipt becomes
possible. The LangGraph README is explicit that the only artefact that seat could return is
the block it built itself, and echoing that back asserts the very thing a receipt exists to
prove, so it sends none and earns no credit. A seat here returns an artefact it did not
author.

**No SDK is a dependency.** The wrappers are duck-typed against the two call shapes rather
than typed against ``anthropic`` and ``openai``, because this package ships exactly one
runtime dependency and adding two model SDKs to a thin client's install path to wrap two
method signatures would be a poor trade. It also means a customer's vendored, proxied or
gateway-fronted client wraps exactly as well as the vanilla one, which is the common shape
in a real deployment.

**What a model-layer seat can and cannot see.** It never sees a tool run. It sees the model
plan a call, and then sees the result of that call only when the customer's loop feeds it
back in the *next* request. So outcomes are harvested from the outgoing messages rather than
observed directly, which is exact for any loop that returns results to the model, and blind
to a tool whose result the customer never shows it. A tool call with no result fed back is
dropped from the episode by the ledger's join, which is the right answer: a call we cannot
see the outcome of is not evidence about anything.

**Async only, and it says so.** The seat's prefetch and write-back are coroutines, and
driving them from a synchronous ``create()`` would mean owning a background event loop
inside a customer's process. Wrapping a synchronous client raises at wrap time naming the
async class to use, rather than wrapping successfully and silently capturing nothing.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from hyperstruck._wire import ToolSpec
from hyperstruck.runtime.receipt import flatten_params
from hyperstruck.runtime.run import HyperstruckRun, RunSeat

logger = logging.getLogger(__name__)

# What the two SDKs call their creation method, and the attribute path to reach it.
_ANTHROPIC_PATH = ("messages", "create")
# The streaming entry points, wrapped alongside the buffered ones. Injection is identical
# (it happens before the call either way); what differs is capture, because the response
# arrives as events rather than as an object. See ``_StreamingProxy``.
_ANTHROPIC_STREAM_PATH = ("messages", "stream")
_OPENAI_STREAM_PATH = ("chat", "completions", "create")
_OPENAI_PATH = ("chat", "completions", "create")


class WrappedModelClient:
    """A model client with the learning loop attached, proxying everything else through.

    Attribute access falls through to the wrapped client, so this is a drop-in replacement
    rather than a facade a customer has to learn. Only the creation method is intercepted.
    """

    def __init__(self, client: Any, seat: RunSeat, adapter: _Adapter) -> None:
        self._hyperstruck_client = client
        self._hyperstruck_seat = seat
        self._hyperstruck_adapter = adapter

    def __getattr__(self, name: str) -> Any:
        return getattr(self._hyperstruck_client, name)

    @property
    def seat(self) -> RunSeat:
        """The seat, for a customer who wants the run handle or the registry."""
        return self._hyperstruck_seat


class _Adapter:
    """One SDK's shape: where the block goes in, and where the plan comes out."""

    name = "adapter"

    def inject(self, kwargs: dict[str, Any], block: str) -> dict[str, Any]:
        raise NotImplementedError

    def planned_calls(self, response: Any) -> list[tuple[str, str, Mapping[str, Any]]]:
        raise NotImplementedError

    def tool_results(self, kwargs: Mapping[str, Any]) -> list[tuple[str, Any, bool]]:
        raise NotImplementedError

    def latest_human_goal(self, kwargs: Mapping[str, Any]) -> str:
        raise NotImplementedError

    def is_continuation(self, kwargs: Mapping[str, Any]) -> bool:
        """Whether this call shows a conversation already under way.

        The signal the inference rung needs, and the only one available at this layer: a
        message list carrying a prior assistant turn or tool results is a continuation of an
        episode, and one carrying neither is its start. Exactly what the spec describes,
        read from the messages rather than guessed at.
        """
        return _is_continuation(_sequence(kwargs.get("messages")))

    def is_final_answer(self, response: Any) -> bool:
        """Whether the model answered rather than asking for another tool call.

        This is the only terminal signal a model-layer seat gets. There is no end hook, so
        a run inferred from activity is closed when the loop stops asking for tools. A
        customer who wants an exact boundary uses the explicit run handle, which is what it
        is for.
        """
        return not self.planned_calls(response)


class _AnthropicAdapter(_Adapter):
    name = "anthropic-sdk"

    def inject(self, kwargs: dict[str, Any], block: str) -> dict[str, Any]:
        """Prepend the block to ``system``, in whichever of its two shapes is in use.

        The system prompt rather than a synthetic first user message, because a user turn
        the customer did not write changes what their own loop sees when it inspects its
        messages, and this seat must be invisible to everything except the model.
        """
        system = kwargs.get("system")
        if system is None or system == "":
            kwargs["system"] = block
        elif isinstance(system, str):
            kwargs["system"] = f"{block}\n\n{system}"
        elif isinstance(system, list):
            kwargs["system"] = [{"type": "text", "text": block}, *system]
        else:
            # An unrecognised shape is left alone. Injecting into something we cannot read
            # risks corrupting the customer's prompt, and no recall is better than that.
            logger.warning(
                "Hyperstruck: unrecognised `system` shape (%s); skipping injection",
                type(system).__name__,
            )
        return kwargs

    def planned_calls(self, response: Any) -> list[tuple[str, str, Mapping[str, Any]]]:
        calls = []
        for block in _sequence(_get(response, "content")):
            if _get(block, "type") == "tool_use":
                calls.append(
                    (
                        str(_get(block, "id") or ""),
                        str(_get(block, "name") or ""),
                        _mapping(_get(block, "input")),
                    )
                )
        return [call for call in calls if call[0]]

    def tool_results(self, kwargs: Mapping[str, Any]) -> list[tuple[str, Any, bool]]:
        results = []
        for message in _sequence(kwargs.get("messages")):
            for block in _sequence(_get(message, "content")):
                if _get(block, "type") != "tool_result":
                    continue
                results.append(
                    (
                        str(_get(block, "tool_use_id") or ""),
                        _get(block, "content"),
                        bool(_get(block, "is_error")),
                    )
                )
        return [result for result in results if result[0]]

    def latest_human_goal(self, kwargs: Mapping[str, Any]) -> str:
        return _latest_user_text(_sequence(kwargs.get("messages")))


class _OpenAIAdapter(_Adapter):
    name = "openai-sdk"

    def inject(self, kwargs: dict[str, Any], block: str) -> dict[str, Any]:
        """Prepend a system message, after any the customer already placed first.

        After rather than before, because a customer's own system message is their
        instruction to the model and demoting it below ours would change their behaviour to
        get our block a better position.
        """
        messages = list(_sequence(kwargs.get("messages")))
        index = 0
        while index < len(messages) and _get(messages[index], "role") in {
            "system",
            "developer",
        }:
            index += 1
        messages.insert(index, {"role": "system", "content": block})
        kwargs["messages"] = messages
        return kwargs

    def planned_calls(self, response: Any) -> list[tuple[str, str, Mapping[str, Any]]]:
        calls = []
        for choice in _sequence(_get(response, "choices")):
            message = _get(choice, "message")
            for call in _sequence(_get(message, "tool_calls")):
                function = _get(call, "function")
                calls.append(
                    (
                        str(_get(call, "id") or ""),
                        str(_get(function, "name") or ""),
                        _json_arguments(_get(function, "arguments")),
                    )
                )
        return [call for call in calls if call[0]]

    def tool_results(self, kwargs: Mapping[str, Any]) -> list[tuple[str, Any, bool]]:
        results = []
        for message in _sequence(kwargs.get("messages")):
            if _get(message, "role") != "tool":
                continue
            call_id = str(_get(message, "tool_call_id") or "")
            if call_id:
                # The chat-completions tool message has no error channel, so a failure is
                # whatever the customer's own loop chose to put in the content. Reporting
                # every result as completed is the honest reading: we did not observe a
                # failure, and inferring one from the text would be guessing.
                results.append((call_id, _get(message, "content"), False))
        return results

    def latest_human_goal(self, kwargs: Mapping[str, Any]) -> str:
        return _latest_user_text(_sequence(kwargs.get("messages")))


def wrap_anthropic(client: Any, seat: RunSeat) -> WrappedModelClient:
    """Attach the learning loop to an ``AsyncAnthropic`` client.

    **This mutates the client you pass.** The seat is installed on the client's own
    ``messages.create`` and ``messages.stream``, so every existing reference to that client
    is wrapped too, and the returned object is a convenience rather than the thing that
    carries the loop. That is deliberate: a customer who wraps in one module and calls
    through a reference held in another would otherwise get silence, which is the failure
    mode this whole seat exists to end. Wrapping the same client twice is a no-op rather
    than a nested seat.

    Both the buffered ``messages.create`` and the streaming ``messages.stream`` are
    wrapped. A seat that covered only the buffered call captured nothing at all for a
    customer who streams, which is the common shape for anything with a user watching, and
    it did so silently: their corpus simply never filled.
    """
    wrapped = _wrap(client, seat, _AnthropicAdapter(), _ANTHROPIC_PATH, "AsyncAnthropic")
    _wrap_stream(client, seat, _AnthropicAdapter(), _ANTHROPIC_STREAM_PATH)
    return wrapped


def wrap_openai(client: Any, seat: RunSeat) -> WrappedModelClient:
    """Attach the learning loop to an ``AsyncOpenAI`` client.

    OpenAI streams through the same ``create`` with ``stream=True`` rather than a separate
    method, so the one wrapper covers both and dispatches on what the call returns.
    """
    return _wrap(client, seat, _OpenAIAdapter(), _OPENAI_PATH, "AsyncOpenAI")


_WRAPPED_MARKER = "_hyperstruck_seat"


def _wrap(
    client: Any,
    seat: RunSeat,
    adapter: _Adapter,
    path: tuple[str, ...],
    async_class_name: str,
) -> WrappedModelClient:
    owner = client
    for attribute in path[:-1]:
        owner = getattr(owner, attribute, None)
        if owner is None:
            raise TypeError(
                f"this does not look like a {async_class_name}: it has no "
                f"`{'.'.join(path[:-1])}` to wrap"
            )
    original = getattr(owner, path[-1], None)
    if original is None:
        raise TypeError(
            f"this does not look like a {async_class_name}: `{'.'.join(path)}` is missing"
        )
    if not _is_coroutine_callable(original):
        raise TypeError(
            f"Hyperstruck wraps the async client only: `{'.'.join(path)}` is synchronous. "
            f"Use {async_class_name}. Wrapping the synchronous client would capture "
            "nothing while appearing to work, because the seat's prefetch and write-back "
            "are coroutines and there is no loop here to run them on."
        )

    if getattr(original, _WRAPPED_MARKER, None) is seat:
        # Wrapping the same client twice is a caller mistake, not a reason to nest a second
        # seat inside the first: nested, every model call would open two runs, inject twice
        # and write two episodes for one turn.
        return WrappedModelClient(client, seat, adapter)

    async def create(*args: Any, **kwargs: Any) -> Any:
        return await _run_call(seat, adapter, original, args, kwargs)

    setattr(create, _WRAPPED_MARKER, seat)
    seat.declare_host(adapter.name)
    setattr(owner, path[-1], create)
    return WrappedModelClient(client, seat, adapter)


def _wrap_stream(
    client: Any, seat: RunSeat, adapter: _Adapter, path: tuple[str, ...]
) -> None:
    """Wrap a streaming entry point, if this client has one.

    Absent quietly rather than raising: a vendored or gateway-fronted client may expose
    only the buffered call, and refusing to wrap it at all because it lacks a streaming
    method would cost that customer the whole seat over a method they never use.
    """
    owner = client
    for attribute in path[:-1]:
        owner = getattr(owner, attribute, None)
        if owner is None:
            return
    original = getattr(owner, path[-1], None)
    if original is None or getattr(original, _WRAPPED_MARKER, None) is seat:
        return

    def stream(*args: Any, **kwargs: Any) -> Any:
        return _StreamingProxy(seat, adapter, original, args, kwargs)

    setattr(stream, _WRAPPED_MARKER, seat)
    setattr(owner, path[-1], stream)


class _StreamingProxy:
    """The seat around a streaming call, without buffering the customer's stream.

    ``messages.stream`` returns an async context manager rather than a coroutine, so the
    seat cannot simply await it. This stands in its place: it opens the run and injects on
    entry, hands the customer the SDK's own stream object untouched, and captures on exit
    from the final message the SDK has already accumulated.

    Nothing is copied or held: the events the customer iterates are the SDK's, in their
    order, at their pace. A seat that buffered a stream to inspect it would change the one
    property a customer chose streaming for.
    """

    def __init__(
        self,
        seat: RunSeat,
        adapter: _Adapter,
        original: Any,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        self._seat = seat
        self._adapter = adapter
        self._original = original
        self._args = args
        self._kwargs = dict(kwargs)
        self._run: HyperstruckRun | None = None
        self._manager: Any = None

    async def __aenter__(self) -> Any:
        try:
            self._run = self._seat.for_call(
                self._adapter.latest_human_goal(self._kwargs),
                tools=_tools_from(self._kwargs),
                is_continuation=self._adapter.is_continuation(self._kwargs),
            )
            _record_results(self._seat, self._run, self._adapter, self._kwargs)
            block = await self._seat.before_model_call(self._run)
            if block:
                self._kwargs = self._adapter.inject(self._kwargs, block)
        except Exception as exc:  # noqa: BLE001 - never break the host's stream
            logger.warning("Hyperstruck: pre-stream capture failed, streaming on: %s", exc)
            self._run = None
        self._manager = self._original(*self._args, **self._kwargs)
        return await self._manager.__aenter__()

    async def __aexit__(self, *exc_info: Any) -> Any:
        result = await self._manager.__aexit__(*exc_info)
        run = self._run
        if run is None or exc_info[0] is not None:
            return result
        try:
            # Located against the params as sent, exactly as the buffered path does.
            self._seat.record_model_call(run)
            self._seat.after_model_call(run, flatten_params(self._kwargs))
            # The SDK accumulates the final message as the stream drains, so by the time
            # the block exits it holds the same object the buffered call would have
            # returned. Read rather than reconstructed: reassembling deltas ourselves would
            # be a second implementation of the SDK's own accumulator.
            final = getattr(self._manager, "get_final_message", None)
            response = await final() if final is not None else None
            if response is not None:
                planned = self._adapter.planned_calls(response)
                if planned:
                    self._seat.record_planned_calls(run, planned)
                elif self._adapter.is_final_answer(response):
                    self._seat.mark_closable(run)
        except Exception as exc:  # noqa: BLE001 - the stream is the customer's, not ours
            logger.warning("Hyperstruck: post-stream capture failed: %s", exc)
        return result

    def __getattr__(self, name: str) -> Any:
        # Anything else the customer reaches for on the stream object passes through, so
        # this is a seat rather than a facade.
        return getattr(self._manager, name)


async def _run_call(
    seat: RunSeat,
    adapter: _Adapter,
    original: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """One model call, with the loop around it and a guard around the loop.

    Every Hyperstruck step here is inside a guard that falls back to calling straight
    through. A learning client that can break a customer's model call is a learning client
    they remove, and there is no recall worth that.
    """
    run: HyperstruckRun | None = None
    try:
        run = seat.for_call(
            adapter.latest_human_goal(kwargs),
            tools=_tools_from(kwargs),
            is_continuation=adapter.is_continuation(kwargs),
        )
        _record_results(seat, run, adapter, kwargs)
        block = await seat.before_model_call(run)
        if block:
            kwargs = adapter.inject(dict(kwargs), block)
    except Exception as exc:  # noqa: BLE001 - never break the host's model call
        logger.warning("Hyperstruck: pre-call capture failed, calling through: %s", exc)
        run = None

    response = await original(*args, **kwargs)

    if run is None:
        return response
    try:
        # Located against the params as sent, which now includes whatever the customer's
        # own middleware did to them on the way here.
        seat.record_model_call(run)
        seat.after_model_call(run, flatten_params(kwargs))
        planned = adapter.planned_calls(response)
        if planned:
            seat.record_planned_calls(run, planned)
        elif adapter.is_final_answer(response):
            # Marked, not closed. A model answering without asking for another tool is the
            # only terminal signal this layer gets, and it is an ambiguous one: a customer's
            # loop that answers, takes a follow-up and answers again is one episode, and
            # closing on the first answer would split it into two runs, the second of which
            # would have carried the follow-up's steps into a fresh recall. The grace window
            # is what tells the two apart, and a further call under the same key cancels it.
            seat.mark_closable(run)
    except Exception as exc:  # noqa: BLE001 - the response is the customer's, not ours
        logger.warning("Hyperstruck: post-call capture failed for this call: %s", exc)
    return response


def _record_results(
    seat: RunSeat, run: HyperstruckRun, adapter: _Adapter, kwargs: Mapping[str, Any]
) -> None:
    """Harvest tool outcomes the customer's loop fed back into this request.

    Recorded by id, so a result arriving in the third request for a call planned in the
    first still joins its plan. A duplicate is harmless: the ledger keys outcomes by id and
    the later write wins, which is what a customer's own retry should produce.
    """
    for call_id, result, is_error in adapter.tool_results(kwargs):
        planned = run.ledger.planned.get(call_id)
        if planned is None:
            continue
        seat.record_step(
            run,
            call_id,
            planned.name,
            result=None if is_error else result,
            error=str(result) if is_error else None,
        )


def _tools_from(kwargs: Mapping[str, Any]) -> tuple[ToolSpec, ...]:
    """The roster the agent had, projected onto the shape resolve expects.

    ``category`` is never inferred. The server treats an unrecognised value as declaring
    nothing, so a guess would be indistinguishable from silence while looking like a
    declaration, and without a declared side-effectful category the server cannot tell a run
    that deliberately held off from one that had nothing to hold off from.
    """
    specs = []
    for tool in _sequence(kwargs.get("tools")):
        # Anthropic puts the schema at the top level; OpenAI nests it under `function`.
        function = _get(tool, "function")
        source = function if function is not None else tool
        name = _get(source, "name")
        if not name:
            continue
        specs.append(
            ToolSpec(
                name=str(name),
                description=str(_get(source, "description") or ""),
                category=_optional_str(_get(source, "category")),
                parameters=_mapping_or_none(
                    _get(source, "input_schema") or _get(source, "parameters")
                ),
            )
        )
    return tuple(specs)


# -- shape readers -------------------------------------------------------------
#
# Both SDKs return pydantic models and accept plain dicts, and a customer's gateway may
# hand back either. Everything below reads a mapping key or an attribute and never assumes
# which, so a vendored client works exactly as well as the vanilla one.


def _get(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _sequence(value: Any) -> Sequence[Any]:
    if value is None or isinstance(value, (str, bytes, Mapping)):
        return ()
    if isinstance(value, Sequence):
        return value
    return ()


def _mapping(value: Any) -> Mapping[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_or_none(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) and value else None


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _json_arguments(value: Any) -> Mapping[str, Any]:
    """OpenAI sends tool arguments as a JSON string, and a model can emit invalid JSON.

    An unparseable argument blob yields an empty mapping rather than raising: the step
    still happened and is still worth recording, and taking the customer's model call down
    over a malformed argument would be absurd.
    """
    if isinstance(value, Mapping):
        return dict(value)
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_continuation(messages: Sequence[Any]) -> bool:
    """A prior assistant turn, or a tool result fed back, means the episode is under way."""
    for message in messages:
        role = _get(message, "role")
        if role == "assistant":
            return True
        # Anthropic returns tool results inside a user turn, so the role alone is not the
        # signal; the content block type is.
        for part in _sequence(_get(message, "content")):
            if _get(part, "type") in {"tool_result", "tool"}:
                return True
        if _get(message, "tool_call_id") is not None:
            return True
    return False


def _latest_user_text(messages: Sequence[Any]) -> str:
    """The latest user message: the ask that started this stretch of the loop.

    This is the inference rung of the run-key ladder and it is last for good reason. It is
    what the LangGraph seat's ``_latest_human_goal`` already does, and it breaks concretely
    on branching, on concurrent conversations sharing one client, and on any agent that
    does not carry a conventional message list. The report always says the goal was
    inferred.
    """
    for message in reversed(list(messages)):
        if _get(message, "role") != "user":
            continue
        content = _get(message, "content")
        if isinstance(content, str):
            return content
        for block in _sequence(content):
            if _get(block, "type") == "text":
                text = _get(block, "text")
                if isinstance(text, str) and text:
                    return text
    return ""


def _is_coroutine_callable(value: Any) -> bool:
    import inspect

    if inspect.iscoroutinefunction(value):
        return True
    call = getattr(value, "__call__", None)  # noqa: B004 - a callable object, not a type
    return call is not None and inspect.iscoroutinefunction(call)
