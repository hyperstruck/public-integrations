import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MAX_PROPAGATED_VALUES_PER_STEP,
  DeclarationRegistry,
  declarationFromSchema,
  join,
  SECRET,
  SHAREABLE,
  subjectArgKey,
  USER_DATA,
} from "./declarations.ts";

test("the lattice escalates and never lowers", () => {
  assert.equal(join(SHAREABLE, SECRET), SECRET);
  assert.equal(join(SECRET, SHAREABLE), SECRET);
  assert.equal(join(USER_DATA, SHAREABLE), USER_DATA);
  assert.equal(join(null, USER_DATA), USER_DATA);
  assert.equal(join(USER_DATA, null), USER_DATA);
  assert.equal(join(null, null), null);
});

test("the subject is read from the schema role annotation Core already reads", () => {
  const parameters = {
    properties: {
      company: { type: "string", role: "entity" },
      note: { type: "string" },
    },
  };
  assert.equal(subjectArgKey(parameters), "company");
});

test("an OpenAPI path parameter counts as an implicit subject", () => {
  assert.equal(subjectArgKey({ properties: { id: { in: "path" } } }), "id");
});

test("two declared subjects are treated as none, so a clean one stays authoritative", () => {
  const parameters = {
    properties: { a: { role: "entity" }, b: { role: "subject" } },
  };
  assert.equal(subjectArgKey(parameters), null);
});

test("an undeclared argument is stamped most restrictive and the withholding is named", () => {
  const registry = new DeclarationRegistry();
  const { stamp, withheld } = registry.declarationFor("lookup", { ssn: "x", note: "y" });
  assert.deepEqual(stamp?.["args"], { ssn: SECRET, note: SECRET });
  assert.equal(withheld.length, 1);
  assert.match(withheld[0] as string, /2 undeclared argument\(s\)/);
  // The one thing the customer can do about it is named, not implied.
  assert.match(withheld[0] as string, /isUndeclaredRestricted: false/);
});

test("the restrictive default governs sensitivity and never the subject", () => {
  const registry = new DeclarationRegistry([
    declarationFromSchema("lookup", { properties: { company: { role: "entity" } } }),
  ]);
  const { stamp } = registry.declarationFor("lookup", { company: "Northwind Clinics Pty Ltd" });
  // The subject survives even though the argument carries the restrictive default: an
  // undeclared subject would otherwise fall back to structural salience and refragment
  // the entity, which is strictly worse than today.
  assert.equal(stamp?.["subject"], "company");
  assert.deepEqual(stamp?.["args"], { company: SECRET });
});

test("the subject is a bare string, which is the shape the boundary reads", () => {
  const registry = new DeclarationRegistry([
    { name: "lookup", args: { company: SHAREABLE }, subject: "company" },
  ]);
  const { stamp } = registry.declarationFor("lookup", { company: "Northwind Clinics" });
  assert.equal(typeof stamp?.["subject"], "string");
});

test("releasing the default stops the stamp and stops the withholding notice", () => {
  const registry = new DeclarationRegistry([], { isUndeclaredRestricted: false });
  const { stamp, withheld } = registry.declarationFor("lookup", { ssn: "x" });
  assert.equal(stamp, null);
  assert.deepEqual(withheld, []);
});

test("org promotion needs every tool declared with real labels", () => {
  const registry = new DeclarationRegistry([
    { name: "declared", args: { a: SHAREABLE } },
    { name: "empty", args: {} },
  ]);
  assert.equal(registry.isFullyDeclared([]), true);
  assert.equal(registry.isFullyDeclared(["declared"]), true);
  assert.equal(registry.isFullyDeclared(["empty"]), false);
  assert.equal(registry.isFullyDeclared(["unknown"]), false);
});

test("a value copied out of an earlier result escalates one hop", () => {
  const registry = new DeclarationRegistry([
    { name: "send", args: { body: SHAREABLE } },
  ]);
  const escalated = registry.propagate(
    "send",
    { body: "please contact ada@example.com about it" },
    new Map([["ada@example.com", USER_DATA]]),
  );
  assert.equal(escalated["body"], USER_DATA);
});

test("propagation only escalates, so a permissive prior output cannot lower a label", () => {
  const registry = new DeclarationRegistry([{ name: "send", args: { body: SECRET } }]);
  const escalated = registry.propagate(
    "send",
    { body: "contains public-token here" },
    new Map([["public-token", SHAREABLE]]),
  );
  assert.deepEqual(escalated, {});
});

test("registering a roster reads the subject off each tool's own schema", () => {
  const registry = new DeclarationRegistry();
  registry.registerTools([
    { name: "lookup", parameters: { properties: { company: { role: "entity" } } } },
    { name: "plain", parameters: { properties: { q: { type: "string" } } } },
  ]);
  assert.equal(registry.declarationFor("lookup").stamp?.["subject"], "company");
  assert.equal(registry.declarationFor("plain").stamp, null);
});

test("the output label is joined over what the tool declared", () => {
  const registry = new DeclarationRegistry([
    { name: "mixed", args: { a: SHAREABLE, b: USER_DATA } },
    { name: "bare", args: {} },
  ]);
  assert.equal(registry.outputLabel("mixed"), USER_DATA);
  // A tool that declared nothing contributes nothing, deliberately: treating its output as
  // most restrictive would taint every later argument that quoted it, which is taint
  // explosion by another route.
  assert.equal(registry.outputLabel("bare"), null);
  assert.equal(registry.outputLabel("unknown"), null);
});

test("an undeclared tool's output cannot escalate anything", () => {
  const registry = new DeclarationRegistry();
  const prior = new Map<string, string>();
  registry.recordOutputs(prior, "unknown", "ada@example.com");
  assert.equal(prior.size, 0);
});

test("a declared tool's output values enter the join table above the length floor", () => {
  const registry = new DeclarationRegistry([{ name: "lookup", args: { q: USER_DATA } }]);
  const prior = new Map<string, string>();
  registry.recordOutputs(prior, "lookup", {
    rows: [{ email: "ada@example.com" }, { note: "hi" }],
  });
  assert.deepEqual([...prior.entries()], [["ada@example.com", USER_DATA]]);
});

test("the join table is bounded so a bulk result cannot hang the close", () => {
  const registry = new DeclarationRegistry([{ name: "dump", args: { q: USER_DATA } }]);
  const prior = new Map<string, string>();
  registry.recordOutputs(
    prior,
    "dump",
    Array.from({ length: 500 }, (_, index) => `value-${String(index).padStart(5, "0")}`),
  );
  assert.equal(prior.size, MAX_PROPAGATED_VALUES_PER_STEP);
});

test("a cyclic result is bounded rather than walked forever", () => {
  const registry = new DeclarationRegistry([{ name: "looped", args: { q: USER_DATA } }]);
  const cyclic: Record<string, unknown> = { value: "ada@example.com" };
  cyclic["self"] = cyclic;
  const prior = new Map<string, string>();
  registry.recordOutputs(prior, "looped", cyclic);
  assert.ok(prior.has("ada@example.com"));
});
