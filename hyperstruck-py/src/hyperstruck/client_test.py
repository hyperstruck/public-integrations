"""HostedLearningClient: auth, resolve deadline/fail-path, async writes, retry."""

from __future__ import annotations

import httpx
import pytest

from hyperstruck._wire import Episode, StepRecord, TerminalOutcome
from hyperstruck.client import HostedLearningClient
from hyperstruck.identity import AgentIdentity

IDENTITY = AgentIdentity(agent_id="support-bot", org_id="org-1")


def _episode() -> Episode:
    return Episode(
        run_id="support-bot:abc",
        goal="help the customer",
        steps=(StepRecord(id="c1", name="lookup", args={"q": "x"}, status="completed", result="ok"),),
        outcome=TerminalOutcome(is_success=True, total_steps=1, completed_steps=1),
    )


def _client(handler, **kwargs) -> HostedLearningClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return HostedLearningClient(api_key="k", http_client=http, **kwargs)


def test_non_https_base_url_rejected() -> None:
    with pytest.raises(ValueError, match="https"):
        HostedLearningClient(api_key="k", base_url="http://api.example.com")


def test_localhost_http_allowed() -> None:
    client = HostedLearningClient(api_key="k", base_url="http://localhost:8000")
    assert client._base_url == "http://localhost:8000"


def test_missing_api_key_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERSTRUCK_API_KEY", raising=False)
    monkeypatch.delenv("HYPER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        HostedLearningClient()


async def test_resolve_returns_bound_context() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"injected_text": "L", "offered_learning_ids": ["a", "b"]})

    client = _client(handler)
    ctx = await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert ctx.injected_text == "L"
    assert ctx.offered_learning_ids == ("a", "b")
    assert seen["path"] == "/v1/resolve"
    assert seen["auth"] == "Bearer k"
    await client.aclose()


async def test_resolve_raises_on_error_so_middleware_can_fail_open() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    client = _client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    await client.aclose()


async def test_observe_is_background_and_redacted() -> None:
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        bodies.append(json.loads(request.content))
        return httpx.Response(202, json={"status": "accepted", "run_id": "support-bot:abc"})

    episode = Episode(
        run_id="support-bot:abc",
        goal="g",
        steps=(
            StepRecord(
                id="c1",
                name="lookup",
                args={"ssn": "111-22-3333"},
                status="completed",
                result="ok",
                declared_sensitivity={"args": {"ssn": "pii"}},
            ),
        ),
        outcome=TerminalOutcome(is_success=True, total_steps=1, completed_steps=1),
    )
    client = _client(handler)
    await client.observe(identity=IDENTITY, episode=episode)
    await client.drain()
    assert client.writes_delivered == 1
    sent = bodies[0]["episode"]["steps"][0]["args"]["ssn"]
    assert sent == "[REDACTED:pii]"
    await client.aclose()


async def test_write_bounded_retry_then_dropped() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(503, json={"detail": "unavailable"})

    client = _client(handler, max_write_retries=3, retry_backoff=0.0)
    await client.reinforce(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert attempts["n"] == 3
    assert client.writes_failed == 1
    assert client.writes_delivered == 0
    await client.aclose()


async def test_at_least_once_safe_same_run_id_sends_each_time() -> None:
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        posts.append(request.url.path)
        return httpx.Response(202, json={"status": "accepted"})

    client = _client(handler)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    # The client sends each time; the platform dedupes by run id server-side.
    assert posts.count("/v1/observe") == 2
    await client.aclose()
