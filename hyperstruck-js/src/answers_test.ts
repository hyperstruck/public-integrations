import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import type { AnswerAt } from "./answers.ts";
import { HostedLearningClient } from "./client.ts";

const AGENT = "11111111-1111-4111-8111-111111111111";

function clientReplying(
  reply: (url: string, init: RequestInit) => unknown,
  seen: { url: string; init: RequestInit }[],
): HostedLearningClient {
  const fetchStub = (async (url: string, init: RequestInit) => {
    seen.push({ url: String(url), init });
    return new Response(JSON.stringify(reply(String(url), init)), { status: 200 });
  }) as unknown as typeof fetch;
  return new HostedLearningClient({ apiKey: "k", baseUrl: "https://api.example.com", fetch: fetchStub });
}

const body = (detail: string, extra: Record<string, unknown> = {}) => ({
  answer_id: "a1",
  detail,
  answer: "Week 5.",
  more: {},
  ...extra,
});

test("an answer is asked for at one level and comes back at it", async () => {
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(() => body("findings", { findings: [] }), seen);

  const got = await client.answer({
    agentId: AGENT,
    question: "Where is Coil up to?",
    detail: "findings",
    idempotencyKey: "k1",
  });

  const findings = got.body.findings;
  assert.deepEqual(findings, []);
  assert.equal(seen[0]?.url, `https://api.example.com/agents/${AGENT}/answer`);
  assert.equal(seen[0]?.init.method, "POST");
  assert.deepEqual(JSON.parse(String(seen[0]?.init.body)), {
    question: "Where is Coil up to?",
    detail: "findings",
  });
  assert.equal((seen[0]?.init.headers as Record<string, string>)["Idempotency-Key"], "k1");
});

test("more fetches the same answer at a higher level from its own link", async () => {
  const link = `/agents/${AGENT}/answers/a1?detail=claims`;
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(
    (_url, init) =>
      init.method === "POST"
        ? body("answer", { more: { claims: link } })
        : body("claims", { findings: [], claims: {} }),
    seen,
  );

  const first = await client.answer({ agentId: AGENT, question: "q" });
  const later = await first.more("claims");

  const claims = later.body.claims;
  assert.deepEqual(claims, {});
  assert.equal(seen[1]?.init.method, "GET");
  assert.equal(seen[1]?.url, `https://api.example.com${link}`);
});

test("more refuses a level the answer does not offer and says why", async () => {
  const client = clientReplying(
    () => body("answer", { more: null, more_unavailable_reason: "not_stored" }),
    [],
  );
  const unstored = await client.answer({ agentId: AGENT, question: "q" });
  await assert.rejects(unstored.more("claims"), /not_stored/);
});

test("the typed answer carries background_finding_ids from findings up and never at answer", () => {
  // Compile-time: `npm run typecheck` fails if either line stops holding.
  const atFindings: AnswerAt<"findings">["background_finding_ids"] = ["f1"];
  type AtAnswer = "background_finding_ids" extends keyof AnswerAt<"answer"> ? never : true;
  const absentAtAnswer: AtAnswer = true;
  type NullableAtFindings = null extends AnswerAt<"findings">["background_finding_ids"] ? true : never;
  const nullable: NullableAtFindings = true;
  assert.equal(nullable, true);
  assert.deepEqual(atFindings, ["f1"]);
  assert.equal(absentAtAnswer, true);
});

test("the typed answer carries lead from findings up, always present, and never at answer", () => {
  // Compile-time: `npm run typecheck` fails if either line stops holding.
  type AtAnswer = "lead" extends keyof AnswerAt<"answer"> ? never : true;
  const absentAtAnswer: AtAnswer = true;
  type RequiredAtFindings = undefined extends AnswerAt<"findings">["lead"] ? never : true;
  const required: RequiredAtFindings = true;
  assert.equal(absentAtAnswer, true);
  assert.equal(required, true);
});

test("the typed answer body admits null wherever the published answer does", () => {
  type Everything = AnswerAt<"everything">;
  type Published = keyof Everything;
  type TypedNullable = { [K in Published]: null extends Everything[K] ? K : never }[Published];
  const nullableNames = [
    "appended_finding_ids",
    "background_finding_ids",
    "claims",
    "findings",
    "multi_valued_slots",
    "read_documents",
    "results",
    "sections",
    "stage_events",
    "subject",
  ] as const;
  // Compile-time: `npm run typecheck` fails if any of these names stops admitting null.
  const admitted: (typeof nullableNames)[number] extends TypedNullable ? true : never = true;

  const properties = JSON.parse(
    readFileSync(new URL("../../openapi.json", import.meta.url), "utf8"),
  ).components.schemas.AnswerView.properties as Record<string, { anyOf?: { type?: string }[] }>;
  const published = Object.entries(properties)
    .filter(([, p]) => (p.anyOf ?? []).some((member) => member.type === "null"))
    .map(([name]) => name);
  for (const name of nullableNames) {
    assert.ok(published.includes(name), `${name} is no longer nullable in the published answer`);
  }
  assert.equal(admitted, true);
});
