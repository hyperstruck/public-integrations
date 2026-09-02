/**
 * Whether a finished turn is worth observing, and why it was declined if not.
 *
 * This table governs what the corpus learns from, and it is the half of the loop that
 * proving reinforce alone leaves unproven. It is ported from the neutral Python layer
 * rather than invented here, and a parity test pins the two against each other: two
 * tables deciding what the corpus learns from is not a duplication that shows up as a
 * merge conflict, it shows up months later as two hosts disagreeing about which turns
 * taught anything, with no single place to read the rule.
 *
 * The server-side critic is the precision backstop and the spend cap is the hard budget,
 * so this gate is a cost and recall optimiser rather than a correctness boundary: it
 * skips turns that cannot teach anything and always keeps the highest-signal one, a turn
 * that recovered from a failure.
 */

import {
  REASON_BELOW_MATERIAL_THRESHOLD,
  REASON_EMPTY_OFFER,
  REASON_NO_GOAL,
  REASON_NO_TOOL_CALLS,
  REASON_UNEVIDENCED_OUTCOME,
} from "./wire.ts";

export const STATUS_COMPLETED = "completed";
export const STATUS_FAILED = "failed";

/**
 * Two, not one. One material step is a turn that did a single thing, which the corpus
 * cannot contrast against anything; two is the minimum from which a lesson can be drawn.
 */
export const MIN_MATERIAL_STEPS = 2;

export interface GatedStep {
  readonly kind?: string;
  readonly status?: string;
}

/**
 * Whether a captured step changed or executed something.
 *
 * The kind set is passed in rather than read from a constant, because what counts as
 * material is the host's judgement about its own tools and hosts do not share a
 * vocabulary. The rule over the set is what is shared.
 */
export function isMaterial(step: GatedStep, materialKinds: ReadonlySet<string>): boolean {
  return step.kind !== undefined && materialKinds.has(step.kind);
}

/** A failed step followed by any later successful step: the prime learning. */
export function recoveredFromFailure(steps: readonly GatedStep[]): boolean {
  let seenFailure = false;
  for (const step of steps) {
    if (step.status === STATUS_FAILED) {
      seenFailure = true;
    } else if (seenFailure && step.status === STATUS_COMPLETED) {
      return true;
    }
  }
  return false;
}

/**
 * Whether a turn's episode is worth shipping to observe.
 *
 * Always for a failure-recovery turn; otherwise only when the turn has at least
 * {@link MIN_MATERIAL_STEPS} material steps. Pure read, search and chat turns, and rapid
 * sub-threshold turns, fall through to false; the debounce is subsumed, since a tiny
 * rapid turn cannot clear the material threshold anyway.
 */
export function shouldObserve(
  steps: readonly GatedStep[],
  materialKinds: ReadonlySet<string>,
): boolean {
  if (steps.length === 0) return false;
  if (recoveredFromFailure(steps)) return true;
  const material = steps.filter((step) => isMaterial(step, materialKinds)).length;
  return material >= MIN_MATERIAL_STEPS;
}

/**
 * Why this turn was declined, from the gate that actually decided it.
 *
 * The goalless case is reported first because it is the only one that is not a judgement
 * about the turn's steps: a goalless turn can be entirely material and is still declined,
 * so reporting it by its step count would name a gate that never ran.
 *
 * Derived rather than invented, so the reported cause and the gate can never disagree.
 * This is what makes the gate measurable: before it was derived, it fired silently and
 * how often it skipped a turn, and why, was invisible.
 *
 * The missing outcome is reported only for a turn the step gates would have let through,
 * because that is the only case where it decided anything. A turn that wrote nothing is
 * below the material threshold whatever its evidence says.
 *
 * `empty_offer` is ordered after the step gates, so a turn with material steps is never
 * explained away by its offer. One says the corpus had nothing to give, the other says
 * the turn had nothing to give back, and the repair is different.
 */
export function declineReason(
  steps: readonly GatedStep[],
  isWorthLearningFrom: boolean,
  options: { isGoalless: boolean; isOfferEmpty?: boolean },
): string {
  if (options.isGoalless) return REASON_NO_GOAL;
  if (isWorthLearningFrom) return REASON_UNEVIDENCED_OUTCOME;
  if (steps.length === 0) return REASON_NO_TOOL_CALLS;
  if (options.isOfferEmpty === true) return REASON_EMPTY_OFFER;
  return REASON_BELOW_MATERIAL_THRESHOLD;
}
