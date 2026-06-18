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
import os
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

import httpx

from hyperstruck._wire import DEFAULT_MAX_LEARNINGS, Episode, ResolvedContext, ToolSpec
from hyperstruck.identity import AgentIdentity
from hyperstruck.redaction import redact_episode_payload

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.hyperstruck.com"
_API_KEY_ENV_VARS = ("HYPERSTRUCK_API_KEY", "HYPER_API_KEY")
_BASE_URL_ENV_VARS = ("HYPERSTRUCK_BASE_URL", "HYPER_BASE_URL")


@runtime_checkable
class LearningClient(Protocol):
    """The observe / resolve / reinforce boundary the middleware depends on."""

    async def resolve(
        self,
        *,
        identity: AgentIdentity,
        run_id: str,
        goal: str,
        available_tools: Sequence[ToolSpec] = (),
        max_learnings: int = DEFAULT_MAX_LEARNINGS,
        model_context_window: int | None = None,
    ) -> ResolvedContext:
        """Return the learnings bound to a goal. Deadline-bounded; may raise."""
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
    ) -> None:
        """Credit the learnings the run used. Non-blocking."""
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
        resolve_timeout: float = 2.0,
        max_write_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        resolved_key = api_key or _first_env(_API_KEY_ENV_VARS)
        if not resolved_key:
            raise ValueError(
                "HostedLearningClient requires an API key: pass api_key=... or set "
                f"one of {', '.join(_API_KEY_ENV_VARS)}"
            )
        self._api_key = resolved_key
        self._base_url = (base_url or _first_env(_BASE_URL_ENV_VARS) or DEFAULT_BASE_URL).rstrip("/")
        _require_secure_base_url(self._base_url)
        self._resolve_timeout = resolve_timeout
        self._max_write_retries = max(1, max_write_retries)
        self._retry_backoff = retry_backoff
        self._is_client_owned = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=resolve_timeout)
        self._pending: set[asyncio.Task[None]] = set()
        # Visibility counters.
        self.resolves = 0
        self.writes_delivered = 0
        self.writes_failed = 0

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

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
    ) -> ResolvedContext:
        body: dict[str, Any] = {
            "agent_id": identity.agent_id,
            "org_id": identity.org_id,
            "run_id": run_id,
            "goal": goal,
            "available_tools": [{"name": t.name, "description": t.description} for t in available_tools],
            "max_learnings": max_learnings,
            "model_context_window": model_context_window,
        }
        response = await asyncio.wait_for(
            self._http.post(self._url("/v1/resolve"), json=body, headers=self._headers),
            timeout=self._resolve_timeout,
        )
        response.raise_for_status()
        self.resolves += 1
        return ResolvedContext.from_response(response.json())

    async def observe(self, *, identity: AgentIdentity, episode: Episode) -> None:
        body = {
            "agent_id": identity.agent_id,
            "org_id": identity.org_id,
            "episode": redact_episode_payload(episode.to_payload()),
        }
        self._schedule_write("/v1/observe", body)

    async def reinforce(
        self,
        *,
        identity: AgentIdentity,
        episode: Episode,
        is_org_promotion_allowed: bool = False,
    ) -> None:
        body = {
            "agent_id": identity.agent_id,
            "org_id": identity.org_id,
            "episode": redact_episode_payload(episode.to_payload()),
            "is_org_promotion_allowed": is_org_promotion_allowed,
        }
        self._schedule_write("/v1/reinforce", body)

    # -- background delivery ------------------------------------------------

    def _schedule_write(self, path: str, body: dict[str, Any]) -> None:
        """Fire-and-forget a write so the host run is never blocked."""
        task = asyncio.ensure_future(self._deliver(path, body))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def _deliver(self, path: str, body: dict[str, Any]) -> None:
        """Deliver one write with bounded retry and backoff.

        At-least-once is safe: the platform dedupes by run id, so a retried write
        is a server-side no-op. After the bounded attempts the write is dropped
        (logged and counted), never raised, since there is nothing to block.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_write_retries):
            try:
                response = await self._http.post(self._url(path), json=body, headers=self._headers)
                response.raise_for_status()
                self.writes_delivered += 1
                return
            except Exception as exc:  # noqa: BLE001 - background best-effort
                last_error = exc
                if attempt + 1 < self._max_write_retries:
                    await asyncio.sleep(self._retry_backoff * (2**attempt))
        self.writes_failed += 1
        logger.warning("Hyperstruck write to %s dropped after %d attempts: %s", path, self._max_write_retries, last_error)

    async def drain(self, timeout: float = 30.0) -> None:
        """Await all in-flight background writes (for shutdown and tests)."""
        if self._pending:
            await asyncio.wait(set(self._pending), timeout=timeout)

    async def aclose(self) -> None:
        await self.drain()
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


def _first_env(names: Sequence[str]) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None
