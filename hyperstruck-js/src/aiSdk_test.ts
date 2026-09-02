import assert from "node:assert/strict";
import { test } from "node:test";

import { hyperstruckMiddleware } from "./aiSdk.ts";
import type { DeclineRequest, LearningClient, ReinforceRequest } from "./client.ts";
import { RunSeat, type RunReport } from "./runtime/run.ts";
import type {
  Episode,
  ObligationClosureResult,
  ReinforceResult,
  ResolvedContext,
} from "./wire.ts";

const EMPTY: ResolvedContext = {
  injectedText: null,
  injectedFactsText: null,
  injectedObligationsText: null,
  offeredLearningIds: [],
  offeredClaimIds: [],
  offeredObligationIds: [],
  deliveredObligationIds: [],
};

class FakeClient implements LearningClient {
  context: ResolvedContext = EMPTY;
  observed: Episode[] = [];
  reinforced: ReinforceRequest[] = [];
  declined: DeclineRequest[] = [];
  declineClosures: readonly ObligationClosureResult[] = [];
  resolveCalls = 0;

  async resolve(): Promise<ResolvedContext> {
    this.resolveCalls += 1;
    return this.context;
  }
  async observe(request: { episode: Episode }): Promise<void> {
    this.observed.push(request.episode);
  }
  async reinforce(request: ReinforceRequest): Promise<ReinforceResult> {
    this.reinforced.push(request);
    return { presenceOutcomes: [], obligationClosures: [] };
  }
  async decline(request: DeclineRequest): Promise<ReinforceResult> {
    this.declined.push(request);
    return { presenceOutcomes: [], obligationClosures: this.declineClosures };
  }
  async drain(): Promise<void> {}
  async replayDurableQueue(): Promise<number> {
    return 0;
  }
  async close(): Promise<void> {}
}

function build(context: ResolvedContext = EMPTY) {
  const client = new FakeClient();
  client.context = context;
  const reports: RunReport[] = [];
  const seat = new RunSeat({
    client,
    identity: { agentName: "agent" },
    onReport: (report) => reports.push(report),
    // Pinned so every call of one test lands in the same run, which is what the ladder's
    // context rung does for a caller using `withRun`.
    runKeyResolvers: [() => ({ key: "fixed", source: "context", isInferred: false })],
  });
  return { client, seat, reports, middleware: hyperstruckMiddleware({ seat }) };
}

const userTurn = (text: string) => ({
  role: "user",
  content: [{ type: "text" as const, text }],
});

test("the block is injected after the customer's own system messages, not as a user turn", async () => {
  const { middleware } = build({ ...EMPTY, injectedText: "- check the currency", offeredLearningIds: ["a1"] });
  const params = {
    prompt: [
      { role: "system", content: "You are helpful." },
      userTurn("reconcile the invoice"),
    ],
  };
  const transformed = await middleware.transformParams({ params });
  assert.deepEqual(
    transformed.prompt.map((message) => message.role),
    ["system", "system", "user"],
  );
  assert.equal(transformed.prompt[1]?.content, "- check the currency");
  // The customer's own prompt object is left alone.
  assert.equal(params.prompt.length, 2);
});

test("a resolve that returned nothing injects nothing rather than an empty block", async () => {
  const { middleware } = build();
  const params = { prompt: [userTurn("go")] };
  const transformed = await middleware.transformParams({ params });
  assert.deepEqual(transformed.prompt.map((message) => message.role), ["user"]);
});

test("the goal is inferred from the latest human turn and the report says it was inferred", async () => {
  const { client, middleware, seat, reports } = build();
  const params = { prompt: [userTurn("first"), { role: "assistant", content: [] }, userTurn("reconcile the invoice")] };
  const transformed = await middleware.transformParams({ params });
  await middleware.wrapGenerate({
    doGenerate: async () => ({ content: [{ type: "text", text: "done" }] }),
    params: transformed,
  });
  await seat.flushAll();
  assert.equal(reports[0]?.goal, "reconcile the invoice");
  assert.equal(client.resolveCalls, 1);
});

test("the tool roster is read off the call options and reaches the episode", async () => {
  const { client, middleware, seat } = build();
  const params = {
    prompt: [userTurn("go")],
    tools: [{ name: "search", description: "look up", inputSchema: { properties: {} } }],
  };
  const transformed = await middleware.transformParams({ params });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "search", input: { q: "x" } },
        { type: "tool-call", toolCallId: "2", toolName: "search", input: { q: "y" } },
      ],
    }),
    params: transformed,
  });
  // The customer's loop returns the results on the next request, which is the only place
  // this layer can see them.
  const second = await middleware.transformParams({
    params: {
      ...params,
      prompt: [
        ...params.prompt,
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "search", output: "found x" },
            { type: "tool-result", toolCallId: "2", toolName: "search", output: "found y" },
          ],
        },
      ],
    },
  });
  await middleware.wrapGenerate({
    doGenerate: async () => ({ content: [{ type: "text", text: "done" }] }),
    params: second,
  });
  await seat.flushAll();
  assert.deepEqual(client.observed[0]?.availableTools?.map((tool) => tool.name), ["search"]);
  assert.equal(client.observed[0]?.steps?.length, 2);
});

test("a tool whose result is never returned is dropped rather than guessed at", async () => {
  const { client, middleware, seat } = build();
  const params = { prompt: [userTurn("go")] };
  const transformed = await middleware.transformParams({ params });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [{ type: "tool-call", toolCallId: "1", toolName: "search", input: {} }],
    }),
    params: transformed,
  });
  await seat.flushAll();
  // No outcome ever arrived, so the run has no steps and is declined rather than
  // reinforced from a plan nobody executed.
  assert.equal(client.reinforced.length, 0);
  assert.equal(client.declined[0]?.reason, "no_tool_calls");
});

test("a tool call whose arguments arrive as a JSON string is parsed", async () => {
  const { client, middleware, seat } = build();
  const first = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "search", input: '{"q":"x"}' },
        { type: "tool-call", toolCallId: "2", toolName: "write", input: '{"body":"y"}' },
      ],
    }),
    params: first,
  });
  const second = await middleware.transformParams({
    params: {
      prompt: [
        userTurn("go"),
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "search", output: "ok" },
            { type: "tool-result", toolCallId: "2", toolName: "write", output: "ok" },
          ],
        },
      ],
    },
  });
  await middleware.wrapGenerate({
    doGenerate: async () => ({ content: [{ type: "text", text: "done" }] }),
    params: second,
  });
  await seat.flushAll();
  assert.deepEqual(client.observed[0]?.steps?.[0]?.args, { q: "x" });
});

test("a tool result flagged as an error grades the step failed", async () => {
  const { client, middleware, seat } = build();
  const first = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "write", input: {} },
        { type: "tool-call", toolCallId: "2", toolName: "write", input: {} },
      ],
    }),
    params: first,
  });
  const second = await middleware.transformParams({
    params: {
      prompt: [
        userTurn("go"),
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "write", output: "no", isError: true },
            { type: "tool-result", toolCallId: "2", toolName: "write", output: "ok" },
          ],
        },
      ],
    },
  });
  await middleware.wrapGenerate({
    doGenerate: async () => ({ content: [] }),
    params: second,
  });
  await seat.flushAll();
  assert.equal(client.observed[0]?.steps?.[0]?.status, "failed");
  // A failure followed by a success is the prime learning, so the turn is kept.
  assert.equal(client.reinforced.length, 1);
});

test("the receipt is located against the params as transformed, which is what went out", async () => {
  const { client, middleware, seat } = build({
    ...EMPTY,
    injectedText: "- check the currency",
    offeredLearningIds: ["a1"],
  });
  const transformed = await middleware.transformParams({
    params: {
      prompt: [
        { role: "system", content: "You are helpful." },
        userTurn("go"),
      ],
    },
  });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "a", input: {} },
        { type: "tool-call", toolCallId: "2", toolName: "b", input: {} },
      ],
    }),
    params: transformed,
  });
  const second = await middleware.transformParams({
    params: {
      prompt: [
        { role: "system", content: "You are helpful." },
        userTurn("go"),
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "a", output: "ok" },
            { type: "tool-result", toolCallId: "2", toolName: "b", output: "ok" },
          ],
        },
      ],
    },
  });
  await middleware.wrapGenerate({
    doGenerate: async () => ({ content: [] }),
    params: second,
  });
  await seat.flushAll();
  assert.equal(client.reinforced[0]?.contextReceipt, "- check the currency");
});

test("a downstream layer that emptied our block leaves no receipt to send", async () => {
  const { client, middleware, seat } = build({
    ...EMPTY,
    injectedText: "- check the currency",
    offeredLearningIds: ["a1"],
  });
  const transformed = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  // The customer's own trimming middleware runs below us and drops the block.
  const trimmed = { ...transformed, prompt: [userTurn("go")] };
  Object.assign(transformed, trimmed);
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "a", input: {} },
        { type: "tool-call", toolCallId: "2", toolName: "b", input: {} },
      ],
    }),
    params: transformed,
  });
  const second = await middleware.transformParams({
    params: {
      prompt: [
        userTurn("go"),
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "a", output: "ok" },
            { type: "tool-result", toolCallId: "2", toolName: "b", output: "ok" },
          ],
        },
      ],
    },
  });
  Object.assign(second, { prompt: second.prompt.filter((m) => m.role !== "system") });
  await middleware.wrapGenerate({ doGenerate: async () => ({ content: [] }), params: second });
  await seat.flushAll();
  assert.equal(client.reinforced[0]?.contextReceipt, null);
});

test("one recall serves every model call of the run", async () => {
  const { client, middleware } = build({ ...EMPTY, injectedText: "- one", offeredLearningIds: ["a1"] });
  const first = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  const second = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  assert.equal(client.resolveCalls, 1);
  assert.equal(first.prompt[0]?.content, second.prompt[0]?.content);
});

test("a generation that throws is not swallowed by the seat", async () => {
  const { middleware } = build();
  const transformed = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  await assert.rejects(
    middleware.wrapGenerate({
      doGenerate: async () => {
        throw new Error("model refused");
      },
      params: transformed,
    }),
    /model refused/,
  );
});

test("a streamed response records its tool calls and passes the stream through unchanged", async () => {
  const { client, middleware, seat } = build();
  const transformed = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  const chunks = [
    { type: "text-delta", delta: "think" },
    { type: "tool-call", toolCallId: "1", toolName: "search", input: { q: "x" } },
    { type: "tool-call", toolCallId: "2", toolName: "write", input: {} },
  ];
  const result = await middleware.wrapStream({
    doStream: async () => ({
      stream: new ReadableStream({
        start(controller) {
          for (const chunk of chunks) controller.enqueue(chunk);
          controller.close();
        },
      }),
    }),
    params: transformed,
  });
  const seen: unknown[] = [];
  for await (const chunk of result["stream"] as ReadableStream) seen.push(chunk);
  assert.deepEqual(seen, chunks);

  const second = await middleware.transformParams({
    params: {
      prompt: [
        userTurn("go"),
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "search", output: "ok" },
            { type: "tool-result", toolCallId: "2", toolName: "write", output: "ok" },
          ],
        },
      ],
    },
  });
  await middleware.wrapGenerate({ doGenerate: async () => ({ content: [] }), params: second });
  await seat.flushAll();
  assert.equal(client.observed[0]?.steps?.length, 2);
});

test("a conversation already under way joins the run its first call opened", async () => {
  // The documented default: no tracer, no explicit wrapper. Before rung 4 this opened a
  // run per model call, so the tool results never joined their planned calls and every
  // turn declined.
  const client = new FakeClient();
  const reports: RunReport[] = [];
  const seat = new RunSeat({
    client,
    identity: { agentName: "agent" },
    onReport: (report) => reports.push(report),
    closeGraceMs: 0,
    // Deliberately the shipped default ladder, with nothing pinned.
  });
  const middleware = hyperstruckMiddleware({ seat });

  const first = await middleware.transformParams({ params: { prompt: [userTurn("go")] } });
  await middleware.wrapGenerate({
    doGenerate: async () => ({
      content: [
        { type: "tool-call", toolCallId: "1", toolName: "a", input: {} },
        { type: "tool-call", toolCallId: "2", toolName: "b", input: {} },
      ],
    }),
    params: first,
  });
  const second = await middleware.transformParams({
    params: {
      prompt: [
        userTurn("go"),
        {
          role: "tool",
          content: [
            { type: "tool-result", toolCallId: "1", toolName: "a", output: "ok" },
            { type: "tool-result", toolCallId: "2", toolName: "b", output: "ok" },
          ],
        },
      ],
    },
  });
  await middleware.wrapGenerate({ doGenerate: async () => ({ content: [] }), params: second });
  await seat.flushAll();

  assert.equal(reports.length, 1, "one episode, not one run per model call");
  assert.equal(client.observed[0]?.steps?.length, 2, "the tool results joined their calls");
  assert.equal(client.reinforced.length, 1);
});
