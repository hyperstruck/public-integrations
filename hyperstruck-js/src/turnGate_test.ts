import assert from "node:assert/strict";
import { test } from "node:test";

import { declineReason, shouldObserve } from "./turnGate.ts";
import {
  REASON_BELOW_MATERIAL_THRESHOLD,
  REASON_EMPTY_OFFER,
  REASON_NO_GOAL,
  REASON_NO_TOOL_CALLS,
  REASON_UNEVIDENCED_OUTCOME,
} from "./wire.ts";

const KINDS = new Set(["tool_call"]);
const step = (status = "completed") => ({ kind: "tool_call", status });

test("a turn with nothing in it is not worth observing", () => {
  assert.equal(shouldObserve([], KINDS), false);
});

test("one material step is below the threshold; two clear it", () => {
  assert.equal(shouldObserve([step()], KINDS), false);
  assert.equal(shouldObserve([step(), step()], KINDS), true);
});

test("a turn that recovered from a failure is always kept, however short", () => {
  assert.equal(shouldObserve([step("failed"), step("completed")], KINDS), true);
});

test("a step of a kind the host did not call material does not count", () => {
  assert.equal(shouldObserve([{ kind: "read", status: "completed" }], KINDS), false);
});

test("a failure with no later success is not a recovery", () => {
  assert.equal(shouldObserve([step("completed"), step("failed")], KINDS), true);
  assert.equal(shouldObserve([step("failed")], KINDS), false);
});

test("a goalless turn is reported by the gate that decided it, not by its step count", () => {
  assert.equal(
    declineReason([step(), step()], false, { isGoalless: true }),
    REASON_NO_GOAL,
  );
});

test("a turn the step gates would have passed is declined for its missing outcome", () => {
  assert.equal(
    declineReason([step()], true, { isGoalless: false }),
    REASON_UNEVIDENCED_OUTCOME,
  );
});

test("a turn with no steps is declined for having none", () => {
  assert.equal(declineReason([], false, { isGoalless: false }), REASON_NO_TOOL_CALLS);
});

test("an empty offer explains a sub-threshold turn, but never one with material steps", () => {
  assert.equal(
    declineReason([step()], false, { isGoalless: false, isOfferEmpty: true }),
    REASON_EMPTY_OFFER,
  );
  assert.equal(
    declineReason([step()], false, { isGoalless: false, isOfferEmpty: false }),
    REASON_BELOW_MATERIAL_THRESHOLD,
  );
});
