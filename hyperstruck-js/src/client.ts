/**
 * The HTTP client for the handful of boundary endpoints this seat needs.
 *
 * Calls go through `fetch` directly, not through the generated `@hyperstruck/sdk` and not
 * through `openapi-fetch`. Both were considered and neither earned its place: the
 * middleware needs five endpoints, and 19,743 lines of generated client to reach them
 * would abandon the thin-client property the Python package states as policy.
 *
 * `openapi-fetch` was dropped for a narrower reason worth recording, because the obvious
 * reading is that it was simply forgotten. Several of the bodies below deliberately *omit*
 * fields an older deployment forbids (see `wire.ts`), and typing them against the current
 * schema would have made that forward-compatibility rule the thing the type checker fights
 * hardest. What the schema is used for instead is the contract pin: `openapi-typescript`
 * generates `schema.ts`, the parity tests assert every field named here exists in it, and
 * a CI job fails when it goes stale. That is the safety the dependency would have bought,
 * without the dependency.
 *
 * **Server-side only.** Tenancy rides entirely on the API key with `org_id` resolved
 * server-side, so a browser entry point here would put the tenant boundary in a bundle.
 * The package ships no browser condition in its `exports`, which makes that a resolution
 * failure at a bundler's build time rather than a warning in a document nobody reads.
 */

import { Answer, type AnswerAt, type AnswerDetail } from "./answers.ts";

// Only a stuck call reaches this: the route's own guard fires under Modal's 150 second cap.
const ANSWER_TIMEOUT_MS = 180_000;
import PQueue from "p-queue";

import { identityPayload, type AgentIdentity } from "./identity.ts";
import { redactEpisodePayload } from "./redaction.ts";
import {
  breakerFor,
  backoffDelayMs,
  DurableOutbox,
  type ResolveBreaker,
} from "./runtime/resilience.ts";
import { CLIENT_PRODUCT, VERSION } from "./version.ts";
import {
  CLOSURE_BUSY,
  DECLINE_REASONS,
  DEFAULT_MAX_LEARNINGS,
  episodePayload,
  obligationClosuresFromResponse,
  reinforceResultFromResponse,
  reportedObligationOutcomePayload,
  resolvedContextFromResponse,
  toolPayload,
  type Episode,
  type ReinforceResult,
  type ReportedObligationOutcome,
  type ResolvedContext,
  type ToolSpec,
} from "./wire.ts";

/** What a write returned when the response never reached the caller: the asynchronous path,
 * and a deployment that returns neither half. */
const EMPTY_WRITE_RESULT: ReinforceResult = {
  presenceOutcomes: [],
  obligationClosures: [],
};

export const DEFAULT_BASE_URL = "https://api.hyperstruck.com";

/** The run lock is usually held by this run's own observe, which finishes in seconds. */
const BUSY_CLOSURE_RESENDS = 3;

/** The id as the boundary echoes it: a UUID in lower-case hyphenated form. */
function canonicalId(id: string): string {
  const hex = id.trim().replace(/^\{|\}$/g, "").replace(/-/g, "").toLowerCase();
  if (!/^[0-9a-f]{32}$/.test(hex)) return id;
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** A closure entry's id when it has a string one, else null. */
function closureId(closure: unknown): string | null {
  if (closure === null || typeof closure !== "object") return null;
  const id = (closure as Record<string, unknown>)["id"];
  return typeof id === "string" ? id : null;
}

/** `response` with each closure the resend answered replaced by that answer. */
function withResentClosures(response: unknown, resent: Record<string, unknown>): unknown {
  if (response === null || typeof response !== "object") return response;
  const record = response as Record<string, unknown>;
  const answered = new Map<string, unknown>();
  const resentClosures = resent["obligation_closures"];
  for (const closure of Array.isArray(resentClosures) ? resentClosures : []) {
    const id = closureId(closure);
    if (id !== null) answered.set(canonicalId(id), closure);
  }
  const closures = record["obligation_closures"] as unknown[];
  return {
    ...record,
    obligation_closures: closures.map((closure) => {
      const id = closureId(closure);
      return id === null ? closure : (answered.get(canonicalId(id)) ?? closure);
    }),
  };
}

/** The only paths a parked write may be replayed to. See `replayDurableQueue`. */
const REPLAYABLE_ENDPOINTS: ReadonlySet<string> = new Set([
  "/observe",
  "/reinforce",
  "/decline",
  "/distill",
]);

/** Writes get their own deadline; resolve passes its own, far shorter one. */
export const DEFAULT_WRITE_TIMEOUT_MS = 30_000;

/**
 * How long resolve may take before the run proceeds without it.
 *
 * Two seconds against a boundary whose hosted p50 is 11.6 seconds and p99 18.7. That is
 * not a mismatch: the prefetch is fired at open and awaited at the first model call, so
 * the budget covers the residue after the overlap rather than the whole round trip.
 */
export const DEFAULT_RESOLVE_TIMEOUT_MS = 2_000;

/** What this client tells the boundary it can do, instead of being inferred from a
 * version number. The boundary reads these tokens out of the User-Agent, so a third
 * product needs no version floor, no constant and no migration to be believed. */
export const CAPABILITY_RECEIPT = "receipt";
export const CAPABILITY_DELIVERY = "delivery";
export const CAPABILITY_READONLY_CLOSE = "readonly-close";

export const DEFAULT_CAPABILITIES: readonly string[] = [
  CAPABILITY_RECEIPT,
  CAPABILITY_DELIVERY,
  CAPABILITY_READONLY_CLOSE,
];

export interface ClientOptions {
  readonly apiKey?: string;
  readonly baseUrl?: string;
  /** The host this seat is attached to: `ai-sdk`, `anthropic-sdk`, `openai-sdk`. Whether
   * a receipt can exist at all is a property of the host, not of this library, so a
   * version alone would report a host that can never send one as ready for the credit
   * rules that require it. */
  readonly clientHost?: string;
  readonly clientCapabilities?: readonly string[];
  readonly resolveTimeoutMs?: number;
  readonly writeTimeoutMs?: number;
  readonly maxWriteRetries?: number;
  readonly retryBackoffMs?: number;
  /** Opt in to the on-disk outbox. Off by default; see {@link DurableOutbox}. */
  readonly durableQueueDir?: string;
  /** Deliver writes inline instead of scheduling them. For a host with no guarantee of
   * a process outliving the scheduling call. */
  readonly isSynchronousWrites?: boolean;
  readonly breaker?: ResolveBreaker;
  readonly fetch?: typeof fetch;
  readonly onDiagnostic?: (message: string) => void;
}

export interface LearningClient {
  resolve(request: ResolveRequest): Promise<ResolvedContext>;
  observe(request: { identity: AgentIdentity; episode: Episode }): Promise<void>;
  reinforce(request: ReinforceRequest): Promise<ReinforceResult>;
  decline(request: DeclineRequest): Promise<ReinforceResult>;
  drain(timeoutMs?: number): Promise<void>;
  replayDurableQueue(): Promise<number>;
  close(timeoutMs?: number): Promise<void>;
}

export interface ResolveRequest {
  readonly identity: AgentIdentity;
  readonly runId: string;
  readonly goal: string;
  readonly availableTools?: readonly ToolSpec[];
  readonly maxLearnings?: number;
  readonly sourceFramework?: string;
  /** A resolve retry without one double-records the recall, so the field is required of
   * any caller that retries rather than optional with a warning. */
  readonly resolveIdempotencyKey?: string;
}

export interface ReinforceRequest {
  readonly identity: AgentIdentity;
  readonly episode: Episode;
  readonly isOrgPromotionAllowed?: boolean;
  readonly contextReceipt?: string | null;
  readonly isDelivered?: boolean;
  readonly recallOutcome?: string | null;
  /** What the turn did with the obligations it was offered, closed at the loop level. */
  readonly obligationOutcomes?: readonly ReportedObligationOutcome[];
}

export interface DeclineRequest {
  readonly identity: AgentIdentity;
  readonly runId: string;
  readonly reason: string;
  readonly isDelivered?: boolean;
  readonly recallOutcome?: string | null;
  readonly sourceFramework?: string;
  /** Accepted here on the same terms as on reinforce: a turn that resolved an obligation and
   * learned nothing is still a turn that resolved an obligation. */
  readonly obligationOutcomes?: readonly ReportedObligationOutcome[];
}

/**
 * Add the `obligation_outcomes` body field, and only when there is something to report.
 *
 * Omitted rather than sent as an empty array, because the field is nullable server-side and a
 * request that carries none is the overwhelmingly common one. Sending `[]` would put a key in
 * every write body for the sake of the rare call that uses it.
 */
function addObligationOutcomes(
  body: Record<string, unknown>,
  outcomes: readonly ReportedObligationOutcome[] | undefined,
): void {
  if (outcomes === undefined || outcomes.length === 0) return;
  body["obligation_outcomes"] = outcomes.map(reportedObligationOutcomePayload);
}

function sanitiseToken(value: string): string {
  return [...value.trim().toLowerCase()]
    .filter((character) => /[a-z0-9-]/.test(character))
    .join("");
}

/**
 * Reject a non-HTTPS base URL so the API key cannot leak over cleartext. Localhost is an
 * explicit escape hatch for local proxies and tests.
 */
const LOCAL_HOSTS: ReadonlySet<string> = new Set(["localhost", "127.0.0.1", "[::1]", "::1"]);

function requireSecureBaseUrl(baseUrl: string): void {
  if (baseUrl.startsWith("https://")) return;
  // Parsed, not prefix-matched. `startsWith("http://localhost")` also admits
  // `http://localhost.attacker.example`, which is a different host entirely, and this
  // client attaches the API key to every request it makes. The escape hatch is for a local
  // proxy, so it has to mean the local host and nothing that merely begins with its name.
  let host = "";
  try {
    host = new URL(baseUrl).hostname;
  } catch {
    host = "";
  }
  if (LOCAL_HOSTS.has(host)) return;
  throw new Error(
    `Hyperstruck base URL must be https:// (got ${JSON.stringify(baseUrl)}); the API key ` +
      "would otherwise be sent in cleartext. Use https, or http://localhost for local " +
      "development.",
  );
}

/**
 * A 4xx means the payload itself is bad, so a retry cannot help and the write is dropped
 * rather than re-queued forever. Counted separately from transient failures so a caller
 * can tell a rejected payload from an unreachable boundary.
 */
class TerminalWriteError extends Error {
  override name = "TerminalWriteError";
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class HostedLearningClient implements LearningClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly clientHost: string;
  private readonly capabilities: readonly string[];
  private readonly resolveTimeoutMs: number;
  private readonly writeTimeoutMs: number;
  private readonly maxWriteRetries: number;
  private readonly retryBackoffMs: number;
  private readonly isSynchronousWrites: boolean;
  private readonly breaker: ResolveBreaker;
  private readonly outbox: DurableOutbox | null;
  private readonly fetchImpl: typeof fetch;
  private readonly onDiagnostic: (message: string) => void;
  /** Bounded rather than unbounded, so a burst of closing runs cannot open one socket
   * per run against a boundary that is already the reason they are queueing. */
  private readonly queue = new PQueue({ concurrency: 8 });

  resolves = 0;
  writesDelivered = 0;
  writesFailed = 0;
  writesTerminalFailed = 0;
  lastWriteError: string | null = null;

  constructor(options: ClientOptions = {}) {
    const apiKey = options.apiKey ?? process.env["HYPERSTRUCK_API_KEY"];
    if (!apiKey) {
      throw new Error(
        "HostedLearningClient requires an API key: pass apiKey, or set " +
          "HYPERSTRUCK_API_KEY.",
      );
    }
    this.apiKey = apiKey;
    this.baseUrl = (
      options.baseUrl ??
      process.env["HYPERSTRUCK_BASE_URL"] ??
      DEFAULT_BASE_URL
    ).replace(/\/+$/, "");
    requireSecureBaseUrl(this.baseUrl);
    this.clientHost = sanitiseToken(options.clientHost ?? "");
    this.capabilities = (options.clientCapabilities ?? DEFAULT_CAPABILITIES)
      .map(sanitiseToken)
      .filter((token) => token.length > 0);
    this.resolveTimeoutMs = options.resolveTimeoutMs ?? DEFAULT_RESOLVE_TIMEOUT_MS;
    this.writeTimeoutMs = options.writeTimeoutMs ?? DEFAULT_WRITE_TIMEOUT_MS;
    this.maxWriteRetries = Math.max(1, options.maxWriteRetries ?? 3);
    this.retryBackoffMs = options.retryBackoffMs ?? 500;
    this.isSynchronousWrites = options.isSynchronousWrites ?? false;
    // Emitting by default. A write dropped after its retries and an outbox that refused a
    // read-only directory are both states a customer has to be able to see: the first
    // loses an episode, the second silently reverts durability they opted into. A no-op
    // default made both invisible.
    this.onDiagnostic = options.onDiagnostic ?? defaultDiagnostic;
    // Process-wide and keyed by boundary, not per instance: the whole value is that the
    // second run does not repeat the first one's timeout, and a service constructing a
    // client per request would never see a second failure on a per-instance breaker.
    this.breaker = options.breaker ?? breakerFor(this.baseUrl);
    this.outbox = options.durableQueueDir
      ? DurableOutbox.open(options.durableQueueDir, this.onDiagnostic)
      : null;
    this.fetchImpl = options.fetch ?? globalThis.fetch;
  }

  /**
   * The declared User-Agent the boundary's receipt gate reads.
   *
   * `hyperstruck-js/0.12.0 (host=ai-sdk; caps=receipt,delivery,readonly-close)`. The
   * version is load bearing rather than decoration: without it a stale client is
   * indistinguishable from a current one server-side, so a bad release cannot be
   * attributed or filtered. The host segment carries the other half, and the capability
   * list carries the third: a client that says what it can do is read at its word rather
   * than having its version sniffed for the answer.
   */
  get userAgent(): string {
    const segments: string[] = [];
    if (this.clientHost) segments.push(`host=${this.clientHost}`);
    if (this.capabilities.length > 0) segments.push(`caps=${this.capabilities.join(",")}`);
    const product = `${CLIENT_PRODUCT}/${VERSION}`;
    return segments.length > 0 ? `${product} (${segments.join("; ")})` : product;
  }

  private headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      "User-Agent": this.userAgent,
      "Content-Type": "application/json",
    };
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  /**
   * Recall for one run. Fails open on everything: the caller proceeds with no context.
   *
   * The breaker is asked *before* the call, not after, because the point of it is that a
   * run reached by a degraded boundary pays nothing rather than paying the timeout again.
   * A run turned away here fails open exactly as a timed-out one does and reports
   * `resolve_failed`, so the seat's taxonomy still separates a broken deployment from a
   * cold corpus.
   *
   * No retry is added around this call, deliberately: a resolve retry without a
   * `resolve_idempotency_key` double-records the recall, and the breaker's job is to make
   * the *first* attempt cheap rather than to make more of them.
   */
  async resolve(request: ResolveRequest): Promise<ResolvedContext> {
    const body: Record<string, unknown> = {
      ...identityPayload(request.identity),
      run_id: request.runId,
      goal: request.goal,
      source_framework: request.sourceFramework ?? "",
      available_tools: (request.availableTools ?? []).map(toolPayload),
      max_learnings: request.maxLearnings ?? DEFAULT_MAX_LEARNINGS,
      model_context_window: null,
    };
    if (request.resolveIdempotencyKey !== undefined) {
      body["resolve_idempotency_key"] = request.resolveIdempotencyKey;
    }

    this.breaker.beforeRequest();
    let response: Response;
    try {
      response = await this.post("/resolve", body, this.resolveTimeoutMs);
    } catch (error) {
      this.breaker.recordFailure();
      throw error;
    }
    if (!response.ok) {
      // A 4xx is the caller's payload and says nothing about the boundary's health, so it
      // must not trip a breaker that would then withhold recall from every other run in
      // the process for a mistake local to this one.
      if (response.status >= 500) this.breaker.recordFailure();
      throw new Error(`hosted resolve failed with ${response.status}`);
    }
    this.breaker.recordSuccess();
    this.resolves += 1;
    return resolvedContextFromResponse(await response.json());
  }

  async answer<D extends AnswerDetail = "answer">(request: {
    agentId: string;
    question: string;
    detail?: D;
    idempotencyKey?: string;
  }): Promise<Answer<D>> {
    const headers: Record<string, string> = { ...this.headers() };
    if (request.idempotencyKey !== undefined) headers["Idempotency-Key"] = request.idempotencyKey;
    const response = await this.send(`/agents/${request.agentId}/answer`, {
      method: "POST",
      headers,
      body: JSON.stringify({ question: request.question, detail: request.detail ?? "answer" }),
    });
    return new Answer<D>((await response.json()) as AnswerAt<D>, (path) => this.storedAnswer(path));
  }

  private async storedAnswer(path: string): Promise<unknown> {
    const response = await this.send(path, { method: "GET", headers: this.headers() });
    return await response.json();
  }

  private async send(path: string, init: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ANSWER_TIMEOUT_MS);
    try {
      const response = await this.fetchImpl(this.url(path), { ...init, signal: controller.signal });
      if (!response.ok) throw new Error(`hosted answer failed with ${response.status}`);
      return response;
    } finally {
      clearTimeout(timer);
    }
  }

  async observe(request: { identity: AgentIdentity; episode: Episode }): Promise<void> {
    await this.scheduleWrite("/observe", {
      ...identityPayload(request.identity),
      episode: redactEpisodePayload(episodePayload(request.episode)),
    });
  }

  /**
   * Credit the learnings the run used, and read back the per-offered-id presence relation.
   *
   * `isDelivered` and `recallOutcome` say whether the recall reached the model at all,
   * and when it did not, why. Without them an absent receipt has two readings: a run that
   * was shown its learnings and lost the evidence, and a run that was never shown them,
   * and the boundary can only assume the first.
   *
   * The returned presence outcomes are the boundary's own verdict per offered id. They
   * come back empty against a deployment that does not yet return them, and the seat's
   * local verbatim check, which is labelled a heuristic precisely because it is not this,
   * stands in until they arrive.
   *
   * `obligationOutcomes` reports what the turn did with the obligations it was offered,
   * closing them at the loop level rather than one call at a time. Each one comes back with
   * its own disposition, because a batch can partly apply and a host that cannot tell a
   * recorded close from a discarded one has to assume the worse of the two.
   */
  async reinforce(request: ReinforceRequest): Promise<ReinforceResult> {
    const body: Record<string, unknown> = {
      ...identityPayload(request.identity),
      episode: redactEpisodePayload(episodePayload(request.episode)),
      is_org_promotion_allowed: request.isOrgPromotionAllowed ?? false,
      context_receipt: request.contextReceipt ?? null,
    };
    if (request.isDelivered !== undefined) body["is_delivered"] = request.isDelivered;
    if (request.recallOutcome != null) body["recall_outcome"] = request.recallOutcome;
    addObligationOutcomes(body, request.obligationOutcomes);
    const response = await this.scheduleWrite("/reinforce", body);
    return response === null ? EMPTY_WRITE_RESULT : reinforceResultFromResponse(response);
  }

  /**
   * Close a run whose turn ended with nothing worth learning.
   *
   * The terminal alternative to observe and reinforce, not a failure path. A run left
   * unclosed is indistinguishable from a host that stopped writing back, and it sits open
   * holding its resolve reservation until the server's reclaim sweep notices.
   *
   * The result's presence half is always empty: a turn nothing was learned from has no credit
   * verdict to read back. Its closure half carries a disposition per reported outcome.
   */
  async decline(request: DeclineRequest): Promise<ReinforceResult> {
    if (!request.runId) {
      throw new Error("decline requires the run_id supplied to resolve");
    }
    if (!DECLINE_REASONS.has(request.reason)) {
      throw new Error(
        `reason must be one of ${[...DECLINE_REASONS].sort().join(", ")}, got ` +
          JSON.stringify(request.reason),
      );
    }
    const body: Record<string, unknown> = {
      ...identityPayload(request.identity),
      run_id: request.runId,
      reason: request.reason,
      is_delivered: request.isDelivered ?? false,
      source_framework: request.sourceFramework ?? "",
    };
    if (request.recallOutcome != null) body["recall_outcome"] = request.recallOutcome;
    addObligationOutcomes(body, request.obligationOutcomes);
    const response = await this.scheduleWrite("/decline", body);
    return response === null ? EMPTY_WRITE_RESULT : reinforceResultFromResponse(response);
  }

  /**
   * Fire-and-forget a write so the host run is never blocked.
   *
   * In synchronous mode the write is delivered inline instead. That mode exists for a
   * host with no guarantee of a process outliving the scheduling call: there, a scheduled
   * task dies at teardown and the episode is lost with no error anywhere, so the customer
   * sees a corpus that never fills and nothing to diagnose from. Paying the latency is
   * the lesser cost, and it is the caller's explicit choice.
   *
   * The response body is returned only in synchronous mode. Asynchronously there is
   * nobody left to hand it to by the time it arrives, and inventing a promise that
   * resolves after the caller has gone is how a "the handle has more" asymmetry starts.
   */
  private async scheduleWrite(
    path: string,
    body: Record<string, unknown>,
  ): Promise<unknown | null> {
    const parked = this.outbox?.park(path, body) ?? null;
    if (this.isSynchronousWrites) {
      return await this.deliverWrite(path, body, parked);
    }
    // Guarded at the boundary of the floating task. `deliver` calls `onDiagnostic`, which
    // is customer code; a throw from it inside a task nobody awaits becomes an unhandled
    // rejection and, on a host that treats those as fatal, takes the process down over a
    // log line.
    void this.queue.add(() => this.deliverWrite(path, body, parked)).catch(() => undefined);
    return null;
  }

  /**
   * Deliver one write, then send again any obligation outcome that came back busy.
   *
   * Busy means the run lock was held and the close was never attempted, so it is the one
   * disposition safe to send again, and an asynchronous caller never sees the response that
   * says so. Only the busy outcomes are resent, and a resend's results replace the busy
   * entries in the response the caller is handed.
   */
  private async deliverWrite(
    path: string,
    body: Record<string, unknown>,
    parked: string | null,
  ): Promise<unknown | null> {
    let response = await this.deliver(path, body, parked);
    for (let attempt = 0; attempt < BUSY_CLOSURE_RESENDS; attempt += 1) {
      const busy = new Set(
        obligationClosuresFromResponse(response)
          .filter((closure) => closure.disposition === CLOSURE_BUSY)
          .map((closure) => canonicalId(closure.id)),
      );
      const outcomes = (
        (body["obligation_outcomes"] as readonly { id: string }[] | undefined) ?? []
      ).filter((outcome) => busy.has(canonicalId(outcome.id)));
      if (outcomes.length === 0) break;
      await sleep(backoffDelayMs(this.retryBackoffMs, attempt));
      const resent = await this.deliver(path, { ...body, obligation_outcomes: outcomes }, null);
      if (resent === null || typeof resent !== "object") break;
      response = withResentClosures(response, resent as Record<string, unknown>);
    }
    return response;
  }

  /**
   * Deliver one write with bounded retry and jittered backoff.
   *
   * At-least-once is safe: the platform dedupes by run id, so a retried write is a
   * server-side no-op. After the bounded attempts the write is dropped and counted, never
   * thrown, since there is nothing left to block.
   *
   * A durably parked write is released on delivery and on a terminal rejection, and left
   * on disk otherwise, so an outage that outlives the process is drained by the next start
   * rather than lost with it. A 4xx is released rather than kept because it fails
   * identically forever, and keeping it would make every later drain re-send a payload the
   * boundary has already refused.
   */
  private async deliver(
    path: string,
    body: Record<string, unknown>,
    parked: string | null,
  ): Promise<unknown | null> {
    let lastError: unknown = null;
    for (let attempt = 0; attempt < this.maxWriteRetries; attempt += 1) {
      try {
        const response = await this.post(path, body, this.writeTimeoutMs);
        if (!response.ok) {
          const message = `write to ${path} rejected with ${response.status}`;
          if (response.status >= 400 && response.status < 500) {
            throw new TerminalWriteError(response.status, message);
          }
          throw new Error(message);
        }
        this.writesDelivered += 1;
        this.outbox?.release(parked);
        return await response.json().catch(() => null);
      } catch (error) {
        lastError = error;
        if (error instanceof TerminalWriteError) break;
        if (attempt + 1 < this.maxWriteRetries) {
          await sleep(backoffDelayMs(this.retryBackoffMs, attempt));
        }
      }
    }
    const isTerminal = lastError instanceof TerminalWriteError;
    if (isTerminal) {
      this.outbox?.release(parked);
      this.writesTerminalFailed += 1;
    }
    this.writesFailed += 1;
    this.lastWriteError = String(lastError);
    this.onDiagnostic(
      `Hyperstruck write to ${path} dropped after ${this.maxWriteRetries} attempts: ` +
        String(lastError),
    );
    return null;
  }

  private async post(
    path: string,
    body: Record<string, unknown>,
    timeoutMs: number,
  ): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await this.fetchImpl(this.url(path), {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timer);
    }
  }

  /** Await all in-flight background writes, for shutdown and for tests. */
  async drain(timeoutMs = 30_000): Promise<void> {
    await Promise.race([this.queue.onIdle(), deadline(timeoutMs)]);
  }

  /**
   * Re-send every write parked on disk, and return how many landed.
   *
   * Called by a host at start-up, which is the moment the durable queue exists for: a
   * process restarted during a boundary outage has episodes on disk that no in-memory
   * queue could have survived. Delivery is at-least-once and the platform dedupes by run
   * id, so replaying a write that did in fact land is a server-side no-op.
   */
  async replayDurableQueue(): Promise<number> {
    if (this.outbox === null) return 0;
    let delivered = 0;
    let before = this.writesDelivered;
    for (const write of this.outbox.pending()) {
      // The endpoint comes off disk, and a file on disk is not trusted input by the time it
      // is read back after a restart: a tampered record naming `//evil.example/x` would
      // make `url()` produce a URL on another host, and every request this client makes
      // carries the API key.
      if (!REPLAYABLE_ENDPOINTS.has(write.endpoint)) {
        this.onDiagnostic(
          `Hyperstruck durable outbox refusing a parked write to an unknown endpoint ` +
            `${JSON.stringify(write.endpoint)}; dropping it rather than sending ` +
            "credentials to it",
        );
        this.outbox.release(write.path);
        continue;
      }
      await this.deliverWrite(write.endpoint, write.body, write.path);
      if (this.writesDelivered > before) {
        delivered += 1;
        before = this.writesDelivered;
      }
    }
    return delivered;
  }

  async close(timeoutMs = 30_000): Promise<void> {
    await this.drain(timeoutMs);
  }
}

/**
 * Where a diagnostic goes when the customer registered none.
 *
 * stderr, one line, because stdout belongs to the host's own program and a library writing
 * there can corrupt a pipeline.
 */
function defaultDiagnostic(message: string): void {
  try {
    process.stderr.write(`${message}\n`);
  } catch {
    // A host that replaced stderr must not lose its run over a log line.
  }
}

/**
 * A real wait, holding the loop open while it runs.
 *
 * Used for the retry backoff, which is work in progress: a write between attempts is
 * pending, not idle. This was briefly unrefed along with the deadline below, and on Node
 * 22.18 that let the test runner tear down mid-retry and cancel eight tests that had not
 * finished. In a customer's process the same unref would have dropped a retry at exit.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

/**
 * A deadline that must never be the reason a process stays alive.
 *
 * Only for racing a wait that may already be over: `drain`'s timeout and the close path's
 * prefetch join. Losing this timer costs nothing, because whatever it was racing has its
 * own completion; keeping the loop open for it would make a short-lived host hang on a
 * deadline it has already stopped caring about.
 */
function deadline(ms: number): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    if (typeof timer === "object" && timer !== null && "unref" in timer) {
      (timer as { unref: () => void }).unref();
    }
  });
}
