import assert from "node:assert/strict";
import { mkdtempSync, chmodSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import {
  backoffDelayMs,
  breakerFor,
  CircuitOpenError,
  DurableOutbox,
  ResolveBreaker,
  resetBreakers,
} from "./resilience.ts";

test("the backoff is equal jitter: half fixed, half random", () => {
  // Attempt 1 over a 500ms base is a 1000ms interval, so 500ms fixed plus 0..500 random.
  assert.equal(backoffDelayMs(500, 1, () => 0), 500);
  assert.equal(backoffDelayMs(500, 1, () => 1), 1000);
  assert.equal(backoffDelayMs(500, 0, () => 0.5), 375);
});

test("one timeout does not open the breaker; three consecutive ones do", () => {
  const breaker = new ResolveBreaker();
  breaker.recordFailure(0);
  assert.equal(breaker.isOpen, false);
  breaker.recordFailure(0);
  breaker.recordFailure(0);
  assert.equal(breaker.isOpen, true);
  assert.throws(() => breaker.beforeRequest(1), CircuitOpenError);
});

test("a single success closes the breaker", () => {
  const breaker = new ResolveBreaker({ failureThreshold: 1 });
  breaker.recordFailure(0);
  assert.equal(breaker.isOpen, true);
  breaker.recordSuccess();
  assert.equal(breaker.isOpen, false);
  breaker.beforeRequest(0);
});

test("exactly one probe is admitted per cooldown", () => {
  const breaker = new ResolveBreaker({ failureThreshold: 1, cooldownMs: 100 });
  breaker.recordFailure(0);
  assert.throws(() => breaker.beforeRequest(50), CircuitOpenError);
  // The cooldown has elapsed: the first caller is let through, the second is not.
  breaker.beforeRequest(200);
  assert.throws(() => breaker.beforeRequest(201), CircuitOpenError);
});

test("the breaker is shared per boundary across the process, not per client", () => {
  resetBreakers();
  const first = breakerFor("https://api.example.com");
  const second = breakerFor("https://api.example.com");
  assert.equal(first, second);
  assert.notEqual(first, breakerFor("https://other.example.com"));
});

test("a durable outbox parks, lists and releases a write", () => {
  const directory = mkdtempSync(join(tmpdir(), "hs-outbox-"));
  const outbox = DurableOutbox.open(directory);
  assert.ok(outbox !== null);
  const path = outbox.park("/observe", { run_id: "r" });
  assert.ok(path !== null);
  const pending = outbox.pending();
  assert.equal(pending.length, 1);
  assert.equal(pending[0]?.endpoint, "/observe");
  outbox.release(path);
  assert.equal(outbox.pending().length, 0);
});

test("an unparseable parked write is discarded rather than retried forever", () => {
  const directory = mkdtempSync(join(tmpdir(), "hs-outbox-"));
  const outbox = DurableOutbox.open(directory);
  assert.ok(outbox !== null);
  writeFileSync(join(directory, "broken.json"), "{not json", "utf8");
  assert.equal(outbox.pending().length, 0);
  assert.equal(readdirSync(directory).length, 0);
});

test("a read-only location refuses the outbox rather than degrading silently", () => {
  const parent = mkdtempSync(join(tmpdir(), "hs-ro-"));
  chmodSync(parent, 0o500);
  const reasons: string[] = [];
  const outbox = DurableOutbox.open(join(parent, "queue"), (reason) => reasons.push(reason));
  chmodSync(parent, 0o700);
  assert.equal(outbox, null);
  assert.equal(reasons.length, 1);
  assert.match(reasons[0] as string, /not writable/);
});

test("the outbox replays oldest first, as its docstring promises", () => {
  // The names used to be bare uuids, so "oldest first" sorted randomly.
  const directory = mkdtempSync(join(tmpdir(), "hs-order-"));
  const outbox = DurableOutbox.open(directory);
  assert.ok(outbox !== null);
  for (let index = 0; index < 6; index += 1) outbox.park("/observe", { n: index });
  assert.deepEqual(outbox.pending().map((write) => write.body["n"]), [0, 1, 2, 3, 4, 5]);
});

test("the parked store and its files are not world-readable", () => {
  // It holds episode content, which is why it inherits the wire's redaction; it should not
  // also be readable by every user on a shared host.
  const directory = mkdtempSync(join(tmpdir(), "hs-perm-"));
  const outbox = DurableOutbox.open(join(directory, "queue"));
  assert.ok(outbox !== null);
  const path = outbox.park("/observe", { run_id: "r" });
  assert.ok(path !== null);
  assert.equal(statSync(outbox.directory).mode & 0o077, 0, "the directory is group/world readable");
  assert.equal(statSync(path).mode & 0o077, 0, "the parked file is group/world readable");
});

test("the breaker says so when it opens", () => {
  // The single event most likely to explain "our corpus stopped filling", and it used to
  // happen with no signal at all in this language while the Python one logged a warning.
  const said: string[] = [];
  const breaker = new ResolveBreaker({ failureThreshold: 1, onTrip: (m) => said.push(m) });
  breaker.recordFailure(0);
  assert.equal(said.length, 1);
  assert.match(said[0] as string, /circuit opened/);
});
