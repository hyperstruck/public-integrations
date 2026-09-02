/**
 * The explicit run handle, in the language's own idiom.
 *
 * The escape hatch, not the headline. It is the only rung of the run-key ladder that is
 * exact in both directions: it supplies the key *and* the end, where a trace context
 * supplies a key and never an end (the bare OpenTelemetry API gives no span-end
 * notification), and where the traffic-shape trigger supplies an end that is one grace
 * window late. A caller who wants the run report to line up exactly with their own
 * episode boundary uses this, and a runtime with no seam at all has nothing else.
 *
 * The Python package's `seat.open()` / `seat.close()` pair is the same thing with the
 * try/finally written out; this wrapper exists so the two languages read the same and so
 * the close cannot be forgotten on a throwing path.
 */

import { randomUUID } from "node:crypto";

import type { HyperstruckRun, RunReport, RunSeat } from "./runtime/run.ts";
import { CLOSE_TRIGGER_EXPLICIT } from "./runtime/run.ts";
import { runWithKey } from "./runtime/runKey.ts";
import type { ToolSpec } from "./wire.ts";

export interface WithRunOptions {
  readonly tools?: readonly ToolSpec[];
  readonly threadId?: string | null;
  /** Called with the run's report once it closes, for a caller that wants it inline
   * rather than off the seat's callback. The same report either way, never a subset. */
  readonly onReport?: (report: RunReport) => void;
}

/**
 * Run `body` inside an explicit Hyperstruck run, closing it on the way out either way.
 *
 * The key is bound in async context for the duration, so any model call the body makes
 * through a wrapped model joins this run rather than minting one of its own.
 *
 * The run is closed in a `finally`, because a run left neither reinforced nor declined
 * sits open holding its resolve reservation until the server's reclaim sweep notices, and
 * that is indistinguishable from a host that stopped writing back. A throwing body closes
 * as unsuccessful rather than not closing at all: a failed episode is evidence, and a
 * failure recovered from later is the highest-signal turn the corpus gets.
 */
export async function withRun<T>(
  seat: RunSeat,
  goal: string,
  body: (run: HyperstruckRun) => Promise<T>,
  options: WithRunOptions = {},
): Promise<T> {
  const key = {
    key: randomUUID().replace(/-/g, ""),
    source: "context",
    isInferred: false,
  };
  return await runWithKey(key.key, async () => {
    const run = seat.open(goal, options.tools ?? [], {
      threadId: options.threadId ?? null,
      runKey: key,
    });
    let isSuccess = true;
    try {
      return await body(run);
    } catch (error) {
      isSuccess = false;
      throw error;
    } finally {
      if (!run.isClosed) {
        const report = await seat.close(run, {
          isSuccess,
          trigger: CLOSE_TRIGGER_EXPLICIT,
        });
        options.onReport?.(report);
      }
    }
  });
}
