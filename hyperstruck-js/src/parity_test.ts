/**
 * What pins this package to the platform and to the Python seat.
 *
 * Contract parity tests prove the two seats agree with the platform schema and with each
 * other. They are necessary and they are not the proof: a real run through the boundary
 * is. What they do catch is the class of drift that is invisible until a customer's run
 * loses its episode, because both halves still look right on their own.
 *
 * **What this file can and cannot catch, stated because the limit is easy to miss.** It
 * compares *constants* by reading the other language's source, so it catches a vocabulary
 * that drifted, a renamed member, a floor that moved. It does not compare behaviour, and
 * two seats can agree on every string here while disagreeing about what they do with them.
 * Behavioural parity is each language's own suite plus the shared e2e harness, which drives
 * both seats against one boundary and asserts the same outcomes; this file is the cheap
 * guard that runs on every change, not the proof.
 *
 * These reach across the repository into `hyperstruck-py` and into the platform's own
 * models. That is deliberate and is the reason the two packages live in one repository:
 * the receipt gate's pattern is read out of a User-Agent this package builds, must move
 * in lockstep with its version, and shares its regex character for character with a
 * Postgres function. Those drift the moment they stop landing in one commit.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { DEFAULT_CAPABILITIES } from "./client.ts";
import {
  CLOSURE_APPLIED,
  CLOSURE_BUSY,
  DECLINE_REASONS,
  publishedDeclineReasons,
} from "./wire.ts";
import {
  DELIVERED_REFORMATTED,
  DELIVERED_VERBATIM,
  UNRESOLVED,
} from "./runtime/receipt.ts";
import {
  CLOSE_TRIGGER_ABANDONED,
  CLOSE_TRIGGER_EXPLICIT,
  CLOSE_TRIGGER_NO_TOOL_CALLS,
  CLOSE_TRIGGER_PROCESS_EXIT,
  DISPOSITION_DECLINED,
  DISPOSITION_EVICTED,
  DISPOSITION_OBSERVED,
  DISPOSITION_REINFORCED,
  DISPOSITION_WITHHELD,
  DISPOSITION_WRITE_FAILED,
  OUTCOME_DELIVERED,
  OUTCOME_RECALL_MISSING,
  OUTCOME_RECALL_UNCLAIMED,
  OUTCOME_RESOLVE_EMPTY,
  OUTCOME_RESOLVE_FAILED,
} from "./runtime/run.ts";
import { SECRET, SHAREABLE, SUBJECT_KEY, USER_DATA } from "./runtime/declarations.ts";
import { CLIENT_PRODUCT, VERSION } from "./version.ts";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const PACKAGE_ROOT = fileURLToPath(new URL("..", import.meta.url));
const PUBLIC_INTEGRATIONS = fileURLToPath(new URL("../..", import.meta.url));
const PLATFORM_ROOT = fileURLToPath(new URL("../../..", import.meta.url));

function pythonSource(relative: string): string {
  return readFileSync(`${PUBLIC_INTEGRATIONS}/hyperstruck-py/src/hyperstruck/${relative}`, "utf8");
}

function platformSource(relative: string): string {
  return readFileSync(`${PLATFORM_ROOT}/${relative}`, "utf8");
}

test("the vendored decline vocabulary is byte-identical to the Python client's", () => {
  const ours = readFileSync(`${PACKAGE_ROOT}contracts/published_decline_reasons.json`, "utf8");
  const theirs = readFileSync(
    `${PUBLIC_INTEGRATIONS}/hyperstruck-py/src/hyperstruck/published_decline_reasons.json`,
    "utf8",
  );
  assert.equal(ours, theirs);
});

test("the decline reasons this client knows are the ones the Python client knows", () => {
  const source = pythonSource("_wire.py");
  const declared = [...source.matchAll(/^REASON_[A-Z_]+ = "([a-z_]+)"$/gm)].map(
    (match) => match[1] as string,
  );
  assert.deepEqual([...DECLINE_REASONS].sort(), declared.sort());
});

test("the published set is a subset of the set this client knows, never the reverse", () => {
  // The client ships ahead of the boundary by design and withholds what the boundary has
  // not published. A published reason this client does not know is the opposite mistake:
  // it means a vocabulary landed at the boundary and one of the two clients was not told.
  for (const reason of publishedDeclineReasons()) {
    assert.ok(DECLINE_REASONS.has(reason), `published reason ${reason} is unknown here`);
  }
});

test("the recall outcome taxonomy matches the Python seat's, member for member", () => {
  const source = pythonSource("runtime/run.py");
  const declared = [...source.matchAll(/^OUTCOME_[A-Z_]+ = "([a-z_]+)"$/gm)].map(
    (match) => match[1] as string,
  );
  assert.deepEqual(
    [
      OUTCOME_DELIVERED,
      OUTCOME_RESOLVE_FAILED,
      OUTCOME_RESOLVE_EMPTY,
      OUTCOME_RECALL_UNCLAIMED,
      OUTCOME_RECALL_MISSING,
    ].sort(),
    declared.sort(),
  );
});

test("the three receipt fidelity outcomes match the Python seat's", () => {
  const source = pythonSource("runtime/receipt.py");
  const declared = [
    ...source.matchAll(/^(?:DELIVERED_[A-Z]+|UNRESOLVED) = "([a-z_]+)"$/gm),
  ].map((match) => match[1] as string);
  assert.deepEqual(
    [DELIVERED_VERBATIM, DELIVERED_REFORMATTED, UNRESOLVED].sort(),
    declared.sort(),
  );
});

test("the sensitivity lattice and its order match the Python seat's", () => {
  const source = pythonSource("runtime/declarations.py");
  const order = /_ORDER = \(([^)]*)\)/.exec(source)?.[1] ?? "";
  assert.deepEqual(
    order.split(",").map((name) => name.trim()).filter(Boolean),
    ["SECRET", "USER_DATA", "SHAREABLE"],
  );
  const values = [...source.matchAll(/^(SECRET|USER_DATA|SHAREABLE) = "([a-z_]+)"$/gm)].map(
    (match) => match[2] as string,
  );
  assert.deepEqual([SECRET, USER_DATA, SHAREABLE], values);
});

test("the subject key both seats stamp is the one Core reads", () => {
  const source = pythonSource("runtime/declarations.py");
  assert.match(source, new RegExp(`SUBJECT_KEY = "${SUBJECT_KEY}"`));
});

test("the close triggers match the Python seat's, member for member", () => {
  const source = pythonSource("runtime/run.py");
  const declared = [...source.matchAll(/^CLOSE_TRIGGER_[A-Z_]+ = "([a-z_]+)"$/gm)].map(
    (match) => match[1] as string,
  );
  assert.deepEqual(
    [
      CLOSE_TRIGGER_EXPLICIT,
      CLOSE_TRIGGER_NO_TOOL_CALLS,
      CLOSE_TRIGGER_PROCESS_EXIT,
      CLOSE_TRIGGER_ABANDONED,
    ].sort(),
    declared.sort(),
  );
});

test("the dispositions match the Python seat's, member for member", () => {
  const source = pythonSource("runtime/run.py");
  const declared = [...source.matchAll(/^DISPOSITION_[A-Z_]+ = "([a-z_]+)"$/gm)].map(
    (match) => match[1] as string,
  );
  assert.deepEqual(
    [
      DISPOSITION_REINFORCED,
      DISPOSITION_OBSERVED,
      DISPOSITION_DECLINED,
      DISPOSITION_EVICTED,
      DISPOSITION_WITHHELD,
      DISPOSITION_WRITE_FAILED,
    ].sort(),
    declared.sort(),
  );
});

test("both seats give a run a discriminated id under a possibly-stable key", () => {
  // The key correlates and the run id identifies. If either language collapsed the two, a
  // second turn under one conversation id would be deduped away server-side and lost.
  const source = pythonSource("runtime/run.py");
  assert.match(source, /run_id=f"\{self\._identity\.agent_name\}:\{key\.key\}:\{/);
  const ours = readFileSync(`${HERE}runtime/run.ts`, "utf8");
  assert.match(ours, /runId: `\$\{this\.identity\.agentName\}:\$\{key\.key\}:\$\{/);
});

test("both seats default to the same close grace window", () => {
  const source = pythonSource("runtime/run.py");
  const seconds = /DEFAULT_CLOSE_GRACE_SECONDS = ([0-9.]+)/.exec(source)?.[1];
  assert.ok(seconds !== undefined);
  const ours = readFileSync(`${HERE}runtime/run.ts`, "utf8");
  const ms = /DEFAULT_CLOSE_GRACE_MS = ([0-9_]+)/.exec(ours)?.[1];
  assert.ok(ms !== undefined);
  assert.equal(Number(ms.replace(/_/g, "")), Number(seconds) * 1000);
});

test("both content scanners take the same span shape and the same echo policy", () => {
  // The one place the two seats genuinely diverged in *behaviour* while a parity test
  // asserted they agreed: Python took values and TypeScript took spans, so identical
  // detector output produced different redaction. Pinned on the fields and on the policy,
  // because a shape that matches and a behaviour that does not is the worse failure.
  const source = pythonSource("runtime/scanning.py");
  const ours = readFileSync(`${HERE}runtime/scanning.ts`, "utf8");

  for (const field of ["start: int", "end: int", "kind: str", "label: str | None"]) {
    assert.ok(source.includes(field), `the Python Finding is missing ${field}`);
  }
  for (const field of ["start: number", "end: number", "kind: string", "label?: string"]) {
    assert.ok(ours.includes(field), `the TypeScript Finding is missing ${field}`);
  }

  // Both run the echo pass, and both fence it the way the declared-value scrubber does: a
  // negative lookbehind on a word character, so a coincidental substring survives.
  assert.ok(source.includes("(?<!"), "the Python echo pass is unfenced");
  assert.ok(ours.includes("(?<!"), "the TypeScript echo pass is unfenced");

  // And both default an absent label to the most restrictive member rather than to none.
  assert.ok(source.includes("UNDECLARED_SENSITIVITY"));
  assert.ok(ours.includes("UNDECLARED_SENSITIVITY"));
});

test("the material step threshold matches the Python turn gate's", () => {
  const source = pythonSource("turn_gate.py");
  assert.match(source, /MIN_MATERIAL_STEPS = 2/);
});

/**
 * Three assertions below depend on the platform half of this work, which the spec's PR
 * plan lands as its own group ahead of this package. Until it does, they skip with the
 * prerequisite named rather than passing quietly: a parity test that goes green because
 * the thing it pins does not exist yet is worse than no test, because it reads as
 * evidence afterwards. Once the platform half lands they run, and they fail if the two
 * halves ever disagree.
 */
const PLATFORM_MODELS = platformSource("api/models/learning_boundary.py");
const IS_CAPABILITY_DECLARATION_LANDED = PLATFORM_MODELS.includes(
  "DECLARED_CAPABILITIES_PATTERN",
);
const PREREQUISITE =
  "the receipt gate's capability declaration has not landed on this branch yet; " +
  "this assertion runs once the platform half is merged";

test("the boundary lists this client's product token as receipt capable", (t) => {
  if (!IS_CAPABILITY_DECLARATION_LANDED) return t.skip(PREREQUISITE);
  // Read out of RECEIPT_CAPABLE_CLIENT_NAMES, which is the set of products the gate
  // recognises and carries no versions. It used to be a name-to-floor mapping and this
  // assertion matched `"hyperstruck-js": (`; the floor was split out because this client
  // declares from its first release and has no pre-declaration traffic to grandfather, so
  // a version number here would have been a proxy for nothing.
  const names =
    /RECEIPT_CAPABLE_CLIENT_NAMES: tuple\[str, \.\.\.\] = \(([\s\S]*?)\)/.exec(
      PLATFORM_MODELS,
    )?.[1] ?? "";
  assert.match(names, new RegExp(`"${CLIENT_PRODUCT}"`));
});

test("this client's declared user agent satisfies the boundary's own capability pattern", (t) => {
  if (!IS_CAPABILITY_DECLARATION_LANDED) return t.skip(PREREQUISITE);
  // The pattern is read out of the platform's own source rather than transcribed here.
  // A transcription is the second copy this work objects to everywhere else, and this is
  // the one place where a divergence costs every run its credit silently.
  // Tolerates the parenthesised form as well as the bare one: the platform repo formats
  // with black, and a constant one character over the line limit is wrapped in brackets
  // onto its own line. Reading only the bare form makes a formatter able to silently stop
  // this assertion from finding anything, which is the failure it is here to prevent.
  const literal = /DECLARED_CAPABILITIES_PATTERN = \(?\s*r"([^"]+)"/.exec(
    PLATFORM_MODELS,
  )?.[1];
  assert.ok(literal !== undefined, "the platform's capability pattern could not be read");
  const capability = /RECEIPT_DECLARED_PATTERN[\s\S]{0,200}?declared_capability_pattern\(\s*([A-Z_]+)/.exec(
    PLATFORM_MODELS,
  );
  assert.ok(capability !== null, "the receipt capability constant could not be read");
  const agent = `${CLIENT_PRODUCT}/${VERSION} (host=ai-sdk; caps=${DEFAULT_CAPABILITIES.join(",")})`;
  assert.match(agent, new RegExp(literal));
  // And the host segment names a host the boundary admits.
  const hosts = /RECEIPT_CAPABLE_CLIENT_HOSTS = \(([\s\S]*?)\)/.exec(PLATFORM_MODELS)?.[1] ?? "";
  assert.match(hosts, /"ai-sdk"/);
});

test("the version this client reports is the version it publishes", () => {
  const manifest = JSON.parse(readFileSync(`${PACKAGE_ROOT}package.json`, "utf8")) as {
    version: string;
    name: string;
  };
  assert.equal(manifest.version, VERSION);
  // The product token is the User-Agent token, not the package name: an npm scope
  // contains a solidus, which is what separates product from version in a User-Agent.
  assert.equal(manifest.name, "@hyperstruck/core");
  assert.notEqual(manifest.name, CLIENT_PRODUCT);
});

/**
 * Why `src/schema.ts` is checked in and imported by nothing.
 *
 * It is the contract pin. These assertions read it as text and require every wire field
 * this client sends or reads to exist in the published schema, and the `schema-is-current`
 * CI job regenerates it and fails on a diff, so checked-in generated output cannot go
 * stale quietly. Typing the request bodies against it was considered and rejected: several
 * of them deliberately omit fields an older deployment forbids, and the type checker would
 * fight that rule hardest. Regenerate with `npm run schema`; never hand-edit it, including
 * to add a comment saying not to, which is how this job first went red.
 */
test("the resolve response fields this client reads exist in the published schema", () => {
  const schema = readFileSync(`${HERE}schema.ts`, "utf8");
  const resolveResponse = /ResolveResponse: \{([\s\S]*?)\n        \};/.exec(schema)?.[1] ?? "";
  assert.notEqual(resolveResponse, "");
  for (const field of [
    "injected_text",
    "injected_facts_text",
    "injected_obligations_text",
    "offered_learning_ids",
    "offered_claim_ids",
    "offered_obligation_ids",
  ]) {
    assert.match(
      resolveResponse,
      new RegExp(`${field}`),
      `resolve response is missing ${field}`,
    );
  }
});

test("the delivered obligation set the client reads is on the published response", (t) => {
  // Exposed by the platform half. Without it the client cannot honour the
  // offered-versus-delivered asymmetry the obligations shelf depends on: the run report
  // would claim an obligation was shown that the block's budget cut, and the ledger's two
  // sets could not be populated at all. The client already degrades to nothing-delivered,
  // which is the safe direction, so this pins the field rather than gating on it.
  const schema = readFileSync(`${HERE}schema.ts`, "utf8");
  const resolveResponse = /ResolveResponse: \{([\s\S]*?)\n        \};/.exec(schema)?.[1] ?? "";
  if (!resolveResponse.includes("offered_obligation_ids")) {
    return t.skip("the obligations shelf is not on this schema");
  }
  if (!IS_CAPABILITY_DECLARATION_LANDED) return t.skip(PREREQUISITE);
  assert.match(resolveResponse, /delivered_obligation_ids/);
});

test("the episode step fields this client sends exist in the published schema", () => {
  const schema = readFileSync(`${HERE}schema.ts`, "utf8");
  const step = /\n        StepModel: \{([\s\S]*?)\n        \};/.exec(schema)?.[1] ?? "";
  assert.notEqual(step, "");
  for (const field of ["id", "name", "args", "status", "result", "error", "declared_sensitivity"]) {
    assert.match(step, new RegExp(field), `step model is missing ${field}`);
  }
});

test("the declared sensitivity wire type admits a bare string section", () => {
  // The narrower nested-only type is what stopped a published client sending the subject
  // key at all, and with it every foreign caller fell to structural salience, which
  // fragments an entity into two dossiers that never reach the stability the read side
  // gates on.
  const schema = readFileSync(`${HERE}schema.ts`, "utf8");
  const step = /\n        StepModel: \{([\s\S]*?)\n        \};/.exec(schema)?.[1] ?? "";
  const declared = /declared_sensitivity\??:([\s\S]*?);\n/.exec(step)?.[1] ?? "";
  assert.match(declared, /string/, "the boundary no longer accepts a bare string section");
});

/**
 * The three assertions this file used to disclaim, and the reason they are now here.
 *
 * The header above says this file compares constants and not behaviour, which is still
 * true, and it also used to mean that nothing anywhere compared method signatures, return
 * types or the shape of the run report. That is a real hole rather than a documented
 * limit: the product's promise is one capability generation per minor across both
 * packages, so one language growing a parameter or a report field and the other not is
 * precisely the drift a customer discovers by moving between them, and neither language's
 * own suite can see it. These read each language's source for the declaration, which
 * cannot catch a difference in what the two do with it, and does catch the half that was
 * invisible.
 */

function snake(name: string): string {
  return name.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

test("the run report declares the same fields in both languages", () => {
  const python = pythonSource("runtime/run.py");
  // The dataclass body, taken to its first method rather than to a line count, so a field
  // added at the bottom of a growing class is inside the region rather than past it.
  const body = /\nclass RunReport:\n([\s\S]*?)\n    def /.exec(python)?.[1] ?? "";
  assert.notEqual(body, "", "the Python RunReport dataclass was not found");
  const declared = [...body.matchAll(/^ {4}([a-z_]+): /gm)].map((match) => match[1] as string);
  assert.ok(declared.length > 8, `only ${declared.length} Python fields parsed`);

  const ours = readFileSync(`${HERE}runtime/run.ts`, "utf8");
  const iface = /\nexport interface RunReport \{\n([\s\S]*?)\n\}/.exec(ours)?.[1] ?? "";
  assert.notEqual(iface, "", "the TypeScript RunReport interface was not found");
  const mine = [...iface.matchAll(/^ {2}readonly ([A-Za-z]+):/gm)].map((match) =>
    snake(match[1] as string),
  );

  assert.deepEqual(mine.sort(), declared.sort());
});

test("the run report serialises the same keys, in the same order, in both languages", () => {
  // The declaration test above compares what each report HOLDS. This compares what each
  // one WRITES, which is what a customer's log line and their observability pipeline
  // actually carry: a field declared in both and serialised in one is the same loss.
  const python = pythonSource("runtime/run.py");
  const toDict = /\n    def to_dict\(self\) -> dict\[str, Any\]:\n        return \{\n([\s\S]*?)\n        \}/.exec(
    python,
  )?.[1] ?? "";
  assert.notEqual(toDict, "", "RunReport.to_dict was not found");
  const theirKeys = [...toDict.matchAll(/^ {12}"([a-z_]+)":/gm)].map((match) => match[1] as string);

  const ours = readFileSync(`${HERE}runtime/run.ts`, "utf8");
  const toJson = /\nexport function reportToJson\(report: RunReport\): Record<string, unknown> \{\n  return \{\n([\s\S]*?)\n  \};/.exec(
    ours,
  )?.[1] ?? "";
  assert.notEqual(toJson, "", "reportToJson was not found");
  const myKeys = [...toJson.matchAll(/^ {4}([a-z_]+):/gm)].map((match) => match[1] as string);

  assert.deepEqual(myKeys, theirKeys);
});

test("both clients take the loop-level obligation outcomes and return the named result", () => {
  const python = pythonSource("client.py");
  for (const method of ["reinforce", "decline"]) {
    // EVERY declaration, not the first one found. `reinforce` is declared twice, on the
    // `LearningClient` port and on the hosted implementation, and a port that still
    // promises the old return is the divergence a customer's own client is written from.
    const declarations = [
      ...python.matchAll(
        new RegExp(`\\n    async def ${method}\\(\\n([\\s\\S]*?)\\n    \\) -> ([A-Za-z]+):`, "g"),
      ),
    ];
    assert.ok(declarations.length > 0, `no declaration of ${method} was parsed`);
    for (const declaration of declarations) {
      assert.match(
        String(declaration[1]),
        /obligation_outcomes: Sequence\[ReportedObligationOutcome\] = \(\)/,
        `a Python ${method} declaration does not take obligation_outcomes`,
      );
      assert.equal(
        declaration[2],
        "ReinforceResult",
        `a Python ${method} declaration does not return ReinforceResult`,
      );
    }
  }

  // The same two facts about this package, read from its own source rather than trusted to
  // the compiler, so the assertion fails on whichever side stops being true.
  const ours = readFileSync(`${HERE}client.ts`, "utf8");
  const port = /\nexport interface LearningClient \{\n([\s\S]*?)\n\}/.exec(ours)?.[1] ?? "";
  assert.match(port, /reinforce\(request: ReinforceRequest\): Promise<ReinforceResult>;/);
  assert.match(port, /decline\(request: DeclineRequest\): Promise<ReinforceResult>;/);
  for (const request of ["ReinforceRequest", "DeclineRequest"]) {
    const shape = new RegExp(`\\nexport interface ${request} \\{\\n([\\s\\S]*?)\\n\\}`).exec(ours)?.[1] ?? "";
    assert.match(
      shape,
      /obligationOutcomes\?: readonly ReportedObligationOutcome\[\];/,
      `${request} does not take obligationOutcomes`,
    );
  }
});

test("the two closure dispositions a caller branches on match the Python client's", () => {
  // Only these two are named as constants in either language, because only these two carry
  // a decision: `applied` is the single success and `busy` the single thing worth sending
  // again. Every other disposition is read as text, so a boundary that grows a seventh word
  // needs no client release.
  const source = pythonSource("_wire.py");
  const declared = [...source.matchAll(/^CLOSURE_([A-Z]+) = "([a-z_]+)"$/gm)].map(
    (match) => match[2] as string,
  );
  assert.deepEqual([CLOSURE_APPLIED, CLOSURE_BUSY].sort(), declared.sort());
});
