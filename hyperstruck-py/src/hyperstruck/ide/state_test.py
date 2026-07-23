"""Session-dir state: round-trips, ordered per-step files, flush staging."""

from __future__ import annotations

import pytest

from hyperstruck.ide import state
from hyperstruck.ide.state import ActiveTurn, PendingTurn


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))


def test_active_round_trip() -> None:
    turn = ActiveTurn(
        run_id="r1",
        agent_name="a",
        goal="g",
        source_framework="claude-code",
        started_at=1.0,
        offered_learning_ids=("L1",),
    )
    state.write_active("s1", turn)
    read = state.read_active("s1")
    assert read == turn
    state.clear_active("s1")
    assert state.read_active("s1") is None


def test_steps_append_and_order() -> None:
    state.write_active(
        "s1",
        ActiveTurn(
            run_id="r", agent_name="a", goal="", source_framework="x", started_at=0.0
        ),
    )
    for i in range(3):
        state.append_step(
            "s1", {"id": str(i), "name": "t", "args": {}, "status": "completed"}
        )
    steps = state.read_steps("s1")
    assert [s["id"] for s in steps] == ["0", "1", "2"]


def test_pending_round_trip() -> None:
    pending = PendingTurn(
        run_id="r",
        agent_name="a",
        goal="g",
        steps=({"id": "1"},),
        is_success=False,
        source_framework="cursor",
        ended_at=2.0,
        offered_learning_ids=("L1", "L2"),
    )
    state.write_active(
        "s1",
        ActiveTurn(
            run_id="r", agent_name="a", goal="g", source_framework="x", started_at=0.0
        ),
    )
    state.write_pending("s1", pending)
    assert state.read_active("s1") is None  # write_pending retires active
    read = state.read_pending("s1")
    assert read == pending
    state.clear_pending("s1")
    assert state.read_pending("s1") is None


def test_flush_staging_round_trip() -> None:
    payload = {"agent_id": "a", "episode": {"run_id": "r"}, "do_observe": True}
    path = state.stage_flush("s1", "a:s1:run123", payload)
    assert state.read_flush(path) == payload
    # Distinct turns never collide on the flush filename, even with the same run id.
    other = state.stage_flush("s1", "a:s1:run123", payload)
    assert other != path
    assert len(state.iter_flush_files("s1")) == 2
    state.remove_flush(path)
    state.remove_flush(other)
    assert state.read_flush(path) is None


def test_recall_claim_is_atomic_and_single_use() -> None:
    recall = {
        "run_id": "r",
        "injected_text": "TEXT",
        "offered_learning_ids": ["L1"],
    }
    state.write_recall("s1", recall)
    assert state.claim_recall("s1") == recall
    assert state.claim_recall("s1") is None


def test_recall_peek_does_not_consume() -> None:
    recall = {
        "run_id": "r",
        "injected_text": "TEXT",
        "offered_learning_ids": ["L1"],
    }
    assert state.peek_recall("s1") is None
    state.write_recall("s1", recall)
    assert state.peek_recall("s1") == recall
    assert state.peek_recall("s1") == recall  # repeatable: peeking never claims
    assert state.claim_recall("s1") == recall
    assert state.peek_recall("s1") is None


def test_remove_session_if_empty() -> None:
    state.write_active(
        "s1",
        ActiveTurn(
            run_id="r", agent_name="a", goal="", source_framework="x", started_at=0.0
        ),
    )
    state.clear_active("s1")
    state.remove_session_if_empty("s1")
    assert not state.session_dir("s1").exists()


def test_read_missing_is_none() -> None:
    assert state.read_active("nope") is None
    assert state.read_pending("nope") is None
    assert state.read_steps("nope") == []


def test_parallel_appends_keep_every_step() -> None:
    # Each tool hook is a separate process writing its own append-only file, so
    # concurrent captures cannot clobber a shared array or drop a step.
    state.write_active(
        "s1",
        ActiveTurn(
            run_id="r", agent_name="a", goal="", source_framework="x", started_at=0.0
        ),
    )
    for i in range(20):
        state.append_step(
            "s1", {"id": str(i), "name": "t", "args": {}, "status": "completed"}
        )
    steps = state.read_steps("s1")
    assert len(steps) == 20  # no step dropped
    assert sorted(int(s["id"]) for s in steps) == list(range(20))
    steps_dir = state.session_dir("s1") / "active" / "steps"
    assert len(list(steps_dir.glob("*.json"))) == 20  # one file per step, no sharing


def _active(run_id: str = "r") -> ActiveTurn:
    return ActiveTurn(
        run_id=run_id, agent_name="a", goal="", source_framework="x", started_at=0.0
    )


def test_lazy_start_does_not_drop_steps() -> None:
    # A racing lazy turn-start (reset_steps=False) must keep a sibling's step.
    state.write_active("s1", _active())
    state.append_step("s1", {"id": "0", "name": "t", "args": {}, "status": "completed"})
    state.write_active("s1", _active("r2"), reset_steps=False)  # racing lazy start
    assert len(state.read_steps("s1")) == 1  # step survived
    state.write_active("s1", _active("r3"))  # a genuine turn start does reset
    assert state.read_steps("s1") == []


def test_session_id_cannot_escape_session_dir() -> None:
    base = state.sessions_dir()
    for evil in ("..", ".", "../../etc", "a/b"):
        sdir = state.session_dir(evil)
        assert sdir.parent == base  # stays one level under sessions/
        assert sdir.name not in ("", ".", "..")
