/**
 * What one run recorded: the two shelves offered to it, and what it then did.
 *
 * `/resolve` returns advice and claims, and the boundary render-confirms both: an item
 * refused by the trust floor or cut by the token budget appears in neither the block nor
 * the offered ids, so a shelf's offer is what it delivered. Open obligations ride the
 * claims shelf as owed claims and have no shelf of their own.
 */

/**
 * A lifecycle call arrived out of order.
 *
 * The LangGraph seat never needed this: the framework's hook ordering enforced the
 * sequence, and the state was flat booleans that could not be reached wrongly. A public
 * open/record/close surface hands that ordering to the caller, so what was structurally
 * impossible becomes an ordinary mistake and has to be named rather than absorbed.
 * Absorbing it would mean recording steps against a closed run and reporting a smaller
 * episode than the one that happened.
 */
export class LedgerStateError extends Error {
  override name = "LedgerStateError";
}

export class LedgerClosedError extends LedgerStateError {
  override name = "LedgerClosedError";
}

/** One shelf's offer to a run: the rendered block and the ids behind it. */
export interface Shelf {
  readonly name: string;
  readonly text: string | null;
  readonly offeredIds: readonly string[];
}

export function isShelfEmpty(shelf: Shelf): boolean {
  return shelf.offeredIds.length === 0 && !shelf.text;
}

/** A shelf whose offer the boundary guarantees was rendered. */
export function renderConfirmedShelf(
  name: string,
  text: string | null,
  offeredIds: readonly string[],
): Shelf {
  return { name, text, offeredIds: [...offeredIds] };
}

interface PlannedCall {
  readonly callId: string;
  readonly name: string;
  readonly args: Record<string, unknown>;
}

interface Outcome {
  readonly callId: string;
  readonly name: string;
  readonly result: unknown;
  readonly error: string | null;
}

export interface JoinedStep {
  readonly id: string;
  readonly name: string;
  readonly args: Record<string, unknown>;
  readonly status: "completed" | "failed";
  readonly result: unknown;
  readonly error: string | null;
  readonly kind?: string;
}

/** Everything one run records, from open to close. */
export class RunLedger {
  readonly runId: string;
  readonly goal: string;

  advice: Shelf | null = null;
  facts: Shelf | null = null;

  isResolved = false;
  /** Latched separately from `isResolved`, which latches either way so a failure never
   * re-triggers retrieval. That makes it useless for telling a fault from a cold corpus,
   * and those two are exactly what the boundary is being told apart. */
  isResolveFailed = false;
  /** Set where the block reaches a model call, not where it is resolved: a run can
   * resolve and then never call a model, and the boundary is told which happened. */
  isInjected = false;

  modelCallCount = 0;
  isClosed = false;

  private readonly planned = new Map<string, PlannedCall>();
  private readonly outcomes = new Map<string, Outcome>();
  private readonly callOrder: string[] = [];

  constructor(runId: string, goal: string) {
    this.runId = runId;
    this.goal = goal;
  }

  private requireOpen(): void {
    if (this.isClosed) {
      throw new LedgerClosedError(
        `run ${this.runId} is closed; recording against it would report a smaller ` +
          "episode than the one that happened",
      );
    }
  }

  /**
   * Close the run once. A second close is a caller fault, not a no-op.
   *
   * Silently allowing it would hide a double close in a retry or a `finally` block, and
   * the second close is the one that would send a duplicate episode.
   */
  close(): void {
    if (this.isClosed) {
      throw new LedgerClosedError(`run ${this.runId} is already closed`);
    }
    this.isClosed = true;
  }

  /**
   * Record what the recall offered, both shelves at once.
   *
   * Both are required rather than defaulted, so a caller cannot record one and leave the
   * other silently missing with every test still passing.
   */
  recordOffer(offer: { advice: Shelf; facts: Shelf }): void {
    this.requireOpen();
    this.advice = offer.advice;
    this.facts = offer.facts;
    this.isResolved = true;
  }

  /** A resolve that threw. Distinct from one that returned nothing. */
  recordResolveFailed(): void {
    this.requireOpen();
    this.isResolved = true;
    this.isResolveFailed = true;
  }

  /** Capture what one model call planned. */
  recordPlannedCalls(
    calls: readonly { callId: string; name: string; args: Record<string, unknown> }[],
  ): void {
    this.requireOpen();
    this.modelCallCount += 1;
    for (const call of calls) {
      // A retried model call replans the same ids, and the ledger folds the several
      // physical sends into one planned step so a retry is one entry in the episode and
      // cannot inflate the outcome the decline table reads.
      if (this.planned.has(call.callId)) continue;
      this.planned.set(call.callId, {
        callId: call.callId,
        name: call.name,
        args: call.args,
      });
      this.callOrder.push(call.callId);
    }
  }

  /** Capture what actually happened for one planned call. */
  recordOutcome(
    callId: string,
    name: string,
    outcome: { result?: unknown; error?: string | null } = {},
  ): void {
    this.requireOpen();
    this.outcomes.set(callId, {
      callId,
      name,
      result: outcome.result ?? null,
      error: outcome.error ?? null,
    });
  }

  /**
   * The join: only calls present in both streams become steps.
   *
   * A call the model planned and the runtime never ran is not evidence about anything,
   * and recording it as a step would teach the corpus from an obligation rather than
   * from an outcome. A result arriving for a call that was never planned is the same
   * defect from the other side and is equally dropped: it means the two streams came
   * from different runs.
   */
  get steps(): JoinedStep[] {
    const joined: JoinedStep[] = [];
    for (const callId of this.callOrder) {
      const outcome = this.outcomes.get(callId);
      if (outcome === undefined) continue;
      const plan = this.planned.get(callId);
      if (plan === undefined) continue;
      joined.push({
        id: callId,
        name: plan.name,
        args: { ...plan.args },
        status: outcome.error !== null ? "failed" : "completed",
        result: outcome.result,
        error: outcome.error,
      });
    }
    return joined;
  }

  /** Whether any shelf put anything forward. */
  get offeredAny(): boolean {
    return [this.advice, this.facts].some(
      (shelf) => shelf !== null && shelf.offeredIds.length > 0,
    );
  }
}
