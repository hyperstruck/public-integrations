"""HostedLearningClient: auth, resolve deadline/fail-path, async writes, retry."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from hyperstruck._wire import (
    Obligation,
    ObligationClosureResult,
    ObligationDue,
    ObligationParty,
    Episode,
    EvidenceItem,
    DistillOutcome,
    ReportedObligationOutcome,
    StepRecord,
    TerminalOutcome,
)
from hyperstruck.client import (
    DEFAULT_RECALL_TIMEOUT,
    DEFAULT_RESOLVE_TIMEOUT,
    HostedLearningClient,
    MAX_LOGGED_VALIDATION_ERRORS,
    MAX_VALIDATION_CAUSE_CHARS,
    ResolvePurpose,
)
from hyperstruck.env import RESOLVE_TIMEOUT_ENV
from hyperstruck.identity import AgentIdentity

IDENTITY = AgentIdentity(agent_name="support-bot", org_id="org-1")


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
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return HostedLearningClient(api_key="k", http_client=http, **kwargs)


def test_non_https_base_url_rejected() -> None:
    with pytest.raises(ValueError, match="https"):
        HostedLearningClient(api_key="k", base_url="http://api.example.com")


def test_localhost_http_allowed() -> None:
    client = HostedLearningClient(api_key="k", base_url="http://localhost:8000")
    assert client._base_url == "http://localhost:8000"


def test_the_declared_host_reaches_the_user_agent() -> None:
    """The server's adoption gate reads the host out of this string.

    Version alone cannot answer whether a receipt can exist: that is a property of the
    editor, and Cursor at the newest version sends an identical string while keeping no
    record of what it accepted. Without the host segment the gate reads a fleet that can
    report nothing as fully adopted.
    """
    client = HostedLearningClient(api_key="k", client_host="claude-code")

    # Present as its own segment rather than last: the capability declaration follows it
    # now, and the gate reads `host=` wherever in the parenthesised list it sits.
    agent = client._headers["User-Agent"]
    assert "(host=claude-code;" in agent or agent.endswith("(host=claude-code)")


def test_a_client_that_declares_no_host_leaves_the_user_agent_unchanged() -> None:
    client = HostedLearningClient(api_key="k")

    assert "host=" not in client._headers["User-Agent"]


def test_a_hostile_host_string_cannot_forge_a_capable_looking_agent() -> None:
    """The host is an argument, so it is sanitised rather than trusted verbatim."""
    client = HostedLearningClient(api_key="k", client_host="cursor) (host=claude-code")

    agent = client._headers["User-Agent"]
    # The whole point: the hostile string was flattened, so it can never be read as the
    # host it was trying to impersonate, wherever the segment sits in the list.
    assert "host=cursorhostclaude-code" in agent
    assert "host=claude-code;" not in agent
    assert "host=claude-code)" not in agent


def test_missing_api_key_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HYPERSTRUCK_API_KEY", raising=False)
    monkeypatch.delenv("HYPER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        HostedLearningClient()


@pytest.mark.parametrize(
    ("passed", "env_value", "expected"),
    [
        (7.5, None, 7.5),
        (7.5, "99", 7.5),
        (None, None, DEFAULT_RESOLVE_TIMEOUT),
        (None, "12.5", 12.5),
        (None, "nonsense", DEFAULT_RESOLVE_TIMEOUT),
    ],
)
def test_resolve_deadline_resolution(
    monkeypatch: pytest.MonkeyPatch, passed, env_value, expected
) -> None:
    if env_value is None:
        monkeypatch.delenv(RESOLVE_TIMEOUT_ENV, raising=False)
    else:
        monkeypatch.setenv(RESOLVE_TIMEOUT_ENV, env_value)

    def _ok(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    kwargs = {} if passed is None else {"resolve_timeout": passed}
    assert _client(_ok, **kwargs)._resolve_timeout == expected


async def test_resolve_applies_its_deadline_to_a_slow_boundary() -> None:
    """The budget must reach asyncio.wait_for, not merely be stored on the client."""

    async def never_answers(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, json={})

    client = _client(never_answers, resolve_timeout=0.05)
    with pytest.raises(TimeoutError):
        await client.resolve(
            identity=AgentIdentity(agent_name="a"), run_id="r", goal="g"
        )
    await client.aclose()


def test_recall_budget_exceeds_the_inline_one() -> None:
    """A prefetched or explicit recall cannot share the inline model-call budget."""
    assert DEFAULT_RECALL_TIMEOUT > DEFAULT_RESOLVE_TIMEOUT


async def test_resolve_returns_bound_context() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200, json={"injected_text": "L", "offered_learning_ids": ["a", "b"]}
        )

    client = _client(handler)
    ctx = await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert ctx.injected_text == "L"
    assert ctx.offered_learning_ids == ("a", "b")
    assert seen["path"] == "/resolve"
    assert seen["auth"] == "Bearer k"
    await client.aclose()


@pytest.mark.parametrize(
    ("resolve_purpose", "expected_wire_value"),
    [
        (ResolvePurpose.AGENT_LOOP, None),
        (ResolvePurpose.EXPLICIT_RECALL, ResolvePurpose.EXPLICIT_RECALL.value),
    ],
)
async def test_resolve_purpose_changes_the_wire_payload(
    resolve_purpose: ResolvePurpose, expected_wire_value: str | None
) -> None:
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={})

    client = _client(handler)
    await client.resolve(
        identity=IDENTITY,
        run_id="r1",
        goal="g",
        resolve_purpose=resolve_purpose,
    )

    assert bodies[0].get("resolve_purpose") == expected_wire_value
    assert ("resolve_purpose" in bodies[0]) is (expected_wire_value is not None)
    await client.aclose()


async def test_resolve_carries_the_fact_block_separately_from_the_advice() -> None:
    """The two blocks are placeable independently, so the client must not merge them."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "injected_text": "L",
                "injected_facts_text": "Acme Corp:\n- region: eu-west-1",
                "offered_learning_ids": ["a"],
                "offered_claim_ids": ["claim-region"],
            },
        )

    client = _client(handler)
    ctx = await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert ctx.injected_text == "L"
    assert "eu-west-1" in ctx.injected_facts_text
    assert ctx.offered_claim_ids == ("claim-region",)
    await client.aclose()


async def test_a_server_that_serves_no_facts_leaves_the_fact_fields_empty() -> None:
    """Every deployment before this lane, and every agent holding no claims."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"injected_text": "L", "offered_learning_ids": ["a"]}
        )

    client = _client(handler)
    ctx = await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert ctx.injected_facts_text is None
    assert ctx.offered_claim_ids == ()
    await client.aclose()


async def test_resolve_carries_the_obligation_block_as_a_third_placeable_half() -> None:
    """A third block, and the ids behind it are not the ids inside it.

    ``offered_obligation_ids`` names what the shelf admitted; the block carries what fit its token
    budget. A client that assumed the two matched would report an obligation as shown when it was
    only considered.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "injected_text": "L",
                "injected_obligations_text": "1. [overdue 2 days] send the migration plan",
                "offered_learning_ids": ["a"],
                "offered_obligation_ids": ["i-1", "i-2"],
            },
        )

    client = _client(handler)
    ctx = await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert "migration plan" in ctx.injected_obligations_text
    assert ctx.offered_obligation_ids == ("i-1", "i-2")
    # Not merged into either of the other two halves.
    assert "migration plan" not in ctx.injected_text
    assert ctx.injected_facts_text is None
    await client.aclose()


async def test_a_server_with_no_obligation_shelf_leaves_the_block_empty() -> None:
    """Every deployment before this lane, and every agent that owes nothing due."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"injected_text": "L", "offered_learning_ids": ["a"]}
        )

    client = _client(handler)
    ctx = await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert ctx.injected_obligations_text is None
    assert ctx.offered_obligation_ids == ()
    await client.aclose()


async def test_the_obligation_request_controls_are_omitted_unless_a_caller_asks() -> None:
    """The boundary forbids unknown request fields, so sending null is not free.

    A server that predates the obligation block rejects the whole call over four keys it does not
    model, which would break every caller of a newer client against an older deployment. Omission
    is what keeps this additive.
    """
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={})

    client = _client(handler)
    await client.resolve(identity=IDENTITY, run_id="r1", goal="g")
    assert not (
        {"as_of", "timezone", "max_obligations", "obligation_horizon_days"}
        & set(bodies[0])
    )

    await client.resolve(
        identity=IDENTITY,
        run_id="r1",
        goal="g",
        as_of=datetime(2026, 8, 27, 9, 0, tzinfo=timezone(timedelta(hours=10))),
        timezone="Australia/Sydney",
        max_obligations=3,
        obligation_horizon_days=7,
    )
    assert bodies[1]["as_of"] == "2026-08-27T09:00:00+10:00"
    assert bodies[1]["timezone"] == "Australia/Sydney"
    assert bodies[1]["max_obligations"] == 3
    assert bodies[1]["obligation_horizon_days"] == 7
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
        return httpx.Response(
            202, json={"status": "accepted", "run_id": "support-bot:abc"}
        )

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


async def test_distill_posts_flat_body_in_background() -> None:
    bodies = []
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        paths.append(request.url.path)
        bodies.append(json.loads(request.content))
        return httpx.Response(
            202, json={"status": "accepted", "run_id": "distill:pm-1"}
        )

    client = _client(handler)
    await client.distill(
        identity=IDENTITY,
        run_id="distill:pm-1",
        goal="extract learnings",
        evidence=(
            EvidenceItem(id="e1", content="a" * 300, role="contrast", status="failed"),
            EvidenceItem(id="e2", content="b" * 300, role="support"),
        ),
        outcome=DistillOutcome(is_success=True, summary="done"),
        evaluation="root cause differed",
    )
    await client.drain()
    assert client.writes_delivered == 1
    assert paths[0] == "/distill"
    # Flat body (agent_id from identity), not wrapped like observe/reinforce.
    assert bodies[0]["agent_name"] == "support-bot"
    assert bodies[0]["run_id"] == "distill:pm-1"
    assert len(bodies[0]["evidence"]) == 2
    # Omit unless overridden so older APIs do not 422 unknown keys.
    assert "max_learnings" not in bodies[0]
    await client.aclose()


async def test_distill_includes_max_learnings_only_when_set() -> None:
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        bodies.append(json.loads(request.content))
        return httpx.Response(
            202, json={"status": "accepted", "run_id": "distill:pm-1"}
        )

    client = _client(handler)
    evidence = (
        EvidenceItem(id="e1", content="a" * 300, role="contrast", status="failed"),
        EvidenceItem(id="e2", content="b" * 300, role="support"),
    )
    await client.distill(
        identity=IDENTITY,
        run_id="distill:pm-1",
        goal="extract learnings",
        evidence=evidence,
        max_learnings=15,
    )
    await client.drain()
    assert bodies[0]["max_learnings"] == 15
    await client.aclose()


async def test_the_client_admits_the_single_item_corpus_the_server_admits() -> None:
    """A price list, a policy, a single contract: one item is a legitimate fact corpus.

    The client refused what the server accepts, so the ergonomic surface was stricter than the API
    it wraps and a caller hit a ValueError for a request that would have succeeded.
    """
    client = _client(lambda request: httpx.Response(202, json={"status": "accepted"}))

    # Writes are fire-and-forget, so what is asserted is that the call-site guard does not refuse
    # it; whether the send lands is the delivery tests' subject, not this one's.
    await client.distill(
        identity=IDENTITY,
        run_id="distill:one-item",
        goal="g",
        evidence=(EvidenceItem(id="e1", content="Meridian Books, plan: enterprise."),),
    )


async def test_distill_raises_on_deterministic_client_errors() -> None:
    # Fire-and-forget delivery would swallow the server's 400, so the deterministic
    # mistakes must fail loud at the call site instead of losing the job silently.
    sent = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["count"] += 1
        return httpx.Response(202, json={"status": "accepted"})

    client = _client(handler)
    ok_evidence = (
        EvidenceItem(id="e1", content="a" * 300, role="contrast", status="failed"),
        EvidenceItem(id="e2", content="b" * 300, role="support"),
    )
    with pytest.raises(ValueError, match="distill:"):
        await client.distill(
            identity=IDENTITY, run_id="pm-1", goal="g", evidence=ok_evidence
        )
    with pytest.raises(ValueError, match="at least 1"):
        await client.distill(
            identity=IDENTITY,
            run_id="distill:pm-1",
            goal="g",
            evidence=(),
        )
    with pytest.raises(ValueError, match="max_learnings"):
        await client.distill(
            identity=IDENTITY,
            run_id="distill:pm-1",
            goal="g",
            evidence=ok_evidence,
            max_learnings=0,
        )
    with pytest.raises(ValueError, match="max_learnings"):
        await client.distill(
            identity=IDENTITY,
            run_id="distill:pm-1",
            goal="g",
            evidence=ok_evidence,
            max_learnings=51,
        )
    await client.drain()
    assert sent["count"] == 0  # nothing dispatched for the rejected calls
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
    assert client.writes_terminal_failed == 0  # a 503 is transient, not terminal
    assert client.writes_delivered == 0
    await client.aclose()


async def test_terminal_4xx_write_fails_fast_and_is_flagged_terminal() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(422, json={"detail": "invalid episode"})

    client = _client(handler, max_write_retries=3, retry_backoff=0.0)
    await client.reinforce(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert attempts["n"] == 1  # a 4xx fails identically on retry, so no retries
    assert client.writes_failed == 1
    assert client.writes_terminal_failed == 1
    assert client.last_write_error == "HTTP 422"
    await client.aclose()


async def test_422_cause_names_the_field_without_carrying_its_value() -> None:
    rejected_goal = "the private prompt text the log must never hold"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": [
                    {
                        "type": "string_too_long",
                        "loc": ["body", "episode", "goal"],
                        "msg": "String should have at most 8000 characters",
                        "input": rejected_goal,
                    }
                ]
            },
        )

    client = _client(handler, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error == "HTTP 422 (body.episode.goal:string_too_long)"
    assert rejected_goal not in client.last_write_error
    await client.aclose()


async def test_422_cause_is_bounded_when_every_step_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": [
                    {"type": "string_too_long", "loc": ["body", "episode", "steps", n]}
                    for n in range(50)
                ]
            },
        )

    client = _client(handler, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error is not None
    named = client.last_write_error.split("(", 1)[1].rstrip(")").split(", ")
    assert len(named) == MAX_LOGGED_VALIDATION_ERRORS
    await client.aclose()


async def test_422_cause_refuses_anything_that_is_not_a_schema_token() -> None:
    smuggled = "refactor the auth module and delete the customer table"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": [{"type": smuggled, "loc": ["body", smuggled]}]},
        )

    client = _client(handler, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error == "HTTP 422 (body.?:?)"
    await client.aclose()


async def test_422_cause_is_length_bounded_even_for_one_huge_location() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": [{"type": "x", "loc": ["body"] + ["field"] * 500}]},
        )

    client = _client(handler, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert len(client.last_write_error or "") <= MAX_VALIDATION_CAUSE_CHARS + len(
        "HTTP 422"
    )
    await client.aclose()


async def test_422_with_an_unparseable_body_keeps_the_bare_status_cause() -> None:
    def not_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, content=b"<html>gateway</html>")

    client = _client(not_json, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error == "HTTP 422"
    await client.aclose()


async def test_422_with_a_non_object_body_keeps_the_bare_status_cause() -> None:
    def listed(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json=["not", "an", "object"])

    client = _client(listed, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error == "HTTP 422"
    await client.aclose()


async def test_422_with_a_string_detail_keeps_the_bare_status_cause() -> None:
    # What a hand-raised HTTPException returns, as opposed to a schema rejection.
    def hand_raised(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "invalid episode"})

    client = _client(hand_raised, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error == "HTTP 422"
    await client.aclose()


async def test_non_422_statuses_are_never_annotated() -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": [{"type": "x", "loc": ["body"]}]})

    client = _client(forbidden, max_write_retries=3, retry_backoff=0.0)
    await client.observe(identity=IDENTITY, episode=_episode())
    await client.drain()
    assert client.last_write_error == "HTTP 403"
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
    assert posts.count("/observe") == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_decline_posts_the_terminal_signal() -> None:
    """Await the REAL client, so its signature is pinned, not just a test double.

    The hook awaits this call. A stub with its own async def masks a sync
    implementation entirely, so the only guard that means anything is awaiting the
    real thing.
    """
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        bodies.append((str(request.url), json.loads(request.content)))
        return httpx.Response(202, json={"status": "accepted", "run_id": "r"})

    client = _client(handler)
    await client.decline(
        identity=IDENTITY,
        run_id="support-bot:abc",
        reason="no_tool_calls",
        is_delivered=True,
        source_framework="claude-code",
    )
    await client.drain()

    assert client.writes_delivered == 1
    url, body = bodies[0]
    assert url.endswith("/decline")
    assert body["run_id"] == "support-bot:abc"
    assert body["reason"] == "no_tool_calls"
    assert body["is_delivered"] is True


@pytest.mark.asyncio
async def test_reinforce_puts_the_delivery_report_on_the_wire() -> None:
    """The fields exist to be read server-side, so what matters is that they are sent.

    Omitted rather than defaulted when the caller says nothing: an older server rejects
    an unknown field, and a newer one reads a missing one as "the client did not say",
    which is a third answer and not a synonym for not delivered.
    """
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202, json={"status": "accepted", "run_id": "r"})

    client = _client(handler)
    await client.reinforce(
        identity=IDENTITY,
        episode=_episode(),
        is_delivered=False,
        recall_outcome="resolve_timed_out",
    )
    await client.reinforce(identity=IDENTITY, episode=_episode())
    await client.drain()

    reported, silent = bodies
    assert reported["is_delivered"] is False
    assert reported["recall_outcome"] == "resolve_timed_out"
    assert "is_delivered" not in silent
    assert "recall_outcome" not in silent


@pytest.mark.asyncio
async def test_decline_rejects_a_reason_outside_the_closed_set() -> None:
    """The boundary rejects an unknown reason; fail in the caller rather than on the wire."""
    client = _client(lambda request: httpx.Response(202, json={}))
    with pytest.raises(ValueError, match="reason must be one of"):
        await client.decline(identity=IDENTITY, run_id="r", reason="because")


async def test_hold_obligation_posts_to_the_agent_and_returns_the_typed_outcome() -> (
    None
):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(202, json={"id": "int-1", "outcome": "written"})

    client = _client(handler)
    outcome = await client.hold_obligation(
        agent_id="8d6f1a2b-0000-4000-8000-000000000001",
        obligation=Obligation(
            statement="Send the SOC 2 report to Meridian Books",
            owed_by=ObligationParty(role="AE"),
            owed_to=ObligationParty(entity="Meridian Books"),
            due=ObligationDue(at="2026-08-29T00:00:00+10:00", tz="Australia/Sydney"),
        ),
    )
    assert seen["path"] == "/agents/8d6f1a2b-0000-4000-8000-000000000001/obligations"
    assert seen["body"]["owed_to"] == {"entity": "Meridian Books"}
    assert outcome.is_held and outcome.id == "int-1"


# -- loop-level obligation closure ----------------------------------------------


_CLOSED = {
    "status": "accepted",
    "run_id": "support-bot:abc",
    "obligation_closures": [
        {"id": "o1", "disposition": "applied", "status": "kept"},
        {"id": "o2", "disposition": "not_offered", "status": None},
    ],
}


def _kept(obligation_id: str = "o1") -> ReportedObligationOutcome:
    return ReportedObligationOutcome(
        id=obligation_id, outcome="kept", kept_basis="reported"
    )


async def test_reinforce_sends_the_reported_outcomes_and_returns_a_result_per_id() -> None:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202, json=_CLOSED)

    client = _client(handler, is_synchronous_writes=True)
    result = await client.reinforce(
        identity=IDENTITY,
        episode=_episode(),
        obligation_outcomes=[
            _kept("o1"),
            ReportedObligationOutcome(
                id="o2", outcome="dropped", dropped_reason="no_longer_applies"
            ),
        ],
    )
    assert bodies[0]["obligation_outcomes"] == [
        {"id": "o1", "outcome": "kept", "kept_basis": "reported"},
        {"id": "o2", "outcome": "dropped", "dropped_reason": "no_longer_applies"},
    ]
    assert result.obligation_closures == (
        ObligationClosureResult(id="o1", disposition="applied", status="kept"),
        ObligationClosureResult(id="o2", disposition="not_offered", status=None),
    )
    # "applied" is the only success; "busy" the only thing worth sending again.
    assert result.obligation_closures[0].is_applied
    assert not result.obligation_closures[0].is_retryable
    assert not result.obligation_closures[1].is_retryable
    await client.aclose()


async def test_a_reinforce_reporting_nothing_omits_the_field_entirely() -> None:
    """Omitted, not sent as an empty list.

    The overwhelmingly common write reports no closure, and a key in every body for the
    sake of the rare call that uses one is a cost paid by every caller.
    """
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202, json={"status": "accepted"})

    client = _client(handler, is_synchronous_writes=True)
    await client.reinforce(identity=IDENTITY, episode=_episode())
    assert "obligation_outcomes" not in bodies[0]
    await client.aclose()


async def test_decline_carries_the_outcomes_and_hands_back_their_results() -> None:
    """A turn that resolved an obligation and learned nothing still resolved an obligation.

    ``decline`` returned nothing at all before this, so a host closing an obligation on a
    declined turn had no way to learn whether the close landed.
    """
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202, json=_CLOSED)

    client = _client(handler, is_synchronous_writes=True)
    result = await client.decline(
        identity=IDENTITY,
        run_id="support-bot:abc",
        reason="no_tool_calls",
        obligation_outcomes=[_kept()],
    )
    assert bodies[0]["obligation_outcomes"] == [
        {"id": "o1", "outcome": "kept", "kept_basis": "reported"}
    ]
    assert [closure.id for closure in result.obligation_closures] == ["o1", "o2"]
    # A declined turn was never credited, so there is no presence verdict to read back.
    assert result.presence_outcomes == ()
    await client.aclose()


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"outcome": "kept"}, "kept_basis"),
        ({"outcome": "dropped"}, "dropped_reason"),
        ({"outcome": "deferred", "kept_basis": "reported"}, "kept or dropped"),
    ],
)
def test_an_incoherent_reported_outcome_is_refused_before_it_reaches_the_wire(
    kwargs: dict, match: str
) -> None:
    """Refused here rather than left to the boundary's 422.

    A write is fire-and-forget by default, so a rejected body would be swallowed with
    nothing said and the host would believe it had closed a row that is still open.
    """
    with pytest.raises(ValueError, match=match):
        ReportedObligationOutcome(id="o1", **kwargs)


async def test_a_disposition_this_client_does_not_know_is_still_carried() -> None:
    """Read as sent rather than checked against a vocabulary.

    A disposition the boundary grows later is still its answer about that id, and refusing
    it here would turn a server that gained a word into a client reporting the close as
    never having been judged.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                "status": "accepted",
                "obligation_closures": [
                    {"id": "o1", "disposition": "deferred_to_operator", "status": "open"}
                ],
            },
        )

    client = _client(handler, is_synchronous_writes=True)
    result = await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept()]
    )
    assert result.obligation_closures == (
        ObligationClosureResult(
            id="o1", disposition="deferred_to_operator", status="open"
        ),
    )
    assert not result.obligation_closures[0].is_applied
    await client.aclose()


@pytest.mark.parametrize(
    "raw",
    [
        {"obligation_closures": "applied"},
        {"obligation_closures": [None, 3, {"id": "o1"}, {"disposition": "applied"}]},
        {},
    ],
)
async def test_a_closure_list_this_client_cannot_read_comes_back_empty(
    raw: dict,
) -> None:
    """Empty rather than raising, on every shape a deployment could answer with.

    This runs on the write path of a host's own turn. A body one field short of what was
    expected must not become an exception the host sees.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"status": "accepted", **raw})

    client = _client(handler, is_synchronous_writes=True)
    result = await client.reinforce(identity=IDENTITY, episode=_episode())
    assert result.obligation_closures == ()
    await client.aclose()


async def test_a_busy_closure_is_the_one_a_caller_may_send_again() -> None:
    """The positive case for ``is_retryable``, which is the only reason it exists.

    The two words are deliberately different: a caller that retries a ``refused`` loops for
    ever, and one that abandons a ``busy`` loses the close. Asserting only that the others
    are not retryable leaves the distinction untested, which is the half that costs.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                "status": "accepted",
                "obligation_closures": [
                    {"id": "o1", "disposition": "busy", "status": None},
                    {"id": "o2", "disposition": "refused", "status": "open"},
                ],
            },
        )

    client = _client(handler, is_synchronous_writes=True)
    result = await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept()]
    )
    busy, refused = result.obligation_closures
    assert busy.is_retryable and not busy.is_applied
    assert not refused.is_retryable and not refused.is_applied
    await client.aclose()


def _busy_then(*answers: str):
    """A handler answering o1 busy first, then each of ``answers`` in turn; records bodies."""
    bodies: list[dict] = []
    replies = ["busy", *answers]

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        reply = replies[min(len(bodies), len(replies)) - 1]
        closures = [{"id": "o1", "disposition": reply, "status": None}]
        if len(bodies) == 1:
            closures.append({"id": "o2", "disposition": "applied", "status": "kept"})
        return httpx.Response(
            202, json={"status": "accepted", "obligation_closures": closures}
        )

    return handler, bodies


async def test_a_busy_close_is_sent_again_alone_and_its_answer_replaces_busy() -> None:
    handler, bodies = _busy_then("applied")
    client = _client(handler, is_synchronous_writes=True, retry_backoff=0.0)
    result = await client.reinforce(
        identity=IDENTITY,
        episode=_episode(),
        obligation_outcomes=[_kept("o1"), _kept("o2")],
    )
    assert [o["id"] for o in bodies[1]["obligation_outcomes"]] == ["o1"]
    assert [(c.id, c.disposition) for c in result.obligation_closures] == [
        ("o1", "applied"),
        ("o2", "applied"),
    ]
    await client.aclose()


async def test_a_fire_and_forget_caller_still_has_its_busy_close_sent_again() -> None:
    """The caller that can never read ``busy`` is the one that needs the resend most."""
    handler, bodies = _busy_then("applied")
    client = _client(handler, retry_backoff=0.0)
    await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept("o1")]
    )
    await client.drain()
    assert len(bodies) == 2
    assert [o["id"] for o in bodies[1]["obligation_outcomes"]] == ["o1"]
    await client.aclose()


async def test_a_busy_close_reported_under_another_spelling_of_its_id_is_still_resent() -> None:
    """The boundary echoes a UUID lower-case and hyphenated, whatever the caller sent."""
    raw = "7F9C1E2A4B6D4E8FA0B1C2D3E4F5A6B7"
    echoed = "7f9c1e2a-4b6d-4e8f-a0b1-c2d3e4f5a6b7"
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        reply = "busy" if len(bodies) == 1 else "applied"
        return httpx.Response(
            202,
            json={"obligation_closures": [{"id": echoed, "disposition": reply}]},
        )

    client = _client(handler, is_synchronous_writes=True, retry_backoff=0.0)
    result = await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept(raw)]
    )
    assert [o["id"] for o in bodies[1]["obligation_outcomes"]] == [raw]
    assert result.obligation_closures[0].is_applied
    await client.aclose()


async def test_a_resend_answering_under_another_spelling_still_replaces_busy() -> None:
    """The busy answer and the resend's answer may spell the same UUID differently."""
    first = "7F9C1E2A4B6D4E8FA0B1C2D3E4F5A6B7"
    second = "7f9c1e2a-4b6d-4e8f-a0b1-c2d3e4f5a6b7"
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        closure = (
            {"id": first, "disposition": "busy"}
            if len(bodies) == 1
            else {"id": second, "disposition": "applied"}
        )
        return httpx.Response(202, json={"obligation_closures": [closure]})

    client = _client(handler, is_synchronous_writes=True, retry_backoff=0.0)
    result = await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept(second)]
    )
    assert len(bodies) == 2
    assert result.obligation_closures[0].is_applied
    await client.aclose()


async def test_a_close_that_stays_busy_is_sent_again_a_bounded_number_of_times() -> None:
    handler, bodies = _busy_then()
    client = _client(handler, is_synchronous_writes=True, retry_backoff=0.0)
    result = await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept("o1")]
    )
    assert len(bodies) == 4
    assert result.obligation_closures[0].is_retryable
    await client.aclose()


async def test_a_closure_whose_status_is_absent_reads_as_null_not_as_missing() -> None:
    """An omitted key and an explicit null are the same answer: no row this call read.

    The boundary sends null today. A deployment that omits the key instead must not leave a
    host holding an attribute that is absent rather than None, because the two are different
    to read and only one of them is documented.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                "status": "accepted",
                "obligation_closures": [
                    {"id": "o1", "disposition": "not_found"},
                    {"id": "o2", "disposition": "applied", "status": 7},
                ],
            },
        )

    client = _client(handler, is_synchronous_writes=True)
    result = await client.reinforce(
        identity=IDENTITY, episode=_episode(), obligation_outcomes=[_kept()]
    )
    assert [closure.status for closure in result.obligation_closures] == [None, None]
    await client.aclose()


async def test_an_empty_list_of_outcomes_is_the_same_as_reporting_none() -> None:
    """Passed explicitly, which is what a host with a conditional list actually sends.

    A caller building the list from a filter hands over ``[]`` on the common turn, and that
    must not put a key in the body any more than omitting the argument does.
    """
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202, json={"status": "accepted"})

    client = _client(handler, is_synchronous_writes=True)
    await client.reinforce(identity=IDENTITY, episode=_episode(), obligation_outcomes=[])
    await client.decline(
        identity=IDENTITY,
        run_id="support-bot:abc",
        reason="no_tool_calls",
        obligation_outcomes=[],
    )
    assert all("obligation_outcomes" not in body for body in bodies)
    await client.aclose()


def test_the_learning_client_port_s_member_set_is_pinned() -> None:
    """A member added to a runtime-checkable Protocol breaks isinstance for every implementer.

    ``LearningClient`` is structural, so nobody inherits from it and nobody gets a default: a
    new member looks additive and is not. It joins ``__protocol_attrs__``, and
    ``isinstance(their_client, LearningClient)`` then reads False for the identical
    population, which is the only thing ``runtime_checkable`` exists to make mean something.
    Growing a method therefore belongs on its own Protocol with this one left frozen, and
    this list is where that decision gets made rather than discovered by a customer.

    A parameter added to an existing member does not change this set, which is why rule 6's
    ``obligation_outcomes`` moved the minor without touching it.

    ``decline`` is deliberately absent and is a known gap, not an omission by this test: the
    seat calls it, the TypeScript ``LearningClient`` declares it, and adding it here is the
    breaking change described above rather than a two-line fix.
    """
    import typing

    from hyperstruck.client import LearningClient

    # `__protocol_attrs__` only exists from Python 3.12; the package supports 3.11.
    members = getattr(LearningClient, "__protocol_attrs__", None)
    if members is None:
        members = typing._get_protocol_attrs(LearningClient)
    assert sorted(members) == [
        "aclose",
        "cancel_obligation",
        "close_obligation",
        "distill",
        "drain",
        "hold_obligation",
        "observe",
        "reinforce",
        "resolve",
        "writes_delivered",
        "writes_duplicated",
        "writes_failed",
    ]
