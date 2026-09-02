/**
 * Which model calls belong to the same run, and how confident we are about it.
 *
 * The model-layer seat's hooks fire once per model call, not once per episode, so the
 * seat has to answer a question the LangGraph seat never had to: which calls are the same
 * run. Getting it wrong is not an inefficiency. Two concurrent conversations sharing one
 * wrapped model would have one run's block matched against the other's params.
 *
 * **We do not invent a correlation key.** The observability layer most customers already
 * run has one. OpenTelemetry's GenAI conventions define an `invoke_agent` span above the
 * model spans, and `gen_ai.conversation.id` as an identifier for a conversation, session
 * or thread, meant for keeping a multi-turn session traceable as a unit. Reading theirs
 * also means our run report lines up against their own incident rather than sitting
 * beside it.
 *
 * **We do not depend on a tracer either.** Taking the OpenTelemetry API as a dependency
 * would be sanctioned by their own client design principles and would serve exactly one
 * tracer; customers run Datadog and Sentry too, and each would be another dependency and
 * another release to wait for. So the rung is a *resolver*: the shipped default reaches
 * for a globally registered OpenTelemetry API if the host installed one, and anything
 * else is a few lines the customer writes today.
 *
 * The ladder is ordered by how much the answer can be trusted, and the run report always
 * says which rung answered, because an inferred key is a fact about the report's own
 * reliability that its reader is entitled to.
 */

import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";

/**
 * A run's correlation key and where it came from.
 *
 * `source` is reported rather than kept internal. "The key came from your trace context"
 * and "we guessed from the message history" license different amounts of confidence in
 * everything downstream of it, and a report that presents both the same way is the one
 * that gets trusted when it should not be.
 */
export interface RunKey {
  readonly key: string;
  readonly source: string;
  readonly isInferred: boolean;
}

export type RunKeyResolver = () => RunKey | null;

/**
 * Set by this seat's own `withRun` wrapper.
 *
 * `AsyncLocalStorage` rather than a module-level variable, which would be shared by every
 * concurrently awaited task on the loop, and that is the same cross-run leak this module
 * exists to prevent.
 */
const CURRENT_RUN = new AsyncLocalStorage<string>();

/** The key set by this seat's own run wrapper. Exact, and requires one wrapper. */
export function currentContextRunKey(): RunKey | null {
  const key = CURRENT_RUN.getStore();
  if (key === undefined) return null;
  return { key, source: "context", isInferred: false };
}

/** Run `body` with `key` bound as the current run key, restoring the previous one after. */
export function runWithKey<T>(key: string, body: () => T): T {
  return CURRENT_RUN.run(key, body);
}

/**
 * The OpenTelemetry JS API's global registry, when the host installed one.
 *
 * `@opentelemetry/api` registers itself on `globalThis` under a versioned symbol, not
 * under a plain property name. Reading a made-up key meant this rung could never fire: a
 * customer with a fully configured tracer still fell through to the wrapper or to a minted
 * key, and the README promised a correlation the code could not deliver.
 *
 * The version suffix is part of the contract and is read by trying each version this
 * package knows about, newest first, so a host on an older API is still found and a future
 * one costs correlation quality rather than correctness.
 */
const OTEL_API_VERSIONS = [1] as const;

export function otelApi(): Record<string, unknown> | null {
  for (const version of OTEL_API_VERSIONS) {
    const registry = (globalThis as Record<symbol, unknown>)[
      Symbol.for(`opentelemetry.js.api.${version}`)
    ];
    if (registry !== null && typeof registry === "object") {
      return registry as Record<string, unknown>;
    }
  }
  return null;
}

/**
 * The active OpenTelemetry trace, when the API is installed and a span is recording.
 *
 * Read off the API's own global rather than imported, so the package takes no dependency,
 * and a breaking change costs correlation quality and never correctness. A non-recording
 * span is treated as absent: the API hands back an invalid no-op span when no SDK is
 * configured, and its all-zero trace id would otherwise become a single shared run key for
 * every concurrent run in the process, which is precisely the collision this module exists
 * to prevent.
 */
export function otelRunKey(): RunKey | null {
  try {
    const registry = otelApi();
    const trace = registry?.["trace"] as
      | { getSpan?: (context: unknown) => unknown }
      | undefined;
    const contextApi = registry?.["context"] as { active?: () => unknown } | undefined;
    if (!trace?.getSpan || !contextApi?.active) return null;
    const span = trace.getSpan(contextApi.active()) as
      | { spanContext?: () => { traceId?: string } }
      | undefined;
    const traceId = span?.spanContext?.().traceId;
    if (typeof traceId !== "string") return null;
    if (traceId.length !== 32 || /^0+$/.test(traceId)) return null;
    return { key: traceId, source: "trace", isInferred: false };
  } catch {
    return null;
  }
}

/**
 * The explicit wrapper first, the trace second.
 *
 * Ordered by how much each rung can be trusted *as a run boundary*, which is not the same
 * as how precise its identifier is: a trace context supplies a key and never an end, while
 * `withRun` supplies both and is the only rung exact in both directions. With the trace
 * first, a caller who wrapped their run explicitly had that wrapper ignored whenever a span
 * was recording, and two concurrent handles inside one trace collided on a single key.
 */
export const DEFAULT_RESOLVERS: readonly RunKeyResolver[] = [
  currentContextRunKey,
  otelRunKey,
];

/**
 * The best available key, or a minted one that says it was minted.
 *
 * Falling back to a fresh identifier rather than to a shared default is deliberate: a
 * process-wide constant would silently merge every unattributed run into one, and a
 * merged run reports a receipt for a block another run was shown. A unique key loses
 * correlation across calls, which the report says out loud; a shared one loses
 * correctness, which it could not.
 */
export function resolveRunKey(
  resolvers: readonly RunKeyResolver[] = DEFAULT_RESOLVERS,
): RunKey {
  for (const resolver of resolvers) {
    try {
      const key = resolver();
      if (key !== null) return key;
    } catch {
      continue;
    }
  }
  return { key: randomUUID().replace(/-/g, ""), source: "minted", isInferred: true };
}
