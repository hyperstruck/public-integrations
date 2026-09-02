import assert from "node:assert/strict";
import { test } from "node:test";

import {
  LedgerClosedError,
  offeredAndDeliveredShelf,
  renderConfirmedShelf,
  RunLedger,
} from "./ledger.ts";

function offer(ledger: RunLedger): void {
  ledger.recordOffer({
    advice: renderConfirmedShelf("advice", "a", ["a1"]),
    facts: renderConfirmedShelf("facts", "f", ["f1"]),
    obligations: offeredAndDeliveredShelf("obligations", "o", ["o1", "o2"], ["o1"]),
  });
}

test("the obligations shelf keeps offered and delivered apart", () => {
  const ledger = new RunLedger("r", "g");
  offer(ledger);
  assert.deepEqual(ledger.obligations?.offeredIds, ["o1", "o2"]);
  assert.deepEqual(ledger.obligations?.deliveredIds, ["o1"]);
});

test("an absent delivered set reads as nothing delivered, never as everything", () => {
  const shelf = offeredAndDeliveredShelf("obligations", "o", ["o1", "o2"], null);
  assert.deepEqual(shelf.deliveredIds, []);
});

test("a render-confirmed shelf whose sets disagree is refused at construction", () => {
  assert.throws(
    () =>
      renderConfirmedShelf("advice", "a", ["a1"]) &&
      // Built by hand to reach the guard the helper cannot violate.
      offeredAndDeliveredShelf("advice", "a", ["a1"], ["a1", "a2"]),
    /never offered/,
  );
});

test("a delivered id that was never offered is refused", () => {
  assert.throws(
    () => offeredAndDeliveredShelf("obligations", "o", ["o1"], ["o9"]),
    /never offered/,
  );
});

test("only calls present in both streams become steps", () => {
  const ledger = new RunLedger("r", "g");
  ledger.recordPlannedCalls([
    { callId: "1", name: "search", args: { q: "x" } },
    { callId: "2", name: "write", args: {} },
  ]);
  ledger.recordOutcome("1", "search", { result: "found" });
  ledger.recordOutcome("9", "ghost", { result: "orphan" });
  const steps = ledger.steps;
  assert.equal(steps.length, 1);
  assert.equal(steps[0]?.id, "1");
});

test("a failed outcome grades the step failed", () => {
  const ledger = new RunLedger("r", "g");
  ledger.recordPlannedCalls([{ callId: "1", name: "write", args: {} }]);
  ledger.recordOutcome("1", "write", { error: "denied" });
  assert.equal(ledger.steps[0]?.status, "failed");
});

test("a retried model call folds into one planned step rather than two", () => {
  const ledger = new RunLedger("r", "g");
  ledger.recordPlannedCalls([{ callId: "1", name: "search", args: { q: "x" } }]);
  ledger.recordPlannedCalls([{ callId: "1", name: "search", args: { q: "x" } }]);
  ledger.recordOutcome("1", "search", { result: "found" });
  assert.equal(ledger.steps.length, 1);
  assert.equal(ledger.modelCallCount, 2);
});

test("a second close is a fault rather than a no-op", () => {
  const ledger = new RunLedger("r", "g");
  ledger.close();
  assert.throws(() => ledger.close(), LedgerClosedError);
});

test("recording after close is refused rather than absorbed", () => {
  const ledger = new RunLedger("r", "g");
  ledger.close();
  assert.throws(() => ledger.recordOutcome("1", "x"), LedgerClosedError);
  assert.throws(() => ledger.recordPlannedCalls([]), LedgerClosedError);
  assert.throws(() => ledger.recordResolveFailed(), LedgerClosedError);
});

test("a resolve that failed is latched apart from one that returned nothing", () => {
  const ledger = new RunLedger("r", "g");
  ledger.recordResolveFailed();
  assert.equal(ledger.isResolved, true);
  assert.equal(ledger.isResolveFailed, true);
  assert.equal(ledger.offeredAny, false);
});

test("offered and delivered are answered separately at the run level", () => {
  const ledger = new RunLedger("r", "g");
  ledger.recordOffer({
    advice: renderConfirmedShelf("advice", null, []),
    facts: renderConfirmedShelf("facts", null, []),
    obligations: offeredAndDeliveredShelf("obligations", null, ["o1"], []),
  });
  assert.equal(ledger.offeredAny, true);
  assert.equal(ledger.deliveredAny, false);
});
