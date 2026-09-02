import assert from "node:assert/strict";
import { test } from "node:test";

import { redactEpisodePayload, REDACTION_MARKER, scrubStrings } from "./redaction.ts";

test("a declared argument never reaches the wire", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "login",
        args: { user: "ada", token: "hunter2secret" },
        declared_sensitivity: { args: { token: "secret" } },
      },
    ],
  };
  const redacted = redactEpisodePayload(payload) as { steps: Record<string, unknown>[] };
  const args = redacted.steps[0]?.["args"] as Record<string, unknown>;
  assert.equal(args["token"], "[REDACTED:secret]");
  assert.equal(args["user"], "ada");
});

test("the caller's own payload is not mutated", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "login",
        args: { token: "hunter2secret" },
        declared_sensitivity: { args: { token: "secret" } },
      },
    ],
  };
  redactEpisodePayload(payload);
  assert.equal(payload.steps[0]?.args.token, "hunter2secret");
});

test("a declared value echoed in a later result is scrubbed too", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "login",
        args: { token: "hunter2secret" },
        declared_sensitivity: { args: { token: "secret" } },
      },
      { id: "2", name: "log", args: {}, result: "used token hunter2secret to sign in" },
    ],
  };
  const redacted = redactEpisodePayload(payload) as { steps: Record<string, unknown>[] };
  assert.equal(redacted.steps[1]?.["result"], `used token ${REDACTION_MARKER} to sign in`);
});

test("a short declared value is stripped from its own argument and scrubbed nowhere else", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "pick",
        args: { code: "5" },
        declared_sensitivity: { args: { code: "secret" } },
      },
      { id: "2", name: "log", args: {}, result: "the answer is 5 out of 50" },
    ],
  };
  const redacted = redactEpisodePayload(payload) as { steps: Record<string, unknown>[] };
  assert.equal((redacted.steps[0]?.["args"] as Record<string, unknown>)["code"], "[REDACTED:secret]");
  assert.equal(redacted.steps[1]?.["result"], "the answer is 5 out of 50");
});

test("a declared value glued inside a longer token is left intact rather than corrupting it", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "pick",
        args: { code: "1234" },
        declared_sensitivity: { args: { code: "secret" } },
      },
      { id: "2", name: "log", args: {}, result: "order-12345 shipped, code 1234 used" },
    ],
  };
  const redacted = redactEpisodePayload(payload) as { steps: Record<string, unknown>[] };
  assert.equal(
    redacted.steps[1]?.["result"],
    `order-12345 shipped, code ${REDACTION_MARKER} used`,
  );
});

test("a longer secret wins over a shorter one that prefixes it", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "login",
        args: { a: "abcd", b: "abcdefgh" },
        declared_sensitivity: { args: { a: "secret", b: "secret" } },
      },
      { id: "2", name: "log", args: {}, result: "saw abcdefgh here" },
    ],
  };
  const redacted = redactEpisodePayload(payload) as { steps: Record<string, unknown>[] };
  assert.equal(redacted.steps[1]?.["result"], `saw ${REDACTION_MARKER} here`);
});

test("a regex metacharacter in a declared value is escaped rather than compiled", () => {
  const payload = {
    steps: [
      {
        id: "1",
        name: "login",
        args: { token: "a.*b" },
        declared_sensitivity: { args: { token: "secret" } },
      },
      { id: "2", name: "log", args: {}, result: "value a.*b and also axxb" },
    ],
  };
  const redacted = redactEpisodePayload(payload) as { steps: Record<string, unknown>[] };
  assert.equal(redacted.steps[1]?.["result"], `value ${REDACTION_MARKER} and also axxb`);
});

test("the traversal reaches a deeply nested string without overflowing the stack", () => {
  let deep: unknown = "leaf";
  for (let index = 0; index < 20000; index += 1) deep = { next: deep };
  const scrubbed = scrubStrings(deep, (text) => text.toUpperCase());
  let cursor = scrubbed as Record<string, unknown>;
  for (let index = 0; index < 20000; index += 1) {
    cursor = cursor["next"] as Record<string, unknown>;
  }
  assert.equal(cursor as unknown, "LEAF");
});

test("a payload with no steps list passes through untouched", () => {
  const payload = { run_id: "r", goal: "g" };
  assert.equal(redactEpisodePayload(payload), payload);
});
