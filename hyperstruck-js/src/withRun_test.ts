import assert from "node:assert/strict";
import { test } from "node:test";

import type { DeclineRequest, LearningClient, ReinforceRequest } from "./client.ts";
import { hyperstruckMiddleware } from "./aiSdk.ts";
import { RunSeat, type RunReport } from "./runtime/run.ts";
import { resolveRunKey } from "./runtime/runKey.ts";
import type {
  Episode,
  ObligationClosureResult,
  ReinforceResult,
  ResolvedContext,
} from "./wire.ts";
import { withRun } from "./withRun.ts";

const EMPTY: ResolvedContext = {
  injectedText: null,
  injectedFactsText: null,
  injectedObligationsText: null,
  offeredLearningIds: [],
  offeredClaimIds: [],
  offeredObligationIds: [],
  deliveredObligationIds: [],
};

class FakeClient implements LearningClient {
  observed: Episode[] = [];
  reinforced: ReinforceRequest[] = [];
  declined: DeclineRequest[] = [];
  declineClosures: readonly ObligationClosureResult[] = [];
  async resolve(): Promise<ResolvedContext> {
    return EMPTY;
  }
  async observe(request: { episode: Episode }): Promise<void> {
    this.observed.push(request.episode);
  }
  async reinforce(request: ReinforceRequest): Promise<ReinforceResult> {
    this.reinforced.push(request);
    return { presenceOutcomes: [], obligationClosures: [] };
  }
  async decline(request: DeclineRequest): Promise<ReinforceResult> {
    this.declined.push(request);
    return { presenceOutcomes: [], obligationClosures: this.declineClosures };
  }
  async drain(): Promise<void> {}
  async replayDurableQueue(): Promise<number> {
    return 0;
  }
  async close(): Promise<void> {}
}

function build() {
  const client = new FakeClient();
  const reports: RunReport[] = [];
  const seat = new RunSeat({
    client,
    identity: { agentName: "agent" },
    onReport: (report) => reports.push(report),
  });
  return { client, seat, reports };
}

test("the run closes on the way out and its key is exact rather than inferred", async () => {
  const { seat, reports } = build();
  const returned = await withRun(seat, "reconcile the invoice", async (run) => {
    assert.equal(run.isClosed, false);
    return 42;
  });
  assert.equal(returned, 42);
  assert.equal(reports.length, 1);
  assert.equal(reports[0]?.runKeySource, "context");
  assert.equal(reports[0]?.isRunKeyInferred, false);
  assert.equal(reports[0]?.closeTrigger, "explicit");
  assert.equal(seat.runs.size, 0);
});

test("a throwing body still closes the run, as unsuccessful", async () => {
  const { client, seat, reports } = build();
  await assert.rejects(
    withRun(seat, "g", async (run) => {
      seat.recordPlannedCalls(run, [
        { callId: "1", name: "a", args: {} },
        { callId: "2", name: "b", args: {} },
      ]);
      seat.recordStep(run, "1", "a", { result: "ok" });
      seat.recordStep(run, "2", "b", { result: "ok" });
      throw new Error("host blew up");
    }),
    /host blew up/,
  );
  assert.equal(reports.length, 1);
  assert.equal(client.observed[0]?.outcome?.isSuccess, false);
});

test("a body that closed the run itself is not closed twice", async () => {
  const { seat, reports } = build();
  await withRun(seat, "g", async (run) => {
    await seat.beforeModelCall(run);
    await seat.close(run);
  });
  assert.equal(reports.length, 1);
});

test("the key is bound in async context, so a model call inside joins this run", async () => {
  const { seat } = build();
  await withRun(seat, "g", async (run) => {
    // Anything resolving the ladder inside the body sees the run's own key, which is what
    // makes a wrapped model join this run rather than minting one of its own.
    assert.ok(run.runId.startsWith(`agent:${resolveRunKey().key}:`));
  });
});

test("a wrapped model call inside the handle lands in the handle's run", async () => {
  const { client, seat } = build();
  const middleware = hyperstruckMiddleware({ seat });
  await withRun(seat, "reconcile the invoice", async (run) => {
    const params = await middleware.transformParams({
      params: { prompt: [{ role: "user", content: [{ type: "text", text: "go" }] }] },
    });
    await middleware.wrapGenerate({
      doGenerate: async () => ({
        content: [
          { type: "tool-call", toolCallId: "1", toolName: "a", input: {} },
          { type: "tool-call", toolCallId: "2", toolName: "b", input: {} },
        ],
      }),
      params,
    });
    seat.recordStep(run, "1", "a", { result: "ok" });
    seat.recordStep(run, "2", "b", { result: "ok" });
    assert.equal(seat.runs.size, 1);
  });
  // The goal is the handle's, not the inferred one, because the handle opened the run.
  assert.equal(client.observed[0]?.goal, "reconcile the invoice");
  assert.equal(client.observed[0]?.steps?.length, 2);
});

test("two concurrent handles keep their runs apart", async () => {
  const { seat, reports } = build();
  await Promise.all([
    withRun(seat, "left", async () => {
      await new Promise((resolve) => setTimeout(resolve, 5));
    }),
    withRun(seat, "right", async () => {}),
  ]);
  assert.deepEqual(reports.map((report) => report.goal).sort(), ["left", "right"]);
  assert.notEqual(reports[0]?.runId, reports[1]?.runId);
});

test("the handle's own callback carries the same report the seat's does", async () => {
  const { seat, reports } = build();
  let handed: RunReport | null = null;
  await withRun(seat, "g", async () => {}, { onReport: (report) => (handed = report) });
  assert.equal(handed, reports[0]);
});
