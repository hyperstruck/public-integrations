/**
 * The conversation rung is best effort, and its failure mode is loss of quality only.
 *
 * The mirror of the Python seat's `otel_test.py`. Both adapters guard every step and fall
 * through rather than raising, and both are excluded from the shipped default ladder, so
 * both need the same behavioural evidence: a guard nobody exercised is a claim, not a
 * guard, and this is the one module whose whole contract is that it fails quietly.
 */

import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { CONVERSATION_ID_ATTRIBUTE, conversationRunKey, otelResolvers } from "./otel.ts";
import {
  DEFAULT_RESOLVERS,
  otelRunKey,
  resolveRunKey,
  runWithKey,
  type RunKey,
} from "./runtime/runKey.ts";

// The symbol `@opentelemetry/api` genuinely registers itself under. Written out here
// rather than imported from the module under test, deliberately: if the production lookup
// and the test's stand-in read the same constant, a wrong constant passes both and the rung
// still never fires against a real tracer, which is exactly the defect this replaced.
const GLOBAL_KEY = Symbol.for("opentelemetry.js.api.1");

/** Install a stand-in for the OpenTelemetry API, since the package takes no dependency. */
function installTracer(span: unknown): void {
  (globalThis as Record<symbol, unknown>)[GLOBAL_KEY] = {
    trace: { getSpan: () => span },
    context: { active: () => ({}) },
  };
}

function span(options: { traceId?: string; attributes?: unknown } = {}): unknown {
  const built: Record<string, unknown> = {
    spanContext: () => ({ traceId: options.traceId ?? "a".repeat(32) }),
  };
  if (options.attributes !== undefined) built["attributes"] = options.attributes;
  return built;
}

afterEach(() => {
  delete (globalThis as Record<symbol, unknown>)[GLOBAL_KEY];
});

test("with no tracer registered the rung answers nothing", () => {
  assert.equal(conversationRunKey(), null);
  assert.equal(otelRunKey(), null);
});

test("the conversation id is read when the host set one", () => {
  installTracer(span({ attributes: { [CONVERSATION_ID_ATTRIBUTE]: "session-42" } }));
  assert.deepEqual(conversationRunKey(), {
    key: "session-42",
    source: "conversation",
    isInferred: false,
  });
});

test("a provider that exposes no attributes falls through", () => {
  installTracer(span());
  assert.equal(conversationRunKey(), null);
});

test("a non-recording span is treated as absent, attributes and all", () => {
  // The same guard the trace rung makes, and for the same reason: reading an attribute off
  // a no-op span would key every concurrent run in the process the same way.
  installTracer(
    span({ traceId: "0".repeat(32), attributes: { [CONVERSATION_ID_ATTRIBUTE]: "session-42" } }),
  );
  assert.equal(conversationRunKey(), null);
});

test("an empty or non-string conversation id is not an answer", () => {
  installTracer(span({ attributes: { [CONVERSATION_ID_ATTRIBUTE]: "" } }));
  assert.equal(conversationRunKey(), null);
  installTracer(span({ attributes: { [CONVERSATION_ID_ATTRIBUTE]: 7 } }));
  assert.equal(conversationRunKey(), null);
});

test("an API that throws costs correlation quality and never the run", () => {
  installTracer({
    spanContext() {
      throw new Error("the tracer changed shape");
    },
    attributes: { [CONVERSATION_ID_ATTRIBUTE]: "session-42" },
  });
  assert.equal(conversationRunKey(), null);
  (globalThis as Record<symbol, unknown>)[GLOBAL_KEY] = {
    trace: {
      getSpan() {
        throw new Error("no provider");
      },
    },
    context: { active: () => ({}) },
  };
  assert.equal(conversationRunKey(), null);
  assert.equal(otelRunKey(), null);
});

test("an all-zero trace id is treated as absent, not as one shared key", () => {
  // The API hands back an invalid no-op span when no SDK is configured. Reading its
  // all-zero trace id as an answer would put every concurrent run in the process under one
  // key, which is precisely the collision the ladder exists to prevent.
  installTracer(span({ traceId: "0".repeat(32) }));
  assert.equal(otelRunKey(), null);
});

test("a trace id of the wrong length is not an answer either", () => {
  installTracer(span({ traceId: "abc" }));
  assert.equal(otelRunKey(), null);
});

test("a valid trace id keys the run and says it was not inferred", () => {
  installTracer(span({ traceId: "b".repeat(32) }));
  const key = otelRunKey();
  assert.equal(key?.key, "b".repeat(32));
  assert.equal(key?.source, "trace");
  assert.equal(key?.isInferred, false);
});

test("the conversation rung sits below trace and above the seat's own wrapper", () => {
  const trace = (): RunKey | null => null;
  const context = (): RunKey | null => null;
  const ladder = otelResolvers([trace, context]);
  assert.equal(ladder[0], trace);
  assert.equal(ladder[1], conversationRunKey);
  assert.equal(ladder[2], context);
});

test("an empty base ladder still yields a usable one", () => {
  assert.deepEqual(otelResolvers([]), [conversationRunKey]);
});

test("a trace rung that answered wins over the conversation rung", () => {
  installTracer(span({ attributes: { [CONVERSATION_ID_ATTRIBUTE]: "session-42" } }));
  const ladder = otelResolvers([
    () => ({ key: "trace-1", source: "trace", isInferred: false }),
  ]);
  assert.equal(resolveRunKey(ladder).source, "trace");
});

test("the conversation rung answers when the trace rung did not", () => {
  installTracer(span({ attributes: { [CONVERSATION_ID_ATTRIBUTE]: "session-42" } }));
  const key = resolveRunKey(otelResolvers([() => null]));
  assert.equal(key.key, "session-42");
  assert.equal(key.source, "conversation");
});

test("the registry is read under the symbol the OpenTelemetry API really registers", () => {
  // The defect this replaced: the lookup used a plain property name the API never sets, so
  // the rung could never fire however completely a customer had configured their tracer.
  installTracer(span({ traceId: "d".repeat(32) }));
  assert.equal(otelRunKey()?.key, "d".repeat(32));
  delete (globalThis as Record<symbol, unknown>)[GLOBAL_KEY];
  (globalThis as Record<string, unknown>)["__OTEL_GLOBAL__"] = {
    trace: { getSpan: () => span({ traceId: "e".repeat(32) }) },
    context: { active: () => ({}) },
  };
  assert.equal(otelRunKey(), null, "a plain-property global must not be read");
  delete (globalThis as Record<string, unknown>)["__OTEL_GLOBAL__"];
});

test("the explicit wrapper outranks the trace, because only it supplies an end", () => {
  // A trace context keys a run and never ends it, so a caller who wrapped their run
  // explicitly must not have that wrapper ignored because a span happened to be recording.
  installTracer(span({ traceId: "f".repeat(32) }));
  runWithKey("explicit", () => {
    const key = resolveRunKey();
    assert.equal(key.key, "explicit");
    assert.equal(key.source, "context");
  });
  assert.equal(resolveRunKey().source, "trace");
});

test("the conversation rung is not in the shipped default ladder", () => {
  // Reading a span attribute is not part of the API's promised surface, so opting into it
  // is the customer's decision about their own instrumentation, not a library's about
  // everyone's.
  assert.ok(!DEFAULT_RESOLVERS.includes(conversationRunKey));
});

test("the pinned attribute name is the conventions' own", () => {
  // Pinned in one place precisely because the conventions are still Development and the
  // name can change without a major version bump.
  assert.equal(CONVERSATION_ID_ATTRIBUTE, "gen_ai.conversation.id");
});

test("a stand-in tracer object is all the adapter needs", () => {
  // Duck-typed rather than depending on the API's types, so a tracer that is not
  // OpenTelemetry is a few lines the customer writes.
  installTracer({
    spanContext: () => ({ traceId: "c".repeat(32) }),
    attributes: { [CONVERSATION_ID_ATTRIBUTE]: "from-another-tracer" },
  });
  assert.equal(conversationRunKey()?.key, "from-another-tracer");
  assert.equal(otelRunKey()?.key, "c".repeat(32));
});
