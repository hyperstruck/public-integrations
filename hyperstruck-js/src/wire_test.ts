import assert from "node:assert/strict";
import { test } from "node:test";

import { resolvedContextFromResponse } from "./wire.ts";

test("a resolve says whether the host has reported outcomes, and an older server says nothing", () => {
  // Until a host reports an outcome no learning can be proven, so a host should be able to read
  // that. A server that predates the field is unknown, never a host that has not reported.
  assert.equal(resolvedContextFromResponse({ has_reported_outcomes: false }).hasReportedOutcomes, false);
  assert.equal(resolvedContextFromResponse({ has_reported_outcomes: true }).hasReportedOutcomes, true);
  assert.equal(resolvedContextFromResponse({ injected_text: "x" }).hasReportedOutcomes, null);
});
