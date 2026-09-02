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
 * `offeredObligationIds` names what the shelf admitted, which can be more than the block
 * carries when the block's token budget cut the tail, and `deliveredObligationIds` names
 * the subset the block actually rendered. The two are held apart because the shelf
 * escalates on deliveries: an obligation admitted by selection and then cut by the
 * budget was shown to no model and must never be escalated for being ignored. Advice and
 * facts need no such pair, because their offer is render-confirmed.
 */
export interface ResolvedContext {
  readonly injectedText: string | null;
  readonly injectedFactsText: string | null;
  readonly injectedObligationsText: string | null;
  readonly offeredLearningIds: readonly string[];
  readonly offeredClaimIds: readonly string[];
  readonly offeredObligationIds: readonly string[];
  /** Empty against a server that predates the field, and that reads as nothing delivered
   * rather than as everything delivered: over-reporting escalates an obligation no model
   * was ever shown, and under-reporting only forgoes credit. */
  readonly deliveredObligationIds: readonly string[];
}

function stringList(value: unknown): readonly string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function optionalText(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function resolvedContextFromResponse(data: unknown): ResolvedContext {
  const body = (data ?? {}) as Record<string, unknown>;
  return {
    injectedText: optionalText(body["injected_text"]),
    injectedFactsText: optionalText(body["injected_facts_text"]),
    injectedObligationsText: optionalText(body["injected_obligations_text"]),
    offeredLearningIds: stringList(body["offered_learning_ids"]),
    offeredClaimIds: stringList(body["offered_claim_ids"]),
    offeredObligationIds: stringList(body["offered_obligation_ids"]),
    deliveredObligationIds: stringList(body["delivered_obligation_ids"]),
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
 * One obligation a turn resolved, reported with the reinforce or decline that ends the run.
 *
 * The loop-level alternative to a call per obligation, for the host that took the due-set
 * block, acted on it, and holds a handful of ids from `offeredObligationIds`. It carries no
 * expected version and the boundary accepts none: the run lock serialises this path, so there
 * is no race for a token to guard, and a host reporting what its own turn did is not racing
 * anybody.
 */
export interface ReportedObligationOutcome {
  readonly id: string;
  readonly outcome: "kept" | "dropped";
  /** Required when the outcome is `kept`. */
  readonly keptBasis?: "reported" | "evidenced" | "declared";
  /** Required when the outcome is `dropped`. Only `not_an_obligation` counts against the
   * source that produced the obligation. */
  readonly droppedReason?: "not_an_obligation" | "no_longer_applies" | "wont_do" | "duplicate";
  readonly note?: string;
}

export const CLOSURE_APPLIED = "applied";
/** The only transient disposition, and the only one worth sending again: the run lock was
 * held past the bound, so the outcome was neither applied nor judged. Every other
 * disposition is terminal, and a caller that retries one loops for ever. */
export const CLOSURE_BUSY = "busy";

/**
 * What the boundary did with one reported outcome, per id.
 *
 * A batch of outcomes can partly apply, and until this existed every mix of applied, ignored
 * and unknown ids came back as the same 202. `status` is the row's status after the call, and
 * null where there was no row this call read.
 */
export interface ObligationClosureResult {
  readonly id: string;
  readonly disposition: string;
  readonly status: string | null;
}

/**
 * What a reinforce or a decline read back: the presence verdicts and the closure results.
 *
 * A named return rather than a bare array, because two unrelated answers now come back from
 * one call and because a developer looks for a value at the call they made. A closure result
 * reachable only through the run report would be invisible to exactly the host that reported
 * the closure.
 *
 * Both halves are empty on the asynchronous write path, where the response arrives after the
 * caller has gone, and empty against a deployment that returns neither, which is what both
 * clients degrade to.
 */
export interface ReinforceResult {
  readonly presenceOutcomes: readonly PresenceOutcome[];
  readonly obligationClosures: readonly ObligationClosureResult[];
}

/**
 * Why one reported outcome cannot go on the wire, or null when it is coherent.
 *
 * Split out from the payload builder so a caller holding a whole batch (`RunSeat.close`) can
 * find and drop the malformed ones itself, before anything is sent, rather than have the
 * first bad entry throw and lose every sibling outcome in the same call.
 */
export function obligationOutcomeProblem(outcome: ReportedObligationOutcome): string | null {
  if (outcome.outcome === "kept" && !outcome.keptBasis) {
    return "closing as kept needs a keptBasis: reported, evidenced or declared";
  }
  if (outcome.outcome === "dropped" && !outcome.droppedReason) {
    return (
      "closing as dropped needs a droppedReason: not_an_obligation, no_longer_applies, " +
      "wont_do or duplicate"
    );
  }
  return null;
}

/**
 * The wire body for one reported outcome.
 *
 * The coherence rules are enforced here too, rather than left to the boundary's 422, because a
 * write is fire-and-forget by default: a rejected body would be swallowed with nothing said,
 * and the host would believe it had closed a row that is still open. `RunSeat.close` filters a
 * batch with `obligationOutcomeProblem` first, so this throw is the backstop for a caller that
 * built a payload directly rather than the path a malformed batch is expected to take.
 */
export function reportedObligationOutcomePayload(
  outcome: ReportedObligationOutcome,
): Record<string, unknown> {
  const problem = obligationOutcomeProblem(outcome);
  if (problem) throw new Error(problem);
  const payload: Record<string, unknown> = { id: outcome.id, outcome: outcome.outcome };
  if (outcome.keptBasis) payload["kept_basis"] = outcome.keptBasis;
  if (outcome.droppedReason) payload["dropped_reason"] = outcome.droppedReason;
  if (outcome.note != null) payload["note"] = outcome.note;
  return payload;
}

/**
 * The boundary's per-reported-id closure result, or empty.
 *
 * The dispositions are read as sent rather than checked against a vocabulary. A disposition
 * this client does not know is still the boundary's answer about that id, and refusing it
 * here would turn a server that grew a seventh word into a client that reports the close as
 * never having been judged.
 */
export function obligationClosuresFromResponse(
  data: unknown,
): readonly ObligationClosureResult[] {
  const body = (data ?? {}) as Record<string, unknown>;
  const raw = body["obligation_closures"];
  if (!Array.isArray(raw)) return [];
  const results: ObligationClosureResult[] = [];
  for (const item of raw) {
    if (item === null || typeof item !== "object") continue;
    const record = item as Record<string, unknown>;
    const id = record["id"];
    const disposition = record["disposition"];
    if (typeof id !== "string" || typeof disposition !== "string") continue;
    const status = record["status"];
    results.push({ id, disposition, status: typeof status === "string" ? status : null });
  }
  return results;
}

export function reinforceResultFromResponse(data: unknown): ReinforceResult {
  return {
    presenceOutcomes: presenceOutcomesFromResponse(data),
    obligationClosures: obligationClosuresFromResponse(data),
  };
}

/**
 * Place the advice, fact and obligation blocks adjacently, for a host that wants no choice.
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
  obligations?: string | null,
): string | null {
  const parts = [advice, facts, obligations].filter(
    (block): block is string => typeof block === "string" && block.length > 0,
  );
  return parts.length === 0 ? null : parts.join("\n\n");
}
