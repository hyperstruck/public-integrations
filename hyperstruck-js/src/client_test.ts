import assert from "node:assert/strict";
import { mkdtempSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { HostedLearningClient } from "./client.ts";
import { CLOSURE_APPLIED, CLOSURE_BUSY } from "./wire.ts";
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
    "hyperstruck-js/0.12.0 (host=ai-sdk; caps=receipt,delivery,readonly-close)",
  );
});

test("a host or capability carrying a regex metacharacter is sanitised out", () => {
  const { client } = clientWith([ok], {
    clientHost: "ai sdk)(",
    clientCapabilities: ["receipt", "de;livery"],
  });
  assert.equal(client.userAgent, "hyperstruck-js/0.12.0 (host=aisdk; caps=receipt,delivery)");
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

test("resolve reads the three shelves and holds obligations offered apart from delivered", async () => {
  const { client } = clientWith([
    () =>
      new Response(
        JSON.stringify({
          injected_text: "- advice",
          injected_facts_text: "- fact",
          injected_obligations_text: "- obligation",
          offered_learning_ids: ["a1"],
          offered_claim_ids: ["f1"],
          offered_obligation_ids: ["o1", "o2"],
          delivered_obligation_ids: ["o1"],
        }),
        { status: 200 },
      ),
  ]);
  const context = await client.resolve({
    identity: { agentName: "agent" },
    runId: "r",
    goal: "g",
  });
  assert.deepEqual(context.offeredObligationIds, ["o1", "o2"]);
  assert.deepEqual(context.deliveredObligationIds, ["o1"]);
});

test("an older boundary returning no delivered set reads as nothing delivered", async () => {
  const { client } = clientWith([
    () => new Response(JSON.stringify({ offered_obligation_ids: ["o1"] }), { status: 200 }),
  ]);
  const context = await client.resolve({
    identity: { agentName: "agent" },
    runId: "r",
    goal: "g",
  });
  assert.deepEqual(context.deliveredObligationIds, []);
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
    { presenceOutcomes: [], obligationClosures: [] },
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

// -- loop-level obligation closure ----------------------------------------------

const CLOSED = {
  status: "accepted",
  obligation_closures: [
    { id: "o1", disposition: "applied", status: "kept" },
    { id: "o2", disposition: "not_offered", status: null },
  ],
};

test("reinforce sends the reported outcomes and returns a result per id", async () => {
  const { client, recorded } = clientWith([
    () => new Response(JSON.stringify(CLOSED), { status: 200 }),
  ]);
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [
      { id: "o1", outcome: "kept", keptBasis: "reported" },
      { id: "o2", outcome: "dropped", droppedReason: "no_longer_applies" },
    ],
  });
  const body = JSON.parse(String(recorded[0]?.init.body)) as Record<string, unknown>;
  assert.deepEqual(body["obligation_outcomes"], [
    { id: "o1", outcome: "kept", kept_basis: "reported" },
    { id: "o2", outcome: "dropped", dropped_reason: "no_longer_applies" },
  ]);
  assert.deepEqual(result.obligationClosures, [
    { id: "o1", disposition: "applied", status: "kept" },
    { id: "o2", disposition: "not_offered", status: null },
  ]);
});

test("a reinforce reporting nothing omits the field entirely", async () => {
  // Omitted, not sent as an empty array: the overwhelmingly common write reports no
  // closure, and a key in every body for the rare call that uses one is a cost every
  // caller pays.
  const { client, recorded } = clientWith([ok]);
  await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
  });
  const body = JSON.parse(String(recorded[0]?.init.body)) as Record<string, unknown>;
  assert.ok(!("obligation_outcomes" in body));
});

test("decline carries the outcomes and hands back their results", async () => {
  // `decline` returned nothing at all before this, so a host closing an obligation on a
  // declined turn had no way to learn whether the close landed.
  const { client, recorded } = clientWith([
    () => new Response(JSON.stringify(CLOSED), { status: 200 }),
  ]);
  const result = await client.decline({
    identity: { agentName: "agent" },
    runId: "r",
    reason: "no_tool_calls",
    obligationOutcomes: [{ id: "o1", outcome: "kept", keptBasis: "reported" }],
  });
  const body = JSON.parse(String(recorded[0]?.init.body)) as Record<string, unknown>;
  assert.deepEqual(body["obligation_outcomes"], [
    { id: "o1", outcome: "kept", kept_basis: "reported" },
  ]);
  assert.deepEqual(
    result.obligationClosures.map((closure) => closure.id),
    ["o1", "o2"],
  );
  // A declined turn was never credited, so there is no presence verdict to read back.
  assert.deepEqual(result.presenceOutcomes, []);
});

test("an incoherent reported outcome is refused before it reaches the wire", async () => {
  // Refused here rather than left to the boundary's 422: a write is fire-and-forget by
  // default, so a rejected body would be swallowed with nothing said and the host would
  // believe it had closed a row that is still open.
  const { client, recorded } = clientWith([ok]);
  await assert.rejects(
    client.reinforce({
      identity: { agentName: "agent" },
      episode: { runId: "r", goal: "g" },
      obligationOutcomes: [{ id: "o1", outcome: "kept" }],
    }),
    /keptBasis/,
  );
  await assert.rejects(
    client.reinforce({
      identity: { agentName: "agent" },
      episode: { runId: "r", goal: "g" },
      obligationOutcomes: [{ id: "o1", outcome: "dropped" }],
    }),
    /droppedReason/,
  );
  assert.equal(recorded.length, 0);
});

test("a disposition this client does not know is still carried", async () => {
  // Read as sent rather than checked against a vocabulary. A disposition the boundary
  // grows later is still its answer about that id, and refusing it here would turn a
  // server that gained a word into a client reporting the close as never judged.
  const { client } = clientWith([
    () =>
      new Response(
        JSON.stringify({
          status: "accepted",
          obligation_closures: [
            { id: "o1", disposition: "deferred_to_operator", status: "open" },
          ],
        }),
        { status: 200 },
      ),
  ]);
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [{ id: "o1", outcome: "kept", keptBasis: "reported" }],
  });
  assert.deepEqual(result.obligationClosures, [
    { id: "o1", disposition: "deferred_to_operator", status: "open" },
  ]);
});

test("a closure list this client cannot read comes back empty", async () => {
  // Empty rather than throwing, on every shape a deployment could answer with. This runs
  // on the write path of a host's own turn: a body one field short of what was expected
  // must not become an exception the host sees.
  for (const raw of [
    { obligation_closures: "applied" },
    { obligation_closures: [null, 3, { id: "o1" }, { disposition: "applied" }] },
    {},
  ]) {
    const { client } = clientWith([
      () => new Response(JSON.stringify({ status: "accepted", ...raw }), { status: 200 }),
    ]);
    const result = await client.reinforce({
      identity: { agentName: "agent" },
      episode: { runId: "r", goal: "g" },
    });
    assert.deepEqual(result.obligationClosures, []);
  }
});

test("a busy closure is the one a caller may send again", async () => {
  // The two words are deliberately different: a caller that retries a `refused` loops for
  // ever, and one that abandons a `busy` loses the close.
  const { client } = clientWith([
    () =>
      new Response(
        JSON.stringify({
          status: "accepted",
          obligation_closures: [
            { id: "o1", disposition: CLOSURE_BUSY, status: null },
            { id: "o2", disposition: "refused", status: "open" },
          ],
        }),
        { status: 200 },
      ),
  ], { retryBackoffMs: 0 });
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [{ id: "o1", outcome: "kept", keptBasis: "reported" }],
  });
  assert.deepEqual(
    result.obligationClosures.map((closure) => closure.disposition === CLOSURE_BUSY),
    [true, false],
  );
  assert.notEqual(result.obligationClosures[0]?.disposition, CLOSURE_APPLIED);
});

function closuresResponse(...closures: [string, string][]): () => Response {
  return () =>
    new Response(
      JSON.stringify({
        status: "accepted",
        obligation_closures: closures.map(([id, disposition]) => ({ id, disposition, status: null })),
      }),
      { status: 200 },
    );
}

function sentOutcomeIds(recorded: Recorded): string[] {
  const body = JSON.parse(String(recorded.init.body)) as {
    obligation_outcomes: { id: string }[];
  };
  return body.obligation_outcomes.map((outcome) => outcome.id);
}

const TWO_KEPT = [
  { id: "o1", outcome: "kept", keptBasis: "reported" },
  { id: "o2", outcome: "kept", keptBasis: "reported" },
] as const;

test("a busy close is sent again alone and its answer replaces busy", async () => {
  const { client, recorded } = clientWith(
    [closuresResponse(["o1", CLOSURE_BUSY], ["o2", CLOSURE_APPLIED]), closuresResponse(["o1", CLOSURE_APPLIED])],
    { retryBackoffMs: 0 },
  );
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: TWO_KEPT,
  });
  assert.deepEqual(sentOutcomeIds(recorded[1]!), ["o1"]);
  assert.deepEqual(
    result.obligationClosures.map((closure) => [closure.id, closure.disposition]),
    [
      ["o1", CLOSURE_APPLIED],
      ["o2", CLOSURE_APPLIED],
    ],
  );
});

test("a fire-and-forget caller still has its busy close sent again", async () => {
  // The caller that can never read `busy` is the one that needs the resend most.
  const { client, recorded } = clientWith(
    [closuresResponse(["o1", CLOSURE_BUSY]), closuresResponse(["o1", CLOSURE_APPLIED])],
    { retryBackoffMs: 0, isSynchronousWrites: false },
  );
  await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [TWO_KEPT[0]],
  });
  await client.drain();
  assert.equal(recorded.length, 2);
  assert.deepEqual(sentOutcomeIds(recorded[1]!), ["o1"]);
});

test("a busy close reported under another spelling of its id is still resent", async () => {
  // The boundary echoes a UUID lower-case and hyphenated, whatever the caller sent.
  const raw = "7F9C1E2A4B6D4E8FA0B1C2D3E4F5A6B7";
  const echoed = "7f9c1e2a-4b6d-4e8f-a0b1-c2d3e4f5a6b7";
  const { client, recorded } = clientWith(
    [closuresResponse([echoed, CLOSURE_BUSY]), closuresResponse([echoed, CLOSURE_APPLIED])],
    { retryBackoffMs: 0 },
  );
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [{ id: raw, outcome: "kept", keptBasis: "reported" }],
  });
  assert.deepEqual(sentOutcomeIds(recorded[1]!), [raw]);
  assert.equal(result.obligationClosures[0]?.disposition, CLOSURE_APPLIED);
});

test("a resend answering under another spelling still replaces busy", async () => {
  // The busy answer and the resend's answer may spell the same UUID differently.
  const first = "7F9C1E2A4B6D4E8FA0B1C2D3E4F5A6B7";
  const second = "7f9c1e2a-4b6d-4e8f-a0b1-c2d3e4f5a6b7";
  const { client, recorded } = clientWith(
    [closuresResponse([first, CLOSURE_BUSY]), closuresResponse([second, CLOSURE_APPLIED])],
    { retryBackoffMs: 0 },
  );
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [{ id: second, outcome: "kept", keptBasis: "reported" }],
  });
  assert.equal(recorded.length, 2);
  assert.equal(result.obligationClosures[0]?.disposition, CLOSURE_APPLIED);
});

test("a close that stays busy is sent again a bounded number of times", async () => {
  const { client, recorded } = clientWith([closuresResponse(["o1", CLOSURE_BUSY])], {
    retryBackoffMs: 0,
  });
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [TWO_KEPT[0]],
  });
  assert.equal(recorded.length, 4);
  assert.equal(result.obligationClosures[0]?.disposition, CLOSURE_BUSY);
});

test("a closure whose status is absent reads as null, not as missing", async () => {
  // An omitted key and an explicit null are the same answer: no row this call read. The
  // boundary sends null today; a deployment that omits the key instead must not leave a
  // host holding `undefined`, because `"status" in closure` then answers differently.
  const { client } = clientWith([
    () =>
      new Response(
        JSON.stringify({
          status: "accepted",
          obligation_closures: [
            { id: "o1", disposition: "not_found" },
            { id: "o2", disposition: "applied", status: 7 },
          ],
        }),
        { status: 200 },
      ),
  ]);
  const result = await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [{ id: "o1", outcome: "kept", keptBasis: "reported" }],
  });
  for (const closure of result.obligationClosures) {
    assert.strictEqual(closure.status, null);
    assert.ok("status" in closure);
  }
});

test("an empty list of outcomes is the same as reporting none", async () => {
  // Passed explicitly, which is what a host building the list from a filter actually sends
  // on the common turn. It must not put a key in the body any more than omitting it does.
  const { client, recorded } = clientWith([ok, ok]);
  await client.reinforce({
    identity: { agentName: "agent" },
    episode: { runId: "r", goal: "g" },
    obligationOutcomes: [],
  });
  await client.decline({
    identity: { agentName: "agent" },
    runId: "r",
    reason: "no_tool_calls",
    obligationOutcomes: [],
  });
  for (const entry of recorded) {
    const body = JSON.parse(String(entry.init.body)) as Record<string, unknown>;
    assert.ok(!("obligation_outcomes" in body));
  }
});
