/**
 * What one run recorded: three shelves offered to it, and what it then did.
 *
 * Two things separate this from the LangGraph seat's ledger it is lifted from.
 *
 * **Three shelves, not two.** `/resolve` returns advice, facts and obligations, and
 * every client we ship has handled two. The parsing for the third already existed and
 * the ledger simply never called it, which is the quietest possible way for a shelf to
 * go missing.
 *
 * **Offered and delivered are separate sets, per shelf.** For advice and facts the
 * boundary render-confirms its offer, so the two sets coincide and the distinction costs
 * nothing. For obligations it deliberately does not: `offeredObligationIds` names
 * everything selection admitted, including one the block's budget then cut, because the
 * shelf escalates on deliveries and an obligation no model was shown must not be
 * escalated for being ignored. Collapsing them would produce a scoring fault on the
 * server that is invisible from here, which is the worst shape a fault can have, so the
 * ledger refuses to represent them as one thing even where they happen to agree.
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

/**
 * One shelf's offer to a run, and what the block actually carried.
 *
 * `isRenderConfirmed` is not decoration. It records whether the boundary promises that
 * everything offered was rendered, which is true of advice and facts and false of
 * obligations. A reader asking "what was the model actually shown" must use
 * `deliveredIds` on every shelf; the flag exists so a reader asking "what did the shelf
 * put forward" can tell the two questions apart rather than guessing from whether the
 * lists happen to match on the run in front of it.
 */
export interface Shelf {
  readonly name: string;
  readonly text: string | null;
  readonly offeredIds: readonly string[];
  readonly deliveredIds: readonly string[];
  readonly isRenderConfirmed: boolean;
}

function checkShelf(shelf: Shelf): Shelf {
  // Deduplicated before comparison. A boundary that repeats an id in one list is not
  // describing a different offer, and throwing on it would take out the prefetch and, with
  // it, the customer's model call. The subset rule is about membership, not multiplicity.
  const offered = new Set(shelf.offeredIds);
  const extra = [...new Set(shelf.deliveredIds)].filter((id) => !offered.has(id));
  if (extra.length > 0) {
    throw new Error(
      `${shelf.name}: delivered ids that were never offered: ${[...extra].sort().join(", ")}. ` +
        "Delivered is a subset of offered by construction; a difference here means the " +
        "two were read from different responses.",
    );
  }
  const delivered = new Set(shelf.deliveredIds);
  if (
    shelf.isRenderConfirmed &&
    (delivered.size !== offered.size || [...offered].some((id) => !delivered.has(id)))
  ) {
    throw new Error(
      `${shelf.name} is render-confirmed, so its offered and delivered sets must agree. ` +
        "They do not, which means either the boundary changed its promise or this shelf " +
        "was constructed with the wrong flag.",
    );
  }
  return shelf;
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
  const ids = [...offeredIds];
  return checkShelf({
    name,
    text,
    offeredIds: ids,
    deliveredIds: ids,
    isRenderConfirmed: true,
  });
}

/**
 * A shelf that offers more than it delivers, and says which is which.
 *
 * An absent delivered set is what an older deployment returns, and it is recorded as
 * nothing delivered rather than as everything delivered: over-reporting a delivery is
 * what causes an obligation nobody saw to be escalated for being ignored, and
 * under-reporting only forgoes credit.
 */
export function offeredAndDeliveredShelf(
  name: string,
  text: string | null,
  offeredIds: readonly string[],
  deliveredIds: readonly string[] | null | undefined,
): Shelf {
  return checkShelf({
    name,
    text,
    offeredIds: [...offeredIds],
    deliveredIds: [...(deliveredIds ?? [])],
    isRenderConfirmed: false,
  });
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
  obligations: Shelf | null = null;

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
   * Record what the recall offered, all three shelves at once.
   *
   * All three are required rather than defaulted. A default would let a caller record
   * two and silently reproduce the missing-shelf fault this ledger exists to end, with
   * every test still passing, which is how it survived this long.
   */
  recordOffer(offer: { advice: Shelf; facts: Shelf; obligations: Shelf }): void {
    this.requireOpen();
    this.advice = offer.advice;
    this.facts = offer.facts;
    this.obligations = offer.obligations;
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

  /** Whether any shelf put anything forward, which is not the same as delivered. */
  get offeredAny(): boolean {
    return [this.advice, this.facts, this.obligations].some(
      (shelf) => shelf !== null && shelf.offeredIds.length > 0,
    );
  }

  get deliveredAny(): boolean {
    return [this.advice, this.facts, this.obligations].some(
      (shelf) => shelf !== null && shelf.deliveredIds.length > 0,
    );
  }
}
