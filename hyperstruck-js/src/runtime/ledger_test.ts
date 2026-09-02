import assert from "node:assert/strict";
import { test } from "node:test";

import {
  LedgerClosedError,
  renderConfirmedShelf,
  RunLedger,
} from "./ledger.ts";

function offer(ledger: RunLedger): void {
  ledger.recordOffer({
    advice: renderConfirmedShelf("advice", "a", ["a1"]),
    facts: renderConfirmedShelf("facts", "f", ["f1"]),
  });
}

test("the ledger holds the two shelves the boundary returns", () => {
  const ledger = new RunLedger("r", "g");
  offer(ledger);
  assert.deepEqual(ledger.advice?.offeredIds, ["a1"]);
  assert.deepEqual(ledger.facts?.offeredIds, ["f1"]);
  assert.equal("obligations" in ledger, false);
  assert.equal(ledger.offeredAny, true);
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
