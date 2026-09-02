/**
 * The run-scoped core: one object per run, attachable from any runtime.
 *
 * Every seat this package ships is a thin adapter over this, and it is the same loop the
 * Python package runs, pinned to it by a parity test rather than merely resembling it.
 *
 *     open(goal, tools)      -> prefetch POST /resolve, hold the three blocks
 *     (model call)           -> replay the block, locate it in the params as sent
 *     recordStep(...)        -> join planned calls against actual outcomes
 *     close(outcome)         -> POST /observe, then /reinforce with the receipt, or /decline
 *
 * **The block is computed once and replayed.** Rate limits and overloads routinely make a
 * customer's own retry logic, or the SDK's built-in retry, resend the same logical call,
 * so the model-layer hook fires several times for one logical step. Recomputing would
 * show the model a different block on the second send and spend a second recall against
 * the run's budget. Receipt location, by contrast, runs on **every** send: a mid-run trim
 * is exactly what it exists to catch, and the latest location wins.
 *
 * **Lifecycle is guarded rather than assumed.** A public surface hands the ordering to
 * the caller, so close-before-open, double close and a step recorded after close are
 * defined here rather than left undefined.
 *
 * **Nothing here breaks the host's run.** Resolve fails open, the write path is scheduled
 * rather than awaited, and every callback the customer registered is called inside a
 * guard. A seat that dies when we do is a seat they remove.
 */

import { randomUUID } from "node:crypto";

import type { LearningClient } from "../client.ts";
import type { AgentIdentity } from "../identity.ts";
import { declineReason, shouldObserve } from "../turnGate.ts";
import {
  combineInjectionBlocks,
  DEFAULT_MAX_LEARNINGS,
  obligationOutcomeProblem,
  PRESENCE_UNRESOLVED,
  publishedDeclineReasons,
  type Episode,
  type ObligationClosureResult,
  type PresenceOutcome,
  type ReinforceResult,
  type ReportedObligationOutcome,
  type ResolvedContext,
  type StepRecord,
  type ToolSpec,
} from "../wire.ts";
import { DeclarationRegistry, join as joinSensitivity } from "./declarations.ts";
import {
  offeredAndDeliveredShelf,
  renderConfirmedShelf,
  RunLedger,
  type JoinedStep,
  type Shelf,
} from "./ledger.ts";
import {
  flattenParams,
  isReceiptPresent,
  locateReceipt,
  receiptOutcome,
  type ReceiptLocation,
} from "./receipt.ts";
import { DEFAULT_RESOLVERS, resolveRunKey, type RunKey, type RunKeyResolver } from "./runKey.ts";
import { describeScan, isScanClean, scanAndScrub, type ContentScanner } from "./scanning.ts";

/**
 * Provenance stamped on every episode this seat produces when no adapter names itself.
 * Not the engine's name: this package deliberately never loads the engine, and naming it
 * here would attribute a foreign customer's episode to it in the one field the platform
 * uses to tell surfaces apart.
 */
export const SOURCE_FRAMEWORK = "hyperstruck-runtime";

/** The boundary's closed vocabulary for why a recall did not reach the model. */
export const OUTCOME_DELIVERED = "delivered";
export const OUTCOME_RESOLVE_FAILED = "resolve_failed";
export const OUTCOME_RESOLVE_EMPTY = "resolve_empty";
export const OUTCOME_RECALL_UNCLAIMED = "recall_unclaimed";
export const OUTCOME_RECALL_MISSING = "recall_missing";

/**
 * How long a run may sit untouched before it counts as abandoned. Measured from the last
 * ledger touch rather than from open, so a long run that is still working is never a
 * candidate while an opened-and-forgotten one ages out. Thirty minutes is above any
 * plausible agent turn and far below the point at which the cap fills in a real
 * deployment.
 */
export const DEFAULT_RUN_TTL_MS = 30 * 60 * 1000;

/**
 * Bound on live runs. Inherited from the LangGraph registry, whose own comment warns that
 * the eviction victim can be a live in-flight run. Pairing it with the TTL above is what
 * turns that warning into a rule: abandoned entries go first, and evicting a live one is a
 * warning rather than routine housekeeping.
 */
export const DEFAULT_MAX_LIVE_RUNS = 2048;

/**
 * How long the seat waits after a tool-free assistant answer before closing the run.
 *
 * The model layer gets no episode-end event, so this is the only terminal signal it has.
 * A further call under the same key inside the window continues the run instead. The
 * honest cost is stated rather than hidden: a grace-window close posts credit up to one
 * window late.
 */
export const DEFAULT_CLOSE_GRACE_MS = 60_000;

/**
 * How long `close` waits for a prefetch still in flight. Short, because nothing is owed to
 * a resolve nobody will read. Matches the Python seat's own join timeout.
 */
const RESOLVE_JOIN_TIMEOUT_MS = 1_000;

/**
 * A deadline that must never be the reason a process stays alive.
 *
 * Only for racing the prefetch join, where whatever it races has its own completion, so
 * losing the timer costs nothing and holding the loop open for it would make a
 * short-lived host hang on a deadline it has stopped caring about.
 */
function deadline(ms: number): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    if (typeof timer === "object" && timer !== null && "unref" in timer) {
      (timer as { unref: () => void }).unref();
    }
  });
}

/**
 * The step kind this seat records. The observe and decline rule is shared across hosts
 * and the vocabulary is not: an editor seat distinguishes an edit from a search because
 * its transcript does, while everything a model-layer seat sees is a tool the runtime
 * actually ran. So this seat has one kind and it is material, and a host that wants a
 * finer vocabulary passes its own `materialKinds` and stamps its own kinds.
 */
export const TOOL_CALL_KIND = "tool_call";
export const DEFAULT_MATERIAL_KINDS: ReadonlySet<string> = new Set([TOOL_CALL_KIND]);

export const DISPOSITION_REINFORCED = "reinforced";
/** Worth learning from and sent, but with no receipt. A weaker success, and distinct from
 * the two failures below, which used to be indistinguishable from it in the one field a
 * reader consults. */
export const DISPOSITION_OBSERVED = "observed";
/** The write-back raised. The episode may or may not have landed, and the run may still be
 * open server-side holding its resolve reservation. */
export const DISPOSITION_WRITE_FAILED = "write_failed";
/** Declined, but the only honest reason is one the boundary has not published, so nothing
 * was sent rather than a refused decline leaving the run open. */
export const DISPOSITION_WITHHELD = "withheld";
export const DISPOSITION_DECLINED = "declined";
export const DISPOSITION_EVICTED = "evicted";

/** Why the close fired, reported beside the rung that keyed the run. */
export const CLOSE_TRIGGER_EXPLICIT = "explicit";
export const CLOSE_TRIGGER_NO_TOOL_CALLS = "no_tool_calls_grace";
export const CLOSE_TRIGGER_PROCESS_EXIT = "process_exit";
export const CLOSE_TRIGGER_ABANDONED = "abandoned_ttl";

/**
 * Why the recall did not reach the model, in the boundary's own vocabulary.
 *
 * Sent beside the delivery boolean because the boolean alone is the half-answer the field
 * exists to remove: without it a run whose corpus was empty is indistinguishable from one
 * whose resolve failed, and both look like a client too old to say. Collapsing
 * `resolve_failed` into `resolve_empty` is the specific failure the taxonomy exists to
 * prevent, because it makes a broken deployment read exactly like a cold corpus.
 */
export function recallOutcome(state: {
  isInjected: boolean;
  isResolveFailed: boolean;
  isResolved: boolean;
  isOffered: boolean;
}): string {
  if (state.isInjected) return OUTCOME_DELIVERED;
  if (state.isResolveFailed) return OUTCOME_RESOLVE_FAILED;
  // The run ended with the prefetch still in flight. Not a fault: the run was short.
  if (!state.isResolved) return OUTCOME_RECALL_MISSING;
  return state.isOffered ? OUTCOME_RECALL_UNCLAIMED : OUTCOME_RESOLVE_EMPTY;
}

export function ledgerRecallOutcome(ledger: RunLedger): string {
  return recallOutcome({
    isInjected: ledger.isInjected,
    isResolveFailed: ledger.isResolveFailed,
    isResolved: ledger.isResolved,
    isOffered: ledger.offeredAny,
  });
}

export interface ShelfReport {
  readonly name: string;
  readonly outcome: string;
  readonly offeredIds: readonly string[];
  readonly linesExpected: number;
  readonly linesFound: number;
  readonly missingLines: readonly string[];
}

/**
 * What happened to one run, in the same shape on every channel that carries it.
 *
 * The same report reaches the structured log line, the callback registered at wrap time,
 * and the handle a caller may be holding, and it is never a subset on any of them. A
 * customer who moves between attachment points must not silently lose a field, which is
 * the failure mode a "the handle has more" design has.
 *
 * Several fields exist only so that nothing is withheld silently. `withheld` names the
 * declarations that were dropped and the configuration that would release them,
 * `recallOutcome` distinguishes a broken boundary from a cold corpus, `runKeySource` says
 * which rung of the ladder answered, and `closeTrigger` says what ended the run, because
 * a customer reading a late or missing reinforcement is entitled to see why.
 */
export interface RunReport {
  readonly runId: string;
  readonly goal: string;
  readonly runKeySource: string;
  readonly isRunKeyInferred: boolean;
  readonly recallOutcome: string;
  /** The seat's own local grading of the block it found in the sent params. A heuristic,
   * and labelled one: the authoritative per-id relation is `presenceOutcomes`. */
  readonly receiptOutcome: string;
  readonly isReceiptSent: boolean;
  readonly shelves: readonly ShelfReport[];
  /** The boundary's own verdict per offered id, once the reinforce has drained. Empty
   * until then, and empty against a deployment that does not return it. */
  readonly presenceOutcomes: readonly PresenceOutcome[];
  /** What the boundary did with each obligation outcome this run reported, per id. Empty when
   * the run reported none, and empty on the asynchronous write path, where the close's
   * response arrives after the report has been built. */
  readonly obligationClosures: readonly ObligationClosureResult[];
  readonly stepCount: number;
  readonly modelCallCount: number;
  readonly disposition: string;
  readonly closeTrigger: string | null;
  readonly declineReason: string | null;
  readonly withheld: readonly string[];
  readonly isEvicted: boolean;
}

/**
 * Read what a reinforce or decline returned, whatever shape the client returns it in.
 *
 * A client written against an earlier version of the `LearningClient` port returns the
 * presence verdicts as a bare array, or nothing at all. Reading a property off that would
 * throw outside the write guard, which is the one thing this seat promises never to do to a
 * host run.
 */
function readWriteResult(value: unknown): ReinforceResult {
  if (Array.isArray(value)) {
    return { presenceOutcomes: value as readonly PresenceOutcome[], obligationClosures: [] };
  }
  if (value === null || typeof value !== "object") {
    return { presenceOutcomes: [], obligationClosures: [] };
  }
  const record = value as Record<string, unknown>;
  const presence = record["presenceOutcomes"];
  const closures = record["obligationClosures"];
  return {
    presenceOutcomes: Array.isArray(presence) ? (presence as readonly PresenceOutcome[]) : [],
    obligationClosures: Array.isArray(closures)
      ? (closures as readonly ObligationClosureResult[])
      : [],
  };
}

/** How much of our block one location found, for comparing two of them. */
function locatedLines(receipt: ReceiptLocation): number {
  return receipt.shelves.reduce((total, shelf) => total + shelf.linesFound, 0);
}

export function reportToJson(report: RunReport): Record<string, unknown> {
  return {
    run_id: report.runId,
    goal: report.goal,
    run_key_source: report.runKeySource,
    is_run_key_inferred: report.isRunKeyInferred,
    recall_outcome: report.recallOutcome,
    receipt_outcome: report.receiptOutcome,
    is_receipt_sent: report.isReceiptSent,
    shelves: report.shelves.map((shelf) => ({
      name: shelf.name,
      outcome: shelf.outcome,
      offered_ids: [...shelf.offeredIds],
      lines_expected: shelf.linesExpected,
      lines_found: shelf.linesFound,
      missing_lines: [...shelf.missingLines],
    })),
    step_count: report.stepCount,
    model_call_count: report.modelCallCount,
    disposition: report.disposition,
    close_trigger: report.closeTrigger,
    // Ordered to match the Python report's own key order, which a parity test asserts.
    // JSON objects are unordered and nothing reads these positionally, so the only thing
    // it buys is that one customer's Python log line and their TypeScript one diff
    // against each other rather than appearing to differ everywhere.
    presence_outcomes: report.presenceOutcomes.map((outcome) => ({
      id: outcome.id,
      outcome: outcome.outcome,
    })),
    obligation_closures: report.obligationClosures.map((closure) => ({
      id: closure.id,
      disposition: closure.disposition,
      status: closure.status,
    })),
    decline_reason: report.declineReason,
    withheld: [...report.withheld],
    is_evicted: report.isEvicted,
  };
}

/**
 * One run, from open through every model call to close.
 *
 * Held by the registry rather than by the seat, so one wrapped model serving many
 * concurrent runs never lets two of them share state.
 */
export class HyperstruckRun {
  readonly runId: string;
  readonly identity: AgentIdentity;
  readonly goal: string;
  readonly key: RunKey;
  tools: readonly ToolSpec[];
  readonly threadId: string | null;

  readonly ledger: RunLedger;
  resolvePromise: Promise<void> | null = null;
  injectionBlock: string | null = null;
  receipt: ReceiptLocation | null = null;
  /** The most complete receipt this run ever saw (the evidence that goes on the wire) and
   * the least complete (the fidelity the run report shows). One artefact cannot be both;
   * see `RunSeat.afterModelCall`. */
  bestReceipt: ReceiptLocation | null = null;
  worstReceipt: ReceiptLocation | null = null;
  report: RunReport | null = null;
  withheld: readonly string[] = [];
  lastTouched = Date.now();
  /** Set when an assistant answer carried no tool calls, cleared when a further call
   * arrives under the same key. The grace window runs from this moment. */
  closableAt: number | null = null;
  /** The seat's own pending grace-window close, so a further call can cancel it. */
  closeTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(init: {
    runId: string;
    identity: AgentIdentity;
    goal: string;
    key: RunKey;
    tools?: readonly ToolSpec[];
    threadId?: string | null;
  }) {
    this.runId = init.runId;
    this.identity = init.identity;
    this.goal = init.goal;
    this.key = init.key;
    this.tools = init.tools ?? [];
    this.threadId = init.threadId ?? null;
    this.ledger = new RunLedger(init.runId, init.goal);
  }

  /** Mark the run as still active, for the abandonment sweep. */
  touch(): void {
    this.lastTouched = Date.now();
  }

  get isClosed(): boolean {
    return this.ledger.isClosed;
  }
}

/**
 * The live runs of one process, bounded by a cap and aged by a TTL.
 *
 * The cap alone was the LangGraph registry's design and its own comment warned that the
 * victim can be a live in-flight run. That was tolerable when the graph's hook ordering
 * decided concurrency; a public surface makes concurrency the customer's choice, so the
 * cap is paired with a TTL and the two answer different questions. The TTL reclaims runs
 * nobody will ever close. The cap is the backstop, and reaching it is a warning.
 */
export class RunRegistry {
  private readonly runs = new Map<string, HyperstruckRun>();
  private readonly maxSize: number;
  private readonly ttlMs: number;
  private readonly onWarning: (message: string) => void;

  constructor(
    options: {
      maxSize?: number;
      ttlMs?: number;
      onWarning?: (message: string) => void;
    } = {},
  ) {
    this.maxSize = options.maxSize ?? DEFAULT_MAX_LIVE_RUNS;
    this.ttlMs = options.ttlMs ?? DEFAULT_RUN_TTL_MS;
    this.onWarning = options.onWarning ?? (() => {});
  }

  /** Add a run, returning any that were evicted to make room for it. */
  register(run: HyperstruckRun): HyperstruckRun[] {
    this.runs.delete(run.key.key);
    this.runs.set(run.key.key, run);
    const evicted = this.sweep();
    while (this.runs.size > this.maxSize) {
      const oldest = this.runs.keys().next();
      if (oldest.done === true) break;
      const victim = this.runs.get(oldest.value);
      this.runs.delete(oldest.value);
      if (victim !== undefined) {
        this.onWarning(
          `Hyperstruck run registry full (${this.maxSize}) with no abandoned run to ` +
            `reclaim; evicted live run ${victim.runId} and its learning capture is lost`,
        );
        evicted.push(victim);
      }
    }
    return evicted;
  }

  /**
   * Drop runs untouched for longer than the TTL, and return them.
   *
   * Abandoned means no activity for the TTL, measured from the last touch. A run that is
   * still working is touched by every model call and every step, so it is never a
   * candidate however long it has been open.
   */
  sweep(now: number = Date.now()): HyperstruckRun[] {
    const abandoned: HyperstruckRun[] = [];
    for (const run of [...this.runs.values()]) {
      if (now - run.lastTouched > this.ttlMs) {
        this.runs.delete(run.key.key);
        abandoned.push(run);
      }
    }
    return abandoned;
  }

  /** Runs whose grace window has elapsed since a tool-free assistant answer. */
  closable(graceMs: number, now: number = Date.now()): HyperstruckRun[] {
    return [...this.runs.values()].filter(
      (run) => run.closableAt !== null && now - run.closableAt >= graceMs,
    );
  }

  /** Every live run, for a process-exit flush. */
  all(): HyperstruckRun[] {
    return [...this.runs.values()];
  }

  /**
   * The live run under one correlation key, or `null`.
   *
   * Keyed on the correlation key rather than on the run id, and the two are no longer the
   * same string. A stable key (a trace, a conversation id) names a *series* of runs, and
   * giving each of them the same run id would have the platform dedupe the second turn's
   * episode against the first and drop it silently, which is the worst shape a fault can
   * have: the customer sees a corpus that stops filling and no error anywhere. The key
   * correlates; the run id identifies.
   */
  get(key: string | null | undefined): HyperstruckRun | null {
    if (!key) return null;
    const run = this.runs.get(key);
    if (run === undefined) return null;
    // Re-inserted to keep the map in access order, which is what makes the cap's victim
    // the least recently used rather than the least recently created.
    this.runs.delete(key);
    this.runs.set(key, run);
    run.touch();
    return run;
  }

  pop(key: string | null | undefined): HyperstruckRun | null {
    if (!key) return null;
    const run = this.runs.get(key);
    this.runs.delete(key);
    return run ?? null;
  }

  get size(): number {
    return this.runs.size;
  }
}

export type ReportSink = (report: RunReport) => void;

/**
 * Where a diagnostic goes when the customer registered nothing.
 *
 * One JSON object per line on stderr. stdout belongs to the host's own program, and a
 * library that writes there can corrupt a pipeline; stderr is where a diagnostic belongs
 * and where every process supervisor already collects it.
 */
function defaultLog(message: string, payload: Record<string, unknown>): void {
  try {
    process.stderr.write(`${JSON.stringify({ message, ...payload })}\n`);
  } catch {
    // A host that replaced stderr, or a payload that will not serialise, must not take the
    // run down for the sake of a log line.
  }
}

export interface RunSeatOptions {
  readonly client: LearningClient;
  readonly identity: AgentIdentity;
  readonly declarations?: DeclarationRegistry;
  readonly onReport?: ReportSink;
  readonly maxLearnings?: number;
  readonly materialKinds?: ReadonlySet<string>;
  readonly sourceFramework?: string;
  readonly runKeyResolvers?: readonly RunKeyResolver[];
  readonly registry?: RunRegistry;
  readonly scanner?: ContentScanner | null;
  readonly closeGraceMs?: number;
  readonly onLog?: (message: string, payload: Record<string, unknown>) => void;
  /**
   * The decline reasons the boundary accepts, defaulted to the vendored contract.
   *
   * Injectable for one reason: without it nothing can test that this seat CALLS the
   * publication gate. A delta review mutated `decline` to `if (false && ...)` and the
   * whole suite stayed green, because the only coverage was a unit test of the exported
   * predicate. Pinning the predicate and leaving the wiring unpinned is the same shape
   * as the unfailable escape-hatch test one level down.
   */
  readonly publishedDeclineReasons?: ReadonlySet<string>;
}

/**
 * Whether this reason must be withheld rather than sent.
 *
 * A decline reason the boundary has not published is refused behind a closed enum, and a
 * refused decline is not a degraded diagnostic: it leaves the run open holding its
 * resolve reservation, which is worse than saying less.
 *
 * Keyed on whether the reason is published, not on which reason it is. This read
 * `reason === REASON_NO_GOAL && ...` while no_goal was the only unpublished member, so
 * publishing it would have left the gate permanently false and the NEXT reason added
 * here with no gate at all, in a branch that still looked guarded. Exported so a test
 * can drive it with a name the boundary will never publish, rather than depending on a
 * real reason still waiting for one. The Python seat states the same rule in
 * `_wire.is_unpublished_decline_reason`; the two are kept word for word.
 *
 * `published` is a parameter, defaulted to the loader, purely so a test can drive the
 * empty-contract case. The Python seat gets that for free through monkeypatch; this
 * package caches its contracts in a module-level Map with no reset, so without the
 * parameter a test can only ever see the real non-empty set and the escape hatch below
 * is unfailable. It was, until this was added: removing `published.size > 0 &&` left
 * the whole suite green.
 */
export function isUnpublishedDeclineReason(
  reason: string,
  published: ReadonlySet<string> = publishedDeclineReasons(),
): boolean {
  // `published.size > 0 &&` is the escape hatch, and widening the key without it is a
  // regression rather than a tidy-up. `publishedNames` degrades a missing, unparseable
  // or wrong-shaped contract to an EMPTY set on purpose, and under the old per-reason
  // key that cost one reason while the rest still went out. Under a property key an
  // empty set withholds EVERY decline, so one corrupt JSON file in a package stops any
  // run closing, with nothing but the run report to show for it. contracts.ts states
  // the invariant this would break: an empty answer keeps the behaviour the client had
  // before that value existed, and withholding all six was never that behaviour.
  return published.size > 0 && !published.has(reason);
}

/**
 * The host-neutral seat: one per wrapped model, many runs.
 *
 * The API key binds on the client this is constructed with, and one seat is therefore one
 * tenant. Tenancy is never derived from a run key: a missed inference would then be a
 * cross-tenant leak rather than a lost attribution, and those are not the same class of
 * mistake.
 */
export class RunSeat {
  private readonly client: LearningClient;
  private readonly identity: AgentIdentity;
  private readonly declarations: DeclarationRegistry;
  private readonly onReport: ReportSink | null;
  private readonly maxLearnings: number;
  private readonly materialKinds: ReadonlySet<string>;
  private sourceFramework: string;
  private readonly resolvers: readonly RunKeyResolver[];
  private readonly scanner: ContentScanner | null;
  private readonly onLog: (message: string, payload: Record<string, unknown>) => void;
  readonly closeGraceMs: number;
  private readonly publishedReasons: ReadonlySet<string> | undefined;
  readonly runs: RunRegistry;
  /** The key of the run the inference rung last opened, so a continuation can find it. */
  private inferredKey: string | null = null;

  constructor(options: RunSeatOptions) {
    this.client = options.client;
    this.identity = options.identity;
    this.declarations = options.declarations ?? new DeclarationRegistry();
    this.onReport = options.onReport ?? null;
    this.maxLearnings = options.maxLearnings ?? DEFAULT_MAX_LEARNINGS;
    this.materialKinds = options.materialKinds ?? DEFAULT_MATERIAL_KINDS;
    this.sourceFramework = options.sourceFramework ?? SOURCE_FRAMEWORK;
    this.resolvers = options.runKeyResolvers ?? DEFAULT_RESOLVERS;
    // Off unless a customer passes one. Origin declaration is the primary mechanism and
    // this is the secondary net over free text, which is where origin labelling
    // under-delivers because one label covers arbitrary content.
    this.scanner = options.scanner ?? null;
    this.closeGraceMs = options.closeGraceMs ?? DEFAULT_CLOSE_GRACE_MS;
    // Emitting by default, because the spec's channel guarantee is that "a customer who
    // registers nothing must still be able to find out what happened to their run". A
    // no-op default made every diagnostic in this package invisible while the docstring
    // below claimed the log line was unconditional, so a customer debugging a run that
    // reinforced nothing had nothing to read at all. Written to stderr as one JSON line, so
    // it neither pollutes a program's stdout nor needs a logging framework.
    this.onLog = options.onLog ?? defaultLog;
    this.publishedReasons = options.publishedDeclineReasons;
    // A caller's own registry is taken as given rather than defaulted over. The Python
    // original had a bug of exactly this shape, where an empty registry was falsy and a
    // caller's was silently swapped for a fresh default at every process start.
    this.runs = options.registry ?? new RunRegistry();
  }

  /**
   * An adapter's own hook failed and it called through instead.
   *
   * Routed to the seat rather than swallowed at the adapter, so a customer who registered
   * a diagnostic sink sees it and the default stderr line carries it. A seat that fails
   * silently is one whose absence of learnings has no explanation.
   */
  reportSeatFailure(where: string, error: unknown): void {
    this.onLog("hyperstruck.seat_failed", { where, error: String(error) });
  }

  /**
   * Let an adapter stamp its own provenance, without overriding a caller's.
   *
   * Only when the framework is still the default, so a customer who named their own
   * surface keeps it: their name is a decision and the adapter's is a fallback.
   */
  declareHost(name: string): void {
    if (this.sourceFramework === SOURCE_FRAMEWORK) this.sourceFramework = name;
  }

  /**
   * Start a run and fire its resolve prefetch.
   *
   * The prefetch is started rather than awaited so its round trip overlaps whatever the
   * host does between opening a run and its first model call. A hosted resolve ran p50
   * 11.6s and p99 18.7s in production, so awaiting it here would put that tail straight
   * into the customer's own latency.
   */
  open(
    goal: string,
    tools: readonly ToolSpec[] = [],
    options: { threadId?: string | null; runKey?: RunKey } = {},
  ): HyperstruckRun {
    const key = options.runKey ?? resolveRunKey(this.resolvers);
    // Read the subject declaration off the roster's own schemas. Without this the
    // registry only ever holds what a caller registered by hand, so the annotation a
    // customer already wrote for their own API documentation would be read by nobody and
    // every run would fall back to structural salience, which is the fragmented-entity
    // problem the subject key exists to fix. `registerTools` adds only a subject and never
    // fabricates an argument label, so it cannot make an undeclared tool look declared.
    this.declarations.registerTools(tools);
    const run = new HyperstruckRun({
      // A discriminator, because a correlation key can be stable across turns while a run
      // id must not be. The platform dedupes writes by run id, so a second turn under one
      // conversation id would otherwise have its episode dropped as a duplicate of the
      // first, silently and with nothing to diagnose from.
      runId: `${this.identity.agentName}:${key.key}:${randomUUID().slice(0, 8)}`,
      identity: this.identity,
      goal,
      key,
      tools,
      threadId: options.threadId ?? null,
    });
    for (const evicted of this.runs.register(run)) {
      this.emit(
        this.buildReport(evicted, DISPOSITION_EVICTED, {
          isEvicted: true,
          closeTrigger: CLOSE_TRIGGER_ABANDONED,
        }),
      );
    }
    run.resolvePromise = this.prefetch(run);
    return run;
  }

  /**
   * The run this model call belongs to, opening one if the ladder names a new key.
   *
   * The model-layer hooks fire once per model call rather than once per episode, so every
   * call has to answer "which run is this" before it can do anything else. The ladder
   * answers it, and the same key maps to the same run id, so a second call of the same
   * run finds the run the first one opened.
   *
   * Getting this wrong is not an inefficiency. Two concurrent conversations sharing one
   * wrapped model would have one run's block matched against the other's params, which is
   * why the ladder puts inference last and why the report always says which rung answered.
   */
  forCall(
    goal: string,
    tools: readonly ToolSpec[] = [],
    options: { isContinuation?: boolean } = {},
  ): HyperstruckRun {
    let key = resolveRunKey(this.resolvers);
    // Rung 4 of the ladder, and the reason it exists. Every rung above supplies a key that
    // is stable across the calls of one episode; minting supplies one that is not, so a
    // customer with no tracer and no explicit wrapper got a fresh run per model call, no
    // joined steps, and a decline every turn. That is the configuration both quick starts
    // document, so the documented default captured nothing at all.
    //
    // The adapter tells us whether this call shows a conversation already in progress (a
    // prior assistant turn, or tool results fed back). If it does, and nothing better than
    // a minted key is available, this call belongs to the run the last one opened. It is
    // still reported as inferred, because it is.
    if (key.isInferred && options.isContinuation === true) {
      const carried = this.inferredKey;
      if (carried !== null && this.runs.get(carried) !== null) {
        key = { key: carried, source: "inferred", isInferred: true };
      }
    }
    const existing = this.runs.get(key.key);
    if (existing !== null) {
      // A further call under the same key continues the run rather than letting the grace
      // window close it. Cancelled here rather than checked at fire time so a long-lived
      // session does not accumulate one pending timer per turn.
      existing.closableAt = null;
      if (existing.closeTimer !== null) {
        clearTimeout(existing.closeTimer);
        existing.closeTimer = null;
      }
      // The roster can arrive on a later call than the first, since a customer may bind
      // tools partway through a loop. Recorded when it does, because a run with an empty
      // roster makes restraint unreadable server-side.
      if (tools.length > 0 && existing.tools.length === 0) {
        existing.tools = tools;
        this.declarations.registerTools(tools);
      }
      return existing;
    }
    const opened = this.open(goal, tools, { runKey: key });
    // Remembered only for the minted rung: every other rung re-derives the same key on the
    // next call, and carrying one of theirs would let a stale run outlive its own context.
    if (key.isInferred) this.inferredKey = key.key;
    return opened;
  }

  /**
   * The block to inject on this model call, awaited off the prefetch once.
   *
   * Returns the same string on every call of the run. A retried send must show the model
   * the block it was shown the first time, or the receipt it produces evidences something
   * other than what happened.
   */
  async beforeModelCall(run: HyperstruckRun): Promise<string | null> {
    run.touch();
    if (!run.ledger.isResolved && run.resolvePromise !== null) {
      // Already fail-open inside; awaiting it here only joins the round trip.
      await run.resolvePromise;
    }
    return run.injectionBlock;
  }

  /**
   * Locate our block in the params as they were actually sent.
   *
   * Runs on every send rather than once, because a mid-run trim is precisely the thing
   * the receipt exists to catch and the latest location is the one that describes what
   * the model was last shown.
   */
  afterModelCall(run: HyperstruckRun, sentPayload: unknown): void {
    run.touch();
    if (run.injectionBlock === null) return;
    const text =
      typeof sentPayload === "string" ? sentPayload : flattenParams(sentPayload);
    const located = locateReceipt(text, this.shelfInputs(run));
    run.receipt = located;

    // Two different facts, and collapsing them is what produced a run reporting
    // `delivered` with no receipt at all.
    //
    // **Delivery is monotone across the run.** "Did the recall reach the model" is answered
    // once and stays answered: a block the model was shown on call one was shown, whatever
    // call three did. So the flag latches on the first located block.
    //
    // **The evidence has to survive with it.** `run.receipt` is overwritten on every send,
    // because the latest location describes what the model was *last* shown. Pairing a
    // latching flag with a last-write-wins artefact meant a run whose final call was
    // trimmed sent `isDelivered: true` with no receipt, which is exactly the pair these
    // fields exist to separate, and which the platform escalates as a client defect.
    //
    // **The trim is still reported**, through `worstReceipt`, which is the customer-facing
    // diagnostic. The wire gets the evidence; the report gets the fidelity.
    if (isReceiptPresent(located)) {
      run.ledger.isInjected = true;
      if (run.bestReceipt === null || locatedLines(located) > locatedLines(run.bestReceipt)) {
        run.bestReceipt = located;
      }
    }
    if (run.worstReceipt === null || locatedLines(located) < locatedLines(run.worstReceipt)) {
      run.worstReceipt = located;
    }
  }

  recordPlannedCalls(
    run: HyperstruckRun,
    calls: readonly { callId: string; name: string; args: Record<string, unknown> }[],
  ): void {
    run.touch();
    run.ledger.recordPlannedCalls(calls);
  }

  recordStep(
    run: HyperstruckRun,
    callId: string,
    name: string,
    outcome: { result?: unknown; error?: string | null } = {},
  ): void {
    run.touch();
    run.ledger.recordOutcome(callId, name, outcome);
  }

  /**
   * Mark a run closable because the model answered without asking for another tool.
   *
   * That is the only terminal signal this layer gets, and it is deliberately a window
   * rather than an edge: a customer's loop that answers, is asked a follow-up, and answers
   * again is one episode, and closing on the first answer would make it two. A further call
   * under the same key inside the window continues the run.
   *
   * The seat starts its own timer here rather than leaving the sweep to the customer.
   * Leaving it to them would make the documented default attachment point earn no credit
   * for anyone who did not read that paragraph, which is the exact failure the grace window
   * exists to close.
   */
  markClosable(run: HyperstruckRun): void {
    run.touch();
    run.closableAt = Date.now();
    if (run.closeTimer !== null) clearTimeout(run.closeTimer);
    const timer = setTimeout(() => {
      run.closeTimer = null;
      if (run.closableAt === null || run.isClosed) return;
      void this.close(run, { trigger: CLOSE_TRIGGER_NO_TOOL_CALLS }).catch((error: unknown) => {
        this.onLog("hyperstruck.grace_close_failed", {
          run_id: run.runId,
          error: String(error),
        });
      });
    }, this.closeGraceMs);
    // The pending close must not be the reason a short-lived process stays alive. A host
    // that wants its last runs credited calls flushAll() at exit, which is the deliberate
    // choice rather than a timer holding the loop open behind their back.
    if (typeof timer === "object" && timer !== null && "unref" in timer) {
      (timer as { unref: () => void }).unref();
    }
    run.closeTimer = timer;
  }

  /**
   * Close what the window has finished with and report what aged out.
   *
   * The timer in {@link markClosable} is the normal path; this is for a host that would
   * rather drive the sweep itself, and it also reclaims runs the TTL has abandoned. Safe to
   * call on a timer and safe to never call. Named to match the Python seat's `sweep`.
   */
  async sweep(now: number = Date.now()): Promise<RunReport[]> {
    const reports: RunReport[] = [];
    for (const run of this.runs.closable(this.closeGraceMs, now)) {
      const report = await this.closeIfOpen(run, CLOSE_TRIGGER_NO_TOOL_CALLS);
      if (report !== null) reports.push(report);
    }
    for (const abandoned of this.runs.sweep(now)) {
      const report = this.buildReport(abandoned, DISPOSITION_EVICTED, {
        isEvicted: true,
        closeTrigger: CLOSE_TRIGGER_ABANDONED,
      });
      // An evicted run reaches none of the boundary's terminal endpoints, and that is
      // deliberate. The decline vocabulary is a closed set with no eviction member, and an
      // evicted entry has already lost the offered ids a decline payload needs, so
      // inventing a reason here would be the vocabulary drift this package forbids
      // elsewhere. The run's server-side resolve reservation is left to the existing
      // reclaim sweep, which is the mechanism that already owns runs that never close.
      this.emit(report);
      reports.push(report);
    }
    return reports;
  }

  /** Close every live run. For a process-exit flush, paired with synchronous writes. */
  async flushAll(): Promise<RunReport[]> {
    const reports: RunReport[] = [];
    for (const run of this.runs.all()) {
      const report = await this.closeIfOpen(run, CLOSE_TRIGGER_PROCESS_EXIT);
      if (report !== null) reports.push(report);
    }
    return reports;
  }

  /**
   * Close one run, tolerating the case where something else closed it first.
   *
   * Both bulk paths above walk a snapshot and await inside the loop, and `close` itself
   * awaits the prefetch. That await is a point at which a *sibling* run's own grace timer
   * can fire and close the run this loop is about to reach. A second close is a caller
   * fault by design and throws, so without this guard one raced run would take down the
   * whole sweep and lose the reports of every run still queued behind it.
   *
   * The guard is here rather than in `close`, deliberately: a double close from a caller's
   * own retry or `finally` is still a fault worth naming, and absorbing it there would hide
   * the duplicate episode that fault would have sent.
   */
  private async closeIfOpen(
    run: HyperstruckRun,
    trigger: string,
  ): Promise<RunReport | null> {
    if (run.isClosed) return null;
    try {
      return await this.close(run, { trigger });
    } catch (error) {
      this.onLog("hyperstruck.bulk_close_failed", {
        run_id: run.runId,
        trigger,
        error: String(error),
      });
      return null;
    }
  }

  /**
   * End the run: observe and reinforce, or decline, and report either way.
   *
   * Always terminal. A run left neither reinforced nor declined is indistinguishable from
   * a host that stopped writing back, and it sits open holding its resolve reservation
   * until the server's reclaim sweep notices.
   *
   * `obligationOutcomes` reports what the turn did with the obligations it was offered. They
   * ride the close rather than taking a call of their own, and either leg carries them,
   * because a turn that resolved an obligation and learned nothing is still a turn that
   * resolved an obligation. What became of each is on the report's `obligationClosures`.
   *
   * **Validated before observe is sent, not by the wire body it becomes.** A kept outcome with
   * no `keptBasis`, or a dropped one with no `droppedReason`, used to throw inside the wire
   * builder after observe had already been posted, losing every sibling outcome, the receipt
   * fold and every other closure in the same call. A malformed outcome is dropped and named on
   * `withheld` instead, and every well-formed sibling still closes.
   */
  async close(
    run: HyperstruckRun,
    options: {
      isSuccess?: boolean;
      trigger?: string;
      obligationOutcomes?: readonly ReportedObligationOutcome[];
    } = {},
  ): Promise<RunReport> {
    this.runs.pop(run.key.key);
    if (run.closeTimer !== null) {
      clearTimeout(run.closeTimer);
      run.closeTimer = null;
    }
    // Bounded, and matching the Python seat's own join timeout. Nothing is owed to a
    // resolve nobody will read, and a boundary that never answers would otherwise hold the
    // close open for as long as it liked: the run would never be reported and the host's
    // shutdown would hang on it.
    if (run.resolvePromise !== null) {
      await Promise.race([run.resolvePromise, deadline(RESOLVE_JOIN_TIMEOUT_MS)]);
    }
    run.ledger.close();

    const steps = run.ledger.steps;
    // The gate reads a kind, and this seat has exactly one. Stamped here rather than in
    // the ledger, because the ledger records what happened and the vocabulary that grades
    // it belongs to the host.
    const graded = steps.map((step) => ({ ...step, kind: TOOL_CALL_KIND }));
    const isWorthObserving = shouldObserve(graded, this.materialKinds);
    const outcome = ledgerRecallOutcome(run.ledger);
    const trigger = options.trigger ?? CLOSE_TRIGGER_EXPLICIT;

    const outcomes = this.validObligationOutcomes(run, options.obligationOutcomes ?? []);
    const report = isWorthObserving
      ? await this.reinforce(run, steps, options.isSuccess ?? true, outcome, trigger, outcomes)
      : await this.decline(run, steps, outcome, trigger, outcomes);
    run.report = report;
    this.emit(report);
    return report;
  }

  /** Drops a malformed reported outcome and names it on `run.withheld`, before anything is sent. */
  private validObligationOutcomes(
    run: HyperstruckRun,
    outcomes: readonly ReportedObligationOutcome[],
  ): readonly ReportedObligationOutcome[] {
    const valid: ReportedObligationOutcome[] = [];
    for (const outcome of outcomes) {
      const problem = obligationOutcomeProblem(outcome);
      if (problem === null) {
        valid.push(outcome);
        continue;
      }
      run.withheld = [...run.withheld, `obligation_outcome id=${outcome.id}: ${problem}`];
    }
    return valid;
  }

  private async reinforce(
    run: HyperstruckRun,
    steps: JoinedStep[],
    isSuccess: boolean,
    outcome: string,
    trigger: string,
    obligationOutcomes: readonly ReportedObligationOutcome[],
  ): Promise<RunReport> {
    const episode = this.buildEpisode(run, steps, isSuccess);
    // The best the run saw, not the last: a receipt is evidence the model was shown the
    // block, and the run's final call is not the only moment that could have happened in.
    const receipt = (run.bestReceipt ?? run.receipt)?.text ?? null;
    let result: unknown;
    try {
      await this.client.observe({ identity: run.identity, episode });
      result = await this.client.reinforce({
        identity: run.identity,
        episode,
        isOrgPromotionAllowed: this.declarations.isFullyDeclared(
          steps.map((step) => step.name),
        ),
        contextReceipt: receipt,
        isDelivered: run.ledger.isInjected,
        recallOutcome: outcome,
        obligationOutcomes,
      });
    } catch (error) {
      this.onLog("hyperstruck.write_failed", {
        run_id: run.runId,
        error: String(error),
      });
      return this.buildReport(run, DISPOSITION_WRITE_FAILED, { closeTrigger: trigger });
    }
    const read = readWriteResult(result);
    return this.buildReport(
      run,
      receipt !== null ? DISPOSITION_REINFORCED : DISPOSITION_OBSERVED,
      {
        isReceiptSent: receipt !== null,
        presenceOutcomes: read.presenceOutcomes,
        obligationClosures: read.obligationClosures,
        closeTrigger: trigger,
      },
    );
  }

  private async decline(
    run: HyperstruckRun,
    steps: JoinedStep[],
    outcome: string,
    trigger: string,
    obligationOutcomes: readonly ReportedObligationOutcome[],
  ): Promise<RunReport> {
    const reason = declineReason(
      steps.map((step) => ({ ...step, kind: TOOL_CALL_KIND })),
      false,
      { isGoalless: run.goal.trim().length === 0, isOfferEmpty: !run.ledger.offeredAny },
    );
    if (
      isUnpublishedDeclineReason(reason, this.publishedReasons ?? publishedDeclineReasons())
    ) {
      run.withheld = [
        ...run.withheld,
        `decline_reason=${reason} (the boundary has not published this reason; upgrade ` +
          "the platform deploy to release it)",
      ];
      return this.buildReport(run, DISPOSITION_WITHHELD, { closeTrigger: trigger });
    }
    let result: unknown;
    try {
      result = await this.client.decline({
        identity: run.identity,
        runId: run.runId,
        reason,
        isDelivered: run.ledger.isInjected,
        recallOutcome: outcome,
        sourceFramework: this.sourceFramework,
        obligationOutcomes,
      });
    } catch (error) {
      this.onLog("hyperstruck.decline_failed", {
        run_id: run.runId,
        error: String(error),
      });
      // Not `declined`. The run is still open server-side holding its resolve reservation,
      // and a report saying otherwise is the one that stops anyone looking.
      return this.buildReport(run, DISPOSITION_WRITE_FAILED, {
        declineReason: reason,
        closeTrigger: trigger,
      });
    }
    return this.buildReport(run, DISPOSITION_DECLINED, {
      declineReason: reason,
      obligationClosures: readWriteResult(result).obligationClosures,
      closeTrigger: trigger,
    });
  }

  /** Resolve once and hold the rendered blocks. Fails open on anything. */
  private async prefetch(run: HyperstruckRun): Promise<void> {
    let context: ResolvedContext;
    try {
      context = await this.client.resolve({
        identity: run.identity,
        runId: run.runId,
        goal: run.goal,
        availableTools: run.tools,
        maxLearnings: this.maxLearnings,
        sourceFramework: this.sourceFramework,
      });
    } catch (error) {
      this.onLog("hyperstruck.resolve_failed", {
        run_id: run.runId,
        error: String(error),
      });
      if (!run.ledger.isClosed) run.ledger.recordResolveFailed();
      return;
    }
    if (run.ledger.isClosed) return;
    run.ledger.recordOffer(shelvesFrom(context));
    run.injectionBlock = combineInjectionBlocks(
      context.injectedText,
      context.injectedFactsText,
      context.injectedObligationsText,
    );
  }

  private shelfInputs(run: HyperstruckRun): {
    name: string;
    text: string | null;
    offeredIds: readonly string[];
  }[] {
    return [run.ledger.advice, run.ledger.facts, run.ledger.obligations]
      .filter((shelf): shelf is Shelf => shelf !== null)
      .map((shelf) => ({
        name: shelf.name,
        text: shelf.text,
        offeredIds: shelf.offeredIds,
      }));
  }

  private buildEpisode(
    run: HyperstruckRun,
    steps: JoinedStep[],
    isSuccess: boolean,
  ): Episode {
    const records: StepRecord[] = [];
    let completed = 0;
    let failed = 0;
    const withheld: string[] = [...run.withheld];
    // The one-hop join's left-hand side: values this run's earlier steps returned, with the
    // label their tool declared. Built as the steps are walked and never carried between
    // runs, because the claim it supports is "this value came out of that tool in this
    // episode" and nothing weaker would be true.
    const priorOutputs = new Map<string, string>();
    for (const step of steps) {
      if (step.status === "failed") failed += 1;
      else completed += 1;
      const declared = this.declarations.declarationFor(step.name, step.args);
      withheld.push(...declared.withheld);
      // A value the agent copied out of an earlier result keeps that result's label. One
      // hop, escalate only, and checked against this run's own recorded outputs rather than
      // across the call graph, which we cannot see from a hook and could not claim soundly
      // if we could.
      const escalated = this.declarations.propagate(step.name, step.args, priorOutputs);
      let stamp = declared.stamp;
      // Joined, not overwritten. `declarationFor` has already stamped every undeclared
      // argument with the restrictive default, and `propagate` computes its own baseline
      // from the registry alone, which does not hold that default. Merging its answer over
      // the stamp therefore *lowered* an undeclared argument from secret to whatever the
      // earlier tool declared, which is the exact inversion the lattice exists to make
      // impossible, and the report announced it as an escalation while doing it.
      const existing = (stamp?.["args"] as Record<string, string> | undefined) ?? {};
      const stamped: Record<string, string> = { ...existing };
      for (const [key, label] of Object.entries(escalated)) {
        const current = Object.prototype.hasOwnProperty.call(stamped, key)
          ? stamped[key] ?? null
          : null;
        stamped[key] = joinSensitivity(current, label) ?? label;
      }
      // Reported only where the stamp actually moved. Testing "the joined value equals the
      // propagated label" also fires when an undeclared argument was already `secret` and
      // the propagated label is `secret` too, which names an earlier tool as the cause of a
      // label the restrictive default had already set, pointing at the wrong remedy.
      const applied = Object.entries(escalated).filter(
        ([key]) => stamped[key] !== existing[key],
      );
      if (applied.length > 0) {
        stamp = { ...(stamp ?? {}), args: stamped };
        withheld.push(
          `${step.name}: ${applied.length} argument(s) ` +
            `(${applied.map(([key]) => key).sort().join(", ")}) escalated to match a value ` +
            "an earlier tool in this run returned",
        );
      }
      // Result and error together, because they share an origin exactly: the same tool,
      // the same call, the same step. Covering one and not the other was an inconsistency
      // rather than a decision, and a stack trace carrying a customer record is an
      // ordinary thing for a failing tool to return.
      const scanned = scanAndScrub({ result: step.result, error: step.error }, this.scanner);
      if (!isScanClean(scanned)) withheld.push(`${step.name}: ${describeScan(scanned)}`);
      const scrubbed = (scanned.payload ?? {}) as Record<string, unknown>;
      const stepResult = isScanClean(scanned) ? step.result : scrubbed["result"];
      const stepError = isScanClean(scanned)
        ? step.error
        : ((scrubbed["error"] ?? null) as string | null);
      records.push({
        id: step.id,
        name: step.name,
        args: step.args,
        status: step.status,
        result: stepResult,
        error: stepError,
        declaredSensitivity: stamp,
      });
      // Recorded after this step's own stamp, so a step can never escalate against itself,
      // and from the scrubbed payload, so a value the scanner removed cannot be
      // reintroduced into the join table it was removed from the wire for.
      this.declarations.recordOutputs(priorOutputs, step.name, stepResult);
    }
    // Scanned before the withheld list is snapshotted: it can add a line of its own, and
    // an entry pushed after the snapshot never reaches the report.
    const availableTools = this.scannedTools(run.tools, withheld);
    run.withheld = [...new Set(withheld)];
    return {
      runId: run.runId,
      goal: run.goal,
      steps: records,
      outcome: {
        isSuccess: isSuccess && failed === 0,
        totalSteps: records.length,
        completedSteps: completed,
        failedSteps: failed,
      },
      sourceFramework: this.sourceFramework,
      threadId: run.threadId,
      // The roster the agent had, not the tools it happened to call. The server reads
      // restraint from what was available and declined, so a roster derived from the steps
      // would only ever hold tools that ran.
      //
      // Scanned as well, because it goes to the platform and is stored alongside the
      // learning, and a JSON Schema carries `description`, `default` and `examples` where
      // an example is routinely a real value. The goal is deliberately *not* scanned: its
      // origin is the principal, which is the case origin labelling handles and the
      // scanner is not for.
      availableTools,
    };
  }

  /** The roster with its schemas scanned, since they reach the platform verbatim. */
  private scannedTools(tools: readonly ToolSpec[], withheld: string[]): readonly ToolSpec[] {
    if (this.scanner === null || tools.length === 0) return tools;
    return tools.map((tool) => {
      const scanned = scanAndScrub(
        { parameters: tool.parameters ?? null, returns: tool.returns ?? null },
        this.scanner,
      );
      if (isScanClean(scanned)) return tool;
      withheld.push(`${tool.name} (schema): ${describeScan(scanned)}`);
      const scrubbed = (scanned.payload ?? {}) as Record<string, unknown>;
      return {
        ...tool,
        parameters: (scrubbed["parameters"] ?? null) as Record<string, unknown> | null,
        returns: (scrubbed["returns"] ?? null) as Record<string, unknown> | null,
      };
    });
  }

  private buildReport(
    run: HyperstruckRun,
    disposition: string,
    options: {
      declineReason?: string | null;
      isReceiptSent?: boolean;
      isEvicted?: boolean;
      presenceOutcomes?: readonly PresenceOutcome[];
      obligationClosures?: readonly ObligationClosureResult[];
      closeTrigger?: string | null;
    } = {},
  ): RunReport {
    // The worst the run saw, because the reader's question is whether anything went wrong
    // on the way to the model.
    const receipt = run.worstReceipt ?? run.receipt;
    return {
      runId: run.runId,
      goal: run.goal,
      runKeySource: run.key.source,
      isRunKeyInferred: run.key.isInferred,
      recallOutcome: ledgerRecallOutcome(run.ledger),
      receiptOutcome: receipt !== null ? receiptOutcome(receipt) : PRESENCE_UNRESOLVED,
      isReceiptSent: options.isReceiptSent ?? false,
      shelves: (receipt?.shelves ?? []).map((shelf) => ({
        name: shelf.name,
        outcome: shelf.outcome,
        offeredIds: [...shelf.offeredIds],
        linesExpected: shelf.linesExpected,
        linesFound: shelf.linesFound,
        missingLines: [...shelf.missingLines],
      })),
      presenceOutcomes: options.presenceOutcomes ?? [],
      obligationClosures: options.obligationClosures ?? [],
      stepCount: run.ledger.steps.length,
      modelCallCount: run.ledger.modelCallCount,
      disposition,
      closeTrigger: options.closeTrigger ?? null,
      declineReason: options.declineReason ?? null,
      withheld: run.withheld,
      isEvicted: options.isEvicted ?? false,
    };
  }

  /**
   * Publish the report on every channel, and never let one break the others.
   *
   * The log line is on by default and unconditional, because a customer who registered
   * nothing must still be able to find out what happened to their run. The callback is
   * how a service routes the report into its own observability, and a callback that
   * throws is the customer's bug, not a reason to lose the run.
   */
  private emit(report: RunReport): void {
    this.onLog("hyperstruck.run", reportToJson(report));
    if (this.onReport === null) return;
    try {
      this.onReport(report);
    } catch (error) {
      this.onLog("hyperstruck.report_callback_failed", {
        run_id: report.runId,
        error: String(error),
      });
    }
  }
}

/** The three shelves as the boundary described them, each with its own promise. */
function shelvesFrom(context: ResolvedContext): {
  advice: Shelf;
  facts: Shelf;
  obligations: Shelf;
} {
  return {
    advice: renderConfirmedShelf("advice", context.injectedText, context.offeredLearningIds),
    facts: renderConfirmedShelf("facts", context.injectedFactsText, context.offeredClaimIds),
    obligations: offeredAndDeliveredShelf(
      "obligations",
      context.injectedObligationsText,
      context.offeredObligationIds,
      context.deliveredObligationIds.length > 0 ? context.deliveredObligationIds : null,
    ),
  };
}

/** A run id for a caller that wants one without opening a seat. */
export function newRunId(agentName: string): string {
  return `${agentName}:${randomUUID().replace(/-/g, "")}`;
}
