"""The claims search through the hand-written client: one safe read, ClaimSearch back."""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args, get_type_hints

import httpx
import pytest

from hyperstruck import claim_search
from hyperstruck.client import HostedLearningClient

_ENTITY = "5f0c2a52-0c3e-4e5f-9a57-1f3a8f0d2b11"
_AGENT = "11111111-1111-4111-8111-111111111111"


def _client(handler) -> HostedLearningClient:
    return HostedLearningClient(
        api_key="k",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _result(**extra: object) -> dict[str, object]:
    return {
        "as_of": "2026-10-15T00:00:00Z",
        "computed_at": "2026-10-15T00:00:01Z",
        "shape": "point",
        "text": "Harlow Freight's fiscal year ends in June.",
        "claims": [],
        "shares_no_word": False,
        "more_matched": 0,
        **extra,
    }


async def test_a_question_is_searched_as_a_plain_read_and_the_result_comes_back() -> (
    None
):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(
            method=request.method,
            path=request.url.path,
            body=json.loads(request.content),
            key=request.headers.get("idempotency-key"),
        )
        return httpx.Response(200, json=_result())

    client = _client(handler)
    got = await client.search_claims(agent_id=_AGENT, question="When does Harlow's year end?")
    await client.aclose()

    assert seen == {
        "method": "POST",
        "path": f"/agents/{_AGENT}/claims/search",
        "body": {"question": "When does Harlow's year end?"},
        "key": None,
    }
    assert got == _result()


async def test_a_search_goes_to_the_claims_search_route_and_the_client_has_no_answer() -> (
    None
):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(
            method=request.method,
            path=request.url.path,
            body=json.loads(request.content),
        )
        return httpx.Response(200, json=_result())

    client = _client(handler)
    got = await client.search_claims(agent_id=_AGENT, question="When does Harlow's year end?")
    await client.aclose()

    assert seen == {
        "method": "POST",
        "path": f"/agents/{_AGENT}/claims/search",
        "body": {"question": "When does Harlow's year end?"},
    }
    assert got == _result()
    assert not hasattr(HostedLearningClient, "answer")


async def test_the_time_and_detail_asked_for_are_sent_and_nothing_else() -> None:
    bodies: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=_result(shape="since"))

    client = _client(handler)
    await client.search_claims(
        agent_id=_AGENT,
        question="What moved?",
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
        since="2026-09-01T00:00:00Z",
        detail="cited",
    )
    await client.aclose()

    assert bodies == [
        {
            "question": "What moved?",
            "as_of": "2026-10-01T00:00:00+00:00",
            "since": "2026-09-01T00:00:00Z",
            "detail": "cited",
        }
    ]


@pytest.mark.parametrize("parameter", ["as_of", "since", "due_before"])
async def test_a_time_with_no_offset_is_refused_naming_the_parameter_and_nothing_is_sent(parameter: str) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json=_result())

    client = _client(handler)
    with pytest.raises(ValueError, match=parameter):
        await client.search_claims(agent_id=_AGENT, question="What moved?", **{parameter: datetime(2026, 9, 1)})
    await client.aclose()

    assert calls == []


async def test_an_entity_asked_about_is_sent_as_the_entity_the_question_is_narrowed_to_and_only_when_given() -> None:
    bodies: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=_result())

    client = _client(handler)
    await client.search_claims(agent_id=_AGENT, question="Who runs it?", entity=_ENTITY)
    await client.search_claims(agent_id=_AGENT, question="Who runs it?")
    await client.aclose()

    assert bodies == [
        {"question": "Who runs it?", "entity": _ENTITY},
        {"question": "Who runs it?"},
    ]


async def test_the_claims_filter_and_the_page_are_sent_as_the_filter_the_search_lists_and_only_when_given() -> (
    None
):
    bodies: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=_result(shape="set", cursor=None))

    client = _client(handler)
    await client.search_claims(
        agent_id=_AGENT,
        question="What is open with Harlow?",
        state="open",
        kind="obligation",
        owner=_ENTITY,
        due_before=datetime(2026, 10, 1, tzinfo=UTC),
        cursor="c1",
        limit=20,
    )
    await client.aclose()

    assert bodies == [
        {
            "question": "What is open with Harlow?",
            "state": "open",
            "kind": "obligation",
            "owner": _ENTITY,
            "due_before": "2026-10-01T00:00:00+00:00",
            "cursor": "c1",
            "limit": 20,
        }
    ]


async def test_a_refusal_is_raised_at_once_and_never_asked_again() -> None:
    """A claims store still being rebuilt answers 409; waiting is the caller's choice."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            409,
            headers={"Retry-After": "3"},
            json={"detail": {"code": "claims_not_replayed"}},
        )

    client = _client(handler)
    with pytest.raises(httpx.HTTPStatusError) as raised:
        await client.search_claims(agent_id=_AGENT, question="Where is Coil up to?")
    await client.aclose()

    assert raised.value.response.status_code == 409
    assert len(calls) == 1


def test_the_client_has_no_retry_or_key_arguments_and_no_stored_answer_call() -> None:
    parameters = set(inspect.signature(HostedLearningClient.search_claims).parameters)

    assert parameters == {
        "self",
        "agent_id",
        "question",
        "entity",
        "as_of",
        "since",
        "detail",
        "state",
        "kind",
        "owner",
        "due_before",
        "cursor",
        "limit",
    }
    assert not hasattr(HostedLearningClient, "_stored_answer")
    assert not hasattr(claim_search, "AnswerBody")


def _published(name: str) -> dict[str, object]:
    path = Path(__file__).resolve().parents[3] / "openapi.json"
    return json.loads(path.read_text())["components"]["schemas"][name]


def test_the_typed_result_carries_exactly_the_fields_the_platform_publishes() -> None:
    """Mutation: add or drop a key on ``ClaimSearch`` and this fails."""
    assert set(get_type_hints(claim_search.ClaimSearch)) == set(
        _published("ClaimSearchOut")["properties"]
    )
    assert not hasattr(claim_search, "AnswerMore"), "the result's sentences are its text"


def test_the_typed_result_marks_nullable_exactly_what_the_platform_does() -> None:
    properties = _published("ClaimSearchOut")["properties"]
    published = {
        name
        for name, spec in properties.items()
        if any(v.get("type") == "null" for v in spec.get("anyOf", []))
    }
    typed = {
        name
        for name, hint in get_type_hints(claim_search.ClaimSearch).items()
        if type(None) in get_args(hint)
    }

    assert typed == published


def test_the_detail_and_shape_literals_match_the_published_enums() -> None:
    assert set(get_args(claim_search.ClaimSearchDetail)) == set(
        _published("ClaimSearchIn")["properties"]["detail"]["enum"]
    )
    assert set(get_args(claim_search.ClaimSearchShape)) == set(
        _published("ClaimSearchOut")["properties"]["shape"]["enum"]
    )


def test_the_search_states_are_the_ones_the_platform_publishes_for_a_claim() -> None:
    """Mutation: name a state the platform does not (``disputed``) and this fails."""
    path = Path(__file__).resolve().parents[3] / "openapi.json"
    parameters = json.loads(path.read_text())["paths"]["/agents/{agent_id}/claims"][
        "get"
    ]["parameters"]
    state = next(p for p in parameters if p["name"] == "state")
    published = next(v["enum"] for v in state["schema"]["anyOf"] if "enum" in v)

    assert set(get_args(claim_search.ClaimSearchState)) == set(published)
