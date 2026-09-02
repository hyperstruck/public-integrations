/**
 * `@hyperstruck/core`: one run-scoped middleware seat, attachable from any TypeScript
 * runtime.
 *
 * Server-side only. Tenancy rides entirely on the API key with `org_id` resolved
 * server-side, so a browser entry point would put the tenant boundary in a bundle. The
 * package declares no browser condition in its `exports`, which makes that a resolution
 * failure at a bundler's build time rather than a warning in a document nobody reads.
 */

export { HostedLearningClient, DEFAULT_BASE_URL } from "./client.ts";
export { Answer } from "./answers.ts";
export type { AnswerAt, AnswerDetail } from "./answers.ts";
export type {
  ClientOptions,
  DeclineRequest,
  LearningClient,
  ReinforceRequest,
  ResolveRequest,
} from "./client.ts";
export {
  CAPABILITY_DELIVERY,
  CAPABILITY_READONLY_CLOSE,
  CAPABILITY_RECEIPT,
  DEFAULT_CAPABILITIES,
} from "./client.ts";

export type { AgentIdentity } from "./identity.ts";

export { hyperstruckMiddleware, AI_SDK_HOST } from "./aiSdk.ts";
export type { HyperstruckMiddleware, MiddlewareOptions } from "./aiSdk.ts";
export { withRun } from "./withRun.ts";
export type { WithRunOptions } from "./withRun.ts";

export { conversationRunKey, otelResolvers } from "./otel.ts";

export {
  DeclarationRegistry,
  declarationFromSchema,
  join as joinSensitivity,
  SECRET,
  SHAREABLE,
  subjectArgKey,
  USER_DATA,
} from "./runtime/declarations.ts";
export type { ToolDeclaration } from "./runtime/declarations.ts";

export {
  LedgerClosedError,
  LedgerStateError,
  RunLedger,
  offeredAndDeliveredShelf,
  renderConfirmedShelf,
} from "./runtime/ledger.ts";
export type { Shelf } from "./runtime/ledger.ts";

export {
  DELIVERED_REFORMATTED,
  DELIVERED_VERBATIM,
  flattenParams,
  locateReceipt,
  receiptOutcome,
  UNRESOLVED,
} from "./runtime/receipt.ts";
export type { ReceiptLocation, ShelfFidelity } from "./runtime/receipt.ts";

export {
  CircuitOpenError,
  DurableOutbox,
  ResolveBreaker,
  backoffDelayMs,
  breakerFor,
  resetBreakers,
} from "./runtime/resilience.ts";

export {
  CompositeScanner,
  NullScanner,
  scanAndScrub,
} from "./runtime/scanning.ts";
export type { ContentScanner, Finding } from "./runtime/scanning.ts";

export {
  CLOSE_TRIGGER_ABANDONED,
  CLOSE_TRIGGER_EXPLICIT,
  CLOSE_TRIGGER_NO_TOOL_CALLS,
  CLOSE_TRIGGER_PROCESS_EXIT,
  DISPOSITION_DECLINED,
  DISPOSITION_EVICTED,
  DISPOSITION_OBSERVED,
  DISPOSITION_REINFORCED,
  DISPOSITION_WITHHELD,
  DISPOSITION_WRITE_FAILED,
  HyperstruckRun,
  OUTCOME_DELIVERED,
  OUTCOME_RECALL_MISSING,
  OUTCOME_RECALL_UNCLAIMED,
  OUTCOME_RESOLVE_EMPTY,
  OUTCOME_RESOLVE_FAILED,
  RunRegistry,
  RunSeat,
  newRunId,
  recallOutcome,
  reportToJson,
} from "./runtime/run.ts";
export type { RunReport, RunSeatOptions, ShelfReport } from "./runtime/run.ts";

export { resolveRunKey, runWithKey } from "./runtime/runKey.ts";
export type { RunKey, RunKeyResolver } from "./runtime/runKey.ts";

export { declineReason, shouldObserve } from "./turnGate.ts";

export { redactEpisodePayload, scrubStrings, REDACTION_MARKER } from "./redaction.ts";

export {
  CLOSURE_APPLIED,
  CLOSURE_BUSY,
  combineInjectionBlocks,
  DECLINE_REASONS,
  publishedDeclineReasons,
  REASON_BELOW_MATERIAL_THRESHOLD,
  REASON_EMPTY_OFFER,
  REASON_NO_GOAL,
  REASON_NO_TOOL_CALLS,
  REASON_READONLY_CLOSE,
  REASON_UNEVIDENCED_OUTCOME,
} from "./wire.ts";
export type {
  Episode,
  ObligationClosureResult,
  PresenceOutcome,
  ReinforceResult,
  ReportedObligationOutcome,
  ResolvedContext,
  StepRecord,
  ToolSpec,
} from "./wire.ts";

export { CLIENT_PRODUCT, VERSION } from "./version.ts";
