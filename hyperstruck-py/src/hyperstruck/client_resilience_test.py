"""The client under a degraded boundary: the breaker, the queue, and the flush mode.

In its own file rather than in ``client_test.py`` because these are the failure-path
behaviours the seat depends on, and the process-wide breaker needs resetting around each
test in a way the existing suite should not have to know about.
"""

from __future__ import annotations

import httpx
import pytest

from hyperstruck._wire import Episode, StepRecord, TerminalOutcome
from hyperstruck.client import CircuitOpenError, HostedLearningClient
from hyperstruck.identity import AgentIdentity
from hyperstruck.runtime.resilience import ResolveBreaker, reset_breakers

IDENTITY = AgentIdentity(agent_name="support-bot", org_id="org-1")


@pytest.fixture(autouse=True)
def _isolated_breakers():
    """A process-wide breaker must not carry one test's outage into the next."""
    reset_breakers()
    yield
    reset_breakers()


def _episode() -> Episode:
    return Episode(
        run_id="support-bot:abc",
        goal="help the customer",
        steps=(
            StepRecord(
                id="c1", name="lookup", args={"q": "x"}, status="completed", result="ok"
            ),
        ),
        outcome=TerminalOutcome(is_success=True, total_steps=1, completed_steps=1),
    )


def _client(handler, **kwargs) -> HostedLearningClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return HostedLearningClient(api_key="k", http_client=http, **kwargs)


async def test_a_declared_capability_reaches_the_user_agent_beside_the_host() -> None:
    """The gate reads a token rather than inferring one from a version number.

    The shape matters character for character: the boundary and a Postgres function read
    the same anchored pattern, and a client whose separator differs is judged capable by
    neither.
    """
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["User-Agent"])
        return httpx.Response(200, json={})

    client = _client(handler, client_host="ai-sdk", client_capabilities=("receipt", "delivery"))
    await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert seen[0].endswith("(host=ai-sdk; caps=receipt,delivery)")


async def test_the_breaker_spares_later_runs_the_timeout_the_first_one_paid() -> None:
    """Without it, a degraded boundary costs the host its whole p99 tail per run."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={})

    breaker = ResolveBreaker(failure_threshold=2, cooldown=60.0)
    client = _client(handler, breaker=breaker)
    for _ in range(2):
        with pytest.raises(httpx.HTTPStatusError):
            await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert attempts == 2

    with pytest.raises(CircuitOpenError):
        await client.resolve(identity=IDENTITY, run_id="r2", goal="g")
    assert attempts == 2, "the third run must not have reached the boundary at all"


async def test_a_4xx_does_not_trip_the_breaker() -> None:
    """A rejected payload says nothing about the boundary's health.

    Tripping on it would withhold recall from every other run in the process because of a
    mistake local to one of them.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": []})

    breaker = ResolveBreaker(failure_threshold=1, cooldown=60.0)
    client = _client(handler, breaker=breaker)
    with pytest.raises(httpx.HTTPStatusError):
        await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert breaker.is_open is False


async def test_a_success_closes_a_breaker_that_had_opened() -> None:
    responses = [httpx.Response(503, json={}), httpx.Response(200, json={})]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    breaker = ResolveBreaker(failure_threshold=1, cooldown=0.0)
    client = _client(handler, breaker=breaker)
    with pytest.raises(httpx.HTTPStatusError):
        await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert breaker.is_open is True
    await client.resolve(identity=IDENTITY, run_id="r2", goal="g")
    assert breaker.is_open is False


async def test_synchronous_writes_land_before_the_call_returns() -> None:
    """For a host with no guarantee of a loop outliving the scheduling call.

    There, a fire-and-forget write is cancelled at teardown, the episode is lost, and the
    customer sees a corpus that never fills with no error anywhere to diagnose from.
    """
    landed: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        landed.append(str(request.url))
        return httpx.Response(200, json={})

    client = _client(handler, is_synchronous_writes=True)
    await client.observe(identity=IDENTITY, episode=_episode())
    assert [url.endswith("/observe") for url in landed] == [True]
    assert client.writes_delivered == 1
    assert client._pending == set()


async def test_the_default_write_path_is_still_non_blocking() -> None:
    """The documented default does not change: nothing lands until the drain."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = _client(handler)
    await client.observe(identity=IDENTITY, episode=_episode())
    assert client.writes_delivered == 0
    await client.drain()
    assert client.writes_delivered == 1


async def test_the_durable_queue_is_off_unless_a_directory_is_given(tmp_path) -> None:
    """The documented rejection stands; the override is opt-in and scoped."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    assert _client(handler)._outbox is None
    assert _client(handler, durable_queue_dir=tmp_path)._outbox is not None


async def test_a_write_lost_to_an_outage_drains_on_the_next_process(tmp_path) -> None:
    """The whole reason the rejection is overturned for this one host shape."""

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    first = _client(
        down,
        durable_queue_dir=tmp_path,
        is_synchronous_writes=True,
        max_write_retries=1,
    )
    await first.observe(identity=IDENTITY, episode=_episode())
    assert first.writes_failed == 1
    assert list(tmp_path.glob("*.json")), "the episode must survive the failed delivery"

    landed: list[str] = []

    def up(request: httpx.Request) -> httpx.Response:
        landed.append(str(request.url))
        return httpx.Response(200, json={})

    second = _client(up, durable_queue_dir=tmp_path, is_synchronous_writes=True)
    assert await second.replay_durable_queue() == 1
    assert landed[0].endswith("/observe")
    assert list(tmp_path.glob("*.json")) == []


async def test_a_delivered_write_is_not_parked_for_replay(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = _client(handler, durable_queue_dir=tmp_path, is_synchronous_writes=True)
    await client.observe(identity=IDENTITY, episode=_episode())
    assert list(tmp_path.glob("*.json")) == []


async def test_a_rejected_write_is_released_rather_than_replayed_forever(tmp_path) -> None:
    """A 4xx fails identically on every attempt; keeping it makes every drain re-send it."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": []})

    client = _client(handler, durable_queue_dir=tmp_path, is_synchronous_writes=True)
    await client.observe(identity=IDENTITY, episode=_episode())
    assert client.writes_terminal_failed == 1
    assert list(tmp_path.glob("*.json")) == []


async def test_what_is_parked_is_what_would_have_been_sent_and_so_is_redacted(
    tmp_path,
) -> None:
    """The store holds episode content, so it inherits the wire's redaction.

    It gets it by construction rather than by a second pass: the payload handed to the
    queue is the one ``redact_episode_payload`` already returned.
    """
    import json

    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    episode = Episode(
        run_id="support-bot:abc",
        goal="rotate the key",
        steps=(
            StepRecord(
                id="c1",
                name="rotate",
                args={"token": "sk-live-supersecret"},
                status="completed",
                result="rotated sk-live-supersecret",
                declared_sensitivity={"args": {"token": "secret"}},
            ),
        ),
        outcome=TerminalOutcome(is_success=True, total_steps=1, completed_steps=1),
    )
    client = _client(
        down, durable_queue_dir=tmp_path, is_synchronous_writes=True, max_write_retries=1
    )
    await client.observe(identity=IDENTITY, episode=episode)

    parked = list(tmp_path.glob("*.json"))
    assert len(parked) == 1
    text = parked[0].read_text(encoding="utf-8")
    assert "sk-live-supersecret" not in text
    assert json.loads(text)["endpoint"] == "/observe"
