"""Session-dir state: round-trips, ordered per-step files, flush staging."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

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
    assert state.record_flush_attempt(path) == 1
    assert state.read_flush(path) == payload
    assert state.read_flush_attempts(path) == 1
    state.remove_flush(path)
    state.remove_flush(other)
    assert state.read_flush(path) is None
    assert state.read_flush_attempts(path) == 0


def test_record_flush_attempt_does_not_recreate_removed_path() -> None:
    path = state.stage_flush(
        "s1", "a:s1:run123", {"agent_id": "a", "episode": {"run_id": "r"}}
    )
    state.remove_flush(path)
    assert state.record_flush_attempt(path) is None
    assert state.read_flush(path) is None


def test_flush_attempts_accumulate_and_sidecar_is_not_a_flush_file() -> None:
    path = state.stage_flush(
        "s1", "a:s1:run123", {"agent_id": "a", "episode": {"run_id": "r"}}
    )
    assert state.record_flush_attempt(path) == 1
    assert state.record_flush_attempt(path) == 2
    assert state.read_flush_attempts(path) == 2
    # The attempt sidecar must never be mistaken for a staged payload to deliver.
    assert state.iter_flush_files("s1") == [path]


def test_record_dropped_flush_appends_a_prompt_free_line(tmp_path) -> None:
    path = state.stage_flush(
        "s1", "a:s1:run123", {"agent_id": "a", "episode": {"run_id": "r"}}
    )
    state.record_dropped_flush(
        path, run_id="r", agent_name="a", attempts=3, cause="HTTP 422"
    )
    state.record_dropped_flush(
        path, run_id="r2", agent_name="a", attempts=3, cause="HTTP 400"
    )
    lines = (tmp_path / "dropped.jsonl").read_text().splitlines()
    assert [json.loads(line)["run_id"] for line in lines] == ["r", "r2"]
    assert json.loads(lines[0])["cause"] == "HTTP 422"


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


def _assert_every_field_differs_from_its_default(populated: Any, empty: Any) -> None:
    """Fail unless the fixture sets every field to something its default is not.

    Without this the round-trip assertions below are vacuous: a field added to the
    dataclass but omitted from both the fixture and the reader round-trips as its own
    default and the equality still passes, while the field is silently dropped in
    production. That is exactly how ``is_injected`` and then ``context_receipt`` broke.
    """
    unset = [
        field.name
        for field in dataclasses.fields(populated)
        if getattr(populated, field.name) == getattr(empty, field.name)
    ]
    assert not unset, (
        f"fields {unset} are at their default in this fixture, so the round-trip "
        "assertion cannot detect them being dropped by the reader"
    )


def test_an_active_turn_round_trips_every_field() -> None:
    """The sweep reads a turn nobody is holding in memory, so a dropped field is silent."""
    turn = ActiveTurn(
        run_id="r1",
        agent_name="a",
        goal="fix the vacuity gate",
        source_framework="claude-code",
        started_at=1.0,
        offered_learning_ids=("l1",),
        is_injected=True,
        transcript_path="/tmp/session/transcript.jsonl",
    )
    _assert_every_field_differs_from_its_default(
        turn,
        ActiveTurn(
            run_id="",
            agent_name="",
            goal="",
            source_framework="",
            started_at=0.0,
        ),
    )

    state.write_active("s-round-trip", turn)

    assert state.read_active("s-round-trip") == turn


def test_a_pending_turn_round_trips_every_field() -> None:
    """Anything written but not read back is dead on disk, which is how is_injected broke."""
    pending = PendingTurn(
        run_id="r1",
        agent_name="a",
        goal="fix the vacuity gate",
        steps=({"status": "completed"},),
        is_success=True,
        source_framework="claude-code",
        ended_at=1.0,
        offered_learning_ids=("l1",),
        is_injected=True,
        principal_utterance="we do not add word lists to our code",
        context_receipt="<!-- hyperstruck-run: r1 -->\n- the rule the editor accepted",
    )

    _assert_every_field_differs_from_its_default(
        pending,
        PendingTurn(
            run_id="",
            agent_name="",
            goal="",
            steps=(),
            is_success=False,
            source_framework="",
            ended_at=0.0,
        ),
    )

    restored = state._pending_from_dict(state._pending_to_dict(pending))

    assert restored == pending
