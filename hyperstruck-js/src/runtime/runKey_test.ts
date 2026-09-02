import assert from "node:assert/strict";
import { test } from "node:test";

import { currentContextRunKey, resolveRunKey, runWithKey } from "./runKey.ts";

test("a minted key says it was minted, and no two runs share one", () => {
  const first = resolveRunKey([]);
  const second = resolveRunKey([]);
  assert.equal(first.source, "minted");
  assert.equal(first.isInferred, true);
  assert.notEqual(first.key, second.key);
});

test("the explicit wrapper's key is exact and is reported as such", () => {
  runWithKey("abc", () => {
    const key = resolveRunKey();
    assert.equal(key.key, "abc");
    assert.equal(key.source, "context");
    assert.equal(key.isInferred, false);
  });
  assert.equal(currentContextRunKey(), null);
});

test("two concurrent bodies do not see each other's key", async () => {
  const seen: string[] = [];
  await Promise.all([
    runWithKey("left", async () => {
      await new Promise((resolve) => setTimeout(resolve, 5));
      seen.push(resolveRunKey().key);
    }),
    runWithKey("right", async () => {
      seen.push(resolveRunKey().key);
    }),
  ]);
  assert.deepEqual(seen.sort(), ["left", "right"]);
});

test("a resolver that throws falls to the next rung rather than taking the run down", () => {
  const key = resolveRunKey([
    () => {
      throw new Error("tracer exploded");
    },
    () => ({ key: "fallback", source: "test", isInferred: false }),
  ]);
  assert.equal(key.key, "fallback");
});

test("the ladder prefers the earlier rung", () => {
  const key = resolveRunKey([
    () => ({ key: "trace", source: "trace", isInferred: false }),
    () => ({ key: "context", source: "context", isInferred: false }),
  ]);
  assert.equal(key.source, "trace");
});
