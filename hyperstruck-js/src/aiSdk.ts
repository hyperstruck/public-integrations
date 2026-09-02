/**
 * The documented default attachment point: middleware for the Vercel AI SDK.
 *
 * **Why the model layer, and not the agent layer.** This runs below every other
 * middleware the customer composed: after trimming, after summarisation, after
 * guardrails. What it sees is the prompt as actually sent on the wire. That dissolves
 * two problems the LangGraph seat documents as unavoidable. The ordering hazard becomes
 * structural rather than a runtime assertion, because there is no layer below to be wrong
 * about. And, commercially, it makes an honest receipt possible: a seat above the
 * composition stack can only echo back the block it built itself, which asserts the very
 * thing a receipt exists to prove, so it sends none and earns no credit. This one returns
 * an artefact it did not author.
 *
 * **No dependency on `ai`.** The middleware contract is a plain object of optional hooks,
 * so it is described structurally here rather than imported. The customer's own `ai`
 * version supplies the real types at their call site, this package pins none of them, and
 * an SDK release that adds a field to the call options cannot break a build that only
 * reads the fields it names. `wrapLanguageModel` accepts the returned object as-is.
 *
 * **What a run is here.** The hooks fire once per model call, not once per episode, so
 * the seat reads the run key off the ladder in `runKey.ts` rather than inventing one, and
 * the report always says which rung answered. Steps are derived by diffing the message
 * history across calls: planned tool calls come from each assistant response, and their
 * outcomes from the tool-result messages in the request that follows. That is exact for
 * any loop that returns results and blind to a tool whose result is never shown, and the
 * ledger's join drops the latter rather than guessing.
 *
 * **When a run ends.** An assistant response carrying no tool calls marks the run
 * closable, and it closes after a grace window unless a further call arrives under the
 * same key. That is the only terminal signal this layer gets; `withRun` is the exact
 * answer for a caller who wants one.
 *
 * **Where to place this middleware, and what happens if you do not.** `wrapLanguageModel`
 * applies `transformParams` outermost-first, so a middleware listed *after* this one
 * transforms the params afterwards and this seat cannot see what it did. Place this one
 * last, which is what "attached at the model layer" means in the AI SDK's own terms.
 * Placed earlier the seat still works and still fails safe: a layer below that empties the
 * block leaves a receipt this seat cannot locate, so the run reports `recall_unclaimed`
 * rather than claiming a delivery it did not observe. The cost is a lost credit, never a
 * false one, which is the direction this lane is required to fail in.
 */

import { RunSeat, type HyperstruckRun } from "./runtime/run.ts";
import type { ToolSpec } from "./wire.ts";

/** The host token this seat reports, and the one the boundary's receipt gate admits. */
export const AI_SDK_HOST = "ai-sdk";

interface TextPart {
  type: "text";
  text?: string;
}

interface ToolCallPart {
  type: "tool-call";
  toolCallId?: string;
  toolName?: string;
  input?: unknown;
  args?: unknown;
}

interface ToolResultPart {
  type: "tool-result";
  toolCallId?: string;
  toolName?: string;
  output?: unknown;
  result?: unknown;
  isError?: boolean;
}

type ContentPart = TextPart | ToolCallPart | ToolResultPart | { type: string };

interface PromptMessage {
  role: string;
  content: string | ContentPart[];
}

interface CallOptions {
  prompt: PromptMessage[];
  tools?: readonly {
    name?: string;
    type?: string;
    description?: string;
    inputSchema?: Record<string, unknown>;
    parameters?: Record<string, unknown>;
  }[];
  [key: string]: unknown;
}

interface GenerateResult {
  content?: ContentPart[];
  [key: string]: unknown;
}

export interface HyperstruckMiddleware {
  middlewareVersion: "v2";
  transformParams(options: { params: CallOptions }): Promise<CallOptions>;
  wrapGenerate(options: {
    doGenerate: () => PromiseLike<GenerateResult>;
    params: CallOptions;
  }): Promise<GenerateResult>;
  wrapStream(options: {
    doStream: () => PromiseLike<Record<string, unknown>>;
    params: CallOptions;
  }): Promise<Record<string, unknown>>;
}

/**
 * The run each transformed params object belongs to.
 *
 * Keyed on the params identity rather than resolved again in `wrapGenerate`, because
 * resolving again would re-enter the ladder and a minted key would name a different run
 * than the one the block was injected for. Weak, so a params object the SDK drops takes
 * its entry with it.
 */
const RUN_BY_PARAMS = new WeakMap<object, HyperstruckRun>();

function toolSpecs(params: CallOptions): ToolSpec[] {
  return (params.tools ?? [])
    .filter((tool) => typeof tool.name === "string" && tool.name.length > 0)
    .map((tool) => ({
      name: tool.name as string,
      description: tool.description ?? "",
      parameters: tool.inputSchema ?? tool.parameters ?? null,
    }));
}

/**
 * Whether this call shows a conversation already under way.
 *
 * The signal the inference rung needs, and the only one available at this layer: a prompt
 * carrying a prior assistant turn or tool results is a continuation of an episode, and one
 * carrying neither is its start. Exactly what the spec describes ("a model call with no
 * prior assistant turn starts a run"), read from the message list rather than guessed at.
 */
function isContinuation(prompt: readonly PromptMessage[]): boolean {
  return prompt.some((message) => message.role === "assistant" || message.role === "tool");
}

function partsOf(message: PromptMessage): ContentPart[] {
  return Array.isArray(message.content) ? message.content : [];
}

/**
 * The latest human turn, which is what the run's goal is taken from when no rung above
 * inference supplied one. Mirrors what the LangGraph seat already does.
 */
function latestHumanGoal(prompt: readonly PromptMessage[]): string {
  for (let index = prompt.length - 1; index >= 0; index -= 1) {
    const message = prompt[index];
    if (message === undefined || message.role !== "user") continue;
    if (typeof message.content === "string") return message.content;
    const text = partsOf(message)
      .filter((part): part is TextPart => part.type === "text")
      .map((part) => part.text ?? "")
      .join("\n")
      .trim();
    if (text) return text;
  }
  return "";
}

/**
 * Tool outcomes are harvested from the next request, not observed.
 *
 * A model-layer seat never sees a tool run; it sees the result only when the customer's
 * own loop feeds it back as a tool-result message. Exact for any loop that returns
 * results, blind to a tool whose result is never shown, and the ledger drops the latter
 * rather than guessing at it.
 */
function recordReturnedResults(
  seat: RunSeat,
  run: HyperstruckRun,
  prompt: readonly PromptMessage[],
): void {
  for (const message of prompt) {
    if (message.role !== "tool") continue;
    for (const part of partsOf(message)) {
      if (part.type !== "tool-result") continue;
      const result = part as ToolResultPart;
      if (typeof result.toolCallId !== "string") continue;
      seat.recordStep(run, result.toolCallId, result.toolName ?? "", {
        result: result.output ?? result.result ?? null,
        error: result.isError === true ? "tool reported an error" : null,
      });
    }
  }
}

function plannedCalls(
  content: readonly ContentPart[],
): { callId: string; name: string; args: Record<string, unknown> }[] {
  const calls: { callId: string; name: string; args: Record<string, unknown> }[] = [];
  for (const part of content) {
    if (part.type !== "tool-call") continue;
    const call = part as ToolCallPart;
    if (typeof call.toolCallId !== "string") continue;
    const raw = call.input ?? call.args;
    let args: Record<string, unknown> = {};
    if (typeof raw === "string") {
      try {
        const parsed: unknown = JSON.parse(raw);
        if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
          args = parsed as Record<string, unknown>;
        }
      } catch {
        // An unparseable argument blob is recorded as no arguments rather than as a
        // string masquerading as an object, so the declaration registry never stamps a
        // label onto a key that does not exist.
      }
    } else if (raw !== null && typeof raw === "object" && !Array.isArray(raw)) {
      args = raw as Record<string, unknown>;
    }
    calls.push({ callId: call.toolCallId, name: call.toolName ?? "", args });
  }
  return calls;
}

/**
 * Inject our block after the customer's own system messages.
 *
 * Not a synthetic user turn, which would change what the customer's own loop sees when it
 * inspects its messages, and not a rewrite of their system message, which would make our
 * lines indistinguishable from theirs to a reader debugging their own prompt.
 */
function injectBlock(params: CallOptions, block: string): CallOptions {
  const prompt = [...params.prompt];
  let insertAt = 0;
  while (insertAt < prompt.length && prompt[insertAt]?.role === "system") insertAt += 1;
  prompt.splice(insertAt, 0, { role: "system", content: block });
  return { ...params, prompt };
}

export interface MiddlewareOptions {
  readonly seat: RunSeat;
  /** Where the run's goal comes from when the ladder supplies no boundary. Defaults to
   * the latest human turn, which is inference and is reported as such. */
  readonly goalFrom?: (params: CallOptions) => string;
}

/**
 * Middleware for `wrapLanguageModel`, over an existing seat.
 *
 * ```ts
 * const model = wrapLanguageModel({
 *   model: openai("gpt-5"),
 *   middleware: hyperstruckMiddleware({ seat }),
 * });
 * ```
 */
export function hyperstruckMiddleware(options: MiddlewareOptions): HyperstruckMiddleware {
  const { seat } = options;
  seat.declareHost(AI_SDK_HOST);
  const goalFrom = options.goalFrom ?? ((params: CallOptions) => latestHumanGoal(params.prompt));

  async function attach(params: CallOptions): Promise<CallOptions> {
    const run = seat.forCall(goalFrom(params), toolSpecs(params), {
      isContinuation: isContinuation(params.prompt),
    });
    recordReturnedResults(seat, run, params.prompt);
    const block = await seat.beforeModelCall(run);
    const transformed = block === null ? { ...params } : injectBlock(params, block);
    RUN_BY_PARAMS.set(transformed, run);
    return transformed;
  }

  function settle(params: CallOptions, content: readonly ContentPart[]): void {
    const run = RUN_BY_PARAMS.get(params);
    if (run === undefined || run.isClosed) return;
    // Located against the params as transformed, which is what went on the wire.
    seat.afterModelCall(run, params);
    const calls = plannedCalls(content);
    seat.recordPlannedCalls(run, calls);
    // A model that answered without asking for another tool is the only terminal signal
    // this layer gets. Marked rather than closed, so a further call under the same key
    // inside the grace window continues the run.
    if (calls.length === 0) seat.markClosable(run);
  }

  return {
    middlewareVersion: "v2",

    async transformParams({ params }) {
      try {
        return await attach(params);
      } catch (error) {
        // The one hook that was unguarded, in a module whose stated promise is that it
        // never breaks the host's run. Everything downstream of a failure here is already
        // fail-open (no block, no run, no receipt), so calling through is the behaviour
        // the rest of the seat already has; throwing would have taken out the customer's
        // generation for a recall that is an enhancement.
        seat.reportSeatFailure("transformParams", error);
        return params;
      }
    },

    async wrapGenerate({ doGenerate, params }) {
      const result = await doGenerate();
      try {
        settle(params, result.content ?? []);
      } catch {
        // A seat that breaks the host's generation is a seat they remove. The run is left
        // to the abandonment sweep, which reports it rather than dressing it up.
      }
      return result;
    },

    async wrapStream({ doStream, params }) {
      const result = await doStream();
      const stream = result["stream"];
      if (!(stream instanceof ReadableStream)) return result;
      const collected: ContentPart[] = [];
      const observer = new TransformStream<unknown, unknown>({
        transform(chunk, controller) {
          const part = chunk as { type?: string; toolCallId?: string; toolName?: string; input?: unknown };
          // Only the finished tool call is recorded. The incremental deltas describe the
          // same call arriving in pieces, and folding them in would count one planned
          // call several times against the material threshold the decline table reads.
          if (part.type === "tool-call") {
            collected.push(part as ToolCallPart);
          }
          controller.enqueue(chunk);
        },
        flush() {
          try {
            settle(params, collected);
          } catch {
            // As above: never break the host's stream.
          }
        },
      });
      return { ...result, stream: (stream as ReadableStream).pipeThrough(observer) };
    },
  };
}
