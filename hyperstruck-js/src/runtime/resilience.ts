/**
 * Staying up while the boundary is not.
 *
 * Three things, and the dependency calculation differs from the Python package's by
 * design rather than by accident. `hyperstruck-py` ships exactly one runtime dependency
 * as a stated property, so its jitter and its breaker are written by hand. TypeScript has
 * no equivalent tradition and the honest calculation comes out the other way: `p-queue`
 * and `p-retry` map cleanly onto the write queue and the terminal-versus-transient split,
 * and `cockatiel` is a zero-dependency fit for the breaker. The asymmetry is deliberate
 * and both READMEs say so.
 *
 * What is *not* delegated is the policy. The thresholds, the cooldown, what counts as a
 * failure and what a 4xx means are stated here, because they are the same policy the
 * Python seat runs and a parity test pins the two.
 */

import { mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { join as joinPath } from "node:path";

/**
 * How many consecutive resolve failures open the breaker.
 *
 * Three rather than one, because a single timeout is ordinary tail latency on a boundary
 * whose p99 is 18.7 seconds, and opening on it would take a healthy deployment's recall
 * away for the cooldown.
 */
export const DEFAULT_FAILURE_THRESHOLD = 3;

/**
 * How long the breaker stays open before letting one probe through. Thirty seconds is
 * short enough that a boundary recovering from a deploy is picked up within a run or two,
 * and long enough that an outage is not re-probed by every run.
 */
export const DEFAULT_BREAKER_COOLDOWN_MS = 30_000;

/**
 * Equal jitter: half the interval fixed, half random.
 *
 * The previous schedule was identical for every concurrent run, so their retries arrived
 * as one wave. One client instance in a standalone service fronts many runs at once,
 * which is what makes this matter more here than in a per-graph seat.
 */
export function backoffDelayMs(
  baseMs: number,
  attempt: number,
  random: () => number = Math.random,
): number {
  const interval = baseMs * 2 ** attempt;
  const half = interval / 2;
  return half + random() * half;
}

/**
 * Resolve was not attempted: the breaker is open on this boundary.
 *
 * A distinct type rather than a timeout, because the two license different readings. A
 * timeout is this run's own observation of a slow boundary. This is a report that other
 * runs already made that observation and this one is being spared the wait, which is the
 * breaker working rather than a fault of the run that sees it.
 */
export class CircuitOpenError extends Error {
  override name = "CircuitOpenError";
}

/**
 * One boundary's health, shared by every run in the process.
 *
 * Deliberately not per client instance. The whole value is that the *second* run does not
 * repeat the first one's timeout, and a per-instance breaker in a service that constructs
 * a client per request would never see a second failure.
 */
export class ResolveBreaker {
  private readonly failureThreshold: number;
  private readonly cooldownMs: number;
  private consecutiveFailures = 0;
  private openedAt: number | null = null;
  private isProbing = false;
  trips = 0;

  private readonly onTrip: (message: string) => void;

  constructor(
    options: {
      failureThreshold?: number;
      cooldownMs?: number;
      onTrip?: (message: string) => void;
    } = {},
  ) {
    this.failureThreshold = Math.max(1, options.failureThreshold ?? DEFAULT_FAILURE_THRESHOLD);
    this.cooldownMs = options.cooldownMs ?? DEFAULT_BREAKER_COOLDOWN_MS;
    // A breaker that opens is the single event most likely to explain "our corpus stopped
    // filling", and it used to happen with no signal at all in this language while the
    // Python one logged a warning. Defaulted to stderr for the same reason the client's
    // diagnostics are.
    this.onTrip =
      options.onTrip ??
      ((message) => {
        try {
          process.stderr.write(`${message}\n`);
        } catch {
          // A host that replaced stderr must not lose recall over a log line.
        }
      });
  }

  get isOpen(): boolean {
    return this.openedAt !== null;
  }

  /**
   * Throw if the call must not be attempted; return to let it through.
   *
   * One probe is admitted per cooldown once it has elapsed. Only one, because a boundary
   * that is still down must not be handed the whole backlog at the moment the cooldown
   * expires, which is the thundering herd the breaker exists to prevent arriving one
   * cooldown later.
   */
  beforeRequest(now: number = Date.now()): void {
    if (this.openedAt === null) return;
    if (now - this.openedAt < this.cooldownMs) {
      throw new CircuitOpenError(
        "resolve skipped: the learning boundary is failing and the circuit is open; " +
          "this run proceeds without recalled context",
      );
    }
    if (this.isProbing) {
      throw new CircuitOpenError(
        "resolve skipped: a probe of the failing boundary is already in flight",
      );
    }
    this.isProbing = true;
  }

  /**
   * Close the breaker. A single success is enough, by design.
   *
   * Requiring a run of successes would keep recall switched off through a recovery that
   * has already happened, and the cost of closing too early is one more timeout, which
   * immediately re-opens it.
   */
  recordSuccess(): void {
    this.consecutiveFailures = 0;
    this.openedAt = null;
    this.isProbing = false;
  }

  recordFailure(now: number = Date.now()): void {
    this.isProbing = false;
    this.consecutiveFailures += 1;
    if (this.consecutiveFailures >= this.failureThreshold && this.openedAt === null) {
      this.openedAt = now;
      this.trips += 1;
      this.onTrip(
        `Hyperstruck resolve circuit opened after ${this.consecutiveFailures} consecutive ` +
          `failures; runs will proceed without recalled context for ` +
          `${Math.round(this.cooldownMs / 1000)}s`,
      );
    } else if (this.openedAt !== null) {
      this.openedAt = now;
    }
  }
}

const BREAKERS = new Map<string, ResolveBreaker>();

/** The process-wide breaker for one boundary, created on first use. */
export function breakerFor(baseUrl: string): ResolveBreaker {
  let breaker = BREAKERS.get(baseUrl);
  if (breaker === undefined) {
    breaker = new ResolveBreaker();
    BREAKERS.set(baseUrl, breaker);
  }
  return breaker;
}

/** Drop every breaker. For tests, and for a host that forks after configuring. */
export function resetBreakers(): void {
  BREAKERS.clear();
}

export interface PendingWrite {
  readonly path: string;
  readonly endpoint: string;
  readonly body: Record<string, unknown>;
}

/**
 * An on-disk parking bay for writes that have not landed yet.
 *
 * Off by default and never enabled implicitly, because the documented rejection this
 * overrides is still right for most hosts: a thin client runs in serverless, read-only
 * and multi-replica environments, where a local store is variously impossible, useless or
 * a correctness hazard. What changed is the host, not the reasoning. So {@link open}
 * refuses rather than degrading: a store that silently fails to write is a corpus that
 * silently never fills, which is the failure this feature was asked for to prevent.
 *
 * The store holds episode content, so it inherits the same redaction the wire does: what
 * is parked is the already-redacted body, never the raw episode.
 */
/**
 * How many parked writes the outbox keeps. Unbounded, a boundary that is down for a day
 * fills the customer's disk with episodes nobody will ever read: the platform dedupes by
 * run id, so the value of an old parked write decays to nothing while its cost does not.
 * The oldest go first, because the newest are the ones still worth delivering.
 */
export const MAX_PARKED_WRITES = 5_000;

export class DurableOutbox {
  readonly directory: string;
  private sequence = 0;

  private constructor(directory: string) {
    this.directory = directory;
  }

  /**
   * Prepare the store, or return `null` with a reason.
   *
   * The read-only check is a real write rather than a permissions probe, because a
   * permissions probe answers about mode bits and the case this guards is a read-only
   * mount, where the bits say yes and the write fails.
   */
  static open(
    directory: string,
    onRefused?: (reason: string) => void,
  ): DurableOutbox | null {
    try {
      // 0o700: the store holds episode content, which is why it inherits the wire's
      // redaction. It should not also be readable by every user on a shared host.
      mkdirSync(directory, { recursive: true, mode: 0o700 });
      const probe = joinPath(directory, `.probe-${randomUUID()}`);
      writeFileSync(probe, "", "utf8");
      rmSync(probe, { force: true });
    } catch (error) {
      onRefused?.(
        `Hyperstruck durable outbox disabled: ${directory} is not writable ` +
          `(${String(error)}). Writes stay in memory, which is the documented default.`,
      );
      return null;
    }
    return new DurableOutbox(directory);
  }

  /**
   * Persist one write, atomically, and return where it landed.
   *
   * Written to a temporary file in the same directory and then renamed, so a process
   * killed mid-write leaves no half-parsed episode for the next start to trip over.
   */
  park(endpoint: string, body: Record<string, unknown>): string | null {
    const record = { endpoint, body, parked_at: Date.now() / 1000 };
    const temporary = joinPath(this.directory, `${randomUUID()}.tmp`);
    // Time-ordered name, because `pending` promises oldest first and `trim` drops the
    // oldest; a bare uuid sorts randomly and would have made both statements false.
    // Timestamp, then a per-instance counter, then a uuid. The timestamp orders across
    // restarts, the counter keeps two writes in the same millisecond apart (a bare
    // timestamp collides constantly and the uuid tiebreak sorts randomly), and the uuid
    // keeps two processes sharing one directory apart.
    const stamp = String(Math.round(record.parked_at * 1000)).padStart(16, "0");
    const sequence = String(this.sequence++).padStart(6, "0");
    const destination = joinPath(this.directory, `${stamp}-${sequence}-${randomUUID()}.json`);
    try {
      writeFileSync(temporary, JSON.stringify(record), { encoding: "utf8", mode: 0o600 });
      renameSync(temporary, destination);
      this.trim();
      return destination;
    } catch {
      // A payload that will not serialise is a client bug, and losing the write is the
      // lesser harm: throwing here would break the host's run for a durability feature
      // they opted into for the opposite reason.
      try {
        rmSync(temporary, { force: true });
      } catch {
        // Nothing further to do; the temporary file is inert.
      }
      return null;
    }
  }

  /** Drop the oldest parked writes once the store is over its cap. */
  private trim(): void {
    try {
      const names = readdirSync(this.directory)
        .filter((name) => name.endsWith(".json"))
        .sort();
      for (const name of names.slice(0, Math.max(0, names.length - MAX_PARKED_WRITES))) {
        rmSync(joinPath(this.directory, name), { force: true });
      }
    } catch {
      // A trim that cannot run is not a reason to lose the write it was making room for.
    }
  }

  /** Forget a write that has landed. A missing file is already forgotten. */
  release(path: string | null): void {
    if (path === null) return;
    try {
      rmSync(path, { force: true });
    } catch {
      // A file we cannot remove is re-read by the next drain and deduped server-side.
    }
  }

  /**
   * Every parked write, oldest first, skipping any that will not parse.
   *
   * A file that will not parse is dropped rather than retried forever: it cannot be
   * delivered, and leaving it would make every later drain re-read it.
   */
  pending(): PendingWrite[] {
    let names: string[];
    try {
      names = readdirSync(this.directory)
        .filter((name) => name.endsWith(".json"))
        .sort();
    } catch {
      return [];
    }
    const writes: PendingWrite[] = [];
    for (const name of names) {
      const path = joinPath(this.directory, name);
      try {
        const record = JSON.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
        const endpoint = record["endpoint"];
        const body = record["body"];
        if (typeof endpoint !== "string" || body === null || typeof body !== "object") {
          throw new Error("unreadable record");
        }
        writes.push({ path, endpoint, body: body as Record<string, unknown> });
      } catch {
        this.release(path);
      }
    }
    return writes;
  }
}
