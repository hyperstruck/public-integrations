"""Session-dir state: round-trips, ordered per-step files, flush staging."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from hyperstruck.ide import state
from hyperstruck.ide.constants import ACTIVE_FILE, PENDING_FILE, RECALL_FILE
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
        transcript_path="/tmp/session/transcript.jsonl",
        cwd="/repo",
        is_stash_emitted=True,
        stash_block_digest="abc123",
        is_injected_by_previous_release=True,
        editor_pid=4242,
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
        final_output="I will confirm the shipment volumes by Friday.",
        cwd="/repo",
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
            "final_output": "I will confirm the shipment volumes by Friday.",
            "cwd": "/repo",
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


class TestReadingATurnAnEarlierReleaseWrote:
    """A client is upgraded in place, and a turn can be in flight when it happens.

    ``active.json`` is this client's own file, written by whichever version was installed
    when the turn started and read by whichever is installed at the next hook. A field the
    reader does not recognise is not a missing default; it is the turn's state, and a turn
    read as never injected shows its block a second time and loses the credit for the first.
    This exact class of bug already shipped once from this file.
    """

    @staticmethod
    def _as_the_previous_release_wrote_it(session_id: str, **fields: Any) -> None:
        state.write_active(
            session_id,
            ActiveTurn(
                run_id="r1",
                agent_name="a",
                goal="g",
                source_framework="claude-code",
                started_at=1.0,
            ),
        )
        path = state.session_dir(session_id) / ACTIVE_FILE
        data = json.loads(path.read_text())
        data.pop("is_injected_by_previous_release", None)
        path.write_text(json.dumps({**data, **fields}))

    def test_a_turn_that_had_injected_is_not_read_as_one_that_never_did(self) -> None:
        self._as_the_previous_release_wrote_it("s-old", is_injected=True)

        turn = state.read_active("s-old")

        assert turn is not None
        assert turn.is_injected_by_previous_release is True

    def test_a_turn_that_had_not_injected_still_reads_as_one_that_did_not(self) -> None:
        self._as_the_previous_release_wrote_it("s-old-clean", is_injected=False)

        turn = state.read_active("s-old-clean")

        assert turn is not None
        assert turn.is_injected_by_previous_release is False


class TestTheExclusiveRecallSlot:
    """One recall slot per session, and a checkpoint may not take one that is still in use.

    ``write_recall`` replaces the slot wholesale and there is no queue, so a checkpoint
    resolve returning while an earlier stash is still waiting to be claimed would destroy
    an injection that was about to happen. Refusing loses one stale block; overwriting
    could lose the injection, which is why the refusal is the fail-open direction.
    """

    def test_an_exclusive_write_refuses_a_slot_that_is_still_occupied(self) -> None:
        assert state.write_recall("s-excl", {"run_id": "r1", "injected_text": "FIRST"})

        assert not state.write_recall(
            "s-excl", {"run_id": "r1", "injected_text": "SECOND"}, is_exclusive=True
        )
        assert state.peek_recall("s-excl")["injected_text"] == "FIRST"

    def test_an_exclusive_write_takes_a_slot_nothing_is_holding(self) -> None:
        assert state.write_recall(
            "s-free", {"run_id": "r1", "injected_text": "FIRST"}, is_exclusive=True
        )

        assert state.peek_recall("s-free")["injected_text"] == "FIRST"

    def test_an_exclusive_write_leaves_no_temporary_file_behind(self) -> None:
        state.write_recall("s-tidy", {"run_id": "r1", "injected_text": "FIRST"})
        state.write_recall(
            "s-tidy", {"run_id": "r1", "injected_text": "SECOND"}, is_exclusive=True
        )

        assert not list(state.session_dir("s-tidy").glob(".*.exclusive"))

    def test_the_turn_start_resolve_still_replaces_the_slot(self) -> None:
        """It is not exclusive, and must not become so: its turn cleared the slot already."""
        state.write_recall("s-open", {"run_id": "r1", "injected_text": "FIRST"})

        assert state.write_recall("s-open", {"run_id": "r1", "injected_text": "SECOND"})
        assert state.peek_recall("s-open")["injected_text"] == "SECOND"


def test_a_turn_start_recall_publishes_by_linking_not_by_replacing(monkeypatch) -> None:
    """A read of the slot and then a write to it is not the guarantee the link gives.

    ``write_json_atomic`` replaces whatever occupies the path without looking, so deciding
    from a prior read leaves a gap a checkpoint's exclusive link can land in, and the
    exclusivity is then overwritten by the very branch that read it to avoid doing so. Both
    branches publish through the link, so the slot is taken atomically or not at all.
    """
    calls: list[str] = []
    linked = state.os.link

    def counting_link(source: Any, target: Any) -> None:
        calls.append(str(target))
        linked(source, target)

    monkeypatch.setattr(state.os, "link", counting_link)

    assert state.write_recall("s-link", {"run_id": "r1", "injected_text": "OPENING"})

    assert [call for call in calls if call.endswith(RECALL_FILE)]
    assert state.peek_recall("s-link")["injected_text"] == "OPENING"


def test_a_turn_start_recall_clears_a_leftover_it_outranks() -> None:
    """A stash from a run this turn replaced never outranked it and still does not."""
    state.write_recall(
        "s-leftover",
        {"run_id": "r0", "injected_text": "OLD", "checkpoint_ordinal": 1},
        is_exclusive=True,
    )

    assert state.write_recall("s-leftover", {"run_id": "r1", "injected_text": "NEW"})
    assert state.peek_recall("s-leftover")["injected_text"] == "NEW"


def test_a_claim_that_cannot_be_written_is_told_apart_from_one_already_held(
    monkeypatch,
) -> None:
    """Three answers, because a disk fault is not a statement about the block."""
    assert state.claim_shown_block("s-tri", "run-1", "d1") is True
    assert state.claim_shown_block("s-tri", "run-1", "d1") is False

    def refuse(_path: Any) -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr(state, "ensure_private_dir", refuse)

    assert state.claim_shown_block("s-tri", "run-1", "d2") is None


class TestTheShownBlockClaim:
    """Asking whether a block has been shown and recording it must be one act.

    A turn can hold more than one stash once it re-resolves mid-flight, so two parallel tool
    hooks can each be past their own claim at the same moment. A digest carried on the
    active turn is read by both before either writes, so both read "not shown yet" and the
    customer is shown the same advice twice with a second marker stamped on it.
    """

    def test_the_same_block_cannot_be_claimed_twice_for_one_run(self) -> None:
        assert state.claim_shown_block("s-shown", "run-1", "d1")

        assert not state.claim_shown_block("s-shown", "run-1", "d1")

    def test_a_different_block_of_the_same_run_is_its_own_claim(self) -> None:
        assert state.claim_shown_block("s-shown", "run-1", "d1")

        assert state.claim_shown_block("s-shown", "run-1", "d2")

    def test_a_new_run_cannot_inherit_what_the_previous_turn_showed(self) -> None:
        assert state.claim_shown_block("s-shown", "run-1", "d1")

        assert state.claim_shown_block("s-shown", "run-2", "d1")

    def test_a_released_claim_can_be_taken_again(self) -> None:
        """A block the editor refused was never put in front of the model."""
        state.claim_shown_block("s-shown", "run-1", "d1")

        state.release_shown_block("s-shown", "run-1", "d1")

        assert state.claim_shown_block("s-shown", "run-1", "d1")

    def test_each_claim_carries_the_offers_that_block_made(self) -> None:
        """So no hook's offers ride a read-modify-write another hook can drop."""
        state.claim_shown_block(
            "s-shown", "run-1", "d1", learning_ids=("L1",), claim_ids=("C1",)
        )
        state.claim_shown_block("s-shown", "run-1", "d2", learning_ids=("L2",))

        shown = state.read_shown_blocks("s-shown", "run-1")

        assert sorted(row["digest"] for row in shown) == ["d1", "d2"]
        assert sorted(item for row in shown for item in row["learning_ids"]) == [
            "L1",
            "L2",
        ]
        assert [item for row in shown for item in row["claim_ids"]] == ["C1"]

    def test_retiring_a_turn_drops_what_it_showed(self) -> None:
        state.claim_shown_block("s-shown", "run-1", "d1")

        state.clear_recall("s-shown")

        assert state.read_shown_blocks("s-shown", "run-1") == []


def test_counting_steps_never_opens_one() -> None:
    """The cheap half of the checkpoint threshold, for the editor's synchronous path."""
    assert state.count_steps("s-count") == 0
    for index in range(3):
        state.append_step("s-count", {"name": f"t{index}", "kind": "edit"})

    assert state.count_steps("s-count") == 3


def test_a_turn_start_recall_yields_to_a_checkpoint_of_its_own_run() -> None:
    """It returns whenever the boundary answers, which can be after a checkpoint landed."""
    assert state.write_recall(
        "s-yield",
        {"run_id": "r1", "injected_text": "CHECKPOINT", "checkpoint_ordinal": 1},
        is_exclusive=True,
    )

    assert not state.write_recall("s-yield", {"run_id": "r1", "injected_text": "OPENING"})
    assert state.peek_recall("s-yield")["injected_text"] == "CHECKPOINT"


class TestTheCheckpointClaim:
    """A threshold crossing is a decision exactly one parallel tool hook wins.

    Tool hooks run as parallel sibling processes sharing only disk, so two tool calls
    landing at the same threshold each read the same steps directory and each see it
    crossed. Without an exclusive claim both spawn a resolve, which doubles the spend the
    idempotency-key design exists to bound and breaks the two-resolve cap.
    """

    def test_only_the_first_caller_takes_a_checkpoint(self) -> None:
        assert state.claim_checkpoint("s-claim", "run-1", 1)

        assert not state.claim_checkpoint("s-claim", "run-1", 1)

    def test_each_checkpoint_of_a_run_is_claimed_separately(self) -> None:
        assert state.claim_checkpoint("s-claim", "run-1", 1)

        assert state.claim_checkpoint("s-claim", "run-1", 2)

    def test_a_new_run_cannot_inherit_the_previous_turns_claims(self) -> None:
        """Named after the run, so a lazily started turn starts with its own checkpoints."""
        assert state.claim_checkpoint("s-claim", "run-1", 1)

        assert state.claim_checkpoint("s-claim", "run-2", 1)

    def test_retiring_a_turn_drops_its_claims(self) -> None:
        state.claim_checkpoint("s-claim", "run-1", 1)

        state.clear_recall("s-claim")

        assert state.claim_checkpoint("s-claim", "run-1", 1)
