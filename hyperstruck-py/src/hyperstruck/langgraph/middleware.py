"""LangGraph learning middleware: a thin client of Hyperstruck's learning boundary.

This middleware turns a vanilla ``langchain.agents.create_agent`` graph into a
full client of Hyperstruck learning. Installing and registering it is the whole
integration: no customer-written episode-assembly or injection code, no engine
import, no local stores. The learning logic runs on the platform.

Each ``invoke()`` runs the loop:

* **Resolve** (read path): at run start the middleware prefetches the learnings
  bound to the run's goal, deadline-bounded and fail-open, and injects the
  server-rendered block into every model call.
* **Link** (attribution): the model's planned tool calls and each tool's outcome
  carry the same id, so the recorder joins decision to outcome by tool-call id.
* **Observe and reinforce** (write path): at invoke end the middleware ships the
  run as an episode (``observe``) and credits the learnings it used
  (``reinforce``), both asynchronously so the host's ``invoke()`` is never
  blocked. The platform extracts, derives eligibility, and attributes server-side.

Because the write path is non-blocking, the background deliveries outlive the
``invoke()`` that scheduled them. In a long-lived server the event loop keeps
running and they complete on their own. In a short-lived process (a script, a
one-shot task, a serverless handler) the process can exit before they land, so
the host must drain them: ``await middleware.aclose()`` (or use the middleware as
an ``async with`` context). The quickstart shows the pattern.

Design notes mirror the boundary's contract: identity is mandatory at
registration with a per-invoke override; learning-pipeline failures never break
the host run; a run that terminates abnormally is never observed (an incomplete
run has no terminal outcome and learning from a half-run risks mistraining).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_config
from typing_extensions import NotRequired, TypedDict

from hyperstruck._wire import DEFAULT_MAX_LEARNINGS, ToolSpec
from hyperstruck.client import LearningClient
from hyperstruck.identity import AgentIdentity
from hyperstruck.langgraph.ledger import LEDGERS, RUN_ID_STATE_KEY, InvokeLedger

logger = logging.getLogger(__name__)

# Reserved ``RunnableConfig.configurable`` key for a per-invoke identity override.
IDENTITY_CONFIG_KEY = "hyperstruck_identity"

# Source-framework provenance stamped onto every episode this adapter produces.
SOURCE_FRAMEWORK = "langgraph"


class LearningLoopState(TypedDict, total=False):
    """The middleware's state contribution: just the per-invoke run id."""

    # Must equal RUN_ID_STATE_KEY ("hyperstruck_run_id"); a TypedDict key must be a
    # literal, so the two cannot share the constant and are kept in sync by hand.
    hyperstruck_run_id: NotRequired[str]


@dataclass
class MiddlewareStats:
    """Runtime counters the middleware exposes for visibility.

    ``runs_incomplete`` (runs started but not observed, minus those still in
    flight) surfaces cancelled or killed streams: LangGraph fires no end hook on
    cancellation, so such a run is correctly never observed, and the gap between
    ``runs_started`` and ``runs_observed`` makes the skip visible.

    ``runs_observed`` counts runs whose observe and reinforce were *scheduled*
    without error at invoke end, not deliveries confirmed by the platform. The
    actual delivery outcome lives on the client (``writes_delivered`` /
    ``writes_failed``, surfaced on the middleware), since the writes complete in
    the background after the run returns.
    """

    tool_calls: int = 0
    learnings_injected: int = 0
    runs_started: int = 0
    runs_observed: int = 0
    errors: int = 0

    def runs_incomplete(self, live: int = 0) -> int:
        return max(0, self.runs_started - self.runs_observed - live)


class HyperstruckLearningMiddleware(AgentMiddleware):
    """LangChain ``AgentMiddleware`` running Hyperstruck's learning loop on a graph.

    Construct with an API key and an ``agent_id`` (the whole configuration for a
    single agent), or pass a custom :class:`LearningClient` to point at a
    different backend. To serve many tenants from one registered middleware, set
    ``"hyperstruck_identity"`` in each invoke's config.
    """

    state_schema = LearningLoopState

    def __init__(
        self,
        *,
        api_key: str | None = None,
        agent_id: str | None = None,
        org_id: str | None = None,
        identity: AgentIdentity | None = None,
        client: LearningClient | None = None,
        base_url: str | None = None,
        goal_extractor: Callable[[list[BaseMessage]], str] | None = None,
        tool_sensitivity: Mapping[str, Mapping[str, str]] | None = None,
        tools: Any = None,
        max_injected_learnings: int = DEFAULT_MAX_LEARNINGS,
    ) -> None:
        super().__init__()
        resolved_identity = identity or (AgentIdentity(agent_id=agent_id, org_id=org_id) if agent_id else None)
        if resolved_identity is None:
            raise ValueError(
                "HyperstruckLearningMiddleware requires an identity: pass agent_id=... "
                "(and optionally org_id), or an AgentIdentity"
            )
        self._identity = resolved_identity
        if client is None:
            # Imported lazily so the package imports without httpx side effects in
            # exotic environments, and so a custom client needs no hosted deps.
            from hyperstruck.client import HostedLearningClient

            client = HostedLearningClient(api_key=api_key, base_url=base_url)
        self._client = client
        self._goal_extractor = goal_extractor or _latest_human_goal
        self._tool_sensitivity: dict[str, Mapping[str, str]] = dict(tool_sensitivity or {})
        self._tools = _tool_specs(tools)
        self._max_injected = max_injected_learnings
        self.stats = MiddlewareStats()

    # -- hooks -------------------------------------------------------------

    async def abefore_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Open the per-invoke ledger, stamp its run id, and prefetch resolve.

        The run id is a fresh UUID namespaced by ``agent_id``, minted once per
        invoke and stable for it. Resolve is fired here so its round-trip overlaps
        graph setup and is usually done by the first model call.
        """
        identity = self._invoke_identity()
        run_id = f"{identity.agent_id}:{uuid.uuid4().hex}"
        ledger = InvokeLedger(
            run_id=run_id,
            agent_id=identity.agent_id,
            org_id=identity.org_id,
            goal=self._goal_extractor(self._messages(state)),
            thread_id=self._thread_id(),
        )
        LEDGERS.register(ledger)
        self.stats.runs_started += 1
        ledger.resolve_task = asyncio.ensure_future(self._prefetch_resolve(identity, ledger))
        return {RUN_ID_STATE_KEY: run_id}

    async def awrap_model_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        """Inject the bound learnings into every model call.

        Awaits the prefetched resolve at the first model call (bounded by the
        client's deadline, fail-open), then reuses the rendered block on every
        later call so a multi-step loop keeps the learnings in view.
        """
        ledger = LEDGERS.get(self._run_id(request.state))
        if ledger is None:
            return await handler(request)
        if not ledger.is_resolved and ledger.resolve_task is not None:
            try:
                await ledger.resolve_task
            except Exception:  # noqa: BLE001 - fail open, already counted in the task
                pass
        if ledger.injected_text:
            request = request.override(messages=[SystemMessage(content=ledger.injected_text), *request.messages])
        return await handler(request)

    async def aafter_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Capture the model's planned tool calls (by id) as pending decisions."""
        ledger = LEDGERS.get(self._run_id(state))
        if ledger is None:
            return None
        messages = self._messages(state)
        if messages and isinstance(messages[-1], AIMessage):
            ledger.record_planned_tool_calls(messages[-1])
        return None

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        """Run the tool, then join its outcome onto the planned call by id."""
        ledger = LEDGERS.get(self._run_id(request.state))
        result = await handler(request)
        self.stats.tool_calls += 1
        if ledger is not None:
            call = request.tool_call
            ledger.record_tool_outcome(_tool_call_field(call, "id"), _tool_call_field(call, "name"), result)
        return result

    async def aafter_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:  # noqa: ARG002
        """Invoke end: ship the run and reinforce the learnings it used.

        Reached only on normal completion; an abnormally terminated run never gets
        here, so its ledger is discarded with no observe/reinforce (the registry
        self-evicts it, and the runs_incomplete counter surfaces the skip). Writes
        are scheduled non-blocking, so this returns immediately. Guarded so a
        learning-pipeline failure never propagates into the host run.
        """
        ledger = LEDGERS.pop(self._run_id(state))
        if ledger is None:
            return None
        try:
            identity = self._invoke_identity()
            episode = ledger.build_episode(source_framework=SOURCE_FRAMEWORK, tool_sensitivity=self._tool_sensitivity)
            await self._client.observe(identity=identity, episode=episode)
            await self._client.reinforce(
                identity=identity,
                episode=episode,
                is_org_promotion_allowed=ledger.is_fully_declared(self._tool_sensitivity),
            )
            self.stats.runs_observed += 1
        except Exception as exc:  # noqa: BLE001 - never break the host run
            logger.warning("HyperstruckLearningMiddleware: learning capture failed for run %s: %s", ledger.run_id, exc, exc_info=True)
            self.stats.errors += 1
        return None

    # -- lifecycle ---------------------------------------------------------

    @property
    def writes_delivered(self) -> int | None:
        """Background writes the client confirmed delivered, if it tracks them."""
        return getattr(self._client, "writes_delivered", None)

    @property
    def writes_failed(self) -> int | None:
        """Background writes the client dropped after retries, if it tracks them."""
        return getattr(self._client, "writes_failed", None)

    async def drain(self, timeout: float = 30.0) -> None:
        """Await all in-flight background writes.

        Call before a short-lived process exits, or its scheduled observe and
        reinforce writes are cancelled at loop teardown and never reach the
        platform. A long-lived server need not call this; the writes complete as
        its loop keeps running.
        """
        drain = getattr(self._client, "drain", None)
        if drain is not None:
            await drain(timeout=timeout)

    async def aclose(self) -> None:
        """Drain in-flight writes and release the client's resources."""
        aclose = getattr(self._client, "aclose", None)
        if aclose is not None:
            await aclose()
            return
        await self.drain()

    async def __aenter__(self) -> HyperstruckLearningMiddleware:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # -- internals ---------------------------------------------------------

    async def _prefetch_resolve(self, identity: AgentIdentity, ledger: InvokeLedger) -> None:
        """Resolve the goal's learnings once and cache the rendered injection.

        Marks the ledger resolved either way, so a resolve failure does not block
        or re-trigger retrieval. Tools are not bound on the graph at run start, so
        tool-aware retrieval uses the tool specs passed at registration (if any);
        otherwise resolve runs goal-primary.
        """
        try:
            context = await self._client.resolve(
                identity=identity,
                run_id=ledger.run_id,
                goal=ledger.goal,
                available_tools=self._tools,
                max_learnings=self._max_injected,
            )
        except Exception as exc:  # noqa: BLE001 - fail open, never break the run
            logger.warning("HyperstruckLearningMiddleware: resolve failed for run %s: %s", ledger.run_id, exc, exc_info=True)
            self.stats.errors += 1
            ledger.is_resolved = True
            return
        ledger.record_injection(context.injected_text, context.offered_learning_ids)
        if context.injected_text:
            self.stats.learnings_injected += len(context.offered_learning_ids)

    def _invoke_identity(self) -> AgentIdentity:
        """The registration identity, overridden per invoke via the config key."""
        override = _config_value(IDENTITY_CONFIG_KEY)
        if override is None:
            return self._identity
        if not isinstance(override, AgentIdentity):
            raise TypeError(f"{IDENTITY_CONFIG_KEY!r} in config must be an AgentIdentity, got {type(override).__name__}")
        return override

    @staticmethod
    def _run_id(state: Any) -> str | None:
        return _state_get(state, RUN_ID_STATE_KEY)

    @staticmethod
    def _messages(state: Any) -> list[BaseMessage]:
        raw = _state_get(state, "messages")
        return [m for m in (raw or []) if isinstance(m, BaseMessage)]

    @staticmethod
    def _thread_id() -> str | None:
        return _config_value("thread_id")


def assert_innermost(middleware_list: list[AgentMiddleware], instance: AgentMiddleware) -> None:
    """Assert the learning middleware sits innermost (last) in the middleware list.

    A middleware outside it (for example a summariser) could compress the injected
    learnings out of the prompt while the recorder still records the injection.
    """
    if not middleware_list or middleware_list[-1] is not instance:
        raise ValueError(
            "HyperstruckLearningMiddleware must be the innermost (last) entry in the middleware list "
            "so no outer middleware strips the injected learnings before the model sees them"
        )


def _state_get(state: Any, key: str, default: Any = None) -> Any:
    """Read a key from LangGraph state, whether it is a mapping or an object."""
    if isinstance(state, Mapping):
        return state.get(key, default)
    return getattr(state, key, default)


def _config_value(key: str) -> Any:
    """Read a ``configurable`` value from the current run config, or ``None``."""
    try:
        config = get_config()
    except Exception:  # noqa: BLE001 - best effort outside a LangGraph context
        return None
    return (config.get("configurable") or {}).get(key)


def _latest_human_goal(messages: list[BaseMessage]) -> str:
    """The latest human message: the ask that triggered this invoke."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            content = message.content
            return content if isinstance(content, str) else str(content)
    return ""


def _tool_specs(tools: Any) -> tuple[ToolSpec, ...]:
    """Project the request's tools onto the spec shape resolve expects."""
    if not tools:
        return ()
    specs: list[ToolSpec] = []
    for tool in tools:
        if isinstance(tool, str):
            name, description = tool, ""
        elif isinstance(tool, Mapping):
            name = tool.get("name")
            description = tool.get("description", "")
        else:
            name = getattr(tool, "name", None)
            description = getattr(tool, "description", "") or ""
        if name:
            specs.append(ToolSpec(name=name, description=description))
    return tuple(specs)


def _tool_call_field(call: Any, field_name: str) -> str:
    """Read a field off a ToolCall, which may be a mapping or an object."""
    if isinstance(call, Mapping):
        return call.get(field_name, "") or ""
    return getattr(call, field_name, "") or ""
