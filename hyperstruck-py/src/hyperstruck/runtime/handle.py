"""The explicit run handle: exact boundaries for a caller willing to name them.

The escape hatch, not the headline. It is the only rung of the run-key ladder that is
exact in both directions: it supplies the key *and* the end, where a trace context
supplies a key and never an end (the bare OpenTelemetry API gives no span-end
notification), and where the traffic-shape trigger supplies an end that is one grace
window late. A caller who wants the run report to line up exactly with their own episode
boundary uses this, and a runtime with no seam at all has nothing else.

``RunSeat.open`` and ``RunSeat.close`` already do the work; this adds nothing to the core
and exists for two reasons. The close cannot be forgotten on a throwing path, which is the
mistake that leaves a run open holding its resolve reservation until the server's reclaim
sweep notices, and that is indistinguishable from a host that stopped writing back. And
the key is bound in context for the duration, so any model call the body makes through a
wrapped client joins this run rather than minting one of its own, which is what makes the
handle compose with the model-layer seat instead of competing with it.

The TypeScript package's ``withRun`` is the same thing in that language's idiom, and a
parity test pins the two behaviours together.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager

from hyperstruck._wire import ToolSpec
from hyperstruck.runtime.run import HyperstruckRun, RunReport, RunSeat
from hyperstruck.runtime.run_key import RunKey, reset_current_run, set_current_run

# The rung this handle occupies, reported on every run it opens. Named rather than
# inferred, because the report's reader is entitled to know that this run's boundaries
# were declared rather than guessed at.
HANDLE_SOURCE = "context"


@asynccontextmanager
async def hyperstruck_run(
    seat: RunSeat,
    goal: str,
    tools: Sequence[ToolSpec] = (),
    *,
    thread_id: str | None = None,
    on_report: Callable[[RunReport], None] | None = None,
) -> AsyncIterator[HyperstruckRun]:
    """Open a run with exact boundaries, and close it on the way out either way.

    ``on_report`` hands the report back inline for a caller who wants it there rather
    than off the seat's own callback. It is the same report, never a subset: a customer
    who moves between attachment points must not silently lose a field.

    A body that raises closes the run as unsuccessful rather than not closing it at all.
    A failed episode is evidence, and a failure recovered from later is the
    highest-signal turn the corpus gets, so swallowing it would cost the very thing the
    gate keeps.
    """
    key = RunKey(key=uuid.uuid4().hex, source=HANDLE_SOURCE, is_inferred=False)
    token = set_current_run(key.key)
    run = seat.open(goal, tools, thread_id=thread_id, run_key=key)
    is_success = True
    try:
        yield run
    except BaseException:
        is_success = False
        raise
    finally:
        try:
            if not run.is_closed:
                report = await seat.close(run, is_success=is_success)
                if on_report is not None:
                    on_report(report)
        finally:
            # Reset even if the close raised, or the caller's context keeps a key naming
            # a run that no longer exists and the next call joins a closed ledger.
            reset_current_run(token)
