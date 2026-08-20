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
``invoke()``. Delivery does a bounded in-memory retry with backoff; this is safe
at-least-once because the platform dedupes by run id. There is deliberately no
durable on-disk outbox: a thin client runs in serverless, read-only, and
multi-replica environments where local disk state is fragile. Durability is the
platform's responsibility on the ``202``.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Sequence
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

import httpx

from hyperstruck._version import __version__
from hyperstruck._wire import (
    DECLINE_REASONS,
    DEFAULT_MAX_LEARNINGS,
    DISTILL_MAX_LEARNINGS,
    DISTILL_MIN_LEARNINGS,
    DistillJob,
    DistillOutcome,
    Episode,
    EvidenceItem,
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
from hyperstruck.identity import AgentIdentity
from hyperstruck.redaction import redact_episode_payload

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.hyperstruck.com"

# Writes run in the background and can afford to wait out a slow boundary.
DEFAULT_WRITE_TIMEOUT = 30.0
# The inline budget, for a resolve awaited between a caller and its model call.
DEFAULT_RESOLVE_TIMEOUT = 2.0
# A hosted resolve cannot land inside the inline budget above: 234 production
# resolves over 24h on 2026-08-20 ran p50 11.6s, p99 18.7s, max 19.1s. Any recall
# that is prefetched or explicit, and so is not what the caller is waiting on, gets
# this instead, and it sits well clear of that tail rather than just above it: a
# recall that misses the deadline is not a slower recall, it is no recall at all,
# and the wait costs nothing because nobody is blocked on it.
DEFAULT_RECALL_TIMEOUT = 45.0


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

    async def observe(self, *, identity: AgentIdentity, episode: Episode) -> None:
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
    ) -> None:
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
        self._client_host = "".join(
            c for c in client_host.strip().lower() if c.isalnum() or c == "-"
        )
        self._max_write_retries = max(1, max_write_retries)
        self._retry_backoff = retry_backoff
        self._is_client_owned = http_client is None
        # Writes get their own, longer deadline; resolve stays bounded by
        # asyncio.wait_for(self._resolve_timeout) regardless of this client timeout.
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
        if self._client_host:
            agent = f"{agent} (host={self._client_host})"
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
    ) -> ResolvedContext:
        body: dict[str, Any] = {
            "agent_name": identity.agent_name,
            "org_id": identity.org_id,
            "run_id": run_id,
            "goal": goal,
            "source_framework": source_framework,
            "available_tools": [
                {"name": t.name, "description": t.description} for t in available_tools
            ],
            "max_learnings": max_learnings,
            "model_context_window": model_context_window,
        }
        if resolve_idempotency_key is not None:
            body["resolve_idempotency_key"] = resolve_idempotency_key
        # Preserve compatibility with older servers by relying on the server's
        # agent_loop default; only the non-default explicit recall needs a key.
        if resolve_purpose != ResolvePurpose.AGENT_LOOP:
            body["resolve_purpose"] = ResolvePurpose(resolve_purpose).value
        response = await asyncio.wait_for(
            self._http.post(self._url("/resolve"), json=body, headers=self._headers),
            timeout=self._resolve_timeout,
        )
        response.raise_for_status()
        self.resolves += 1
        return ResolvedContext.from_response(response.json())

    async def observe(self, *, identity: AgentIdentity, episode: Episode) -> None:
        body = {
            "agent_name": identity.agent_name,
            "org_id": identity.org_id,
            "episode": redact_episode_payload(episode.to_payload()),
        }
        self._schedule_write("/observe", body)

    async def reinforce(
        self,
        *,
        identity: AgentIdentity,
        episode: Episode,
        is_org_promotion_allowed: bool = False,
        context_receipt: str | None = None,
        is_delivered: bool | None = None,
        recall_outcome: str | None = None,
    ) -> None:
        """Credit the learnings the run used. Non-blocking.

        ``is_delivered`` and ``recall_outcome`` say whether the recall reached the
        model at all, and when it did not, why. Without them an absent receipt has
        two readings, a run that was shown its learnings and lost the evidence, and
        a run that was never shown them, and the boundary can only assume the first.
        """
        body = {
            "agent_name": identity.agent_name,
            "org_id": identity.org_id,
            "episode": redact_episode_payload(episode.to_payload()),
            "is_org_promotion_allowed": is_org_promotion_allowed,
            "context_receipt": context_receipt,
        }
        if is_delivered is not None:
            body["is_delivered"] = is_delivered
        if recall_outcome:
            body["recall_outcome"] = recall_outcome
        self._schedule_write("/reinforce", body)

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
        if len(evidence) < 2:
            raise ValueError("distill requires at least 2 evidence items")
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
        self._schedule_write("/distill", job.to_payload())

    async def decline(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        reason: str,
        is_delivered: bool = False,
        recall_outcome: str | None = None,
        source_framework: str = "",
    ) -> None:
        """Close a run whose turn ended with nothing worth learning.

        The terminal alternative to observe/reinforce, not a failure path. A run
        left unclosed is indistinguishable from a host that stopped writing back,
        so a host that decides a turn is not worth learning from should say so.

        ``is_delivered`` reports whether the recall reached the model this turn. A
        turn can be shown its learnings and still not be worth learning from, and
        only the host knows, so the caller is billed for recall it received and
        released otherwise.
        """
        if not run_id:
            raise ValueError("decline requires the run_id supplied to resolve")
        if reason not in DECLINE_REASONS:
            raise ValueError(
                f"reason must be one of {sorted(DECLINE_REASONS)}, got {reason!r}"
            )
        self._schedule_write(
            "/decline",
            {
                "agent_name": identity.agent_name,
                "org_id": identity.org_id,
                "run_id": run_id,
                "reason": reason,
                "is_delivered": is_delivered,
                "source_framework": source_framework,
                **({"recall_outcome": recall_outcome} if recall_outcome else {}),
            },
        )

    # -- background delivery ------------------------------------------------

    def _schedule_write(self, path: str, body: dict[str, Any]) -> None:
        """Fire-and-forget a write so the host run is never blocked."""
        task = asyncio.ensure_future(self._deliver(path, body))
        self._pending.add(task)
        task.add_done_callback(self._on_write_done)

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

    async def _deliver(self, path: str, body: dict[str, Any]) -> None:
        """Deliver one write with bounded retry and backoff.

        At-least-once is safe: the platform dedupes by run id, so a retried write
        is a server-side no-op. After the bounded attempts the write is dropped
        (logged and counted), never raised, since there is nothing to block.
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
                return
            except Exception as exc:  # noqa: BLE001 - background best-effort
                last_error = exc
                if _is_terminal_write_error(exc):
                    break  # a 4xx fails identically on every retry
                if attempt + 1 < self._max_write_retries:
                    await asyncio.sleep(self._retry_backoff * (2**attempt))
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

    async def drain(self, timeout: float = 30.0) -> None:
        """Await all in-flight background writes (for shutdown and tests)."""
        if self._pending:
            await asyncio.wait(set(self._pending), timeout=timeout)

    async def aclose(self, drain_timeout: float = 30.0) -> None:
        await self.drain(timeout=drain_timeout)
        if self._is_client_owned:
            await self._http.aclose()


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
