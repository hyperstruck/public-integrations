"""The learning client: the port the middleware depends on, and its HTTP backend.

``LearningClient`` is the boundary the LangGraph middleware talks to. It is a
*port* (dependency inversion): the middleware never names a concrete backend, so
the same middleware runs against the hosted platform now and an embedded backend
later by swapping the implementation. ``HostedLearningClient`` is the hosted
implementation over HTTP.

Read path (``resolve``): on the model-call hot path, so it is deadline-bounded.
On timeout or error it raises and the middleware fails open (skips injection for
the run). Prefetching is the middleware's job.

Write path (``observe`` / ``reinforce``): heavy and end-of-run, so they schedule
a background delivery and return immediately, never blocking the host's
``invoke()``. Delivery does a bounded in-memory retry with jittered backoff; this
is safe at-least-once because the platform dedupes by run id. The in-memory queue
remains the default, for the reason it always has: a thin client runs in
serverless, read-only, and multi-replica environments where local disk state is
variously impossible, useless or a correctness hazard, and durability is the
platform's responsibility on the ``202``.

That reasoning is not being called wrong, and the override on it is scoped. A
long-lived single-process standalone service is a host of a shape this package has
not had before, and it is also the one that loses days of work to a boundary
outage. So an on-disk outbox exists, is **opt-in and off by default** via
``durable_queue_dir``, refuses to enable itself on a read-only filesystem, and
persists only what would have been sent, which is already redacted. Alongside it,
``is_synchronous_writes`` awaits each write inline for a host that cannot promise
an event loop outliving the call, where a fire-and-forget write is dropped at
teardown with no error anywhere.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, cast, runtime_checkable

import httpx

from hyperstruck._version import __version__
from hyperstruck._wire import (
    _tool_payload,
    DECLINE_REASONS,
    DEFAULT_MAX_LEARNINGS,
    DISTILL_MAX_LEARNINGS,
    DISTILL_MIN_LEARNINGS,
    DistillJob,
    DistillOutcome,
    Episode,
    EvidenceItem,
    ObserveResult,
    ReinforceResult,
    ResolvedContext,
    ToolSpec,
)
from hyperstruck.env import (
    API_KEY_ENV_VARS,
    BASE_URL_ENV_VARS,
    RESOLVE_TIMEOUT_ENV,
    WRITE_TIMEOUT_ENV,
    env_float,
    first_env,
)
from hyperstruck.claim_search import (
    ClaimSearch,
    ClaimSearchDetail,
    ClaimSearchKind,
    ClaimSearchState,
)
from hyperstruck.identity import AgentIdentity
from hyperstruck.redaction import redact_episode_payload
from hyperstruck.runtime.resilience import (
    CircuitOpenError,
    DurableOutbox,
    ResolveBreaker,
    backoff_delay,
    breaker_for,
)

# Re-exported here because ``resolve`` is the only method that raises it and a caller
# writing ``except CircuitOpenError`` around a resolve should not have to know which
# module the breaker lives in.
__all__ = [
    "CircuitOpenError",
    "HostedLearningClient",
    "LearningClient",
    "ResolvePurpose",
]

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.hyperstruck.com"

# The only paths a parked write may be replayed to. The durable queue's records are read
# back from disk after a restart, so the endpoint in one is untrusted input by the time it
# is used, and every request this client makes carries the API key.
_REPLAYABLE_ENDPOINTS = frozenset({"/observe", "/reinforce", "/decline", "/distill"})


def _with_stated_channels(endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """A corpus parked before channels were compulsory states ``unknown``, so its replay is accepted."""
    evidence = body.get("evidence")
    if endpoint != "/distill" or not isinstance(evidence, list):
        return body
    return {
        **body,
        "evidence": [
            {"channel": "unknown", **item} if isinstance(item, dict) else item
            for item in evidence
        ],
    }


# What a User-Agent token may contain, matching the boundary's own `[a-z0-9-]` exactly.
_TOKEN_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")

# What this client tells the boundary it can do, rather than having it inferred from a
# version number. Declared by default and not left to the customer to copy out of a README:
# the gate prefers the declaration branch, and a client that says nothing falls back to the
# version-floor shim, so an omitted argument quietly decided which branch a customer's
# traffic took. The TypeScript client has defaulted these from the start; this is the two
# ends agreeing.
# ``final-output`` says this client can send the composed answer a turn gave its principal, which
# is what the obligation shelf's own-output lane reads. Declared rather than inferred from a
# version, for the reason the block above gives: a third client product must not need a constant
# in the boundary to be believed, and whether a host can produce the artefact at all is a property
# of the editor rather than of this library.
DEFAULT_CAPABILITIES: tuple[str, ...] = (
    "receipt",
    "delivery",
    "readonly-close",
    "final-output",
)

# Writes run in the background and can afford to wait out a slow boundary.
DEFAULT_WRITE_TIMEOUT = 30.0
# The inline budget, for a resolve awaited between a caller and its model call.
DEFAULT_RESOLVE_TIMEOUT = 2.0
# A hosted resolve cannot land inside the inline budget above: 234 production
# resolves over 24h on 2026-08-20 ran p50 11.6s, p99 18.7s, max 19.1s. A prefetched
# or explicit recall gets this instead.
DEFAULT_RECALL_TIMEOUT = 20.0
# The detached seat gets longer, and only the detached seat. Nothing waits on the IDE
# hook's resolver, so a budget close to that measured tail buys no latency and loses the
# recall outright on a slow minute. The LangGraph middleware's prefetch is a different
# case wearing the same name: it is awaited at the first model call, so raising its
# budget would put the tail straight into a customer's turn.
DEFAULT_DETACHED_RECALL_TIMEOUT = 45.0


def _delivery_fields(
    is_delivered: bool | None, recall_outcome: str | None
) -> dict[str, Any]:
    """The delivery fields a caller actually supplied, omitting what it did not say.

    Omitted rather than defaulted, because an older server rejects an unknown field and
    a newer one reads a missing one as "the client did not say", which is a third answer
    and not a synonym for not delivered.
    """
    reported: dict[str, Any] = {}
    if is_delivered is not None:
        reported["is_delivered"] = is_delivered
    if recall_outcome:
        reported["recall_outcome"] = recall_outcome
    return reported


class ResolvePurpose(StrEnum):
    """Why a resolve is being performed."""

    AGENT_LOOP = "agent_loop"
    EXPLICIT_RECALL = "explicit_recall"


HTTP_UNPROCESSABLE_ENTITY = 422
# A rejection can name one field per step of a 500-step episode, so both the
# number of named fields and the length of the resulting tag are bounded.
MAX_LOGGED_VALIDATION_ERRORS = 5
MAX_VALIDATION_CAUSE_CHARS = 200
# A field name or a pydantic error type. Anything else in `loc`/`type` did not come
# from the schema and is not copied into a log that must hold no payload content.
_VALIDATION_TOKEN = re.compile(r"[A-Za-z0-9_]{1,40}")


def _is_duplicate_receipt(response: Any) -> bool:
    """Whether the server accepted the write but dispatched nothing.

    A duplicate is still a 2xx, because at-least-once delivery makes a repeat
    legitimate. It is not, however, work: reporting one as delivered is what let a
    class of silently discarded distils go unnoticed. Absent on older servers,
    where it reads False and behaviour is unchanged.
    """
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - a receipt we cannot parse is not a duplicate
        return False
    return bool(body.get("is_duplicate")) if isinstance(body, dict) else False


def _is_terminal_write_error(exc: Exception | None) -> bool:
    """A 4xx response means the payload is rejected; retrying it cannot succeed."""
    return (
        isinstance(exc, httpx.HTTPStatusError) and 400 <= exc.response.status_code < 500
    )


def _describe_write_error(exc: Exception | None) -> str | None:
    """A cause tag with no request body, safe to persist to a diagnostic log."""
    if exc is None:
        return None
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}{_validation_locations(exc.response)}"
    return type(exc).__name__


def _validation_locations(response: httpx.Response) -> str:
    """Which fields a 422 rejected, taken structurally so no content is carried.

    A rejected write is dropped after its retries and the payload is deleted with
    it, so ``HTTP 422`` alone leaves nothing to diagnose from. The server's detail
    names the offending field but echoes the rejected ``input`` verbatim, which for
    a goal or a command is the very content this log must never hold. So ``msg``
    and ``input`` are never read, and what is read is admitted only if it looks
    like a schema token: the guarantee is then ours to keep, not the boundary's to
    honour, and a compromised or merely buggy one cannot talk its way into the log.
    """
    if response.status_code != HTTP_UNPROCESSABLE_ENTITY:
        return ""
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return ""  # a non-JSON or non-object error body is still just "HTTP 422"
    if not isinstance(detail, list):
        return ""
    located = []
    for error in detail[:MAX_LOGGED_VALIDATION_ERRORS]:
        if not isinstance(error, dict):
            continue
        loc = error.get("loc")
        if not isinstance(loc, (list, tuple)) or not loc:
            continue
        path = ".".join(_validation_token(part) for part in loc)
        located.append(f"{path}:{_validation_token(error.get('type'))}")
    if not located:
        return ""
    return f" ({', '.join(located)})"[:MAX_VALIDATION_CAUSE_CHARS]


def _validation_token(value: Any) -> str:
    """The value if it is a bare schema token, else a placeholder standing in."""
    text = str(value)
    return text if _VALIDATION_TOKEN.fullmatch(text) else "?"


@runtime_checkable
class LearningClient(Protocol):
    """The observe / resolve / reinforce boundary the middleware depends on."""

    # Delivery counters, part of the contract so callers can read the write outcome
    # after a drain (e.g. to report an honest loop-closure status) without reaching
    # past the port into a concrete implementation.
    writes_delivered: int
    writes_duplicated: int
    writes_failed: int

    async def resolve(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        goal: str,
        available_tools: Sequence[ToolSpec] = (),
        max_learnings: int = DEFAULT_MAX_LEARNINGS,
        model_context_window: int | None = None,
        source_framework: str = "",
        resolve_idempotency_key: str | None = None,
        resolve_purpose: ResolvePurpose = ResolvePurpose.AGENT_LOOP,
    ) -> ResolvedContext:
        """Return the learnings bound to a goal. Deadline-bounded; may raise.

        Pass ``resolve_idempotency_key`` (stable across retries of one recall,
        distinct across genuine recalls) to recall more than once in a run: each
        distinct key accumulates its offers and is charged once. Omit it for a
        single recall per run.
        """
        ...

    async def observe(
        self, *, identity: AgentIdentity, episode: Episode
    ) -> ObserveResult:
        """Submit a finished episode for server-side extraction. Non-blocking."""
        ...

    async def reinforce(
        self,
        *,
        identity: AgentIdentity,
        episode: Episode,
        is_org_promotion_allowed: bool = False,
        context_receipt: str | None = None,
        is_delivered: bool | None = None,
        recall_outcome: str | None = None,
    ) -> ReinforceResult:
        """Credit the learnings the run used. Non-blocking."""
        ...

    async def distill(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        goal: str,
        evidence: Sequence[EvidenceItem],
        outcome: DistillOutcome | None = None,
        evaluation: str | None = None,
        synthesis_notes: str | None = None,
        source_framework: str = "api:distill",
        occurred_at: str | None = None,
        max_learnings: int | None = None,
    ) -> None:
        """Distill learnings from a corpus of evidence. Non-blocking."""
        ...

    async def drain(self, timeout: float = 30.0) -> None:
        """Await any in-flight background writes.

        Part of the contract because the write path is non-blocking: a client that
        buffers observe/reinforce (like the hosted one) MUST flush here so a
        short-lived host can drain before exit. A client that writes synchronously
        has nothing to flush and implements this as a no-op.
        """
        ...

    async def aclose(self, drain_timeout: float = 30.0) -> None:
        """Drain in-flight writes (within ``drain_timeout``) and release resources."""
        ...


# The claims search is code with no model call, so only a hung request reaches this ceiling.
CLAIM_SEARCH_TIMEOUT_SECONDS = 180.0


class HostedLearningClient:
    """HTTP implementation of :class:`LearningClient` against the platform.

    Single-event-loop assumption: one instance is constructed once and reused for
    every invoke. The underlying ``httpx.AsyncClient`` and the in-flight write set
    bind to the event loop that first uses them, so this is safe under ``ainvoke``
    on one loop. Driving it from synchronous ``.invoke()`` across multiple threads
    (each with its own loop) is not supported; construct one client per loop.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        resolve_timeout: float | None = None,
        max_write_retries: int = 3,
        retry_backoff: float = 0.5,
        client_host: str = "",
        client_capabilities: Sequence[str] = DEFAULT_CAPABILITIES,
        durable_queue_dir: str | os.PathLike[str] | None = None,
        is_synchronous_writes: bool = False,
        breaker: ResolveBreaker | None = None,
    ) -> None:
        resolved_key = api_key or first_env(API_KEY_ENV_VARS)
        if not resolved_key:
            raise ValueError(
                "HostedLearningClient requires an API key: pass api_key=... or set "
                f"one of {', '.join(API_KEY_ENV_VARS)}"
            )
        self._api_key = resolved_key
        self._base_url = (
            base_url or first_env(BASE_URL_ENV_VARS) or DEFAULT_BASE_URL
        ).rstrip("/")
        _require_secure_base_url(self._base_url)
        self._resolve_timeout = (
            resolve_timeout
            if resolve_timeout is not None
            else env_float(RESOLVE_TIMEOUT_ENV, DEFAULT_RESOLVE_TIMEOUT)
        )
        self._client_host = _ascii_token(client_host)
        self._max_write_retries = max(1, max_write_retries)
        self._retry_backoff = retry_backoff
        # Declared rather than inferred from the version. The boundary reads a capability
        # token out of this user agent, so a client says what it can do and a third product
        # needs no version floor, no constant and no migration to be believed.
        self._client_capabilities = tuple(
            token
            for capability in client_capabilities
            if (token := _ascii_token(capability))
        )
        # Process-wide and keyed by boundary, not per instance: the whole value is that the
        # second run does not repeat the first one's timeout, and a service constructing a
        # client per request would never see a second failure on a per-instance breaker.
        self._breaker = breaker or breaker_for(self._base_url)
        self._outbox = (
            DurableOutbox.open(durable_queue_dir) if durable_queue_dir else None
        )
        self._is_synchronous_writes = is_synchronous_writes
        self._is_client_owned = http_client is None
        # Writes get their own deadline. Resolve passes its own per-request timeout
        # below rather than relying on this one: httpx applies the client timeout to
        # the transport, so a resolve budget above it would be silently capped there
        # and the wait_for would never fire.
        self._http = http_client or httpx.AsyncClient(
            timeout=env_float(WRITE_TIMEOUT_ENV, DEFAULT_WRITE_TIMEOUT)
        )
        self._pending: set[asyncio.Task[None]] = set()
        # Visibility counters.
        self.resolves = 0
        self.writes_delivered = 0
        self.writes_duplicated = 0
        self.writes_failed = 0
        # A 4xx rejection means the payload itself is bad, so a retry cannot help.
        # Tracked apart from transient 5xx/network failures so a caller (the IDE
        # flush outbox) can count only terminal rejections toward a retry cap and
        # let transient outages keep retrying.
        self.writes_terminal_failed = 0
        self.last_write_error: str | None = None

    @property
    def _headers(self) -> dict[str, str]:
        # The version is load bearing, not decoration: without it a stale client is
        # indistinguishable from a current one server-side, so a bad release cannot
        # be attributed or filtered, and the host cannot be attributed at resolve.
        # The host segment carries the other half: whether a receipt can exist at all
        # is a property of the editor, not of this library, so a version alone would
        # report a host that can never send one as ready for the credit rules that
        # require it.
        agent = f"hyperstruck-py/{__version__}"
        segments = []
        if self._client_host:
            segments.append(f"host={self._client_host}")
        if self._client_capabilities:
            segments.append(f"caps={','.join(self._client_capabilities)}")
        if segments:
            agent = f"{agent} ({'; '.join(segments)})"
        return {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": agent,
        }

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def resolve(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        goal: str,
        available_tools: Sequence[ToolSpec] = (),
        max_learnings: int = DEFAULT_MAX_LEARNINGS,
        model_context_window: int | None = None,
        source_framework: str = "",
        resolve_idempotency_key: str | None = None,
        resolve_purpose: ResolvePurpose = ResolvePurpose.AGENT_LOOP,
        session_id: str | None = None,
        session_epoch: str | None = None,
        undelivered_run_id: str | None = None,
        undelivered_resolve_key: str | None = None,
        undelivered_resolves: Sequence[dict[str, str | None]] = (),
        tool_in_play: str | None = None,
        standards_tools: Sequence[str] = (),
    ) -> ResolvedContext:
        body: dict[str, Any] = {
            "agent_name": identity.agent_name,
            "org_id": identity.org_id,
            "run_id": run_id,
            "goal": goal,
            "source_framework": source_framework,
            "available_tools": [_tool_payload(t) for t in available_tools],
            "max_learnings": max_learnings,
            "model_context_window": model_context_window,
        }
        if resolve_idempotency_key is not None:
            body["resolve_idempotency_key"] = resolve_idempotency_key
        # Preserve compatibility with older servers by relying on the server's
        # agent_loop default; only the non-default explicit recall needs a key.
        if resolve_purpose != ResolvePurpose.AGENT_LOOP:
            body["resolve_purpose"] = ResolvePurpose(resolve_purpose).value
        # Omitted when absent: an older boundary forbids unknown fields.
        if session_id is not None:
            body["session_id"] = session_id
        if session_epoch is not None:
            body["session_epoch"] = session_epoch
        if undelivered_run_id is not None:
            body["undelivered_run_id"] = undelivered_run_id
        if undelivered_resolve_key is not None:
            body["undelivered_resolve_key"] = undelivered_resolve_key
        if undelivered_resolves:
            body["undelivered_resolves"] = [dict(item) for item in undelivered_resolves]
        if tool_in_play is not None:
            body["tool_in_play"] = tool_in_play
        if standards_tools:
            body["standards_tools"] = list(standards_tools)
        # Asked before the call, not after: the point of the breaker is that a run reached
        # by a degraded boundary pays nothing rather than paying the timeout again. A run
        # turned away here fails open exactly as a timed-out one does, and reports
        # ``resolve_failed``, so the seat's taxonomy still separates a broken deployment
        # from a cold corpus. No retry is added around this call, deliberately: a resolve
        # retry without a ``resolve_idempotency_key`` double-records the recall, and the
        # breaker's job is to make the *first* attempt cheap rather than to make more of them.
        self._breaker.before_request()
        try:
            response = await asyncio.wait_for(
                self._http.post(
                    self._url("/resolve"),
                    json=body,
                    headers=self._headers,
                    timeout=self._resolve_timeout,
                ),
                timeout=self._resolve_timeout,
            )
        except httpx.TimeoutException as exc:
            self._breaker.record_failure()
            # Raised as the language's own timeout so a caller can tell "the boundary
            # ran out of time", a capacity fact, from "the call broke", a fault. The
            # transport's timeout and the wait_for race each other by design, and which
            # one wins is an implementation detail no caller should have to know.
            raise TimeoutError(
                f"hosted resolve exceeded {self._resolve_timeout}s"
            ) from exc
        except Exception:
            self._breaker.record_failure()
            raise
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            # A 4xx is the caller's payload and says nothing about the boundary's health,
            # so it must not trip a breaker that would then withhold recall from every
            # other run in the process for a mistake local to this one.
            if response.status_code >= 500:
                self._breaker.record_failure()
            else:
                # A 4xx says nothing about the boundary's health, so it must not count as a
                # failure. It must still *release* the probe slot: ``before_request`` claims
                # it before the call, and a path that returns without recording either
                # outcome leaves the breaker latched half-open, refusing every later probe
                # for the life of the process and disabling recall for every run in it.
                self._breaker.release_probe()
            raise
        self._breaker.record_success()
        self.resolves += 1
        return ResolvedContext.from_response(response.json())

    async def search_claims(
        self,
        *,
        agent_id: str,
        question: str,
        entity: str | None = None,
        as_of: datetime | str | None = None,
        since: datetime | str | None = None,
        detail: ClaimSearchDetail | None = None,
        state: ClaimSearchState | None = None,
        kind: ClaimSearchKind | None = None,
        owner: str | None = None,
        due_before: datetime | str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> ClaimSearch:
        """Search the hosted agent ``agent_id``'s claims for a question; get ClaimSearch back.

        A read: nothing is stored or billed, so there is no key and no retry, and an error status
        is raised as ``httpx.HTTPStatusError``. ``entity`` narrows the question to one entity's id
        (404 when the account does not hold it). ``as_of`` searches the account as it stood
        then and ``since`` searches what changed after it; a ``datetime`` is sent as ISO 8601
        and must carry a timezone offset (a naive one raises ``ValueError`` naming the
        parameter). ``detail`` is ``concise`` (the default), ``cited`` or ``full``. ``state``,
        ``kind``, ``owner`` (an entity id) and ``due_before`` are the filter ``GET /claims``
        takes: with any of them the result is the filtered set (``shape: set``), paged by
        ``cursor`` and ``limit``.
        """
        given = {
            "question": question,
            "entity": entity,
            "as_of": _iso(as_of, "as_of"),
            "since": _iso(since, "since"),
            "detail": detail,
            "state": state,
            "kind": kind,
            "owner": owner,
            "due_before": _iso(due_before, "due_before"),
            "cursor": cursor,
            "limit": limit,
        }
        response = await self._http.post(
            self._url(f"/agents/{agent_id}/claims/search"),
            json={name: value for name, value in given.items() if value is not None},
            headers=self._headers,
            timeout=CLAIM_SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return cast(ClaimSearch, response.json())

    async def observe(
        self, *, identity: AgentIdentity, episode: Episode
    ) -> ObserveResult:
        body = {
            "agent_name": identity.agent_name,
            "org_id": identity.org_id,
            "episode": redact_episode_payload(episode.to_payload()),
        }
        response = await self._schedule_write("/observe", body)
        return ObserveResult(keys_awaiting_review=_keys_awaiting_review(response))

    async def reinforce(
        self,
        *,
        identity: AgentIdentity,
        episode: Episode,
        is_org_promotion_allowed: bool = False,
        context_receipt: str | None = None,
        is_delivered: bool | None = None,
        recall_outcome: str | None = None,
    ) -> ReinforceResult:
        """Credit the learnings the run used. Non-blocking.

        ``is_delivered`` and ``recall_outcome`` say whether the recall reached the
        model at all, and when it did not, why. Without them an absent receipt has
        two readings, a run that was shown its learnings and lost the evidence, and
        a run that was never shown them, and the boundary can only assume the first.

        Both halves of the result are the boundary's own, sent only when the caller is in
        synchronous mode: asynchronously there is nobody left to hand them to by the time
        they arrive. Empty otherwise, and empty against a deployment that returns neither,
        which is what both clients degrade to.
        """
        body = {
            "agent_name": identity.agent_name,
            "org_id": identity.org_id,
            "episode": redact_episode_payload(episode.to_payload()),
            "is_org_promotion_allowed": is_org_promotion_allowed,
            "context_receipt": context_receipt,
        }
        body.update(_delivery_fields(is_delivered, recall_outcome))
        response = await self._schedule_write("/reinforce", body)
        return _reinforce_result(response)

    async def distill(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        goal: str,
        evidence: Sequence[EvidenceItem],
        outcome: DistillOutcome | None = None,
        evaluation: str | None = None,
        synthesis_notes: str | None = None,
        source_framework: str = "api:distill",
        occurred_at: str | None = None,
        max_learnings: int | None = None,
    ) -> None:
        # Writes are fire-and-forget, so a server 4xx would be swallowed silently.
        # Fail loud here on the structural mistakes a caller is most likely to hit
        # (unnamespaced run id, too few items, out-of-range max_learnings). The
        # server's content-size and occurred_at gates are not mirrored to avoid
        # duplicating its thresholds; those surface only server-side.
        if not run_id.startswith("distill:"):
            raise ValueError(
                "run_id must be namespaced with the 'distill:' prefix "
                "(e.g. 'distill:my-postmortem-2026-07')"
            )
        if not evidence:
            raise ValueError("distill requires at least 1 evidence item")
        if max_learnings is not None and not (
            DISTILL_MIN_LEARNINGS <= max_learnings <= DISTILL_MAX_LEARNINGS
        ):
            raise ValueError(
                f"max_learnings must be between {DISTILL_MIN_LEARNINGS} and "
                f"{DISTILL_MAX_LEARNINGS}"
            )
        # Identity is authoritative (as for observe/reinforce); the caller must
        # pre-redact secrets in evidence content, which is stored verbatim server-side.
        job = DistillJob(
            agent_name=identity.agent_name,
            org_id=identity.org_id,
            run_id=run_id,
            goal=goal,
            evidence=tuple(evidence),
            outcome=outcome or DistillOutcome(is_success=True),
            evaluation=evaluation,
            synthesis_notes=synthesis_notes,
            source_framework=source_framework,
            occurred_at=occurred_at,
            max_learnings=max_learnings,
        )
        await self._schedule_write("/distill", job.to_payload())

    async def decline(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        reason: str,
        is_delivered: bool = False,
        recall_outcome: str | None = None,
        source_framework: str = "",
    ) -> ReinforceResult:
        """Close a run whose turn ended with nothing worth learning.

        The terminal alternative to observe/reinforce, not a failure path. A run
        left unclosed is indistinguishable from a host that stopped writing back,
        so a host that decides a turn is not worth learning from should say so.

        ``is_delivered`` reports whether the recall reached the model this turn. A
        turn can be shown its learnings and still not be worth learning from, and
        only the host knows, so the caller is billed for recall it received and
        released otherwise.

        The presence half of the result is empty: a turn nothing was learned from has no
        credit verdict to read back.
        """
        if not run_id:
            raise ValueError("decline requires the run_id supplied to resolve")
        if reason not in DECLINE_REASONS:
            raise ValueError(
                f"reason must be one of {sorted(DECLINE_REASONS)}, got {reason!r}"
            )
        response = await self._schedule_write(
            "/decline",
            {
                "agent_name": identity.agent_name,
                "org_id": identity.org_id,
                "run_id": run_id,
                "reason": reason,
                "is_delivered": is_delivered,
                "source_framework": source_framework,
                **_delivery_fields(None, recall_outcome),
            },
        )
        return _reinforce_result(response)

    # -- background delivery ------------------------------------------------

    async def _schedule_write(self, path: str, body: dict[str, Any]) -> Any:
        """Fire-and-forget a write so the host run is never blocked.

        In synchronous mode the write is delivered inline instead. That mode exists for a
        host with no guarantee of an event loop or a process outliving the scheduling call:
        there, a scheduled task is cancelled at teardown and the episode is lost with no
        error anywhere, so the customer sees a corpus that never fills and nothing to
        diagnose from. Paying the latency is the lesser cost, and it is the caller's
        explicit choice.

        The method is ``async`` so that both branches are reached the same way. The
        scheduling branch never awaits anything, so it still returns to the host in the
        same tick and the write path stays non-blocking by default.
        """
        # Synchronous disk I/O on an otherwise non-blocking path, and that is the trade the
        # durable mode *is*: parking after the write is scheduled would lose exactly the
        # writes it exists to keep, the ones a process death takes with it. It is opt-in, it
        # is off by default, and a host that cannot afford the write should not enable it.
        # One small file per write, so the cost is a few hundred microseconds rather than a
        # round trip.
        parked = self._outbox.park(path, body) if self._outbox is not None else None
        if self._is_synchronous_writes:
            return await self._deliver(path, body, parked=parked)
        task = asyncio.ensure_future(self._deliver(path, body, parked=parked))
        self._pending.add(task)
        task.add_done_callback(self._on_write_done)
        return None

    def _on_write_done(self, task: asyncio.Task[None]) -> None:
        """Drop a finished write; surface an unexpected escape rather than hide it.

        ``_deliver`` handles its own delivery errors, so a task that ends with an
        exception here is an unexpected one (not a cancellation) and is logged
        instead of silently swallowed by the discard.
        """
        self._pending.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.warning("Hyperstruck write task ended unexpectedly: %s", exc)

    async def _deliver(
        self, path: str, body: dict[str, Any], *, parked: Any = None
    ) -> Any:
        """Deliver one write with bounded retry and jittered backoff.

        At-least-once is safe: the platform dedupes by run id, so a retried write
        is a server-side no-op. After the bounded attempts the write is dropped
        (logged and counted), never raised, since there is nothing to block.

        A durably parked write is released on delivery and on a terminal rejection, and
        left on disk otherwise, so an outage that outlives the process is drained by the
        next start rather than lost with it. A 4xx is released rather than kept because it
        fails identically forever, and keeping it would make every later drain re-send a
        payload the boundary has already refused.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_write_retries):
            try:
                response = await self._http.post(
                    self._url(path), json=body, headers=self._headers
                )
                response.raise_for_status()
                self.writes_delivered += 1
                if _is_duplicate_receipt(response):
                    self.writes_duplicated += 1
                if self._outbox is not None:
                    self._outbox.release(parked)
                try:
                    return response.json()
                except ValueError:
                    return None
            except Exception as exc:  # noqa: BLE001 - background best-effort
                last_error = exc
                if _is_terminal_write_error(exc):
                    break  # a 4xx fails identically on every retry
                if attempt + 1 < self._max_write_retries:
                    # Jittered, because the previous schedule was identical for every
                    # concurrent run and their retries therefore arrived as one wave. One
                    # client instance in a standalone service fronts many runs at once,
                    # which is what makes this matter more here than in the graph seat.
                    await asyncio.sleep(backoff_delay(self._retry_backoff, attempt))
        if self._outbox is not None and _is_terminal_write_error(last_error):
            self._outbox.release(parked)
        self.writes_failed += 1
        if _is_terminal_write_error(last_error):
            self.writes_terminal_failed += 1
        self.last_write_error = _describe_write_error(last_error)
        logger.warning(
            "Hyperstruck write to %s dropped after %d attempts: %s",
            path,
            self._max_write_retries,
            last_error,
        )
        return None

    async def drain(self, timeout: float = 30.0) -> None:
        """Await all in-flight background writes (for shutdown and tests)."""
        if self._pending:
            await asyncio.wait(set(self._pending), timeout=timeout)

    async def replay_durable_queue(self) -> int:
        """Re-send every write parked on disk, and return how many landed.

        Called by a host at start-up, which is the moment the durable queue exists for: a
        process restarted during a boundary outage has episodes on disk that no in-memory
        queue could have survived. Delivery is at-least-once and the platform dedupes by
        run id, so replaying a write that did in fact land is a server-side no-op.
        """
        if self._outbox is None:
            return 0
        delivered = 0
        before = self.writes_delivered
        for write in list(self._outbox.pending()):
            # The endpoint comes off disk, and a file on disk is not a trusted input: a
            # tampered or corrupted record naming `//evil.example.com/x` would make
            # ``_url`` produce a URL on another host, and this client attaches the Bearer
            # key to every request it makes. Only the paths this client itself parks are
            # replayable; anything else is dropped and said out loud.
            if write.endpoint not in _REPLAYABLE_ENDPOINTS:
                logger.warning(
                    "Hyperstruck durable outbox refusing a parked write to an unknown "
                    "endpoint %r; dropping it rather than sending credentials to it",
                    write.endpoint,
                )
                self._outbox.release(write.path)
                continue
            body = _with_stated_channels(write.endpoint, write.body)
            await self._deliver(write.endpoint, body, parked=write.path)
            if self.writes_delivered > before:
                delivered += 1
                before = self.writes_delivered
        return delivered

    async def aclose(self, drain_timeout: float = 30.0) -> None:
        await self.drain(timeout=drain_timeout)
        if self._is_client_owned:
            await self._http.aclose()


def _iso(moment: datetime | str | None, parameter: str) -> str | None:
    """A moment as ISO 8601; the hosted read refuses one with no offset, so a naive datetime is refused here, naming the parameter."""
    if isinstance(moment, datetime) and moment.utcoffset() is None:
        raise ValueError(
            f"{parameter} needs a timezone offset (use datetime.now(UTC) or tzinfo=UTC); got a datetime with none"
        )
    return moment.isoformat() if isinstance(moment, datetime) else moment


def _ascii_token(value: str) -> str:
    """One User-Agent token, reduced to what the boundary's own pattern can match.

    ASCII explicitly, because ``str.isalnum`` is true for every alphanumeric in Unicode:
    ``"①".isalnum()`` is ``True``. A token carrying one reached the header and then failed
    the boundary's ``[a-z0-9-]`` pattern, so the client fell out of the declaration branch
    and back to the version floor with nothing said. The TypeScript client's character
    class was ASCII-only from the start, so this was also a divergence between two clients
    a parity test claims agree.
    """
    return "".join(c for c in value.strip().lower() if c in _TOKEN_CHARS)


def _presence_outcomes(response: Any) -> tuple[dict[str, str], ...]:
    """The boundary's per-offered-id presence verdict, or empty.

    Empty against a deployment that does not return it, and empty on the asynchronous write
    path where the response arrives after the caller has gone. The seat's own local verbatim
    check stands in until this is populated, and is labelled a heuristic precisely because
    it is not this.
    """
    if not isinstance(response, dict):
        return ()
    raw = response.get("presence_outcomes")
    if not isinstance(raw, list):
        return ()
    return tuple(
        {"id": item["id"], "outcome": item["outcome"]}
        for item in raw
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("outcome"), str)
    )


def _keys_awaiting_review(response: Any) -> int | None:
    """How many keys wait on a person, or None when the boundary did not say.

    None, never zero, against a deployment that does not return it and on the asynchronous
    write path: zero would tell a host nothing is held when it simply was not told.
    """
    if not isinstance(response, dict):
        return None
    count = response.get("keys_awaiting_review")
    if isinstance(count, bool) or not isinstance(count, int):
        return None
    return count


def _reinforce_result(response: Any) -> ReinforceResult:
    return ReinforceResult(
        presence_outcomes=_presence_outcomes(response),
        keys_awaiting_review=_keys_awaiting_review(response),
    )


def _require_secure_base_url(base_url: str) -> None:
    """Reject a non-HTTPS base URL so the API key cannot leak over cleartext.

    Localhost is allowed as an explicit escape hatch for local proxies and tests.
    """
    if base_url.startswith("https://"):
        return
    if base_url.startswith(("http://localhost", "http://127.0.0.1", "http://[::1]")):
        return
    raise ValueError(
        f"Hyperstruck base URL must be https:// (got {base_url!r}); the API key would otherwise "
        "be sent in cleartext. Use https, or http://localhost for local development."
    )
