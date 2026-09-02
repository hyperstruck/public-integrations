/**
 * The OpenTelemetry adapter, best effort only.
 *
 * The GenAI semantic conventions define agent, workflow, tool and model spans, and auto
 * instrumentation exists for most stacks in both languages, so deriving an episode
 * passively is attractive. It is not the contract, and the reason is dated rather than
 * vague: every `gen_ai.*` attribute still carries the Development stability badge, and
 * the conventions were moved out of the main semantic-conventions repository into a
 * dedicated one in June 2026 with no published stabilisation timeline. Attribute names
 * can therefore change without a major version bump.
 *
 * So the mapping is pinned here in one place, documented as best effort, and **no
 * contract test depends on it**. A customer with no instrumentation loses correlation
 * quality, never correctness.
 *
 * The dependency question was resolved by rejecting both options it was offered. Taking
 * the OpenTelemetry API would be sanctioned by their own client design principles and
 * would serve exactly one tracer, and customers run Datadog and Sentry too. Guard-loading
 * it would serve the same one tracer with worse ergonomics. What ships instead is a
 * resolver protocol any tracer plugs into, of which this is the shipped default: it reads
 * the API off the documented global the API itself registers, so a host that installed
 * it is picked up and a host that did not pays nothing.
 */

import { otelApi, type RunKey, type RunKeyResolver } from "./runtime/runKey.ts";

/**
 * The attribute naming a conversation, session or thread, meant for keeping a multi-turn
 * session traceable as a unit. Pinned as a constant so the day it is renamed is a
 * one-line change with a reader who knows why it is here.
 */
export const CONVERSATION_ID_ATTRIBUTE = "gen_ai.conversation.id";

interface SpanLike {
  spanContext?: () => { traceId?: string };
  attributes?: Record<string, unknown>;
}

/**
 * Whether a span is one a real SDK is recording.
 *
 * The API hands back an invalid no-op span when nothing is configured. Its all-zero trace
 * id would otherwise become a single shared run key for every concurrent run in the
 * process, which is precisely the collision the ladder exists to prevent, and an attribute
 * read off such a span is no more trustworthy than the id.
 */
function isRecording(span: SpanLike | null): boolean {
  try {
    const traceId = span?.spanContext?.().traceId;
    return typeof traceId === "string" && traceId.length === 32 && !/^0+$/.test(traceId);
  } catch {
    return false;
  }
}

function activeSpan(): SpanLike | null {
  try {
    // The same registry lookup the trace rung uses, so the two rungs cannot disagree about
    // whether a tracer is present.
    const registry = otelApi();
    const trace = registry?.["trace"] as
      | { getSpan?: (context: unknown) => unknown }
      | undefined;
    const contextApi = registry?.["context"] as { active?: () => unknown } | undefined;
    if (!trace?.getSpan || !contextApi?.active) return null;
    return (trace.getSpan(contextApi.active()) as SpanLike | undefined) ?? null;
  } catch {
    return null;
  }
}

/**
 * The conversation rung: `gen_ai.conversation.id` when the host set it.
 *
 * Below the trace context and above our own wrapper, because a conversation id keys a
 * multi-turn session where a trace id keys one operation, and a customer who set both
 * meant the trace to be the finer of the two.
 *
 * Reading an attribute off a live span is not part of the OpenTelemetry API's public
 * surface, so this is guarded and returns nothing rather than throwing when the SDK in
 * use does not expose it. Losing this rung costs correlation quality and never
 * correctness, which is the whole basis on which the adapter is best effort.
 *
 * A non-recording span is treated as absent, exactly as the trace rung treats one.
 */
export function conversationRunKey(): RunKey | null {
  const span = activeSpan();
  // The recording check matters as much here as it does for the trace rung, and the Python
  // seat makes the same one: an attribute read off a non-recording span is not an answer.
  if (!isRecording(span)) return null;
  const value = span?.attributes?.[CONVERSATION_ID_ATTRIBUTE];
  if (typeof value !== "string" || value.length === 0) return null;
  return { key: value, source: "conversation", isInferred: false };
}

/**
 * The full ladder including the conversation rung, for a customer who wants it.
 *
 * Not the package default: a resolver that reads a span attribute the API does not
 * promise is exactly the sort of thing that should be opted into by a customer who knows
 * their own instrumentation, rather than switched on for everyone by a library.
 */
export function otelResolvers(base: readonly RunKeyResolver[]): readonly RunKeyResolver[] {
  const [traceResolver, ...rest] = base;
  return traceResolver === undefined
    ? [conversationRunKey]
    : [traceResolver, conversationRunKey, ...rest];
}
