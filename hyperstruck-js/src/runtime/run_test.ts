import assert from "node:assert/strict";
import { test } from "node:test";

import type { DeclineRequest, LearningClient, ReinforceRequest } from "../client.ts";
import type { AgentIdentity } from "../identity.ts";
import type {
  Episode,
  ObligationClosureResult,
  PresenceOutcome,
  ReinforceResult,
  ReportedObligationOutcome,
  ResolvedContext,
} from "../wire.ts";
import { publishedDeclineReasons } from "../contracts.ts";
import { DeclarationRegistry, join as joinSensitivity } from "./declarations.ts";
import {
  CLOSE_TRIGGER_ABANDONED,
  DISPOSITION_DECLINED,
  DISPOSITION_EVICTED,
  DISPOSITION_OBSERVED,
  DISPOSITION_REINFORCED,
  HyperstruckRun,
  isUnpublishedDeclineReason,
  OUTCOME_DELIVERED,
  OUTCOME_RECALL_MISSING,
  OUTCOME_RECALL_UNCLAIMED,
  OUTCOME_RESOLVE_EMPTY,
  OUTCOME_RESOLVE_FAILED,
  recallOutcome,
  reportToJson,
  RunRegistry,
  RunSeat,
  type RunReport,
} from "./run.ts";

const IDENTITY: AgentIdentity = { agentName: "agent" };

const EMPTY_CONTEXT: ResolvedContext = {
  injectedText: null,
  injectedFactsText: null,
  injectedObligationsText: null,
  offeredLearningIds: [],
  offeredClaimIds: [],
  offeredObligationIds: [],
  deliveredObligationIds: [],
};

class FakeClient implements LearningClient {
  context: ResolvedContext = EMPTY_CONTEXT;
  resolveError: Error | null = null;
  presence: readonly PresenceOutcome[] = [];
  closures: readonly ObligationClosureResult[] = [];
  declineClosures: readonly ObligationClosureResult[] = [];
  observed: Episode[] = [];
  reinforced: ReinforceRequest[] = [];
  declined: DeclineRequest[] = [];

  async resolve(): Promise<ResolvedContext> {
    if (this.resolveError !== null) throw this.resolveError;
    return this.context;
  }
  async observe(request: { episode: Episode }): Promise<void> {
    this.observed.push(request.episode);
  }
  async reinforce(request: ReinforceRequest): Promise<ReinforceResult> {
    this.reinforced.push(request);
    return { presenceOutcomes: this.presence, obligationClosures: this.closures };
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

function seatWith(client: FakeClient, options: Record<string, unknown> = {}) {
  const reports: RunReport[] = [];
  const seat = new RunSeat({
    client,
    identity: IDENTITY,
    onReport: (report) => reports.push(report),
    ...options,
  });
  return { seat, reports };
}

function twoSteps(seat: RunSeat, run: HyperstruckRun): void {
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "search", args: { q: "x" } },
    { callId: "2", name: "write", args: { body: "y" } },
  ]);
  seat.recordStep(run, "1", "search", { result: "found" });
  seat.recordStep(run, "2", "write", { result: "ok" });
}

test("the recall taxonomy separates a broken boundary from a cold corpus", () => {
  const base = { isInjected: false, isResolveFailed: false, isResolved: true, isOffered: false };
  assert.equal(recallOutcome({ ...base, isInjected: true }), OUTCOME_DELIVERED);
  assert.equal(recallOutcome({ ...base, isResolveFailed: true }), OUTCOME_RESOLVE_FAILED);
  assert.equal(recallOutcome({ ...base, isResolved: false }), OUTCOME_RECALL_MISSING);
  assert.equal(recallOutcome(base), OUTCOME_RESOLVE_EMPTY);
  assert.equal(recallOutcome({ ...base, isOffered: true }), OUTCOME_RECALL_UNCLAIMED);
});

test("a run with a located receipt reinforces and reports the receipt as sent", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- check the currency", offeredLearningIds: ["a1"] };
  const { seat, reports } = seatWith(client);
  const run = seat.open("do the thing");
  const block = await seat.beforeModelCall(run);
  assert.equal(block, "- check the currency");
  seat.afterModelCall(run, `system\n${block}\nuser: go`);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.equal(report.disposition, DISPOSITION_REINFORCED);
  assert.equal(report.isReceiptSent, true);
  assert.equal(report.recallOutcome, OUTCOME_DELIVERED);
  assert.equal(client.reinforced.length, 1);
  assert.equal(client.reinforced[0]?.contextReceipt, "- check the currency");
  assert.deepEqual(reports, [report]);
});

test("a block that never reached the model sends no receipt and says so", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- check the currency", offeredLearningIds: ["a1"] };
  const { seat } = seatWith(client);
  const run = seat.open("do the thing");
  await seat.beforeModelCall(run);
  seat.afterModelCall(run, "a trimming layer emptied everything");
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.equal(report.isReceiptSent, false);
  assert.equal(report.disposition, DISPOSITION_OBSERVED);
  assert.equal(client.reinforced[0]?.contextReceipt, null);
});

test("the block is computed once and replayed, so a retried send shows the same one", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const first = await seat.beforeModelCall(run);
  client.context = { ...EMPTY_CONTEXT, injectedText: "- two", offeredLearningIds: ["a2"] };
  const second = await seat.beforeModelCall(run);
  assert.equal(first, second);
  assert.equal(client.reinforced.length, 0);
});

test("receipt location runs on every send, and the latest wins", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  seat.afterModelCall(run, `intact\n${block}`);
  assert.notEqual(run.receipt?.text, null);
  // A mid-run trim, which is exactly what the receipt exists to catch.
  seat.afterModelCall(run, "the trimmer emptied it");
  assert.equal(run.receipt?.text, null);
});

test("a resolve that failed reports resolve_failed rather than resolve_empty", async () => {
  const client = new FakeClient();
  client.resolveError = new Error("boundary unreachable");
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.equal(report.recallOutcome, OUTCOME_RESOLVE_FAILED);
  assert.equal(client.reinforced[0]?.recallOutcome, OUTCOME_RESOLVE_FAILED);
});

test("a resolve that failed does not break the host's run", async () => {
  const client = new FakeClient();
  client.resolveError = new Error("boundary unreachable");
  const { seat } = seatWith(client);
  const run = seat.open("g");
  assert.equal(await seat.beforeModelCall(run), null);
});

test("a turn with nothing worth learning declines with a published reason", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  const report = await seat.close(run);
  assert.equal(report.disposition, DISPOSITION_DECLINED);
  assert.equal(report.declineReason, "no_tool_calls");
  assert.equal(client.declined.length, 1);
});

test("a reason the boundary has not published is withheld", () => {
  // Driven with a name the boundary will never publish. This test used to open a
  // goalless run and expect `no_goal` to be withheld, which held only while that reason
  // was still unpublished: a guard on the backlog rather than on the mechanism.
  assert.equal(isUnpublishedDeclineReason("a_reason_the_boundary_has_not_taken"), true);
  assert.equal(isUnpublishedDeclineReason("no_tool_calls"), false);
});

test("the seat withholds a decline whose reason the boundary has not published", async () => {
  // Pins the WIRING, not the predicate. A delta review mutated `decline` to
  // `if (false && isUnpublishedDeclineReason(reason))` and the whole suite stayed green,
  // because the only coverage left was the unit test below: the gate was proved correct
  // and proved to be called by nothing. The Python seat kept its equivalent.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    publishedDeclineReasons: new Set(["a_reason_this_turn_will_not_choose"]),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  const report = await seat.close(run);
  assert.equal(report.disposition, "withheld");
  assert.equal(client.declined.length, 0);
  assert.match(report.withheld.join(" "), /the boundary has not published/);
});

test("an unreadable contract withholds nothing rather than everything", () => {
  // The regression a property-keyed gate introduces if it drops the escape hatch.
  // `publishedNames` degrades a missing, unparseable or wrong-shaped contract to an
  // EMPTY set by design. Under the old per-reason key that cost one reason and the rest
  // still went out; under a property key with no escape hatch it withholds EVERY
  // decline, so one corrupt JSON file stops any run closing and each sits open holding
  // its resolve reservation. contracts.ts states the invariant that would break: an
  // empty answer keeps the behaviour the client had before that value existed, and
  // withholding everything was never that behaviour.
  //
  // Driven through the injected set. Written first as a loop over the REAL published
  // set, which cannot fail: removing `published.size > 0 &&` from the predicate left all
  // 220 tests green, because a non-empty set never reaches the branch under test.
  const empty: ReadonlySet<string> = new Set();
  for (const reason of publishedDeclineReasons()) {
    assert.equal(isUnpublishedDeclineReason(reason, empty), false);
  }
  assert.equal(isUnpublishedDeclineReason("anything_at_all", empty), false);
  // And the ordinary path still withholds, so the escape hatch has not swallowed it.
  assert.equal(
    isUnpublishedDeclineReason("a_reason_the_boundary_has_not_taken", new Set(["no_tool_calls"])),
    true,
  );
});

test("an undeclared argument is named in the run report with the release for it", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, { declarations: new DeclarationRegistry() });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.ok(report.withheld.some((line) => line.includes("undeclared argument")));
  assert.ok(report.withheld.some((line) => line.includes("isUndeclaredRestricted: false")));
});

test("the roster the agent had is sent, not the tools that happened to run", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client);
  const run = seat.open("g", [{ name: "search" }, { name: "never_called" }]);
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  await seat.close(run);
  assert.deepEqual(
    client.observed[0]?.availableTools?.map((tool) => tool.name),
    ["search", "never_called"],
  );
});

test("the boundary's per-id presence verdict reaches the report when it arrives", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  client.presence = [{ id: "a1", outcome: "delivered_reformatted" }];
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  seat.afterModelCall(run, `x\n${block}`);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.deepEqual(report.presenceOutcomes, [{ id: "a1", outcome: "delivered_reformatted" }]);
});

test("a report is empty of presence outcomes against a boundary that returns none", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.deepEqual(report.presenceOutcomes, []);
});

test("a callback that throws does not lose the run", async () => {
  const client = new FakeClient();
  const logged: string[] = [];
  const seat = new RunSeat({
    client,
    identity: IDENTITY,
    onReport: () => {
      throw new Error("customer bug");
    },
    onLog: (message) => logged.push(message),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  await seat.close(run);
  assert.ok(logged.includes("hyperstruck.report_callback_failed"));
  assert.ok(logged.includes("hyperstruck.run"));
});

test("the log line, the callback and the handle carry the same report", async () => {
  const client = new FakeClient();
  const logged: Record<string, unknown>[] = [];
  const seen: RunReport[] = [];
  const seat = new RunSeat({
    client,
    identity: IDENTITY,
    onReport: (report) => seen.push(report),
    onLog: (message, payload) => {
      if (message === "hyperstruck.run") logged.push(payload);
    },
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  const report = await seat.close(run);
  assert.equal(seen[0], report);
  assert.equal(run.report, report);
  assert.deepEqual(logged[0], reportToJson(report));
});

test("a write that fails is reported as a failure, not as a weaker success", async () => {
  const client = new FakeClient();
  client.reinforce = async () => {
    throw new Error("boundary down");
  };
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  const report = await seat.close(run);
  // Distinct from `observed`, which means sent without a receipt. Here the episode may or
  // may not have landed, and a reader needs to know which situation they are in.
  assert.equal(report.disposition, "write_failed");
});

test("a run that aged out is reported as evicted rather than declined", async () => {
  const client = new FakeClient();
  const registry = new RunRegistry({ ttlMs: 0 });
  const { seat, reports } = seatWith(client, { registry });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  run.lastTouched = Date.now() - 10_000;
  await seat.sweep();
  const evicted = reports.find((report) => report.runId === run.runId);
  assert.equal(evicted?.disposition, DISPOSITION_EVICTED);
  assert.equal(evicted?.closeTrigger, CLOSE_TRIGGER_ABANDONED);
  // Never a decline: the vocabulary has no eviction member and inventing one would be the
  // drift the package forbids elsewhere.
  assert.equal(client.declined.length, 0);
});

test("a run still working is never a candidate for the abandonment sweep", () => {
  const registry = new RunRegistry({ ttlMs: 1000 });
  const run = new HyperstruckRun({
    runId: "r",
    identity: IDENTITY,
    goal: "g",
    key: { key: "k", source: "context", isInferred: false },
  });
  registry.register(run);
  run.touch();
  assert.deepEqual(registry.sweep(Date.now() + 500), []);
  assert.equal(registry.sweep(Date.now() + 5000).length, 1);
});

test("the cap evicts and says so rather than silently losing a live run", () => {
  const warnings: string[] = [];
  const registry = new RunRegistry({ maxSize: 1, onWarning: (message) => warnings.push(message) });
  // Distinct correlation keys, because that is what the registry is keyed on: two runs
  // under one key are one conversation continuing, not two runs competing for a slot.
  const evicted = (() => {
    registry.register(
      new HyperstruckRun({
        runId: "first",
        identity: IDENTITY,
        goal: "g",
        key: { key: "k1", source: "context", isInferred: false },
      }),
    );
    return registry.register(
      new HyperstruckRun({
        runId: "second",
        identity: IDENTITY,
        goal: "g",
        key: { key: "k2", source: "context", isInferred: false },
      }),
    );
  })();
  assert.deepEqual(evicted.map((run) => run.runId), ["first"]);
  assert.match(warnings[0] as string, /registry full/);
});

test("a caller's own registry is used rather than silently swapped for a default", () => {
  const registry = new RunRegistry();
  const seat = new RunSeat({ client: new FakeClient(), identity: IDENTITY, registry });
  assert.equal(seat.runs, registry);
});

test("a second call under the same key continues the run rather than opening another", () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    runKeyResolvers: [() => ({ key: "fixed", source: "context", isInferred: false })],
  });
  const first = seat.forCall("g");
  const second = seat.forCall("g");
  assert.equal(first, second);
  assert.equal(seat.runs.size, 1);
});

test("a tool roster arriving on a later call is still recorded", () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    runKeyResolvers: [() => ({ key: "fixed", source: "context", isInferred: false })],
  });
  seat.forCall("g");
  const run = seat.forCall("g", [{ name: "search" }]);
  assert.deepEqual(run.tools.map((tool) => tool.name), ["search"]);
});

test("the report says which rung of the ladder keyed the run", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, { runKeyResolvers: [] });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  const report = await seat.close(run);
  assert.equal(report.runKeySource, "minted");
  assert.equal(report.isRunKeyInferred, true);
});

test("a tool-free answer closes only after the grace window, and a further call cancels it", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    closeGraceMs: 1000,
    runKeyResolvers: [() => ({ key: "fixed", source: "context", isInferred: false })],
  });
  const run = seat.forCall("g");
  await seat.beforeModelCall(run);
  seat.markClosable(run);
  assert.deepEqual(await seat.sweep(Date.now()), []);
  // A further call under the same key continues the run instead of closing it.
  seat.forCall("g");
  assert.deepEqual(await seat.sweep(Date.now() + 5000), []);
  seat.markClosable(run);
  const closed = await seat.sweep(Date.now() + 5000);
  assert.equal(closed.length, 1);
  assert.equal(closed[0]?.closeTrigger, "no_tool_calls_grace");
});

test("a process-exit flush closes every live run", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    runKeyResolvers: [() => null],
  });
  seat.open("a");
  seat.open("b");
  const reports = await seat.flushAll();
  assert.equal(reports.length, 2);
  assert.ok(reports.every((report) => report.closeTrigger === "process_exit"));
  assert.equal(seat.runs.size, 0);
});

test("an adapter's host name is a fallback the caller's own decision overrides", async () => {
  const named = new FakeClient();
  const namedSeat = new RunSeat({ client: named, identity: IDENTITY, sourceFramework: "mine" });
  namedSeat.declareHost("ai-sdk");
  const namedRun = namedSeat.open("g");
  await namedSeat.beforeModelCall(namedRun);
  twoSteps(namedSeat, namedRun);
  await namedSeat.close(namedRun);
  assert.equal(named.observed[0]?.sourceFramework, "mine");

  const defaulted = new FakeClient();
  const defaultedSeat = new RunSeat({ client: defaulted, identity: IDENTITY });
  defaultedSeat.declareHost("ai-sdk");
  const defaultedRun = defaultedSeat.open("g");
  await defaultedSeat.beforeModelCall(defaultedRun);
  twoSteps(defaultedSeat, defaultedRun);
  await defaultedSeat.close(defaultedRun);
  assert.equal(defaulted.observed[0]?.sourceFramework, "ai-sdk");
});

test("a value copied out of an earlier result is escalated on the wire", async () => {
  // The one-hop join, fired from the seat rather than merely available to it. An agent
  // reading an address out of a lookup and handing it to a mailer is the common real case,
  // and without this the second call's argument would be stamped with whatever the mailer
  // declared, which says nothing about where the value came from.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    declarations: new DeclarationRegistry([
      { name: "lookup", args: { company: "user_data" } },
      { name: "send", args: { body: "shareable" } },
    ]),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "lookup", args: { company: "Northwind Clinics Pty Ltd" } },
    { callId: "2", name: "send", args: { body: "posting to ada@example.com today" } },
  ]);
  seat.recordStep(run, "1", "lookup", { result: { email: "ada@example.com" } });
  seat.recordStep(run, "2", "send", { result: "sent" });
  const report = await seat.close(run);

  const steps = client.observed[0]?.steps ?? [];
  const declared = steps[1]?.declaredSensitivity as Record<string, Record<string, string>>;
  assert.equal(declared["args"]?.["body"], "user_data");
  // And it is never silent: the run says which arguments were escalated and why.
  assert.ok(report.withheld.some((line) => line.includes("escalated")));
});

test("propagation never lowers a label a tool already declared", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    declarations: new DeclarationRegistry([
      { name: "lookup", args: { q: "shareable" } },
      { name: "send", args: { body: "secret" } },
    ]),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "lookup", args: { q: "x" } },
    { callId: "2", name: "send", args: { body: "quoting public-notice-1234 here" } },
  ]);
  seat.recordStep(run, "1", "lookup", { result: "public-notice-1234" });
  seat.recordStep(run, "2", "send", { result: "sent" });
  await seat.close(run);
  const declared = (client.observed[0]?.steps ?? [])[1]?.declaredSensitivity as Record<
    string,
    Record<string, string>
  >;
  assert.equal(declared["args"]?.["body"], "secret");
});

test("a step cannot escalate against its own output", async () => {
  // The join is one hop against *earlier* steps, so ordering is load bearing.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    declarations: new DeclarationRegistry([{ name: "echo", args: { text: "shareable" } }]),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "echo", args: { text: "value-abcdef" } },
    { callId: "2", name: "echo", args: { text: "unrelated" } },
  ]);
  seat.recordStep(run, "1", "echo", { result: "value-abcdef" });
  seat.recordStep(run, "2", "echo", { result: "ok" });
  await seat.close(run);
  const declared = (client.observed[0]?.steps ?? [])[0]?.declaredSensitivity as Record<
    string,
    Record<string, string>
  >;
  assert.equal(declared["args"]?.["text"], "shareable");
});

test("a scrubbed value does not re-enter the join table", async () => {
  // A value the scanner removed from the wire must not come back as a join key, or the one
  // field the customer paid a scanner to remove would be the field this run matched every
  // later argument against.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    declarations: new DeclarationRegistry([
      { name: "lookup", args: { q: "user_data" } },
      { name: "send", args: { body: "shareable" } },
    ]),
    scanner: {
      scan(text: string) {
        const index = text.indexOf("ada@example.com");
        return index < 0
          ? []
          : [{ kind: "EMAIL", start: index, end: index + "ada@example.com".length }];
      },
    },
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "lookup", args: { q: "x" } },
    { callId: "2", name: "send", args: { body: "posting to ada@example.com today" } },
  ]);
  seat.recordStep(run, "1", "lookup", { result: "ada@example.com" });
  seat.recordStep(run, "2", "send", { result: "sent" });
  await seat.close(run);
  const declared = (client.observed[0]?.steps ?? [])[1]?.declaredSensitivity as Record<
    string,
    Record<string, string>
  >;
  assert.equal(declared["args"]?.["body"], "shareable");
});

test("a stable correlation key gives each turn its own run id", async () => {
  // The key correlates; the run id identifies, and the two must not be one string. A
  // conversation id is stable across turns by design, so giving every turn under it the
  // same run id would have the platform dedupe the second turn's episode against the first
  // and drop it, silently and with nothing to diagnose from.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    closeGraceMs: 0,
    runKeyResolvers: [() => ({ key: "session-42", source: "conversation", isInferred: false })],
  });
  const first = seat.forCall("turn one");
  await seat.beforeModelCall(first);
  twoSteps(seat, first);
  await seat.close(first);

  const second = seat.forCall("turn two");
  await seat.beforeModelCall(second);
  twoSteps(seat, second);
  await seat.close(second);

  assert.notEqual(first.runId, second.runId);
  assert.deepEqual(
    new Set(client.observed.map((episode) => episode.runId)),
    new Set([first.runId, second.runId]),
  );
});

test("a tool-free answer closes the run on the seat's own timer, not the caller's", async () => {
  // Leaving the sweep to the customer would make the documented default attachment point
  // earn no credit for anyone who did not read that paragraph, which is the exact failure
  // the grace window exists to close.
  const client = new FakeClient();
  const { seat } = seatWith(client, { closeGraceMs: 0 });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  seat.markClosable(run);
  await new Promise((resolve) => setTimeout(resolve, 5));
  assert.equal(run.isClosed, true);
  assert.equal(run.report?.closeTrigger, "no_tool_calls_grace");
});

test("a further call inside the window continues the run rather than closing it", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    closeGraceMs: 30_000,
    runKeyResolvers: [() => ({ key: "fixed", source: "context", isInferred: false })],
  });
  const run = seat.forCall("g");
  await seat.beforeModelCall(run);
  seat.markClosable(run);
  assert.notEqual(run.closableAt, null);
  const again = seat.forCall("g");
  assert.equal(again, run);
  assert.equal(run.closableAt, null);
  assert.equal(run.closeTimer, null);
  assert.equal(run.isClosed, false);
  assert.equal(client.observed.length, 0);
  assert.equal(client.declined.length, 0);
});

test("an explicit close cancels a pending grace timer rather than closing twice", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, { closeGraceMs: 0 });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.markClosable(run);
  await seat.close(run);
  await new Promise((resolve) => setTimeout(resolve, 5));
  // One close, not two: the second would send a duplicate episode.
  assert.equal(client.declined.length, 1);
});

test("the subject declaration is read off the roster without the caller registering it", async () => {
  // The annotation a customer already wrote is the one Core reads, and it must fire. Left
  // unregistered, the registry only ever holds what a caller passed by hand, so every run
  // falls back to structural salience: the same company under two spellings accumulates two
  // dossiers and neither reaches the stability the read side gates on.
  const client = new FakeClient();
  const { seat } = seatWith(client);
  const run = seat.open("g", [
    {
      name: "lookup_account",
      parameters: { properties: { company_name: { type: "string", role: "entity" } } },
    },
  ]);
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "lookup_account", args: { company_name: "Northwind Clinics Pty Ltd" } },
    { callId: "2", name: "lookup_account", args: { company_name: "Northwind Clinics" } },
  ]);
  seat.recordStep(run, "1", "lookup_account", { result: "ok" });
  seat.recordStep(run, "2", "lookup_account", { result: "ok" });
  await seat.close(run);
  const declared = (client.observed[0]?.steps ?? [])[0]?.declaredSensitivity as Record<
    string,
    unknown
  >;
  assert.equal(declared["subject"], "company_name");
});

test("a roster read from schema does not make an undeclared tool look declared", async () => {
  // Reading a subject must not fabricate argument labels, or cross-tenant org promotion
  // would open for a tool nobody described.
  const client = new FakeClient();
  const { seat } = seatWith(client);
  const run = seat.open("g", [{ name: "t", parameters: { properties: { id: { in: "path" } } } }]);
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "t", args: { id: "x" } },
    { callId: "2", name: "t", args: { id: "y" } },
  ]);
  seat.recordStep(run, "1", "t", { result: "ok" });
  seat.recordStep(run, "2", "t", { result: "ok" });
  await seat.close(run);
  assert.equal(client.reinforced[0]?.isOrgPromotionAllowed, false);
});

test("a middleware-driven run reads its subject off the call options' own tool schemas", async () => {
  // The path a customer actually takes: they never touch the registry at all.
  const { hyperstruckMiddleware } = await import("../aiSdk.ts");
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    runKeyResolvers: [() => ({ key: "fixed", source: "context", isInferred: false })],
  });
  const middleware = hyperstruckMiddleware({ seat });
  const tools = [
    {
      name: "lookup_account",
      inputSchema: { properties: { company_name: { type: "string", role: "entity" } } },
    },
  ];
  const first = await middleware.transformParams({
    params: { prompt: [{ role: "user", content: [{ type: "text", text: "go" }] }], tools },
  });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "lookup_account", input: { company_name: "Northwind Clinics Pty Ltd" } },
        { type: "tool-call", toolCallId: "2", toolName: "lookup_account", input: { company_name: "Northwind Clinics" } },
      ],
    }),
    params: first,
  });
  const second = await middleware.transformParams({
    params: {
      prompt: [
        { role: "user", content: [{ type: "text", text: "go" }] },
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "lookup_account", output: "ok" },
            { type: "tool-result", toolCallId: "2", toolName: "lookup_account", output: "ok" },
          ],
        },
      ],
      tools,
    },
  });
  await middleware.wrapGenerate({ doGenerate: async () => ({ content: [] }), params: second });
  await seat.flushAll();
  const declared = (client.observed[0]?.steps ?? [])[0]?.declaredSensitivity as Record<
    string,
    unknown
  >;
  assert.equal(declared["subject"], "company_name");
});

test("a bulk close survives a sibling run closing underneath it", async () => {
  // The two close paths race by construction, and one raced run must not lose the rest.
  // flushAll walks a snapshot and awaits inside the loop, and close awaits the prefetch.
  // That await is where a sibling's own grace timer fires. A second close is a fault by
  // design and throws, so without a guard the whole sweep would abort and every run still
  // queued behind the raced one would go unreported.
  const client = new FakeClient();
  const { seat } = seatWith(client, { runKeyResolvers: [] });
  const first = seat.open("a");
  const second = seat.open("b");
  await seat.beforeModelCall(first);
  await seat.beforeModelCall(second);
  // Something else got there first, exactly as a fired grace timer would have.
  await seat.close(first);
  const reports = await seat.flushAll();
  assert.deepEqual(reports.map((report) => report.goal), ["b"]);
  assert.equal(second.isClosed, true);
});

test("a copied value can never lower an undeclared argument's label", async () => {
  // The escalate-only guarantee, at the one place it was actually inverted.
  // `declarationFor` stamps every undeclared argument secret; `propagate` computes its own
  // baseline from the registry, which does not hold that default, so merging its answer
  // over the stamp lowered the argument and the report called it an escalation.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    declarations: new DeclarationRegistry([{ name: "lookup", args: { q: "shareable" } }]),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "lookup", args: { q: "x" } },
    // `send` is undeclared, so its body is stamped secret by the default, and it quotes a
    // value an earlier shareable tool returned.
    { callId: "2", name: "send", args: { body: "quoting public-notice-1234 here" } },
  ]);
  seat.recordStep(run, "1", "lookup", { result: "public-notice-1234" });
  seat.recordStep(run, "2", "send", { result: "sent" });
  const report = await seat.close(run);

  const declared = (client.observed[0]?.steps ?? [])[1]?.declaredSensitivity as Record<
    string,
    Record<string, string>
  >;
  assert.equal(declared["args"]?.["body"], "secret");
  assert.ok(!report.withheld.some((line) => line.includes("escalated")));
});

test("a block that did not arrive is not reported as delivered", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  assert.ok(block);
  // A layer below emptied it. Not one line of ours is in what went out.
  seat.afterModelCall(run, "You are helpful.\nUser: go");
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.equal(report.receiptOutcome, "unresolved");
  assert.equal(report.isReceiptSent, false);
  // `delivered` here is the exact ambiguity the delivery pair exists to remove.
  assert.equal(report.recallOutcome, "recall_unclaimed");
  assert.equal(client.reinforced[0]?.isDelivered, false);
});

test("a second call of the same conversation joins the first run", async () => {
  // Rung 4. Without it the documented default opens a run per model call: no tracer, no
  // explicit wrapper, which is exactly the configuration both quick starts show.
  const client = new FakeClient();
  const { seat } = seatWith(client, { closeGraceMs: 0 });
  const first = seat.forCall("reconcile the invoices", [], { isContinuation: false });
  const second = seat.forCall("", [], { isContinuation: true });
  assert.equal(second, first);
  assert.equal(second.key.isInferred, true);
  assert.equal(seat.runs.size, 1);
});

test("a fresh conversation does not join the previous run", () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, { closeGraceMs: 0 });
  const first = seat.forCall("first task", [], { isContinuation: false });
  const second = seat.forCall("second task", [], { isContinuation: false });
  assert.notEqual(second, first);
});

test("the grace-window close does not cancel the timer running it", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client, { closeGraceMs: 0 });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  seat.markClosable(run);
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.equal(run.isClosed, true);
  assert.equal(client.observed.length, 1, "the episode never reached the boundary");
  assert.equal(client.reinforced.length, 1);
});

test("a run trimmed on its last call still sends the evidence it earned earlier", async () => {
  // The defect the first fix introduced: `isInjected` latches and `receipt` is
  // last-write-wins, so a run that delivered twice and was trimmed on the third call sent
  // `isDelivered: true` with no receipt, which is the pair these fields exist to separate
  // and which the platform escalates as a client defect.
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  seat.afterModelCall(run, `system\n${block}`);
  seat.afterModelCall(run, `system\n${block}`);
  // A trimming layer emptied it on the last call only.
  seat.afterModelCall(run, "the trimmer emptied it");
  twoSteps(seat, run);
  const report = await seat.close(run);

  // The wire gets the evidence the run genuinely earned.
  assert.equal(client.reinforced[0]?.contextReceipt, "- one");
  assert.equal(client.reinforced[0]?.isDelivered, true);
  assert.equal(report.isReceiptSent, true);
  // The report still surfaces the trim, which is what a mid-run trim exists to show.
  assert.equal(report.receiptOutcome, "unresolved");
});

test("an unrecognised label cannot win a tie and be read as no declaration", () => {
  // `join` ranked an unknown label 0, tied with `secret`, and ties returned the left
  // operand, so a tool declared {a: "Secret", b: "secret"} propagated "Secret" onward.
  // That looks maximally restrictive locally and is *no declaration* at the boundary.
  assert.equal(joinSensitivity("Secret", "secret"), "secret");
  assert.equal(joinSensitivity("SECRET", null), "secret");
  assert.equal(joinSensitivity("nonsense", "shareable"), "shareable");
  assert.equal(joinSensitivity("nonsense", null), null);
});

test("an argument named for a prototype member still gets the restrictive default", () => {
  // `key in declaredArgs` walks the prototype chain, so `toString` and friends reported as
  // already declared, were never stamped, produced no withheld line, and were released.
  const registry = new DeclarationRegistry();
  const { stamp, withheld } = registry.declarationFor("t", {
    toString: "x",
    constructor: "y",
    __proto__: "z",
  });
  const args = stamp?.["args"] as Record<string, string>;
  assert.equal(args["toString"], "secret");
  assert.equal(args["constructor"], "secret");
  assert.equal(withheld.length, 1);
});

test("an escalation is reported only when the stamp actually moved", async () => {
  // Firing on "the joined value equals the propagated label" also fired for an undeclared
  // argument already stamped secret, naming an earlier tool as the cause of a label the
  // restrictive default had set, and pointing the customer at the wrong remedy.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    declarations: new DeclarationRegistry([{ name: "lookup", args: { q: "secret" } }]),
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "lookup", args: { q: "x" } },
    { callId: "2", name: "send", args: { body: "quoting secret-value-1234 here" } },
  ]);
  seat.recordStep(run, "1", "lookup", { result: "secret-value-1234" });
  seat.recordStep(run, "2", "send", { result: "sent" });
  const report = await seat.close(run);
  // `send` is undeclared, so `body` was already secret. Nothing escalated.
  assert.ok(!report.withheld.some((line) => line.includes("escalated")));
  assert.ok(report.withheld.some((line) => line.includes("undeclared argument")));
});

test("a tool's error is scanned, because it shares the result's origin exactly", async () => {
  // Same tool, same call, same step. Covering one and not the other was an inconsistency,
  // and a stack trace carrying a customer record is an ordinary tool failure.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    scanner: {
      scan(text: string) {
        const index = text.indexOf("ada@example.com");
        return index < 0 ? [] : [{ start: index, end: index + 15, kind: "EMAIL" }];
      },
    },
  });
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "a", args: {} },
    { callId: "2", name: "b", args: {} },
  ]);
  seat.recordStep(run, "1", "a", { error: "lookup failed for ada@example.com" });
  seat.recordStep(run, "2", "b", { result: "ok" });
  await seat.close(run);
  const wire = JSON.stringify(client.observed[0]);
  assert.ok(!wire.includes("ada@example.com"), "the error reached the wire unscanned");
});

test("a tool schema is scanned, because it is stored alongside the learning", async () => {
  // ToolSpec's own docstring says "pre-redact: these are stored alongside the learning",
  // and nothing enforced it. A schema's `examples` are routinely real values.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    scanner: {
      scan(text: string) {
        const index = text.indexOf("ada@example.com");
        return index < 0 ? [] : [{ start: index, end: index + 15, kind: "EMAIL" }];
      },
    },
  });
  const run = seat.open("g", [
    {
      name: "lookup",
      parameters: { properties: { email: { type: "string", examples: ["ada@example.com"] } } },
    },
  ]);
  await seat.beforeModelCall(run);
  seat.recordPlannedCalls(run, [
    { callId: "1", name: "a", args: {} },
    { callId: "2", name: "b", args: {} },
  ]);
  seat.recordStep(run, "1", "a", { result: "ok" });
  seat.recordStep(run, "2", "b", { result: "ok" });
  const report = await seat.close(run);
  const wire = JSON.stringify(client.observed[0]?.availableTools);
  assert.ok(!wire.includes("ada@example.com"), "the schema reached the wire unscanned");
  assert.ok(report.withheld.some((line) => line.includes("(schema)")));
});

test("the goal is not scanned, because its origin is the principal", async () => {
  // Origin, not field list: the goal comes from the human, which is the case origin
  // labelling already handles, and it is what a learning is transferable against.
  const client = new FakeClient();
  const { seat } = seatWith(client, {
    scanner: {
      scan(text: string) {
        const index = text.indexOf("ada@example.com");
        return index < 0 ? [] : [{ start: index, end: index + 15, kind: "EMAIL" }];
      },
    },
  });
  const run = seat.open("reconcile for ada@example.com");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  await seat.close(run);
  assert.equal(client.observed[0]?.goal, "reconcile for ada@example.com");
});

// -- loop-level obligation closure through the seat -----------------------------

const APPLIED: ObligationClosureResult = {
  id: "o1",
  disposition: "applied",
  status: "kept",
};
const KEPT: ReportedObligationOutcome = {
  id: "o1",
  outcome: "kept",
  keptBasis: "reported",
};

test("the outcomes a close reports reach the boundary and their results the report", async () => {
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  client.closures = [APPLIED];
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  seat.afterModelCall(run, `x\n${block}`);
  twoSteps(seat, run);
  const report = await seat.close(run, { obligationOutcomes: [KEPT] });
  assert.deepEqual(client.reinforced[0]?.obligationOutcomes, [KEPT]);
  assert.deepEqual(report.obligationClosures, [APPLIED]);
  assert.deepEqual(reportToJson(report)["obligation_closures"], [
    { id: "o1", disposition: "applied", status: "kept" },
  ]);
});

test("a malformed reported outcome is dropped and named, and its siblings still close", async () => {
  // Before this, a kept-without-keptBasis outcome anywhere in the batch threw inside the
  // wire builder AFTER observe had already been posted, losing the receipt fold and every
  // sibling outcome in the same call. It must instead be dropped, named on `withheld`, and
  // every well-formed sibling must still close.
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  client.closures = [APPLIED];
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  seat.afterModelCall(run, `x\n${block}`);
  twoSteps(seat, run);
  const malformed: ReportedObligationOutcome = { id: "o2", outcome: "kept" };
  const report = await seat.close(run, { obligationOutcomes: [malformed, KEPT] });
  assert.equal(client.observed.length, 1, "observe must still be posted");
  assert.deepEqual(client.reinforced[0]?.obligationOutcomes, [KEPT]);
  assert.equal(report.disposition, DISPOSITION_REINFORCED);
  assert.deepEqual(report.obligationClosures, [APPLIED]);
  assert.ok(
    report.withheld.some((line) => line.includes("o2") && line.includes("keptBasis")),
  );
});

test("a declined turn carries its outcomes and reports their results too", async () => {
  // The leg a goalless or toolless turn takes. A turn can resolve an obligation and be
  // worth learning nothing from, and closure results on the reinforce leg alone would
  // silently lose them on exactly that turn.
  const client = new FakeClient();
  client.declineClosures = [APPLIED];
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  const report = await seat.close(run, { obligationOutcomes: [KEPT] });
  assert.equal(report.disposition, DISPOSITION_DECLINED);
  assert.deepEqual(client.declined[0]?.obligationOutcomes, [KEPT]);
  assert.deepEqual(report.obligationClosures, [APPLIED]);
});

test("a report is empty of closures against a boundary that returns none", async () => {
  const client = new FakeClient();
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  assert.deepEqual((await seat.close(run)).obligationClosures, []);
});

test("a client returning the older bare array still reports its presence", async () => {
  // The version-skew seam. A client written against 0.8.0 returns the presence verdicts
  // alone, and reading a property off that array would throw outside the write guard,
  // which is the one thing this seat promises never to do to a host run.
  const client = new FakeClient();
  client.context = { ...EMPTY_CONTEXT, injectedText: "- one", offeredLearningIds: ["a1"] };
  client.reinforce = async () =>
    [{ id: "a1", outcome: "delivered_verbatim" }] as unknown as ReinforceResult;
  const { seat } = seatWith(client);
  const run = seat.open("g");
  const block = await seat.beforeModelCall(run);
  seat.afterModelCall(run, `x\n${block}`);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.deepEqual(report.presenceOutcomes, [{ id: "a1", outcome: "delivered_verbatim" }]);
  assert.deepEqual(report.obligationClosures, []);
});

test("a client returning nothing at all still closes the run", async () => {
  const client = new FakeClient();
  client.reinforce = async () => undefined as unknown as ReinforceResult;
  const { seat } = seatWith(client);
  const run = seat.open("g");
  await seat.beforeModelCall(run);
  twoSteps(seat, run);
  const report = await seat.close(run);
  assert.equal(report.disposition, DISPOSITION_OBSERVED);
  assert.deepEqual(report.presenceOutcomes, []);
  assert.deepEqual(report.obligationClosures, []);
});
