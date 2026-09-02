"""Session-dir state: round-trips, ordered per-step files, flush staging."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from hyperstruck.ide import state
from hyperstruck.ide.constants import PENDING_FILE
from hyperstruck.ide.recall import RecallOutcome
from hyperstruck.ide.state import ActiveTurn, FinishedTurn


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HYPER_HOME", str(tmp_path))


def _write_legacy_pending(session_id: str, data: dict[str, Any]) -> None:
    """A ``pending.json`` as the previous release wrote it, by hand.

    Written directly rather than through a writer, because this release has none:
    the drain has to read a file shape that no code in the tree can produce.
    """
    sdir = state.session_dir(session_id)
    state.ensure_private_dir(sdir)
    (sdir / PENDING_FILE).write_text(json.dumps(data))


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


def test_a_previous_release_pending_file_reads_back_for_the_drain() -> None:
    """Nothing writes ``pending.json`` any more, so only the read side survives."""
    _write_legacy_pending(
        "s1",
        {
            "run_id": "r",
            "agent_name": "a",
            "goal": "g",
            "steps": [{"id": "1"}],
            "is_success": False,
            "source_framework": "cursor",
            "ended_at": 2.0,
            "offered_learning_ids": ["L1", "L2"],
            "is_injected": True,
            "principal_utterance": "a field this release no longer carries",
        },
    )
    read = state.read_pending("s1")
    assert read is not None
    turn, is_success = read
    assert is_success is False  # the label travels beside the turn, not on it
    assert turn == FinishedTurn(
        run_id="r",
        agent_name="a",
        goal="g",
        steps=({"id": "1"},),
        source_framework="cursor",
        ended_at=2.0,
        offered_learning_ids=("L1", "L2"),
        is_injected=True,
    )
    state.clear_pending("s1")
    assert state.read_pending("s1") is None


def test_retire_active_closes_the_turn_out() -> None:
    state.write_active(
        "s1",
        ActiveTurn(
            run_id="r", agent_name="a", goal="g", source_framework="x", started_at=0.0
        ),
    )
    state.retire_active("s1")
    assert state.read_active("s1") is None


def test_one_run_id_stages_to_one_path_however_many_writers_reach_it() -> None:
    """The single-delivery guard: the staged filename is keyed on the run id alone.

    Two writers can now reach the same turn, since a stop and the sweep's orphan
    recovery both stage directly with no pending file serialising them. The guard is
    the name, not a lock: the second write atomically replaces the first file, so the
    run can be delivered at most once.
    """
    run_id = "a:s1:run123"
    first = state.stage_flush("s-once", run_id, {"episode": {"run_id": run_id}})
    second = state.stage_flush(
        "s-once", run_id, {"episode": {"run_id": run_id}, "do_observe": True}
    )

    assert first == second
    staged = list((state.session_dir("s-once") / "flushing").glob("*.json"))
    assert len(staged) == 1
    assert state.read_flush(first) == {
        "episode": {"run_id": run_id},
        "do_observe": True,
    }


def test_a_turn_with_no_run_id_keeps_its_own_path() -> None:
    """With no identity to collapse onto, losing a write is worse than two deliveries."""
    first = state.stage_flush("s-unkeyed", "", {"episode": {}})
    second = state.stage_flush("s-unkeyed", "", {"episode": {}})

    assert first != second


def test_a_delivered_run_id_is_not_resurrected_by_a_later_stage() -> None:
    """``record_flush_attempt`` returning None is how a flush learns it lost the race."""
    run_id = "a:s1:run777"
    path = state.stage_flush("s-race", run_id, {"episode": {"run_id": run_id}})
    state.remove_flush(path)

    assert state.record_flush_attempt(path) is None


def test_flush_staging_round_trip() -> None:
    payload = {"agent_id": "a", "episode": {"run_id": "r"}, "do_observe": True}
    path = state.stage_flush("s1", "a:s1:run123", payload)
    assert state.read_flush(path) == payload
    # Distinct turns never collide, because a run id ends in a fresh uuid4 (_new_run_id),
    # so a shared filename can only ever mean the same turn staged twice.
    other = state.stage_flush("s1", "a:s1:run999", payload)
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
        offered_claim_ids=("c1",),
        is_injected=True,
        transcript_path="/tmp/session/transcript.jsonl",
        cwd="/repo",
        is_stash_emitted=True,
        stash_block_digest="abc123",
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


def test_the_drain_reads_back_every_field_a_legacy_pending_file_carries() -> None:
    """A field the drain drops is a turn delivered wrong, which is how is_injected broke."""
    expected = FinishedTurn(
        run_id="r1",
        agent_name="a",
        goal="fix the vacuity gate",
        steps=({"status": "completed"},),
        source_framework="claude-code",
        ended_at=1.0,
        offered_learning_ids=("l1",),
        offered_claim_ids=("c1",),
        is_injected=True,
        context_receipt="<!-- hyperstruck-run: r1 -->\n- the rule the editor accepted",
        recall_outcome=RecallOutcome.DELIVERED,
    )

    _assert_every_field_differs_from_its_default(
        expected,
        FinishedTurn(
            run_id="",
            agent_name="",
            goal="",
            steps=(),
            source_framework="",
            ended_at=0.0,
        ),
    )

    _write_legacy_pending(
        "s-drain",
        {
            "run_id": "r1",
            "agent_name": "a",
            "goal": "fix the vacuity gate",
            "steps": [{"status": "completed"}],
            "is_success": True,
            "source_framework": "claude-code",
            "ended_at": 1.0,
            "offered_learning_ids": ["l1"],
            "offered_claim_ids": ["c1"],
            "is_injected": True,
            "context_receipt": (
                "<!-- hyperstruck-run: r1 -->\n- the rule the editor accepted"
            ),
            "recall_outcome": "delivered",
        },
    )

    drained = state.read_pending("s-drain")
    assert drained is not None
    turn, is_success = drained
    assert turn == expected
    assert is_success is True


class TestTheInjectionPointMarker:
    """A marker file rather than a field on the active turn, and named after its run.

    The field it replaced was a read-modify-write of ``active.json`` from hooks that run
    as parallel processes with no lock, so one could clobber another's ``is_injected`` and
    offered ids and silently lose the credit for rules that were genuinely shown.
    """

    def test_a_mark_is_visible_to_the_run_it_was_made_for(self) -> None:
        assert state.mark_injection_point("s-mark", "run-1") is True
        assert state.has_injection_point("s-mark", "run-1")

    def test_an_unmarked_run_reads_false(self) -> None:
        assert not state.has_injection_point("s-mark", "run-1")

    def test_the_next_turn_does_not_inherit_the_previous_turns_answer(self) -> None:
        """The lazy turn start in the per-tool hook does not clear recall state, so a
        marker with no run id on it made turn N+1 report ``RECALL_UNCLAIMED`` -- the
        actionable half, the one an alert asks someone to fix -- for a turn that never had
        anywhere to show anything."""
        state.mark_injection_point("s-mark", "run-1")

        assert not state.has_injection_point("s-mark", "run-2")

    def test_parallel_hooks_do_not_destroy_each_others_marks(self) -> None:
        """Creating a file is atomic and carries no other state, which is the whole
        argument for the marker over a field."""
        state.mark_injection_point("s-mark", "run-1")
        state.mark_injection_point("s-mark", "run-2")

        assert state.has_injection_point("s-mark", "run-1")
        assert state.has_injection_point("s-mark", "run-2")

    def test_a_mark_does_not_disturb_the_active_turn(self) -> None:
        turn = ActiveTurn(
            run_id="run-1",
            agent_name="a",
            goal="g",
            source_framework="x",
            started_at=0.0,
            offered_learning_ids=("L1",),
            is_injected=True,
        )
        state.write_active("s-mark", turn)
        state.mark_injection_point("s-mark", "run-1")

        assert state.read_active("s-mark") == turn

    def test_retiring_the_turn_clears_the_mark(self) -> None:
        state.mark_injection_point("s-mark", "run-1")
        state.clear_recall("s-mark")

        assert not state.has_injection_point("s-mark", "run-1")

    def test_a_mark_that_could_not_be_written_says_so(self, monkeypatch) -> None:
        """Silence here is not neutral: an unwritten mark reads back as "there was nowhere
        to show anything", the structural verdict with no remedy, so an unwritable session
        dir would quietly relabel every real drop as nothing to fix."""

        def refuse(_path):
            raise OSError("read-only home")

        monkeypatch.setattr(state, "ensure_private_dir", refuse)

        assert state.mark_injection_point("s-mark", "run-1") is False
