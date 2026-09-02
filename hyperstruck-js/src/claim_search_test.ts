import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import type { ClaimSearch, ClaimSearchDetail } from "./claim_search.ts";
import * as claimSearch from "./claim_search.ts";
import { HostedClaimSearchError, HostedLearningClient } from "./client.ts";

const AGENT = "11111111-1111-4111-8111-111111111111";
const ENTITY = "5f0c2a52-0c3e-4e5f-9a57-1f3a8f0d2b11";

const result = (extra: Record<string, unknown> = {}) => ({
  as_of: "2026-10-15T00:00:00Z",
  computed_at: "2026-10-15T00:00:01Z",
  shape: "point",
  text: "Harlow Freight's fiscal year ends in June.",
  claims: [],
  shares_no_word: false,
  more_matched: 0,
  ...extra,
});

function clientReplying(
  reply: () => Response,
  seen: { url: string; init: RequestInit }[],
): HostedLearningClient {
  const fetchStub = (async (url: string, init: RequestInit) => {
    seen.push({ url: String(url), init });
    return reply();
  }) as unknown as typeof fetch;
  return new HostedLearningClient({ apiKey: "k", baseUrl: "https://api.example.com", fetch: fetchStub });
}

const ok = (body: unknown = result()) => () => new Response(JSON.stringify(body), { status: 200 });

test("a question is searched as a plain read and the result comes back", async () => {
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(ok(), seen);

  const got = await client.searchClaims({ agentId: AGENT, question: "When does Harlow's year end?" });

  assert.equal(seen.length, 1);
  assert.equal(seen[0]!.url, `https://api.example.com/agents/${AGENT}/claims/search`);
  assert.equal(seen[0]!.init.method, "POST");
  assert.deepEqual(JSON.parse(String(seen[0]!.init.body)), { question: "When does Harlow's year end?" });
  assert.equal((seen[0]!.init.headers as Record<string, string>)["Idempotency-Key"], undefined);
  assert.deepEqual(got, result());
});

test("a search goes to the claims search route and the client has no answer", async () => {
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(ok(), seen);

  const got = await client.searchClaims({ agentId: AGENT, question: "When does Harlow's year end?" });

  assert.equal(seen.length, 1);
  assert.equal(seen[0]?.url, `https://api.example.com/agents/${AGENT}/claims/search`);
  assert.equal(seen[0]?.init.method, "POST");
  assert.deepEqual(got, result());
  assert.equal("answer" in client, false);
});

test("the time and detail asked for are sent and nothing else", async () => {
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(ok(result({ shape: "since" })), seen);

  await client.searchClaims({
    agentId: AGENT,
    question: "What moved?",
    asOf: new Date("2026-10-01T00:00:00Z"),
    since: "2026-09-01T00:00:00Z",
    detail: "cited",
  });

  assert.deepEqual(JSON.parse(String(seen[0]!.init.body)), {
    question: "What moved?",
    as_of: "2026-10-01T00:00:00.000Z",
    since: "2026-09-01T00:00:00Z",
    detail: "cited",
  });
});

test("an entity asked about is sent as the entity the question is narrowed to, and only when given", async () => {
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(ok(), seen);

  await client.searchClaims({ agentId: AGENT, question: "Who runs it?", entity: ENTITY });
  await client.searchClaims({ agentId: AGENT, question: "Who runs it?" });

  assert.deepEqual(
    seen.map((s) => JSON.parse(String(s.init.body))),
    [{ question: "Who runs it?", entity: ENTITY }, { question: "Who runs it?" }],
  );
});

test("the claims filter and the page are sent as the filter the search lists, and only when given", async () => {
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(ok(result({ shape: "set", cursor: null })), seen);

  await client.searchClaims({
    agentId: AGENT,
    question: "What is open with Harlow?",
    state: "open",
    kind: "obligation",
    owner: ENTITY,
    dueBefore: new Date("2026-10-01T00:00:00Z"),
    cursor: "c1",
    limit: 20,
  });

  assert.deepEqual(JSON.parse(String(seen[0]!.init.body)), {
    question: "What is open with Harlow?",
    state: "open",
    kind: "obligation",
    owner: ENTITY,
    due_before: "2026-10-01T00:00:00.000Z",
    cursor: "c1",
    limit: 20,
  });
});

test("a refusal is thrown at once with its status and detail, and never asked again", async () => {
  // A claims store still being rebuilt answers 409; waiting is the caller's choice.
  const seen: { url: string; init: RequestInit }[] = [];
  const client = clientReplying(
    () =>
      new Response(JSON.stringify({ detail: { code: "claims_not_replayed" } }), {
        status: 409,
        headers: { "Retry-After": "3" },
      }),
    seen,
  );

  await assert.rejects(
    client.searchClaims({ agentId: AGENT, question: "Where is Coil up to?" }),
    (error: unknown) =>
      error instanceof HostedClaimSearchError &&
      error.status === 409 &&
      error.retryAfterSeconds === 3 &&
      (error.detail as { code: string }).code === "claims_not_replayed",
  );
  assert.equal(seen.length, 1);
});

test("the client takes no retry or key option and has no stored answer call", () => {
  const client = new HostedLearningClient({ apiKey: "k", baseUrl: "https://api.example.com" });

  // Compile-time: `npm run typecheck` fails if either option comes back.
  // @ts-expect-error no idempotency key on a read
  void client.searchClaims({ agentId: AGENT, question: "q", idempotencyKey: "k1" }).catch(() => {});
  // @ts-expect-error no retry count on a read
  void client.searchClaims({ agentId: AGENT, question: "q", maxRetries: 2 }).catch(() => {});
  assert.equal("storedAnswer" in client, false);
  assert.equal("Answer" in claimSearch, false);
});

test("the typed result carries every field the published result does", () => {
  type Published = keyof ClaimSearch;
  const fields = ["as_of", "claims", "computed_at", "cursor", "degraded", "more_matched", "shape", "shares_no_word", "text"] as const;
  // Compile-time: `npm run typecheck` fails if the schema grows or loses a field.
  const covered: Published extends (typeof fields)[number] ? ((typeof fields)[number] extends Published ? true : never) : never = true;

  const contract = JSON.parse(readFileSync(new URL("../../openapi.json", import.meta.url), "utf8"));
  const published = Object.keys(contract.components.schemas.ClaimSearchOut.properties).sort();
  assert.deepEqual(published, [...fields].sort());
  assert.equal(covered, true);
});

test("the typed detail is the three levels the platform publishes", () => {
  const levels: ClaimSearchDetail[] = ["concise", "cited", "full"];
  const contract = JSON.parse(readFileSync(new URL("../../openapi.json", import.meta.url), "utf8"));
  assert.deepEqual(contract.components.schemas.ClaimSearchIn.properties.detail.enum, levels);
});
