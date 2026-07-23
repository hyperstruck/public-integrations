import importlib.util
from pathlib import Path


def _model_class(module_name: str, class_name: str):
    path = Path(__file__).parent / "hyperstruck" / "models" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


DistillRequest = _model_class("distill_request", "DistillRequest")
ObserveRequest = _model_class("observe_request", "ObserveRequest")
ReinforceRequest = _model_class("reinforce_request", "ReinforceRequest")
ResolveRequest = _model_class("resolve_request", "ResolveRequest")


def test_learning_boundary_request_models_serialize_agent_name() -> None:
    episode = {"run_id": "run-1", "goal": "ship", "steps": []}
    requests = [
        ResolveRequest(agent_name="agent-a", run_id="run-1", goal="ship"),
        ObserveRequest(agent_name="agent-a", episode=episode),
        ReinforceRequest(agent_name="agent-a", episode=episode),
        DistillRequest(
            agent_name="agent-a",
            run_id="distill:run-1",
            goal="ship",
            outcome="fixed",
        ),
    ]

    for request in requests:
        data = request.to_dict()
        assert data["agent_name"] == "agent-a"
        assert "agent_id" not in data
