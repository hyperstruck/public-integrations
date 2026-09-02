/**
 * The secondary net over free text: what it catches, and what it must never break.
 *
 * The mirror of the Python seat's `scanning_test.py`, assertion for assertion, because the
 * two now share one interface shape and one scrubbing policy and the whole point of that is
 * that a customer's scanner behaves the same in either language.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import { SECRET, SHAREABLE, USER_DATA } from "./declarations.ts";
import {
  CompositeScanner,
  NullScanner,
  scanAndScrub,
  describeScan,
  isScanClean,
  type ContentScanner,
  type Finding,
} from "./scanning.ts";

const EMAIL = "ada@example.com";

/**
 * A scanner that reports occurrences of one value, by span.
 *
 * `onlyContaining` narrows it to texts carrying a marker, so a test can put the detector's
 * reach in one field and prove the *echo pass* is what reached the other. A scanner that
 * fired everywhere would test the fake rather than the policy.
 */
class Finds implements ContentScanner {
  readonly needle: string;
  readonly label: string | null;
  readonly onlyContaining: string | null;

  constructor(needle: string, label: string | null = USER_DATA, onlyContaining: string | null = null) {
    this.needle = needle;
    this.label = label;
    this.onlyContaining = onlyContaining;
  }

  scan(text: string): readonly Finding[] {
    if (this.onlyContaining !== null && !text.includes(this.onlyContaining)) return [];
    const findings: Finding[] = [];
    let start = text.indexOf(this.needle);
    while (start >= 0) {
      findings.push({ start, end: start + this.needle.length, kind: "PII", label: this.label });
      start = text.indexOf(this.needle, start + 1);
    }
    return findings;
  }
}

test("no scanner is the default and returns the payload untouched", () => {
  const payload = { note: EMAIL };
  const result = scanAndScrub(payload, null);
  assert.equal(result.payload, payload);
  assert.equal(isScanClean(result), true);
  assert.equal(scanAndScrub(payload, new NullScanner()).payload, payload);
});

test("a scanner that finds nothing changes nothing", () => {
  const result = scanAndScrub({ note: "nothing here" }, new Finds(EMAIL));
  assert.deepEqual(result.payload, { note: "nothing here" });
  assert.equal(isScanClean(result), true);
});

test("a finding is scrubbed out of the payload before it leaves the process", () => {
  const result = scanAndScrub({ note: `write to ${EMAIL} today` }, new Finds(EMAIL));
  assert.deepEqual(result.payload, { note: `write to [REDACTED:${USER_DATA}] today` });
  assert.equal(result.findingCount, 1);
  assert.match(describeScan(result), /1 content scan finding/);
});

test("the same datum echoed into another field is scrubbed too", () => {
  // The case a scanner is fitted for: an agent copying a value out of one result.
  const payload = { result: `contact ${EMAIL}`, summary: `emailed ${EMAIL} about it` };
  const result = scanAndScrub(payload, new Finds(EMAIL));
  assert.ok(!JSON.stringify(result.payload).includes(EMAIL));
  assert.equal(
    (result.payload as Record<string, string>)["summary"],
    `emailed [REDACTED:${USER_DATA}] about it`,
  );
});

test("the echo pass is fenced so a coincidental substring survives", () => {
  // The same fence, and the same reason, as the declared-value scrubber's.
  const payload = { result: "code 1234 here", other: "order-12345 shipped" };
  const result = scanAndScrub(payload, new Finds("1234", USER_DATA, "code"));
  const out = result.payload as Record<string, string>;
  assert.equal(out["result"], `code [REDACTED:${USER_DATA}] here`);
  assert.equal(out["other"], "order-12345 shipped");
});

test("a span shorter than the floor is scrubbed but never echoed", () => {
  const payload = { result: "pick 7 now", other: "7 of 77" };
  const result = scanAndScrub(payload, new Finds("7", USER_DATA, "pick"));
  assert.equal((result.payload as Record<string, string>)["other"], "7 of 77");
});

test("overlapping spans merge rather than being replaced twice", () => {
  const overlapping: ContentScanner = {
    scan: () => [
      { start: 0, end: 5, kind: "A", label: SHAREABLE },
      { start: 3, end: 8, kind: "B", label: USER_DATA },
    ],
  };
  // One marker, and the stricter of the two labels: the join is escalate-only here too.
  assert.equal(scanAndScrub("0123456789", overlapping).payload, `[REDACTED:${USER_DATA}]89`);
});

test("an impossible span is ignored rather than corrupting the text", () => {
  const bad: ContentScanner = {
    scan: () => [
      { start: 5, end: 2, kind: "X" },
      { start: 0, end: 99, kind: "X" },
      { start: -1, end: 3, kind: "X" },
    ],
  };
  assert.equal(scanAndScrub("hello", bad).payload, "hello");
});

test("a finding with no label reads as the most restrictive member", () => {
  // A detector that says what it found without saying how sensitive has licensed nothing.
  const result = scanAndScrub({ note: `see ${EMAIL}` }, new Finds(EMAIL, null));
  assert.deepEqual(result.payload, { note: `see [REDACTED:${SECRET}]` });
});

test("two scanners disagreeing about one span resolve to the stricter label", () => {
  const composite = new CompositeScanner([
    new Finds(EMAIL, SHAREABLE),
    new Finds(EMAIL, SECRET),
  ]);
  assert.deepEqual(scanAndScrub({ note: `see ${EMAIL}` }, composite).payload, {
    note: `see [REDACTED:${SECRET}]`,
  });
});

test("a scanner that throws loses its own findings and not the episode", () => {
  const composite = new CompositeScanner([
    {
      scan() {
        throw new Error("model not loaded");
      },
    },
    new Finds(EMAIL),
  ]);
  assert.deepEqual(scanAndScrub({ note: `see ${EMAIL}` }, composite).payload, {
    note: `see [REDACTED:${USER_DATA}]`,
  });
});
