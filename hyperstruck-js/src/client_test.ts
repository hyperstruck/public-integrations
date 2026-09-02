import assert from "node:assert/strict";
import { mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { HostedLearningClient } from "./client.ts";
import { ResolveBreaker } from "./runtime/resilience.ts";

interface Recorded {
  url: string;
  init: RequestInit;
}

function stubFetch(
  responses: (() => Response | Promise<Response>)[],
  recorded: Recorded[],
): typeof fetch {
  let index = 0;
  return (async (url: string, init: RequestInit) => {
    recorded.push({ url: String(url), init });
    const next = responses[Math.min(index, responses.length - 1)];
    index += 1;
    if (next === undefined) return new Response("{}", { status: 200 });
    return await next();
  }) as unknown as typeof fetch;
}

const ok = () => new Response(JSON.stringify({}), { status: 200 });

function clientWith(
  responses: (() => Response | Promise<Response>)[],
  options: Record<string, unknown> = {},
): { client: HostedLearningClient; recorded: Recorded[] } {
  const recorded: Recorded[] = [];
  const client = new HostedLearningClient({
    apiKey: "test-key",
    baseUrl: "https://api.example.com",
    clientHost: "ai-sdk",
    fetch: stubFetch(responses, recorded),
    breaker: new ResolveBreaker(),
    isSynchronousWrites: true,
    ...options,
  });
  return { client, recorded };
}

test("the declared user agent carries the product, host and capability list", () => {
  const { client } = clientWith([ok]);
  assert.equal(
    client.userAgent,
    "hyperstruck-js/0.21.0 (host=ai-sdk; caps=receipt,delivery,readonly-close)",
  );
});

test("a host or capability carrying a regex metacharacter is sanitised out", () => {
  const { client } = clientWith([ok], {
    clientHost: "ai sdk)(",
    clientCapabilities: ["receipt", "de;livery"],
  });
  assert.equal(client.userAgent, "hyperstruck-js/0.21.0 (host=aisdk; caps=receipt,delivery)");
});

test("a non-HTTPS base URL is refused so the API key cannot go in cleartext", () => {
  assert.throws(
    () => new HostedLearningClient({ apiKey: "k", baseUrl: "http://api.example.com" }),
    /must be https/,
  );
  // Localhost stays available as the explicit local-development escape hatch.
  new HostedLearningClient({ apiKey: "k", baseUrl: "http://localhost:8000" });
});

test("a missing API key is refused at construction rather than at the first call", () => {
  const saved = process.env["HYPERSTRUCK_API_KEY"];
  delete process.env["HYPERSTRUCK_API_KEY"];
  try {
    assert.throws(() => new HostedLearningClient({}), /requires an API key/);
  } finally {
    if (saved !== undefined) process.env["HYPERSTRUCK_API_KEY"] = saved;
  }
});

test("resolve reads advice and claims, and carries no obligation fields", async () => {
  const { client } = clientWith([
    () =>
      new Response(
        JSON.stringify({
          injected_text: "- advice",
          injected_facts_text: "- Harlow Freight owes the migration plan",
          offered_learning_ids: ["a1"],
          offered_claim_ids: ["key-1"],
          claims: [{ id: "key-1", state: "open" }],
        }),
        { status: 200 },
      ),
  ]);
  const context = await client.resolve({
    identity: { agentName: "agent" },
    runId: "r",
    goal: "g",
  });
  assert.equal(context.injectedFactsText, "- Harlow Freight owes the migration plan");
  assert.deepEqual(context.offeredClaimIds, ["key-1"]);
  assert.deepEqual(Object.keys(context).sort(), [
    "hasReportedOutcomes",
    "injectedFactsText",
    "injectedText",
    "offeredClaimIds",
    "offeredLearningIds",
  ]);
});

test("a 5xx on resolve trips the breaker and a 4xx does not", async () => {
  const breaker = new ResolveBreaker({ failureThreshold: 1 });
  const { client } = clientWith([() => new Response("", { status: 400 })], { breaker });
  await assert.rejects(
    client.resolve({ identity: { agentName: "a" }, runId: "r", goal: "g" }),
    /400/,
  );
  assert.equal(breaker.isOpen, false);

  const serverBreaker = new ResolveBreaker({ failureThreshold: 1 });
  const { client: second } = clientWith([() => new Response("", { status: 503 })], {
    breaker: serverBreaker,
  });
  await assert.rejects(
    second.resolve({ identity: { agentName: "a" }, runId: "r", goal: "g" }),
    /503/,
  );
  assert.equal(serverBreaker.isOpen, true);
});

test("an open breaker turns the run away without spending a timeout on it", async () => {
  const breaker = new ResolveBreaker({ failureThreshold: 1 });
  breaker.recordFailure();
  const recorded: Recorded[] = [];
  const client = new HostedLearningClient({
    apiKey: "k",
    baseUrl: "https://api.example.com",
    breaker,
    fetch: stubFetch([ok], recorded),
  });
  await assert.rejects(
    client.resolve({ identity: { agentName: "a" }, runId: "r", goal: "g" }),
    /circuit is open/,
  );
  assert.equal(recorded.length, 0);
});

test("an observed episode is redacted before it leaves the process", async () => {
  const { client, recorded } = clientWith([ok]);
  await client.observe({
    identity: { agentName: "agent" },
    episode: {
      runId: "r",
      goal: "g",
      steps: [
        {
          id: "1",
          name: "login",
          args: { token: "hunter2secret" },
          declaredSensitivity: { args: { token: "secret" } },
        },
      ],
    },
  });
  const body = String(recorded[0]?.init.body);
  assert.ok(!body.includes("hunter2secret"));
  assert.ok(body.includes("[REDACTED:secret]"));
});

test("a reinforced episode is redacted on the same path", async () => {
  const { client, recorded } = clientWith([ok]);
  await client.reinforce({
    identity: { agentName: "agent" },
    episode: {
      runId: "r",
      goal: "g",
      steps: [
        {
          id: "1",
          name: "login",
          args: { token: "hunter2secret" },
          declaredSensitivity: { args: { token: "secret" } },
        },
      ],
    },
  });
  assert.ok(!String(recorded[0]?.init.body).includes("hunter2secret"));
});

test("reinforce returns the boundary's per-id presence verdict when it sends one", async () => {
  const { client } = clientWith([
    () =>
      new Response(
        JSON.stringify({
          status: "accepted",
          presence_outcomes: [{ id: "a1", outcome: "delivered_verbatim" }],
        }),
        { status: 200 },
      ),
  ]);
  const outcomes = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
  });
  assert.deepEqual(outcomes.presenceOutcomes, [{ id: "a1", outcome: "delivered_verbatim" }]);
});

test("a boundary that returns no presence outcomes yields an empty list, not a guess", async () => {
  const { client } = clientWith([() => new Response(JSON.stringify({ status: "accepted" }), { status: 200 })]);
  assert.deepEqual(
    await client.reinforce({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } }),
    { presenceOutcomes: [], keysAwaitingReview: null },
  );
});

test("a decline reason outside the closed set is refused before it reaches the wire", async () => {
  const { client, recorded } = clientWith([ok]);
  await assert.rejects(
    client.decline({ identity: { agentName: "a" }, runId: "r", reason: "made_up" }),
    /reason must be one of/,
  );
  assert.equal(recorded.length, 0);
});

test("a transient failure is retried and a 4xx is not", async () => {
  let calls = 0;
  const { client } = clientWith(
    [
      () => {
        calls += 1;
        return new Response("", { status: 503 });
      },
    ],
    { retryBackoffMs: 1 },
  );
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(calls, 3);
  assert.equal(client.writesFailed, 1);
  assert.equal(client.writesTerminalFailed, 0);

  calls = 0;
  const { client: rejecting } = clientWith(
    [
      () => {
        calls += 1;
        return new Response("", { status: 422 });
      },
    ],
    { retryBackoffMs: 1 },
  );
  await rejecting.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(calls, 1);
  assert.equal(rejecting.writesTerminalFailed, 1);
});

test("a durable write is parked, then released on delivery", async () => {
  const directory = mkdtempSync(join(tmpdir(), "hs-client-"));
  const { client } = clientWith([ok], { durableQueueDir: directory });
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(readdirSync(directory).length, 0);
});

test("a durable write survives an outage and drains on the next start", async () => {
  const directory = mkdtempSync(join(tmpdir(), "hs-client-"));
  const { client } = clientWith([() => new Response("", { status: 503 })], {
    durableQueueDir: directory,
    retryBackoffMs: 1,
  });
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(readdirSync(directory).length, 1);

  const { client: restarted } = clientWith([ok], { durableQueueDir: directory });
  assert.equal(await restarted.replayDurableQueue(), 1);
  assert.equal(readdirSync(directory).length, 0);
});

test("a durably parked write refused with a 4xx is released rather than re-sent forever", async () => {
  const directory = mkdtempSync(join(tmpdir(), "hs-client-"));
  const { client } = clientWith([() => new Response("", { status: 422 })], {
    durableQueueDir: directory,
    retryBackoffMs: 1,
  });
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(readdirSync(directory).length, 0);
});

test("nothing is parked when durability was not asked for", async () => {
  const { client } = clientWith([ok]);
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(client.writesDelivered, 1);
});

test("an asynchronous write does not block the host, and drain waits for it", async () => {
  let release = (): void => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const { client } = clientWith(
    [
      async () => {
        await held;
        return ok();
      },
    ],
    { isSynchronousWrites: false },
  );
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  // The host is back with the write still in flight, which is the whole point of the
  // default mode: a run must never wait on a boundary it does not read.
  assert.equal(client.writesDelivered, 0);
  release();
  await client.drain(1000);
  assert.equal(client.writesDelivered, 1);
});

test("synchronous mode delivers inline, for a host with no process to outlive the call", async () => {
  const { client, recorded } = clientWith([ok], { isSynchronousWrites: true });
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(recorded.length, 1);
  assert.equal(client.writesDelivered, 1);
});

test("an empty roster is omitted so an older API does not reject the whole write", async () => {
  const { client, recorded } = clientWith([ok]);
  await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  const body = JSON.parse(String(recorded[0]?.init.body)) as Record<string, unknown>;
  const episode = body["episode"] as Record<string, unknown>;
  assert.ok(!("available_tools" in episode));
  assert.ok(!("principal_utterance" in episode));
  assert.ok(!("spans" in episode));
});

test("spans reach the wire, so principalUtterance survives the containment check", async () => {
  // Without them the platform drops the utterance for every caller on this client: it has no
  // tagged prose to place it in, and answers no rather than yes.
  const { client, recorded } = clientWith([ok]);
  await client.observe({
    identity: { agentName: "a" },
    episode: {
      runId: "r",
      goal: "<tag>x</tag>use British English",
      principalUtterance: "use British English",
      spans: [
        { text: "<tag>x</tag>", origin: "harness" },
        { text: "use British English", origin: "user_prose" },
      ],
    },
  });
  const body = JSON.parse(String(recorded[0]?.init.body)) as Record<string, unknown>;
  const episode = body["episode"] as Record<string, unknown>;
  assert.deepStrictEqual(episode["spans"], [
    { text: "<tag>x</tag>", origin: "harness" },
    { text: "use British English", origin: "user_prose" },
  ]);
  assert.strictEqual(episode["principal_utterance"], "use British English");
});

test("a reinforce tells the host how many keys wait on a person", async () => {
  const { client } = clientWith([
    () => new Response(JSON.stringify({ status: "accepted", keys_awaiting_review: 3 }), { status: 200 }),
  ]);
  const result = await client.reinforce({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(result.keysAwaitingReview, 3);
});

test("an observe tells the host how many keys wait on a person", async () => {
  const { client } = clientWith([
    () => new Response(JSON.stringify({ status: "accepted", keys_awaiting_review: 2 }), { status: 200 }),
  ]);
  const result = await client.observe({ identity: { agentName: "a" }, episode: { runId: "r", goal: "g" } });
  assert.equal(result.keysAwaitingReview, 2);
});

test("a boundary that does not say leaves the count unknown, never zero", async () => {
  const { client } = clientWith([
    () => new Response(JSON.stringify({ status: "accepted" }), { status: 200 }),
    () => new Response(JSON.stringify({ status: "accepted" }), { status: 200 }),
  ]);
  const episode = { runId: "r", goal: "g" };
  assert.equal((await client.reinforce({ identity: { agentName: "a" }, episode })).keysAwaitingReview, null);
  assert.equal((await client.observe({ identity: { agentName: "a" }, episode })).keysAwaitingReview, null);
});
