/**
 * Wire types crossing the boundary to the Hyperstruck platform.
 *
 * Plain, JSON-serialisable value types. The platform owns the authoritative contract;
 * these mirror only what the client must send and receive, and a parity test pins them
 * against `openapi.json` and against the Python client's own copies.
 *
 * The serialisers drop default-valued keys rather than emitting them. Every field on
 * this wire is added to the API model before it is added here, but a client is upgraded
 * on the customer's schedule and an API on ours, so both orders happen. The API forbids
 * extra keys and a 4xx is terminal to the flush retry, so a field emitted
 * unconditionally does not degrade against an older API: it drops those episodes
 * permanently.
 */

import { publishedDeclineReasons } from "./contracts.ts";

/** Default cap on learnings resolved and injected per run. */
export const DEFAULT_MAX_LEARNINGS = 8;

export const REASON_NO_TOOL_CALLS = "no_tool_calls";
export const REASON_BELOW_MATERIAL_THRESHOLD = "below_material_threshold";
export const REASON_EMPTY_OFFER = "empty_offer";
export const REASON_UNEVIDENCED_OUTCOME = "unevidenced_outcome";
/** A read-only recall closing itself. It has no outcome to reinforce against, so it is
 * not a turn judged not worth learning from: there was never a judgement to make. */
export const REASON_READONLY_CLOSE = "readonly_close";
/** A turn the host started without ever handing this client a prompt. Not a turn that
 * did too little: its steps may be entirely material. What it has no account of is what
 * it was trying to do, and a goal is what an extracted rule is transferable against. */
export const REASON_NO_GOAL = "no_goal";

export const DECLINE_REASONS: ReadonlySet<string> = new Set([
  REASON_NO_TOOL_CALLS,
  REASON_BELOW_MATERIAL_THRESHOLD,
  REASON_EMPTY_OFFER,
  REASON_UNEVIDENCED_OUTCOME,
  REASON_READONLY_CLOSE,
  REASON_NO_GOAL,
]);

export { publishedDeclineReasons };

export type StepStatus = "completed" | "failed" | "skipped";

/** A tool the agent has available, as the platform's resolve expects it. */
export interface ToolSpec {
  readonly name: string;
  readonly description?: string;
  /** Only the server's own categories are read: `read_only`, `write`, `destructive`,
   * `external`, `delegation`. A near-miss such as `read` declares nothing. */
  readonly category?: string | null;
  /** Pre-redact: schemas are stored alongside the learning. */
  readonly parameters?: Record<string, unknown> | null;
  readonly returns?: Record<string, unknown> | null;
}

/**
 * One executed tool call: a planned decision joined to its outcome by id.
 *
 * `declaredSensitivity` sections may be a bare string, of which `subject` is the one the
 * server reads: the argument key naming the entity this step's result is about. Without
 * it every foreign caller falls to structural salience, which is the fallback rung
 * operating as the only rung, and the cost is entity fragmentation.
 */
export interface StepRecord {
  readonly id: string;
  readonly name: string;
  readonly args?: Record<string, unknown>;
  readonly status?: StepStatus;
  readonly result?: unknown;
  readonly error?: string | null;
  /** Valid only with `status: "skipped"` and no error; the three together are what the
   * server reads as a refusal. `"skipped"` alone is not one. */
  readonly isRefused?: boolean;
  readonly declaredSensitivity?: Record<string, Record<string, string> | string> | null;
}

export interface TerminalOutcome {
  readonly isSuccess: boolean;
  readonly totalSteps?: number;
  readonly completedSteps?: number;
  readonly failedSteps?: number;
}

/**
 * One contiguous stretch of the goal, with the origin the caller asserts for it.
 *
 * Send these whenever the host wraps its turns in markup. `principalUtterance` is dropped by the
 * platform for a caller that sends none: the containment check has nothing to place the utterance
 * in, and the honest answer to "is this the principal's own text" is then no rather than yes.
 * Spans must be cut from the goal itself, in order and without overlapping, or the whole episode
 * is refused.
 */
export interface EpisodeSpan {
  readonly text: string;
  /** `user_prose` for what the principal wrote, `harness` for the host's own markup. */
  readonly origin: string;
}

export interface Episode {
  readonly runId: string;
  readonly goal: string;
  readonly steps?: readonly StepRecord[];
  readonly outcome?: TerminalOutcome;
  readonly sourceFramework?: string;
  /** Populate only from a human-input channel. Model output, tool results and retrieved
   * documents must never reach this: the guarantee it carries is about which writer can
   * set it, not about what it contains. */
  readonly principalUtterance?: string | null;
  /** The goal cut into prose and host markup. Without it `principalUtterance` is dropped. */
  readonly spans?: readonly EpisodeSpan[];
  readonly threadId?: string | null;
  /** The roster the agent had, not the tools it happened to call. Left empty, the server
   * writes an empty capability fingerprint and cannot read restraint at all. */
  readonly availableTools?: readonly ToolSpec[];
}

export function toolPayload(tool: ToolSpec): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    name: tool.name,
    description: tool.description ?? "",
  };
  if (tool.category != null) payload["category"] = tool.category;
  if (tool.parameters != null) payload["parameters"] = tool.parameters;
  if (tool.returns != null) payload["returns"] = tool.returns;
  return payload;
}

export function stepPayload(step: StepRecord): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    id: step.id,
    name: step.name,
    args: step.args ?? {},
    status: step.status ?? "completed",
    result: step.result ?? null,
    error: step.error ?? null,
    declared_sensitivity: step.declaredSensitivity ?? null,
  };
  if (step.isRefused === true) payload["is_refused"] = true;
  return payload;
}

export function episodePayload(episode: Episode): Record<string, unknown> {
  const outcome = episode.outcome ?? { isSuccess: true };
  const payload: Record<string, unknown> = {
    run_id: episode.runId,
    goal: episode.goal,
    steps: (episode.steps ?? []).map(stepPayload),
    outcome: {
      is_success: outcome.isSuccess,
      total_steps: outcome.totalSteps ?? 0,
      completed_steps: outcome.completedSteps ?? 0,
      failed_steps: outcome.failedSteps ?? 0,
    },
    source_framework: episode.sourceFramework ?? "",
    thread_id: episode.threadId ?? null,
  };
  // Emitted only when it carries something, for the same reason as
  // `principal_utterance` below: an API that predates the field forbids it outright, so
  // an unconditional key 422s every write for anyone who upgrades this package before
  // the deploy lands, and a 4xx is terminal to the flush retry.
  if (episode.availableTools && episode.availableTools.length > 0) {
    payload["available_tools"] = episode.availableTools.map(toolPayload);
  }
  if (episode.principalUtterance) {
    payload["principal_utterance"] = episode.principalUtterance;
  }
  if (episode.spans && episode.spans.length > 0) {
    payload["spans"] = episode.spans.map((span) => ({
      text: span.text,
      origin: span.origin,
    }));
  }
  return payload;
}

/**
 * The bound learnings for a goal, as returned by resolve.
 *
 * `injectedFactsText` is the block of claims the account holds about the entities the goal
 * names, open obligations among them as owed claims; `offeredClaimIds` names the claims it
 * carries. Both blocks are render-confirmed, so an offered id is one the block carries.
 */
export interface ResolvedContext {
  readonly injectedText: string | null;
  readonly injectedFactsText: string | null;
  readonly offeredLearningIds: readonly string[];
  readonly offeredClaimIds: readonly string[];
  /** Whether this agent's host has ever reported a run outcome. Until it has, no learning can be
   * proven and the advice block says so. Null against a server that predates the field. */
  readonly hasReportedOutcomes?: boolean | null;
}

function stringList(value: unknown): readonly string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function optionalText(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function resolvedContextFromResponse(data: unknown): ResolvedContext {
  const body = (data ?? {}) as Record<string, unknown>;
  return {
    injectedText: optionalText(body["injected_text"]),
    injectedFactsText: optionalText(body["injected_facts_text"]),
    offeredLearningIds: stringList(body["offered_learning_ids"]),
    offeredClaimIds: stringList(body["offered_claim_ids"]),
    hasReportedOutcomes: optionalBoolean(body["has_reported_outcomes"]),
  };
}

/** What became of one offered id on the way to the model, as the boundary judged it. */
export const PRESENCE_DELIVERED_VERBATIM = "delivered_verbatim";
export const PRESENCE_DELIVERED_REFORMATTED = "delivered_reformatted";
export const PRESENCE_UNRESOLVED = "unresolved";

/**
 * The authoritative three-way presence relation, per offered id.
 *
 * Returned by the boundary rather than computed here, and that is the load-bearing part.
 * Verbatim is a substring check anyone can do, but telling reformatted from unresolved is
 * Core's anchored-token matcher, and a client-side copy of it would be a second
 * implementation free to disagree with the credit verdict, which is a support-ticket
 * generator of its own.
 */
export interface PresenceOutcome {
  readonly id: string;
  readonly outcome: string;
}

export function presenceOutcomesFromResponse(data: unknown): readonly PresenceOutcome[] {
  const body = (data ?? {}) as Record<string, unknown>;
  const raw = body["presence_outcomes"];
  if (!Array.isArray(raw)) return [];
  const outcomes: PresenceOutcome[] = [];
  for (const item of raw) {
    if (item === null || typeof item !== "object") continue;
    const record = item as Record<string, unknown>;
    const id = record["id"];
    const outcome = record["outcome"];
    if (typeof id === "string" && typeof outcome === "string") {
      outcomes.push({ id, outcome });
    }
  }
  return outcomes;
}

/**
 * What a reinforce or a decline read back: the presence verdicts and the held-key count.
 *
 * Both are empty on the asynchronous write path, where the response arrives after the caller
 * has gone, and empty against a deployment that returns neither, which is what both clients
 * degrade to.
 */
export interface ReinforceResult {
  readonly presenceOutcomes: readonly PresenceOutcome[];
  /** How many of the agent's keys hold a changed value for a person to review; null when the
   * boundary did not say, which is never the same as none. */
  readonly keysAwaitingReview?: number | null;
}

/** What an observe read back: how many keys wait on a person, null when it was not told. */
export interface ObserveResult {
  readonly keysAwaitingReview: number | null;
}

export function keysAwaitingReviewFromResponse(data: unknown): number | null {
  if (data === null || typeof data !== "object") return null;
  const count = (data as Record<string, unknown>)["keys_awaiting_review"];
  return typeof count === "number" && Number.isInteger(count) && count >= 0 ? count : null;
}

export function reinforceResultFromResponse(data: unknown): ReinforceResult {
  return {
    presenceOutcomes: presenceOutcomesFromResponse(data),
    keysAwaitingReview: keysAwaitingReviewFromResponse(data),
  };
}

/**
 * Place the advice and claims blocks adjacently, for a host that wants no choice.
 *
 * The blank line between them is this client's own convention, not the boundary's: Core
 * joins the same halves with a single newline. Nothing depends on the separator, since
 * the receipt matcher is anchored per fragment and explicitly does not require the halves
 * to be adjacent, so the two are allowed to differ and neither is the documented
 * placement.
 */
export function combineInjectionBlocks(
  advice: string | null | undefined,
  facts: string | null | undefined,
): string | null {
  const parts = [advice, facts].filter(
    (block): block is string => typeof block === "string" && block.length > 0,
  );
  return parts.length === 0 ? null : parts.join("\n\n");
}
