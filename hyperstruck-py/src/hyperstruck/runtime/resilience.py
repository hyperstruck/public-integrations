"""What the client does when the boundary is slow, broken, or gone.

Three mechanisms, each answering a failure this client currently has no answer for.

**Jitter**, because the existing backoff is ``retry_backoff * 2**attempt`` with no
randomisation, so every concurrent run retries on an identical schedule and the retries
arrive as a wave. That is tolerable in the LangGraph seat, where one graph invocation is
one run; it is not in a standalone service where one client instance fronts many runs at
once. The scheme here is equal jitter, half the interval fixed and half random, which is
the middle option in AWS's "Exponential Backoff And Jitter": full jitter can schedule a
retry at nearly zero and re-converge, and no jitter is the wave we are removing.

**A circuit breaker over resolve**, because there is none anywhere in the client and
resolve fails open per run with nothing shared between runs, against a measured p99 of
18.7 seconds. Without a breaker a degraded boundary costs the host that tail *per run*. The
breaker makes it cost one timeout, after which every run fails open immediately and pays
nothing. It is process-wide and keyed by base URL, so two clients pointed at one boundary
share the observation and two pointed at different boundaries do not.

**A durable write queue**, which deliberately overturns a rejection this package documents
at the top of ``client.py``, and the override is scoped. That rejection says a thin client
runs in serverless, read-only and multi-replica environments where local disk state is
variously impossible, useless or a correctness hazard. That reasoning holds and is not
being called wrong. What changed is the host: a standalone long-lived single-process
service is the first host of that shape we have had, and it is also the host that loses
days of testing to 403s and 503s. So durability is **opt-in, off by default**, refuses to
enable itself on a read-only filesystem, and the documented default stays the in-memory
queue.

Two consequences follow from that and both are requirements rather than niceties. The
store holds episode content, so it inherits the same redaction the wire does, which it gets
by construction here: the payload handed to the queue has already been through
``redact_episode_payload``, and the queue persists exactly what would have been sent.
And the queue needs a synchronous flush mode, because if nothing guarantees an event loop
or a process outliving the scheduling call, every observe, reinforce and decline is dropped
at teardown with no error anywhere, which is the failure a fire-and-forget queue has in
precisely the serverless host the original rejection was written for.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import logging
import os
import random
import tempfile
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# How many consecutive resolve failures open the breaker. Three rather than one, because a
# single timeout is ordinary tail latency on a boundary whose p99 is 18.7s and opening on
# it would take a healthy deployment's recall away for the cooldown.
DEFAULT_FAILURE_THRESHOLD = 3

# How long the breaker stays open before letting one probe through. Thirty seconds is short
# enough that a boundary recovering from a deploy is picked up within a run or two, and long
# enough that an outage is not re-probed by every run.
DEFAULT_BREAKER_COOLDOWN = 30.0

# How many parked writes the outbox keeps. Unbounded, a boundary that is down for a day
# fills the customer's disk with episodes nobody will ever read: the platform dedupes by run
# id, so an old parked write's value decays to nothing while its cost does not. The oldest
# go first, because the newest are the ones still worth delivering.
MAX_PARKED_WRITES = 5_000


def backoff_delay(base: float, attempt: int, *, rand: random.Random | None = None) -> float:
    """Equal jitter: half the interval fixed, half random.

    Written by hand rather than reached for from ``tenacity`` or ``stamina``. This package
    ships exactly one runtime dependency, ``httpx``, as a stated design property, and a few
    lines of arithmetic is not a reason to spend it.
    """
    interval = base * (2**attempt)
    half = interval / 2
    return half + (rand or random).uniform(0, half)


class CircuitOpenError(RuntimeError):
    """Resolve was not attempted: the breaker is open on this boundary.

    A distinct type rather than a timeout, because the two license different readings. A
    timeout is this run's own observation of a slow boundary. This is a report that other
    runs already made that observation and this one is being spared the wait, which is the
    breaker working rather than a fault of the run that sees it.
    """


class ResolveBreaker:
    """One boundary's health, shared by every run in the process.

    Deliberately not per client instance. The whole value is that the *second* run does not
    repeat the first one's timeout, and a per-instance breaker in a service that constructs
    a client per request would never see a second failure.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        cooldown: float = DEFAULT_BREAKER_COOLDOWN,
    ) -> None:
        self._failure_threshold = max(1, failure_threshold)
        self._cooldown = cooldown
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._is_probing = False
        self.trips = 0

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None

    def before_request(self, now: float | None = None) -> None:
        """Raise if the call must not be attempted; return to let it through.

        One probe is admitted per cooldown once it has elapsed. Only one, because a
        boundary that is still down must not be handed the whole backlog at the moment the
        cooldown expires, which is the thundering herd the breaker exists to prevent
        arriving one cooldown later.
        """
        if self._opened_at is None:
            return
        moment = time.monotonic() if now is None else now
        if moment - self._opened_at < self._cooldown:
            raise CircuitOpenError(
                "resolve skipped: the learning boundary is failing and the circuit is "
                "open; this run proceeds without recalled context"
            )
        if self._is_probing:
            raise CircuitOpenError(
                "resolve skipped: a probe of the failing boundary is already in flight"
            )
        self._is_probing = True

    def release_probe(self) -> None:
        """Give back the probe slot without judging the boundary.

        For an outcome that is neither evidence of health nor of failure, of which a 4xx is
        the one that matters: the caller's payload was wrong and the boundary answered
        promptly. Without this the slot claimed by :meth:`before_request` is never returned
        and the breaker stays latched half-open for the life of the process.
        """
        self._is_probing = False

    def record_success(self) -> None:
        """Close the breaker. A single success is enough, by design.

        Requiring a run of successes would keep recall switched off through a recovery that
        has already happened, and the cost of closing too early is one more timeout, which
        immediately re-opens it.
        """
        self._consecutive_failures = 0
        self._opened_at = None
        self._is_probing = False

    def record_failure(self, now: float | None = None) -> None:
        self._is_probing = False
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold and self._opened_at is None:
            self._opened_at = time.monotonic() if now is None else now
            self.trips += 1
            logger.warning(
                "Hyperstruck resolve circuit opened after %d consecutive failures; runs "
                "will proceed without recalled context for %.0fs",
                self._consecutive_failures,
                self._cooldown,
            )
        elif self._opened_at is not None:
            self._opened_at = time.monotonic() if now is None else now


_BREAKERS: dict[str, ResolveBreaker] = {}


def breaker_for(base_url: str) -> ResolveBreaker:
    """The process-wide breaker for one boundary, created on first use."""
    breaker = _BREAKERS.get(base_url)
    if breaker is None:
        breaker = ResolveBreaker()
        _BREAKERS[base_url] = breaker
    return breaker


def reset_breakers() -> None:
    """Drop every breaker. For tests, and for a host that forks after configuring."""
    _BREAKERS.clear()


@dataclass(frozen=True)
class PendingWrite:
    """One write waiting to be delivered, and where it is parked on disk."""

    path: Path
    endpoint: str
    body: dict


class DurableOutbox:
    """An on-disk parking bay for writes that have not landed yet.

    Off by default and never enabled implicitly. Enabling it on a host that cannot support
    it is worse than not having it, so :meth:`open` refuses rather than degrading: a store
    that silently fails to write is a corpus that silently never fills.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._sequence = itertools.count()

    @classmethod
    def open(cls, directory: str | os.PathLike[str]) -> DurableOutbox | None:
        """Prepare the store, or return ``None`` with a reason logged.

        The read-only check is a real write rather than an ``os.access`` probe, because
        ``access`` answers about permission bits and the case this guards is a read-only
        mount, where the bits say yes and the write fails.
        """
        path = Path(directory)
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / f".probe-{uuid.uuid4().hex}"
            probe.write_text("", encoding="utf-8")
            # The store holds episode content, which is why it inherits the wire's redaction.
            # It should not also be world-readable on a shared host.
            path.chmod(0o700)
            probe.unlink()
        except OSError as exc:
            logger.warning(
                "Hyperstruck durable outbox disabled: %s is not writable (%s). Writes "
                "stay in memory, which is the documented default.",
                path,
                exc,
            )
            return None
        return cls(path)

    def park(self, endpoint: str, body: dict) -> Path | None:
        """Persist one write, atomically, and return where it landed.

        Written to a temporary file in the same directory and then renamed, so a process
        killed mid-write leaves no half-parsed episode for the next start to trip over.
        """
        parked_at = time.time()
        record = {"endpoint": endpoint, "body": body, "parked_at": parked_at}
        temporary = ""
        try:
            handle, temporary = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
            # mkstemp already creates at 0o600; stated here because the guarantee matters
            # rather than because the call needs help.
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(record, stream)
            # Time-ordered name, because ``pending`` promises oldest first and a bare uuid
            # sorts randomly. The counter keeps two writes in the same millisecond apart,
            # and the uuid keeps two processes sharing one directory apart.
            destination = (
                self.directory
                / f"{parked_at:015.4f}-{next(self._sequence):06d}-{uuid.uuid4().hex}.json"
            )
            os.replace(temporary, destination)
            self._trim()
            return destination
        except (OSError, TypeError, ValueError) as exc:
            # A payload that will not serialise is a client bug, and losing the write is
            # the lesser harm: raising here would break the host's run for a durability
            # feature it opted into for the opposite reason. The half-written temporary is
            # removed rather than left: it is invisible to ``pending`` (which reads
            # ``*.json``) and so would accumulate forever, one file per failure.
            logger.warning("Hyperstruck durable outbox could not park a write: %s", exc)
            with contextlib.suppress(OSError, UnboundLocalError, NameError):
                Path(temporary).unlink(missing_ok=True)
            return None

    def _trim(self) -> None:
        """Drop the oldest parked writes once the store is over its cap."""
        try:
            paths = sorted(self.directory.glob("*.json"))
            for stale in paths[: max(0, len(paths) - MAX_PARKED_WRITES)]:
                stale.unlink(missing_ok=True)
        except OSError:
            # A trim that cannot run is not a reason to lose the write it was making room
            # for.
            return

    def release(self, path: Path | None) -> None:
        """Forget a write that has landed. A missing file is already forgotten."""
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Hyperstruck durable outbox could not release %s: %s", path, exc)

    def pending(self) -> Iterator[PendingWrite]:
        """Every parked write, oldest first, skipping any that will not parse.

        A file that will not parse is dropped rather than retried forever: it cannot be
        delivered, and leaving it would make every later drain re-read it.
        """
        try:
            paths = sorted(self.directory.glob("*.json"))
        except OSError:
            return
        for path in paths:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                endpoint = record["endpoint"]
                body = record["body"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                logger.warning(
                    "Hyperstruck durable outbox discarding unreadable write %s: %s",
                    path,
                    exc,
                )
                self.release(path)
                continue
            yield PendingWrite(path=path, endpoint=endpoint, body=body)
