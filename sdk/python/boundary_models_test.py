import json
from types import SimpleNamespace
from urllib.parse import quote, urlencode

from hyperstruck.api_client import ApiClient
from hyperstruck.models.decline_reason import DeclineReason
from hyperstruck.models.decline_request import DeclineRequest
from hyperstruck.models.distill_outcome_model import DistillOutcomeModel
from hyperstruck.models.distill_request import DistillRequest
from hyperstruck.models.episode_model import EpisodeModel
from hyperstruck.models.observe_request import ObserveRequest
from hyperstruck.models.outcome_model import OutcomeModel
from hyperstruck.models.reinforce_request import ReinforceRequest
from hyperstruck.models.resolve_purpose import ResolvePurpose
from hyperstruck.models.resolve_request import ResolveRequest


def test_boundary_models_keep_agent_name_wire_key() -> None:
    for model in (
        DeclineRequest,
        DistillRequest,
        ObserveRequest,
        ReinforceRequest,
        ResolveRequest,
    ):
        assert model.attribute_map["agent_name"] == "agent_name"
        assert "agent_id" not in model.attribute_map


def test_boundary_models_accept_already_snake_case_inputs() -> None:
    episode = EpisodeModel(
        run_id="support-agent:run-1",
        goal="Finish the task.",
        steps=[],
        outcome=OutcomeModel(
            is_success=True,
            total_steps=0,
            completed_steps=0,
            failed_steps=0,
        ),
    )
    requests = (
        DeclineRequest(
            agent_name="support-agent",
            run_id="support-agent:run-1",
            reason=DeclineReason.NO_TOOL_CALLS,
            is_delivered=True,
        ),
        DistillRequest(
            agent_name="support-agent",
            run_id="distill:review-lessons",
            goal="Extract review lessons.",
            evidence=[],
            outcome=DistillOutcomeModel(is_success=True, summary="done"),
            max_learnings=3,
        ),
        ObserveRequest(agent_name="support-agent", episode=episode),
        ReinforceRequest(
            agent_name="support-agent",
            episode=episode,
            is_org_promotion_allowed=False,
        ),
        ResolveRequest(
            agent_name="support-agent",
            run_id="support-agent:run-1",
            goal="Use prior learnings.",
            max_learnings=3,
            resolve_purpose=ResolvePurpose.EXPLICIT_RECALL,
        ),
    )

    for request in requests:
        payload = request.to_dict()
        assert payload["agent_name"] == "support-agent"
        assert "agent_id" not in payload

    assert requests[-1].to_dict()["resolve_purpose"] is ResolvePurpose.EXPLICIT_RECALL

    wire = ApiClient().sanitize_for_serialization(requests[-1])
    assert json.loads(json.dumps(wire))["resolve_purpose"] == "explicit_recall"


def test_resolve_purpose_deserializes_as_a_closed_enum() -> None:
    client = ApiClient()
    response = SimpleNamespace(
        data=json.dumps(
            {
                "agent_name": "support-agent",
                "run_id": "support-agent:run-1",
                "goal": "Use prior learnings.",
                "resolve_purpose": "agent_loop",
            }
        )
    )

    request = client.deserialize(response, "ResolveRequest")
    assert request.resolve_purpose is ResolvePurpose.AGENT_LOOP


def test_an_unknown_enum_value_falls_back_to_the_raw_string() -> None:
    """A client pinned to today's SDK must keep working when a later release adds a member.
    Raising here would lose the whole response over one unrecognised field."""
    client = ApiClient()
    response = SimpleNamespace(
        data=json.dumps(
            {
                "agent_name": "support-agent",
                "run_id": "support-agent:run-1",
                "goal": "Use prior learnings.",
                "resolve_purpose": "a_purpose_this_client_has_never_heard_of",
            }
        )
    )

    request = client.deserialize(response, "ResolveRequest")
    assert request.resolve_purpose == "a_purpose_this_client_has_never_heard_of"


def test_a_closed_enum_serialises_as_its_value_in_a_query_or_path_parameter() -> None:
    """The body path is safe because json.dumps reads the underlying str, so a body test passes
    whether or not __str__ is overridden. A query or path parameter is not: the client's
    primitive-type check lets a str subclass through untouched, and urlencode and quote then call
    str() on it. Without the override that yields 'ResolvePurpose.AGENT_LOOP'."""
    purpose = ResolvePurpose.AGENT_LOOP

    assert str(purpose) == "agent_loop"
    assert urlencode([("resolve_purpose", purpose)]) == "resolve_purpose=agent_loop"
    assert quote(str(purpose)) == "agent_loop"
    assert (
        json.dumps({"resolve_purpose": purpose}) == '{"resolve_purpose": "agent_loop"}'
    )


def test_every_closed_enum_matches_the_generator_template() -> None:
    """The post-processor in scripts/generate_sdk.sh rewrites each generated enum wholesale, so
    a committed model that does not match the template byte for byte was edited by hand and the
    next regeneration will silently revert it. That is not hypothetical: this file exists because
    a hand patch was reverted by a regeneration once already."""
    import re
    from pathlib import Path

    template = (
        'from enum import Enum\n\n\nclass %s(str, Enum):\n'
        '    """The closed set of values this field may take."""\n\n'
        "    __str__ = str.__str__\n\n"
        "%s\n"
    )
    member = re.compile(r'^    ([A-Z][A-Z0-9_]*) = ("[^"]*")$', re.MULTILINE)

    models = Path(__file__).parent / "hyperstruck" / "models"
    checked = 0
    for path in sorted(models.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "The closed set of values this field may take." not in text:
            continue
        name = re.search(r"^class (\w+)\(str, Enum\):", text, re.MULTILINE)
        assert name, f"{path.name} carries the docstring but not the generated class line"
        members = member.findall(text)
        assert members, f"{path.name} has no members at the generated indent"
        expected = template % (
            name.group(1),
            "\n".join(f"    {key} = {value}" for key, value in members),
        )
        assert text == expected, f"{path.name} differs from what the generator would emit"
        checked += 1

    # Against the contract rather than a hardcoded number, so adding an enum to the API does not
    # fail this test, while generating one fewer model than the schema declares still does. This
    # is the same comparison the generator's own post-processing guard makes.
    spec = json.loads(
        (Path(__file__).parent.parent.parent / "openapi.json").read_text(encoding="utf-8")
    )
    declared = sum(
        1
        for schema in spec["components"]["schemas"].values()
        if isinstance(schema, dict) and "enum" in schema
    )
    assert checked == declared, f"{declared} enum schemas declared, {checked} models generated"
