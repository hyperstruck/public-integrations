"""The hosted answer through the hand-written client: one level now, more of the same answer later."""

from __future__ import annotations

import json

import httpx

from hyperstruck.client import HostedLearningClient

_AGENT = "11111111-1111-4111-8111-111111111111"


def _client(handler) -> HostedLearningClient:
    return HostedLearningClient(
        api_key="k",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _body(detail: str, **extra: object) -> dict[str, object]:
    return {
        "answer_id": "a1",
        "detail": detail,
        "answer": "Week 5.",
        "more": {},
        **extra,
    }


async def test_an_answer_is_asked_for_at_one_level_and_comes_back_at_it() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(
            method=request.method,
            path=request.url.path,
            body=json.loads(request.content),
            key=request.headers.get("idempotency-key"),
        )
        return httpx.Response(200, json=_body("findings", findings=[]))

    client = _client(handler)
    got = await client.answer(
        agent_id=_AGENT,
        question="Where is Coil up to?",
        detail="findings",
        idempotency_key="k1",
    )
    await client.aclose()

    assert seen == {
        "method": "POST",
        "path": f"/agents/{_AGENT}/answer",
        "body": {"question": "Where is Coil up to?", "detail": "findings"},
        "key": "k1",
    }
    assert got.body == _body("findings", findings=[])


async def test_more_fetches_the_same_answer_at_a_higher_level_from_its_own_link() -> (
    None
):
    link = f"/agents/{_AGENT}/answers/a1?detail=claims"
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (request.method, str(request.url.copy_with(scheme=None, host=None)))
        )
        if request.method == "POST":
            return httpx.Response(200, json=_body("answer", more={"claims": link}))
        return httpx.Response(200, json=_body("claims", claims={}))

    client = _client(handler)
    first = await client.answer(agent_id=_AGENT, question="q")
    later = await first.more("claims")
    await client.aclose()

    assert later.body == _body("claims", claims={})
    assert seen[-1][0] == "GET" and seen[-1][1].endswith(link)


async def test_more_refuses_a_level_the_answer_does_not_offer_and_says_why() -> None:
    import pytest

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=_body("answer", more=None, more_unavailable_reason="not_stored")
        )

    client = _client(handler)
    unstored = await client.answer(agent_id=_AGENT, question="q")
    with pytest.raises(ValueError, match="not_stored"):
        await unstored.more("claims")
    await client.aclose()


def test_the_typed_answer_body_carries_every_field_the_published_answer_does() -> None:
    """A field the contract adds and the TypedDict omits is refused by a type checker in every typed host.

    Compared against the committed contract, not a list kept here, so the next field fails this rather
    than drifting silently. The level bodies are compared the same way against what each level adds.
    """
    import typing
    from pathlib import Path

    from hyperstruck.answers import AnswerBody, ClaimsBody, EverythingBody, FindingsBody

    contract = json.loads(
        (Path(__file__).resolve().parents[3] / "openapi.json").read_text()
    )
    published = set(contract["components"]["schemas"]["AnswerView"]["properties"])
    levels = {
        "findings": set(typing.get_type_hints(FindingsBody))
        - set(typing.get_type_hints(AnswerBody)),
        "claims": set(typing.get_type_hints(ClaimsBody))
        - set(typing.get_type_hints(FindingsBody)),
        "everything": set(typing.get_type_hints(EverythingBody))
        - set(typing.get_type_hints(ClaimsBody)),
    }
    above = set().union(*levels.values())

    assert set(typing.get_type_hints(AnswerBody)) == published - above
    assert set(typing.get_type_hints(EverythingBody)) == published


def test_the_typed_answer_body_admits_null_wherever_the_published_answer_does() -> None:
    """A section whose step did not run is null, so a type checker must make a host guard it."""
    import types
    import typing
    from pathlib import Path

    from hyperstruck.answers import EverythingBody

    properties = json.loads(
        (Path(__file__).resolve().parents[3] / "openapi.json").read_text()
    )["components"]["schemas"]["AnswerView"]["properties"]
    nullable = {
        name
        for name, published in properties.items()
        if {"type": "null"} in published.get("anyOf", [])
    }
    typed = {
        name
        for name, hint in typing.get_type_hints(EverythingBody).items()
        if isinstance(hint, types.UnionType) and type(None) in typing.get_args(hint)
    }

    assert typed == nullable


def test_the_typed_lead_and_support_flags_carry_every_field_the_contract_publishes() -> None:
    """The lead and a support record's flags are typed the way the contract publishes them.

    Read from the committed contract, so a field added there and not typed here fails this.
    """
    import typing
    from pathlib import Path

    from hyperstruck.answers import (
        AnswerLead,
        BulletSupport,
        FindingsBody,
        SupportFlag,
    )

    schemas = json.loads(
        (Path(__file__).resolve().parents[3] / "openapi.json").read_text()
    )["components"]["schemas"]
    for typed in (AnswerLead, BulletSupport, SupportFlag):
        assert set(typing.get_type_hints(typed)) == set(
            schemas[typed.__name__]["properties"]
        ), typed.__name__
    assert typing.get_type_hints(BulletSupport)["flags"] == list[SupportFlag]
    assert typing.get_type_hints(AnswerLead)["support"] is BulletSupport
    assert typing.get_type_hints(FindingsBody)["lead"] == AnswerLead | None


async def test_an_answer_at_the_answer_level_has_no_lead_key_and_the_typed_body_says_so() -> (
    None
):
    """The lead belongs to the findings level up, so the answer level's typed body omits it."""
    import typing

    from hyperstruck.answers import AnswerBody, FindingsBody

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_body("answer"))

    client = _client(handler)
    got = await client.answer(agent_id=_AGENT, question="q")
    await client.aclose()

    assert "lead" not in got.body
    assert "lead" not in typing.get_type_hints(AnswerBody)
    assert "lead" in typing.get_type_hints(FindingsBody)
