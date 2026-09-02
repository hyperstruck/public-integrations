"""What the run core must guarantee to two shipped seats and to every new host."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from hyperstruck._wire import (
    ObligationClosureResult,
    ReinforceResult,
    ReportedObligationOutcome,
    ResolvedContext,
    ToolSpec,
)
from hyperstruck.identity import AgentIdentity
from hyperstruck.runtime.declarations import (
    SECRET,
    SHAREABLE,
    USER_DATA,
    DeclarationRegistry,
    ToolDeclaration,
)
from hyperstruck.runtime.ledger import LedgerClosedError
from hyperstruck.runtime.receipt import DELIVERED_VERBATIM, UNRESOLVED
from hyperstruck.runtime.run import (
    CLOSE_TRIGGER_NO_TOOL_CALLS,
    DISPOSITION_OBSERVED,
    DISPOSITION_WITHHELD,
    RunReport,
    DISPOSITION_WRITE_FAILED,
    CLOSE_TRIGGER_PROCESS_EXIT,
    DISPOSITION_DECLINED,
    DISPOSITION_EVICTED,
    DISPOSITION_REINFORCED,
    OUTCOME_RECALL_UNCLAIMED,
    OUTCOME_RESOLVE_EMPTY,
    OUTCOME_RESOLVE_FAILED,
    RunRegistry,
    RunSeat,
)
from hyperstruck.runtime.run_key import RunKey

IDENTITY = AgentIdentity(agent_name="support-bot")
ADVICE = "Relevant learnings from prior runs (hyperstruck):\n- prefer the bulk endpoint"
OBLIGATIONS = "Open obligations:\n- send the Northwind Clinics renewal"


class FakeClient:
    """A boundary that records what it was asked to do and answers as told."""

    def __init__(
        self,
        context: ResolvedContext | None = None,
        *,
        resolve_error: Exception | None = None,
    ) -> None:
        self._context = context if context is not None else ResolvedContext()
        self._resolve_error = resolve_error
        self.resolves: list[dict[str, Any]] = []
        self.observed: list[Any] = []
        self.reinforced: list[dict[str, Any]] = []
        self.declined: list[dict[str, Any]] = []

    async def resolve(self, **kwargs: Any) -> ResolvedContext:
        self.resolves.append(kwargs)
        if self._resolve_error is not None:
            raise self._resolve_error
        return self._context

    async def observe(self, *, identity: Any, episode: Any) -> None:
        self.observed.append(episode)

    async def reinforce(self, **kwargs: Any) -> None:
        self.reinforced.append(kwargs)

    async def decline(self, **kwargs: Any) -> None:
        self.declined.append(kwargs)


def _context(**overrides: Any) -> ResolvedContext:
    base: dict[str, Any] = {
        "injected_text": ADVICE,
        "offered_learning_ids": ("l1",),
    }
    base.update(overrides)
    return ResolvedContext(**base)


def _seat(client: FakeClient, **overrides: Any) -> RunSeat:
    options: dict[str, Any] = {
        "client": client,
        "identity": IDENTITY,
        "run_key_resolvers": (),
        "declarations": DeclarationRegistry(
            [ToolDeclaration(name="search", args={"query": "user_data"})]
        ),
    }
    options.update(overrides)
    return RunSeat(**options)


def _steps(seat: RunSeat, run: Any) -> None:
    """Two material steps, which is the minimum the observe gate keeps."""
    seat.record_planned_calls(run, [("t1", "search", {}), ("t2", "write", {})])
    seat.record_step(run, "t1", "search", result="ok")
    seat.record_step(run, "t2", "write", result="ok")


async def _worked_run(seat: RunSeat, *, sent: str | None = None) -> Any:
    run = seat.open("find the renewal", (ToolSpec(name="search"),))
    block = await seat.before_model_call(run)
    seat.after_model_call(run, sent if sent is not None else f"system\n{block}")
    seat.record_planned_calls(
        run, [("t1", "search", {"query": "renewal"}), ("t2", "search", {"query": "northwind clinics"})]
    )
    seat.record_step(run, "t1", "search", result="ok")
    seat.record_step(run, "t2", "search", result="ok")
    return run


async def test_the_block_is_computed_once_and_replayed_on_every_send() -> None:
    """A retried send must show the model the block it was shown the first time.

    Recomputing would show a different block on the second send, spend a second recall
    against the run's budget, and make the receipt evidence something other than what
    happened.
    """
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    first = await seat.before_model_call(run)
    second = await seat.before_model_call(run)
    third = await seat.before_model_call(run)
    assert first == second == third == ADVICE
    assert len(client.resolves) == 1


async def test_receipt_location_runs_on_every_send_and_the_latest_wins() -> None:
    """A mid-run trim is exactly what the receipt exists to catch.

    Locating once would report the first send's fidelity for a run whose block a
    summariser emptied on the third.
    """
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    block = await seat.before_model_call(run)
    seat.after_model_call(run, f"system\n{block}")
    assert run.receipt is not None
    assert run.receipt.outcome == DELIVERED_VERBATIM
    seat.after_model_call(run, "system\n(the summariser ate it)")
    assert run.receipt.outcome == UNRESOLVED


async def test_a_resolve_failure_never_breaks_the_run_and_is_reported_as_itself() -> None:
    """Collapsing resolve_failed into resolve_empty is what the taxonomy exists to stop.

    It makes a broken deployment indistinguishable from a cold corpus, which is the single
    most expensive confusion this field can cause.
    """
    client = FakeClient(resolve_error=RuntimeError("boundary down"))
    seat = _seat(client)
    run = await _worked_run(seat)
    report = await seat.close(run)
    assert report.recall_outcome == OUTCOME_RESOLVE_FAILED
    assert client.reinforced[0]["recall_outcome"] == OUTCOME_RESOLVE_FAILED


async def test_a_cold_corpus_reports_resolve_empty_rather_than_a_failure() -> None:
    client = FakeClient(ResolvedContext())
    seat = _seat(client)
    run = await _worked_run(seat)
    report = await seat.close(run)
    assert report.recall_outcome == OUTCOME_RESOLVE_EMPTY


async def test_a_run_that_resolved_and_never_called_a_model_is_unclaimed() -> None:
    """Offered is not shown. The distinction is what the boundary is being told."""
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(run, [("t1", "search", {"query": "x"})])
    seat.record_step(run, "t1", "search", result="ok")
    report = await seat.close(run)
    assert report.recall_outcome == OUTCOME_RECALL_UNCLAIMED


async def test_a_worked_run_reinforces_with_a_receipt_it_did_not_author() -> None:
    """The commercial point of the whole seat: an artefact we did not write ourselves."""
    client = FakeClient(_context())
    seat = _seat(client)
    run = await _worked_run(seat)
    report = await seat.close(run)
    assert report.disposition == DISPOSITION_REINFORCED
    assert report.is_receipt_sent is True
    receipt = client.reinforced[0]["context_receipt"]
    assert receipt is not None
    assert "prefer the bulk endpoint" in receipt
    assert client.reinforced[0]["is_delivered"] is True


async def test_a_run_with_nothing_material_declines_rather_than_sitting_open() -> None:
    """A run left neither reinforced nor declined holds its resolve reservation.

    It is then indistinguishable from a host that stopped writing back, which is the state
    the decline exists to prevent.
    """
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    report = await seat.close(run)
    assert report.disposition == DISPOSITION_DECLINED
    assert client.declined[0]["reason"] == "no_tool_calls"
    assert client.observed == []


async def test_the_obligation_shelf_keeps_its_offered_and_delivered_sets_apart() -> None:
    """The shelf escalates on deliveries, so an unshown obligation must not be one.

    Collapsing the two would produce a scoring fault on the server that is invisible from
    here, which is the worst shape a fault can have.
    """
    client = FakeClient(
        _context(
            injected_obligations_text=OBLIGATIONS,
            offered_obligation_ids=("o1", "o2"),
            delivered_obligation_ids=("o1",),
        )
    )
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    assert run.ledger.obligations is not None
    assert run.ledger.obligations.offered_ids == ("o1", "o2")
    assert run.ledger.obligations.delivered_ids == ("o1",)


async def test_a_boundary_that_reports_no_delivered_set_reads_as_nothing_delivered() -> None:
    """Under-reporting forgoes credit; over-reporting escalates against a real person."""
    client = FakeClient(
        _context(
            injected_obligations_text=OBLIGATIONS, offered_obligation_ids=("o1", "o2")
        )
    )
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    assert run.ledger.obligations is not None
    assert run.ledger.obligations.delivered_ids == ()


async def test_a_double_close_raises_rather_than_quietly_sending_a_second_episode() -> None:
    """Absorbing it would hide a double close in a retry or a finally block."""
    client = FakeClient(_context())
    seat = _seat(client)
    run = await _worked_run(seat)
    await seat.close(run)
    with pytest.raises(LedgerClosedError):
        await seat.close(run)


async def test_a_step_recorded_after_close_is_refused() -> None:
    """Absorbing it would report a smaller episode than the one that happened."""
    client = FakeClient(_context())
    seat = _seat(client)
    run = await _worked_run(seat)
    await seat.close(run)
    with pytest.raises(LedgerClosedError):
        seat.record_step(run, "t3", "search", result="late")


async def test_an_undeclared_argument_is_named_in_the_run_report() -> None:
    """A configuration state must never look like a broken product."""
    client = FakeClient(_context())
    seat = _seat(client, declarations=DeclarationRegistry())
    run = await _worked_run(seat)
    report = await seat.close(run)
    assert report.withheld
    assert any("search" in note for note in report.withheld)
    assert client.reinforced[0]["is_org_promotion_allowed"] is False


async def test_the_report_reaches_the_callback_and_a_raising_one_does_not_lose_the_run() -> None:
    """A customer callback is their bug, not a reason to drop the report's other channels."""
    seen: list[Any] = []

    def sink(report: Any) -> None:
        seen.append(report)
        raise RuntimeError("customer observability is down")

    client = FakeClient(_context())
    seat = _seat(client, on_report=sink)
    run = await _worked_run(seat)
    report = await seat.close(run)
    assert seen == [report]
    assert run.report is report


async def test_the_report_says_which_rung_of_the_ladder_answered() -> None:
    """An inferred key is a fact about the report's own reliability."""
    client = FakeClient(_context())
    seat = _seat(client)
    run = await _worked_run(seat)
    report = await seat.close(run)
    assert report.run_key_source == "minted"
    assert report.is_run_key_inferred is True

    explicit = seat.open("g", run_key=RunKey(key="abc", source="trace", is_inferred=False))
    assert explicit.key.source == "trace"
    await seat.close(explicit)


async def test_tenancy_rides_the_seat_and_never_the_run_key() -> None:
    """A missed inference must cost attribution, never cross a tenant boundary."""
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g", run_key=RunKey(key="abc", source="trace", is_inferred=False))
    assert run.run_id.startswith("support-bot:")
    assert run.identity is IDENTITY
    await seat.close(run)


async def test_an_abandoned_run_ages_out_and_a_working_one_never_does() -> None:
    """Abandoned means untouched, not old. A long run still working is not a candidate."""
    client = FakeClient(_context())
    registry = RunRegistry(ttl_seconds=0.01)
    seat = _seat(client, registry=registry)
    stale = seat.open("forgotten")
    working = seat.open("still going")
    await asyncio.sleep(0.05)
    seat.record_planned_calls(working, [("t1", "search", {})])

    evicted = registry.sweep()
    assert [run.run_id for run in evicted] == [stale.run_id]
    assert registry.get(working.key.key) is working
    await seat.close(working)


async def test_an_evicted_run_is_reported_rather_than_declined() -> None:
    """DeclineReason is a closed five-member set with no eviction member.

    An evicted entry has also already lost the offered ids a decline payload needs, so
    inventing a reason here would be exactly the vocabulary drift this package forbids.
    The server's own reclaim sweep owns the resolve reservation.
    """
    reports: list[Any] = []
    client = FakeClient(_context())
    registry = RunRegistry(max_size=1, ttl_seconds=0.01)
    seat = _seat(client, registry=registry, on_report=reports.append)
    seat.open("first")
    await asyncio.sleep(0.05)
    second = seat.open("second")

    assert [report.disposition for report in reports] == [DISPOSITION_EVICTED]
    assert reports[0].is_evicted is True
    assert client.declined == []
    await seat.close(second)


@pytest.mark.asyncio
async def test_a_value_copied_out_of_an_earlier_result_is_escalated_on_the_wire() -> None:
    """The one-hop join, fired from the seat rather than merely available to it.

    An agent reading an address out of a lookup and handing it to a mailer is the common
    real case, and without this the second call's argument would be stamped with whatever
    the mailer declared, which says nothing about where the value came from.
    """
    client = FakeClient()
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        declarations=DeclarationRegistry(
            [
                ToolDeclaration(name="lookup", args={"company": USER_DATA}),
                ToolDeclaration(name="send", args={"body": SHAREABLE}),
            ]
        ),
    )
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run,
        [
            ("1", "lookup", {"company": "Northwind Clinics Pty Ltd"}),
            ("2", "send", {"body": "posting to ada@example.com today"}),
        ],
    )
    seat.record_step(run, "1", "lookup", result={"email": "ada@example.com"})
    seat.record_step(run, "2", "send", result="sent")
    report = await seat.close(run)

    steps = client.observed[0].steps
    assert steps[1].declared_sensitivity is not None
    assert steps[1].declared_sensitivity["args"]["body"] == USER_DATA
    # And it is never silent: the run says which arguments were escalated and why.
    assert any("escalated" in line for line in report.withheld)


@pytest.mark.asyncio
async def test_propagation_never_lowers_a_label_a_tool_already_declared() -> None:
    client = FakeClient()
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        declarations=DeclarationRegistry(
            [
                ToolDeclaration(name="lookup", args={"q": SHAREABLE}),
                ToolDeclaration(name="send", args={"body": SECRET}),
            ]
        ),
    )
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run,
        [
            ("1", "lookup", {"q": "x"}),
            ("2", "send", {"body": "quoting public-notice-1234 here"}),
        ],
    )
    seat.record_step(run, "1", "lookup", result="public-notice-1234")
    seat.record_step(run, "2", "send", result="sent")
    await seat.close(run)
    assert client.observed[0].steps[1].declared_sensitivity["args"]["body"] == SECRET


@pytest.mark.asyncio
async def test_a_step_cannot_escalate_against_its_own_output() -> None:
    """The join is one hop against *earlier* steps, so ordering is load bearing."""
    client = FakeClient()
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        declarations=DeclarationRegistry(
            [ToolDeclaration(name="echo", args={"text": SHAREABLE})]
        ),
    )
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run, [("1", "echo", {"text": "value-abcdef"}), ("2", "echo", {"text": "unrelated"})]
    )
    seat.record_step(run, "1", "echo", result="value-abcdef")
    seat.record_step(run, "2", "echo", result="ok")
    await seat.close(run)
    assert client.observed[0].steps[0].declared_sensitivity["args"]["text"] == SHAREABLE


@pytest.mark.asyncio
async def test_a_scrubbed_value_does_not_re_enter_the_join_table() -> None:
    """A value the scanner removed from the wire must not come back as a join key.

    Otherwise the one field the customer paid a scanner to remove would be the field this
    run matched every later argument against.
    """

    class _Scanner:
        def scan(self, text: str):
            from hyperstruck.runtime.scanning import Finding

            index = text.find("ada@example.com")
            if index < 0:
                return ()
            return (
                Finding(
                    start=index,
                    end=index + len("ada@example.com"),
                    kind="EMAIL",
                    label=USER_DATA,
                ),
            )

    client = FakeClient()
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        declarations=DeclarationRegistry(
            [
                ToolDeclaration(name="lookup", args={"q": USER_DATA}),
                ToolDeclaration(name="send", args={"body": SHAREABLE}),
            ]
        ),
        scanner=_Scanner(),
    )
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run,
        [
            ("1", "lookup", {"q": "x"}),
            ("2", "send", {"body": "posting to ada@example.com today"}),
        ],
    )
    seat.record_step(run, "1", "lookup", result="ada@example.com")
    seat.record_step(run, "2", "send", result="sent")
    await seat.close(run)
    assert client.observed[0].steps[1].declared_sensitivity["args"]["body"] == SHAREABLE


@pytest.mark.asyncio
async def test_a_stable_correlation_key_gives_each_turn_its_own_run_id() -> None:
    """The key correlates; the run id identifies, and the two must not be one string.

    A conversation id is stable across turns by design. Giving every turn under it the same
    run id would have the platform dedupe the second turn's episode against the first and
    drop it, silently and with nothing to diagnose from: the customer sees a corpus that
    stops filling and no error anywhere.
    """
    client = FakeClient()
    key = RunKey(key="session-42", source="conversation", is_inferred=False)
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        run_key_resolvers=(lambda: key,),
        close_grace_seconds=0.0,
    )
    first = seat.for_call("turn one")
    await seat.before_model_call(first)
    _steps(seat, first)
    await seat.close(first)

    second = seat.for_call("turn two")
    await seat.before_model_call(second)
    _steps(seat, second)
    await seat.close(second)

    assert first.run_id != second.run_id
    assert {episode.run_id for episode in client.observed} == {
        first.run_id,
        second.run_id,
    }


@pytest.mark.asyncio
async def test_a_tool_free_answer_closes_the_run_after_the_window_on_the_seat_s_own_timer() -> None:
    """Driven by the seat, not by the caller.

    Leaving the sweep to the customer would make the documented default attachment point
    earn no credit for anyone who did not read that paragraph, which is the exact failure
    the grace window exists to close.
    """
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, close_grace_seconds=0.0)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    seat.mark_closable(run)
    for _ in range(8):
        await asyncio.sleep(0)
    assert run.is_closed
    assert run.report is not None
    assert run.report.close_trigger == CLOSE_TRIGGER_NO_TOOL_CALLS


@pytest.mark.asyncio
async def test_a_further_call_inside_the_window_continues_the_run_rather_than_closing_it() -> None:
    client = FakeClient()
    key = RunKey(key="fixed", source="context", is_inferred=False)
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        run_key_resolvers=(lambda: key,),
        close_grace_seconds=30.0,
    )
    run = seat.for_call("g")
    await seat.before_model_call(run)
    seat.mark_closable(run)
    assert run.closable_at is not None
    # The follow-up arrives inside the window. One episode, not two.
    again = seat.for_call("g")
    assert again is run
    assert run.closable_at is None
    assert not run.is_closed
    assert client.observed == [] and client.declined == []


@pytest.mark.asyncio
async def test_the_sweep_is_available_to_a_host_that_would_rather_drive_it() -> None:
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, close_grace_seconds=30.0)
    run = seat.open("g")
    await seat.before_model_call(run)
    run.closable_at = time.monotonic() - 60
    reports = await seat.sweep()
    assert [report.close_trigger for report in reports] == [CLOSE_TRIGGER_NO_TOOL_CALLS]


@pytest.mark.asyncio
async def test_a_process_exit_flush_closes_every_live_run() -> None:
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, run_key_resolvers=())
    seat.open("a")
    seat.open("b")
    reports = await seat.flush_all()
    assert len(reports) == 2
    assert all(report.close_trigger == CLOSE_TRIGGER_PROCESS_EXIT for report in reports)
    assert len(seat.runs) == 0


@pytest.mark.asyncio
async def test_an_explicit_close_cancels_a_pending_grace_timer() -> None:
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, close_grace_seconds=30.0)
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.mark_closable(run)
    assert run.close_task is not None
    await seat.close(run)
    for _ in range(4):
        await asyncio.sleep(0)
    # One close, not two: the second would send a duplicate episode.
    assert len(client.declined) == 1


@pytest.mark.asyncio
async def test_the_subject_declaration_is_read_off_the_roster_without_the_caller_registering_it() -> None:
    """The annotation a customer already wrote is the one Core reads, and it must fire.

    Left unregistered, the registry only ever holds what a caller passed by hand, so every
    run falls back to structural salience: the same company under two spellings accumulates
    two dossiers and neither reaches the stability the read side gates on.
    """
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY)
    run = seat.open(
        "g",
        (
            ToolSpec(
                name="lookup_account",
                parameters={"properties": {"company_name": {"type": "string", "role": "entity"}}},
            ),
        ),
    )
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run,
        [
            ("1", "lookup_account", {"company_name": "Northwind Clinics Pty Ltd"}),
            ("2", "lookup_account", {"company_name": "Northwind Clinics"}),
        ],
    )
    seat.record_step(run, "1", "lookup_account", result="ok")
    seat.record_step(run, "2", "lookup_account", result="ok")
    await seat.close(run)
    declared = client.observed[0].steps[0].declared_sensitivity
    assert declared is not None
    assert declared["subject"] == "company_name"


@pytest.mark.asyncio
async def test_a_roster_read_from_schema_does_not_make_an_undeclared_tool_look_declared() -> None:
    """Reading a subject must not fabricate argument labels, or org promotion would open."""
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY)
    run = seat.open(
        "g",
        (ToolSpec(name="t", parameters={"properties": {"id": {"in": "path"}}}),),
    )
    await seat.before_model_call(run)
    seat.record_planned_calls(run, [("1", "t", {"id": "x"}), ("2", "t", {"id": "y"})])
    seat.record_step(run, "1", "t", result="ok")
    seat.record_step(run, "2", "t", result="ok")
    await seat.close(run)
    assert client.reinforced[0]["is_org_promotion_allowed"] is False


@pytest.mark.asyncio
async def test_a_bulk_close_survives_a_sibling_run_closing_underneath_it() -> None:
    """The two close paths race by construction, and one raced run must not lose the rest.

    ``flush_all`` walks a snapshot and awaits inside the loop, and ``close`` awaits the
    prefetch. That await is where a sibling's own grace timer fires. A second close is a
    fault by design and raises, so without a guard the whole sweep would abort and every
    run still queued behind the raced one would go unreported.
    """
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, run_key_resolvers=())
    first = seat.open("a")
    second = seat.open("b")
    await seat.before_model_call(first)
    await seat.before_model_call(second)
    # Something else got there first, exactly as a fired grace timer would have.
    await seat.close(first)
    reports = await seat.flush_all()
    assert [report.goal for report in reports] == ["b"]
    assert second.is_closed


@pytest.mark.asyncio
async def test_a_copied_value_can_never_lower_an_undeclared_argument_s_label() -> None:
    """The escalate-only guarantee, at the one place it was actually inverted.

    `declaration_for` stamps every undeclared argument `secret`; `propagate` computes its
    own baseline from the registry, which does not hold that default. Merging its answer
    over the stamp lowered the argument to whatever the earlier tool declared, and the run
    report announced the de-escalation as an escalation.
    """
    client = FakeClient()
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        declarations=DeclarationRegistry(
            [ToolDeclaration(name="lookup", args={"q": SHAREABLE})]
        ),
    )
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run,
        [
            ("1", "lookup", {"q": "x"}),
            # `send` is undeclared, so its body is stamped secret by the default, and it
            # quotes a value an earlier shareable tool returned.
            ("2", "send", {"body": "quoting public-notice-1234 here"}),
        ],
    )
    seat.record_step(run, "1", "lookup", result="public-notice-1234")
    seat.record_step(run, "2", "send", result="sent")
    report = await seat.close(run)

    body = client.observed[0].steps[1].declared_sensitivity["args"]["body"]
    assert body == SECRET, f"a copied value lowered the label to {body}"
    # And nothing is announced as an escalation that did not escalate.
    assert not any("escalated" in line for line in report.withheld)


@pytest.mark.asyncio
async def test_the_grace_window_close_does_not_cancel_the_task_running_it() -> None:
    """`_close_after_grace` calls straight into `close`, which cancelled `close_task`.

    That is the very coroutine doing the closing, so the run was popped from the registry
    and the write never went out: the documented default attachment point reinforced
    nothing while appearing to close.
    """
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, close_grace_seconds=0.0)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    seat.mark_closable(run)
    for _ in range(12):
        await asyncio.sleep(0)
    assert run.is_closed
    assert len(client.observed) == 1, "the episode never reached the boundary"
    assert len(client.reinforced) == 1


@pytest.mark.asyncio
async def test_a_block_that_did_not_arrive_is_not_reported_as_delivered() -> None:
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    block = await seat.before_model_call(run)
    assert block
    # A layer below emptied it, or an adapter declined to inject it. Either way not one
    # line of ours is in what went out.
    seat.after_model_call(run, "You are helpful.\nUser: go")
    _steps(seat, run)
    report = await seat.close(run)
    assert report.receipt_outcome == "unresolved"
    assert report.is_receipt_sent is False
    # `delivered` here is the exact ambiguity the delivery pair exists to remove.
    assert report.recall_outcome == "recall_unclaimed"
    assert client.reinforced[0]["is_delivered"] is False


@pytest.mark.asyncio
async def test_a_second_call_of_the_same_conversation_joins_the_first_run() -> None:
    """Rung 4. Without it the documented default opens a run per model call.

    No tracer, no explicit wrapper: exactly the configuration both quick starts show.
    """
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, close_grace_seconds=0.0)
    first = seat.for_call("reconcile the invoices", is_continuation=False)
    second = seat.for_call("", is_continuation=True)
    assert second is first
    # The run keeps the key it was opened under, which is honest: it was minted, and the
    # report says so. What rung 4 changes is that the second call *finds* it rather than
    # opening a third run beside it.
    assert second.key.is_inferred is True
    assert len(seat.runs) == 1


@pytest.mark.asyncio
async def test_a_fresh_conversation_does_not_join_the_previous_run() -> None:
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, close_grace_seconds=0.0)
    first = seat.for_call("first task", is_continuation=False)
    second = seat.for_call("second task", is_continuation=False)
    assert second is not first


@pytest.mark.asyncio
async def test_the_explicit_wrapper_outranks_the_trace_rung() -> None:
    """A trace keys a run and never ends it; the wrapper does both, so it goes first."""
    from hyperstruck.runtime.run_key import DEFAULT_RESOLVERS, current_context_run_key

    assert DEFAULT_RESOLVERS[0] is current_context_run_key


@pytest.mark.asyncio
async def test_the_three_non_reinforcing_outcomes_are_told_apart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """They all reported `observed`, so the one field a reader consults said nothing.

    A run sent without a receipt, a run whose write-back raised, and a run whose only
    honest decline reason the boundary has not published are three different situations
    with three different repairs, and only the first is a weaker success.

    Case 3 withholds against an EMPTY published set rather than relying on a real reason
    being unpublished. It used to open a goalless run and expect `no_goal` to be
    withheld, which held only while the boundary had not taken that reason; publishing
    it turned this from a test of the withholding path into a test of the backlog, and
    the path would have gone uncovered at the moment a second unpublished reason
    appeared.
    """
    # 1. Sent, no receipt: a weaker success.
    client = FakeClient()
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    assert (await seat.close(run)).disposition == DISPOSITION_OBSERVED

    # 2. The write-back raised. The episode may or may not have landed.
    failing = FakeClient()

    async def _raise(**_: Any) -> None:
        raise RuntimeError("boundary down")

    failing.reinforce = _raise  # type: ignore[assignment]
    seat = _seat(failing)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    assert (await seat.close(run)).disposition == DISPOSITION_WRITE_FAILED

    # 3. Withheld: the honest reason is unpublished, so nothing was sent. Driven with a
    # published set that is NON-empty and simply lacks the reason. An empty set is a
    # different state entirely: it means the contract file could not be read, and the
    # escape hatch sends optimistically rather than withholding every decline, which is
    # what the next test pins.
    withholding = FakeClient()
    seat = _seat(withholding)
    monkeypatch.setattr(
        "hyperstruck._wire.published_decline_reasons",
        lambda: frozenset({"a_reason_this_turn_will_not_choose"}),
    )
    run = seat.open("   ")
    await seat.before_model_call(run)
    report = await seat.close(run)
    assert report.disposition == DISPOSITION_WITHHELD
    assert withholding.declined == []
    assert any("the boundary has not published" in w for w in run.withheld)


@pytest.mark.asyncio
async def test_an_unreadable_contract_sends_rather_than_withholding_every_decline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression a property-keyed gate introduces if it drops the escape hatch.

    ``published_names`` degrades a missing, truncated or wrong-shaped contract file to
    an EMPTY set by design. Under the old per-reason key that cost one reason and the
    other five still went out. Under a property key with no escape hatch an empty set
    withholds EVERY decline, so one corrupt JSON file in a wheel stops any run closing,
    fleet-wide, and each of those runs sits open holding its resolve reservation until
    the retention sweep with only the run report to show for it.

    ``wire_value`` already reasons this out for the recall half: an unreadable contract
    is not an empty one, and reading it as one turns a loud packaging fault into a silent
    data-integrity one. Sending optimistically is strictly no worse, because a genuinely
    unpublished reason is refused and the run is left open either way.
    """
    client = FakeClient()
    seat = _seat(client)
    monkeypatch.setattr("hyperstruck._wire.published_decline_reasons", frozenset)
    run = seat.open("g")
    await seat.before_model_call(run)
    report = await seat.close(run)
    assert report.disposition != DISPOSITION_WITHHELD
    assert [d["reason"] for d in client.declined] == ["no_tool_calls"]


@pytest.mark.asyncio
async def test_a_decline_that_never_landed_is_not_reported_as_declined() -> None:
    """The run is still open server-side, and a report saying otherwise stops the search."""
    client = FakeClient()

    async def _raise(**_: Any) -> None:
        raise RuntimeError("boundary down")

    client.decline = _raise  # type: ignore[assignment]
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    report = await seat.close(run)
    assert report.disposition == DISPOSITION_WRITE_FAILED
    # The reason it would have sent is still reported, so the reader knows what was meant.
    assert report.decline_reason == "no_tool_calls"


@pytest.mark.asyncio
async def test_a_run_displaced_under_a_live_key_is_reported_rather_than_orphaned() -> None:
    client = FakeClient()
    reports: list[RunReport] = []
    seat = RunSeat(client=client, identity=IDENTITY, on_report=reports.append)
    key = RunKey(key="shared", source="context", is_inferred=False)
    first = seat.open("first", run_key=key)
    await seat.before_model_call(first)
    seat.open("second", run_key=key)
    displaced = [r for r in reports if r.goal == "first"]
    assert displaced, "the first run vanished with no report"
    assert displaced[0].disposition == DISPOSITION_EVICTED


@pytest.mark.asyncio
async def test_a_resolve_whose_offer_is_unusable_reports_a_fault_not_a_short_run() -> None:
    """`recall_missing` is documented as "not a fault"; a malformed offer is one."""

    class _Bad(FakeClient):
        async def resolve(self, **_: Any) -> ResolvedContext:
            # Delivered ids the offer never contained: the shelf refuses to represent it.
            return ResolvedContext(
                injected_obligations_text="- o",
                offered_obligation_ids=("o1",),
                delivered_obligation_ids=("o1", "never-offered"),
            )

    client = _Bad()
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    report = await seat.close(run)
    assert report.recall_outcome == "resolve_failed"


def test_open_does_not_require_a_running_event_loop() -> None:
    """Reachable from synchronous host code, where raising would break their start-up."""
    seat = RunSeat(client=FakeClient(), identity=IDENTITY)
    run = seat.open("g")
    assert run.resolve_task is None


@pytest.mark.asyncio
async def test_a_run_trimmed_on_its_last_call_still_sends_the_evidence_it_earned() -> None:
    """The defect the first delivery fix introduced.

    `is_injected` latches and `receipt` is last-write-wins, so a run that delivered twice
    and was trimmed on its third call sent `is_delivered=True` with no receipt, which is
    the pair these fields exist to separate and which the platform escalates as a client
    defect.
    """
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    block = await seat.before_model_call(run)
    seat.after_model_call(run, f"system\n{block}")
    seat.after_model_call(run, f"system\n{block}")
    seat.after_model_call(run, "the trimmer emptied it")  # the last call only
    _steps(seat, run)
    report = await seat.close(run)

    # The wire gets the evidence the run genuinely earned.
    assert client.reinforced[0]["context_receipt"] is not None
    assert client.reinforced[0]["is_delivered"] is True
    assert report.is_receipt_sent is True
    # The report still surfaces the trim, which is what a mid-run trim exists to show.
    assert report.receipt_outcome == "unresolved"


def test_an_unrecognised_label_cannot_win_a_tie_and_read_as_no_declaration() -> None:
    """`join` ranked an unknown label 0, tied with secret, and ties returned the left.

    So a tool declared {"a": "Secret", "b": "secret"} propagated "Secret" onward, which
    looks maximally restrictive here and is *no declaration* at the boundary.
    """
    from hyperstruck.runtime.declarations import join as join_labels

    assert join_labels("Secret", "secret") == SECRET
    assert join_labels("SECRET", None) == SECRET
    assert join_labels("nonsense", SHAREABLE) == SHAREABLE
    assert join_labels("nonsense", None) is None


def test_an_unrecognised_label_does_not_become_a_tool_s_output_label() -> None:
    registry = DeclarationRegistry(
        [ToolDeclaration(name="fetch", args={"a": "Secret", "b": "secret"})]
    )
    assert registry.output_label("fetch") == SECRET


@pytest.mark.asyncio
async def test_an_escalation_is_reported_only_when_the_stamp_actually_moved() -> None:
    """Naming an earlier tool as the cause of a label the default had already set points
    the customer at the wrong remedy."""
    client = FakeClient()
    seat = RunSeat(
        client=client,
        identity=IDENTITY,
        declarations=DeclarationRegistry(
            [ToolDeclaration(name="lookup", args={"q": SECRET})]
        ),
    )
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(
        run,
        [
            ("1", "lookup", {"q": "x"}),
            ("2", "send", {"body": "quoting secret-value-1234 here"}),
        ],
    )
    seat.record_step(run, "1", "lookup", result="secret-value-1234")
    seat.record_step(run, "2", "send", result="sent")
    report = await seat.close(run)
    # `send` is undeclared, so `body` was already secret. Nothing escalated.
    assert not any("escalated" in line for line in report.withheld)
    assert any("undeclared argument" in line for line in report.withheld)


@pytest.mark.asyncio
async def test_the_boundary_s_presence_verdict_reaches_the_python_report_too() -> None:
    """The field existed in the TypeScript report alone, so the "one report shape"
    promise was true within a language and false across them: a customer moving from
    TypeScript to Python lost it silently, which is the failure the promise prevents."""

    class _WithPresence(FakeClient):
        async def reinforce(self, **kwargs: Any) -> tuple[dict[str, str], ...]:
            await super().reinforce(**kwargs)
            return ({"id": "a1", "outcome": "delivered_reformatted"},)

    client = _WithPresence(_context())
    seat = _seat(client)
    run = seat.open("g")
    block = await seat.before_model_call(run)
    seat.after_model_call(run, f"system\n{block}")
    _steps(seat, run)
    report = await seat.close(run)
    assert report.presence_outcomes == ({"id": "a1", "outcome": "delivered_reformatted"},)
    assert report.to_dict()["presence_outcomes"] == [
        {"id": "a1", "outcome": "delivered_reformatted"}
    ]


@pytest.mark.asyncio
async def test_a_boundary_that_returns_no_presence_verdict_yields_empty_not_a_guess() -> None:
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    assert (await seat.close(run)).presence_outcomes == ()


def _email_scanner() -> Any:
    class _Scanner:
        def scan(self, text: str):
            from hyperstruck.runtime.scanning import Finding

            index = text.find("ada@example.com")
            if index < 0:
                return ()
            return (Finding(start=index, end=index + 15, kind="EMAIL", label=USER_DATA),)

    return _Scanner()


@pytest.mark.asyncio
async def test_a_tool_s_error_is_scanned_because_it_shares_the_result_s_origin() -> None:
    """Same tool, same call, same step. Covering one and not the other was an
    inconsistency, and a stack trace carrying a customer record is an ordinary failure."""
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, scanner=_email_scanner())
    run = seat.open("g")
    await seat.before_model_call(run)
    seat.record_planned_calls(run, [("1", "a", {}), ("2", "b", {})])
    seat.record_step(run, "1", "a", error="lookup failed for ada@example.com")
    seat.record_step(run, "2", "b", result="ok")
    await seat.close(run)
    assert "ada@example.com" not in str(client.observed[0])


@pytest.mark.asyncio
async def test_a_tool_schema_is_scanned_because_it_is_stored_with_the_learning() -> None:
    """``ToolSpec`` says "pre-redact: these are stored alongside the learning" and nothing
    enforced it. A schema's ``examples`` are routinely real values."""
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, scanner=_email_scanner())
    run = seat.open(
        "g",
        (
            ToolSpec(
                name="lookup",
                parameters={
                    "properties": {"email": {"type": "string", "examples": ["ada@example.com"]}}
                },
            ),
        ),
    )
    await seat.before_model_call(run)
    seat.record_planned_calls(run, [("1", "a", {}), ("2", "b", {})])
    seat.record_step(run, "1", "a", result="ok")
    seat.record_step(run, "2", "b", result="ok")
    report = await seat.close(run)
    assert "ada@example.com" not in str(client.observed[0].available_tools)
    assert any("(schema)" in line for line in report.withheld)


@pytest.mark.asyncio
async def test_the_goal_is_not_scanned_because_its_origin_is_the_principal() -> None:
    """Origin, not a field list: the goal comes from the human, which is the case origin
    labelling already handles, and it is what a learning is transferable against."""
    client = FakeClient()
    seat = RunSeat(client=client, identity=IDENTITY, scanner=_email_scanner())
    run = seat.open("reconcile for ada@example.com")
    await seat.before_model_call(run)
    _steps(seat, run)
    await seat.close(run)
    assert client.observed[0].goal == "reconcile for ada@example.com"


# -- loop-level obligation closure through the seat ------------------------------


_APPLIED = ObligationClosureResult(id="o1", disposition="applied", status="kept")
_KEPT = ReportedObligationOutcome(id="o1", outcome="kept", kept_basis="reported")


class _Closing(FakeClient):
    """A boundary at this version: it answers both calls with a ``ReinforceResult``."""

    async def reinforce(self, **kwargs: Any) -> ReinforceResult:
        await super().reinforce(**kwargs)
        return ReinforceResult(obligation_closures=(_APPLIED,))

    async def decline(self, **kwargs: Any) -> ReinforceResult:
        await super().decline(**kwargs)
        return ReinforceResult(obligation_closures=(_APPLIED,))


@pytest.mark.asyncio
async def test_the_outcomes_a_close_reports_reach_the_boundary_and_their_results_the_report() -> None:
    client = _Closing(_context())
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    report = await seat.close(run, obligation_outcomes=[_KEPT])
    assert client.reinforced[0]["obligation_outcomes"] == (_KEPT,)
    assert report.obligation_closures == (_APPLIED,)
    assert report.to_dict()["obligation_closures"] == [
        {"id": "o1", "disposition": "applied", "status": "kept"}
    ]


@pytest.mark.asyncio
async def test_a_declined_turn_carries_its_outcomes_and_reports_their_results_too() -> None:
    """The decline leg, which is the one a goalless or toolless turn takes.

    A turn can resolve an obligation and be worth learning nothing from, and a host that
    only got closure results on the reinforce leg would silently lose them on that turn.
    """
    client = _Closing(_context())
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    report = await seat.close(run, obligation_outcomes=[_KEPT])
    assert report.disposition == DISPOSITION_DECLINED
    assert client.declined[0]["obligation_outcomes"] == (_KEPT,)
    assert report.obligation_closures == (_APPLIED,)


@pytest.mark.asyncio
async def test_a_close_reporting_nothing_never_passes_the_parameter_at_all() -> None:
    """So a client written against the port before the parameter existed is driven as it was.

    This seat drives whatever client it was handed, including one a customer implemented
    against ``LearningClient`` at an earlier version. Passing the keyword unconditionally
    would raise ``TypeError`` inside the write guard and turn every such run into
    ``write_failed``.

    Driven with the plain fake, which returns ``None``, so this covers the other half of
    the same seam: a client that answers with nothing at all still closes the run.
    """
    client = FakeClient(_context())
    seat = _seat(client)
    run = seat.open("g")
    await seat.before_model_call(run)
    _steps(seat, run)
    report = await seat.close(run)
    assert "obligation_outcomes" not in client.reinforced[0]
    assert report.disposition == DISPOSITION_OBSERVED
    assert report.obligation_closures == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        ({"id": "a1", "outcome": "delivered_verbatim"},),
        [{"id": "a1", "outcome": "delivered_verbatim"}],
    ],
)
async def test_a_client_returning_the_older_bare_sequence_still_reports_its_presence(
    answer: Any,
) -> None:
    """The version-skew seam, in both shapes an older client could return.

    A client written against 0.8.0 returns the presence verdicts alone, as a tuple or a
    list. Reading ``.presence_outcomes`` off that would raise outside the write guard,
    which is the one thing this seat promises never to do to a host run.
    """

    class _Older(FakeClient):
        async def reinforce(self, **kwargs: Any) -> Any:
            await super().reinforce(**kwargs)
            return answer

    seat = _seat(_Older(_context()))
    run = seat.open("g")
    block = await seat.before_model_call(run)
    seat.after_model_call(run, f"system\n{block}")
    _steps(seat, run)
    report = await seat.close(run)
    assert report.presence_outcomes == ({"id": "a1", "outcome": "delivered_verbatim"},)
    assert report.obligation_closures == ()
