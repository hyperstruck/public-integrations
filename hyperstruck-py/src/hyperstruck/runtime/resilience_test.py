"""What the client does when the boundary is slow, broken, or gone."""

from __future__ import annotations

from pathlib import Path

import json
import random
import stat

import pytest

from hyperstruck.runtime import resilience
from hyperstruck.runtime.resilience import (
    CircuitOpenError,
    DurableOutbox,
    ResolveBreaker,
    backoff_delay,
    breaker_for,
    reset_breakers,
)


def test_jitter_spreads_retries_that_used_to_land_on_one_schedule() -> None:
    """The wave is the defect: every concurrent run retried at the identical instant.

    Equal jitter keeps half the interval fixed, so a retry is never scheduled at nearly
    zero and cannot re-converge the way full jitter can.
    """
    interval = 0.5 * (2**2)
    delays = {
        backoff_delay(0.5, 2, rand=random.Random(seed)) for seed in range(20)
    }
    assert len(delays) > 1
    assert all(interval / 2 <= delay <= interval for delay in delays)


def test_the_breaker_stays_closed_through_ordinary_tail_latency() -> None:
    """One timeout on a boundary whose p99 is 18.7s is not an outage.

    Opening on it would take a healthy deployment's recall away for the whole cooldown.
    """
    breaker = ResolveBreaker(failure_threshold=3, cooldown=30.0)
    breaker.record_failure()
    breaker.record_failure()
    breaker.before_request()
    assert breaker.is_open is False


def test_an_open_breaker_costs_a_run_nothing_instead_of_a_timeout() -> None:
    """The whole point: a degraded boundary costs the host one timeout, not one per run."""
    breaker = ResolveBreaker(failure_threshold=2, cooldown=30.0)
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.is_open is True
    with pytest.raises(CircuitOpenError):
        breaker.before_request()
    assert breaker.trips == 1


def test_only_one_probe_is_admitted_when_the_cooldown_expires() -> None:
    """Otherwise the herd arrives one cooldown later instead of not at all."""
    breaker = ResolveBreaker(failure_threshold=1, cooldown=10.0)
    breaker.record_failure(now=0.0)
    breaker.before_request(now=100.0)  # the probe is let through
    with pytest.raises(CircuitOpenError):
        breaker.before_request(now=100.0)


def test_one_success_closes_the_breaker() -> None:
    """Requiring a run of successes keeps recall off through a recovery already made.

    Closing too early costs one more timeout, which immediately re-opens it, so the
    asymmetry favours closing.
    """
    breaker = ResolveBreaker(failure_threshold=1, cooldown=0.0)
    breaker.record_failure()
    breaker.before_request()
    breaker.record_success()
    assert breaker.is_open is False
    breaker.before_request()


def test_the_breaker_is_shared_per_boundary_and_not_per_client() -> None:
    """A service constructing a client per request would never see a second failure."""
    reset_breakers()
    try:
        assert breaker_for("https://api.example.com") is breaker_for(
            "https://api.example.com"
        )
        assert breaker_for("https://api.example.com") is not breaker_for(
            "https://other.example.com"
        )
    finally:
        reset_breakers()


def test_the_outbox_refuses_a_read_only_location_rather_than_failing_silently(
    tmp_path,
) -> None:
    """A store that silently fails to write is a corpus that silently never fills.

    The probe is a real write rather than an ``os.access`` check, because the case this
    guards is a read-only mount, where the permission bits say yes and the write fails.
    """
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        assert DurableOutbox.open(locked) is None
    finally:
        locked.chmod(stat.S_IRWXU)


def test_a_parked_write_survives_the_process_that_scheduled_it(tmp_path) -> None:
    """The whole reason durability is offered: an outage that outlives the process."""
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    outbox.park("/observe", {"run_id": "r1"})
    outbox.park("/reinforce", {"run_id": "r1"})

    reopened = DurableOutbox.open(tmp_path)
    assert reopened is not None
    pending = list(reopened.pending())
    assert {write.endpoint for write in pending} == {"/observe", "/reinforce"}


def test_a_released_write_is_not_replayed(tmp_path) -> None:
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    path = outbox.park("/observe", {"run_id": "r1"})
    outbox.release(path)
    assert list(outbox.pending()) == []
    # Releasing twice is not an error: a write that has landed is already forgotten.
    outbox.release(path)


def test_an_unreadable_parked_write_is_discarded_rather_than_retried_forever(
    tmp_path,
) -> None:
    """It cannot be delivered, and leaving it makes every later drain re-read it."""
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    (tmp_path / "corrupt.json").write_text("{not json", encoding="utf-8")
    outbox.park("/observe", {"run_id": "r1"})
    pending = list(outbox.pending())
    assert [write.endpoint for write in pending] == ["/observe"]
    assert not (tmp_path / "corrupt.json").exists()


def test_a_payload_that_will_not_serialise_loses_the_write_rather_than_the_run(
    tmp_path,
) -> None:
    """Raising here would break the host's run for a feature opted into for the opposite reason."""
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    assert outbox.park("/observe", {"body": object()}) is None


def test_parking_is_atomic_so_a_kill_leaves_no_half_written_episode(tmp_path) -> None:
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    outbox.park("/observe", {"run_id": "r1", "goal": "g"})
    parked = list(tmp_path.glob("*.json"))
    assert len(parked) == 1
    assert json.loads(parked[0].read_text(encoding="utf-8"))["body"]["goal"] == "g"
    assert list(tmp_path.glob("*.tmp")) == []


def test_the_outbox_replays_oldest_first_as_its_docstring_promises(tmp_path: Path) -> None:
    """The names used to be bare uuids, so "oldest first" sorted randomly."""
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    for index in range(6):
        outbox.park("/observe", {"n": index})
    assert [write.body["n"] for write in outbox.pending()] == [0, 1, 2, 3, 4, 5]


def test_the_outbox_drops_its_oldest_once_over_the_cap(tmp_path: Path, monkeypatch) -> None:
    """Unbounded, a boundary down for a day fills the customer's disk with dead episodes."""
    monkeypatch.setattr(resilience, "MAX_PARKED_WRITES", 3)
    outbox = DurableOutbox.open(tmp_path)
    assert outbox is not None
    for index in range(6):
        outbox.park("/observe", {"n": index})
    kept = [write.body["n"] for write in outbox.pending()]
    assert kept == [3, 4, 5], f"kept {kept}"


def test_a_4xx_gives_back_the_probe_slot_rather_than_latching_the_breaker(tmp_path: Path) -> None:
    """`before_request` claims the slot; a path that records neither outcome kept it."""
    breaker = ResolveBreaker(failure_threshold=1, cooldown=100.0)
    breaker.record_failure(now=0.0)
    breaker.before_request(now=200.0)  # the one probe per cooldown
    breaker.release_probe()  # a 4xx: not the boundary's fault, but the slot is returned
    # Without the release this raises "a probe is already in flight", for ever.
    breaker.before_request(now=201.0)
