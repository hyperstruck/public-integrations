import json
from types import SimpleNamespace

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
