/**
 * Finding our own block in the params as they were actually sent.
 *
 * This is the artefact that makes a non-Claude-Code customer creditable at all, and the
 * whole of its value rests on one distinction. Remembering where we put the block and
 * handing that back is an echo: it asserts the very thing a receipt exists to prove, and
 * it would report a rendered learning just as confidently for a run whose trimming
 * middleware had emptied the block on the way to the model. Searching the sent params
 * for our own lines is an observation. The LangGraph seat sends no receipt precisely
 * because, sitting above the composition stack, an echo is the only artefact it could
 * produce.
 *
 * **The disclosure cost is zero, and that is enforced by construction rather than
 * asserted.** The receipt is assembled from the payload lines that matched lines *we
 * authored*, and never from the lines between them. An earlier version of the Python
 * original took the span from the first match to the last and returned everything
 * inside it, which is a different thing wearing the same description: a model quoting
 * one of our advice lines back, which is the ordinary case for an agent restating
 * guidance it was given, put a match early and our real block late, and the span
 * swallowed every message in between. A probe of that version produced a receipt
 * carrying a patient record, a card number and a password. Nothing between two matches
 * is ours, so nothing between two matches goes in.
 *
 * **An echo is not an exposure.** For the same reason, a line counts as delivered only
 * when it appears inside the region where our block actually sits. A tool result or a
 * model turn that quotes one of our lines elsewhere in the history is not evidence that
 * the system block survived; treating it as evidence would be a positive claim of
 * exposure drawn from the model's own output, which is the one assertion this lane must
 * never make.
 *
 * **This does not re-implement the server's matcher and must not grow into one.** Core's
 * receipt module owns the judgement that decides credit, and a second copy would drift
 * into two answers about the same run. What lives here is a *local* fidelity report for
 * the customer's own eyes: it tells them their own trimming middleware emptied our
 * block, without a support ticket. Where the two disagree, the server's answer is the
 * one that decides anything, and the run report is amended with it when the queued
 * reinforce drains.
 */

/**
 * Leading list markers a host may add, replace or renumber.
 *
 * Stripped as whole tokens and never as a character class: trimming a set of characters
 * eats the minus sign off a continuation line that a hard-wrapping host broke on
 * `range = -5 to -10`, and that line then never matches again. The rule is copied from
 * Core's own stripper for exactly this reason.
 */
const LIST_MARKER = /^([-*•–—]|\d+[.)]|[a-zA-Z][.)])$/;

/**
 * How many unrelated lines may sit between two of ours before we stop believing they are
 * the same block. Our block is contiguous when we send it, so any gap at all is the
 * host's doing: a few lines of its own framing is ordinary, and a hundred means the
 * second match is somewhere else in the conversation and belongs to a different region.
 */
export const MAX_INTERLEAVE_LINES = 8;

export const DELIVERED_VERBATIM = "delivered_verbatim";
export const DELIVERED_REFORMATTED = "delivered_reformatted";
export const UNRESOLVED = "unresolved";

export const FIDELITY_OUTCOMES: ReadonlySet<string> = new Set([
  DELIVERED_VERBATIM,
  DELIVERED_REFORMATTED,
  UNRESOLVED,
]);

/**
 * Collapse whitespace, so a host that re-wraps or re-indents still matches.
 *
 * A host that reflows our block to its own column width still showed the model the
 * learning. Reading that as a drop would be a positive claim of non-exposure drawn from
 * formatting alone, which is the one thing this lane must never assert.
 */
function normalise(text: string): string {
  return text.split(/\s+/).filter((part) => part.length > 0).join(" ");
}

/** One line, normalised and stripped of the markers a rendered block begins with. */
function stripMarkers(line: string): string {
  const tokens = normalise(line).split(" ").filter((token) => token.length > 0);
  let index = 0;
  while (index < tokens.length && LIST_MARKER.test(tokens[index] as string)) index += 1;
  return tokens.slice(index).join(" ");
}

/** The lines of a block that carry content, in order, marker-stripped. */
function significantLines(text: string | null | undefined): string[] {
  if (!text) return [];
  const lines: string[] = [];
  for (const line of text.split("\n")) {
    const stripped = stripMarkers(line);
    if (stripped) lines.push(stripped);
  }
  return lines;
}

/**
 * How much of one shelf's block survived the journey to the model.
 *
 * `outcome` is stated per shelf rather than per offered id, and the field name says so
 * on purpose. The rendered block carries no id markers: the boundary returns the text
 * and the offered id sets as two separate things, and nothing in the render says which
 * line came from which learning. A per-id verdict derived from a per-shelf observation
 * would be a precision this seat does not have, presented as one it does, so the ids are
 * listed beside the verdict they share instead of each being handed one of its own.
 * Recovering true per-id fidelity needs id markers in the render, which is a boundary
 * change and not this seat's to make; the authoritative per-id relation comes back on
 * the reinforce response instead.
 */
export interface ShelfFidelity {
  readonly name: string;
  readonly outcome: string;
  readonly offeredIds: readonly string[];
  readonly linesExpected: number;
  readonly linesFound: number;
  readonly missingLines: readonly string[];
}

export function isShelfDelivered(shelf: ShelfFidelity): boolean {
  return shelf.outcome !== UNRESOLVED;
}

/**
 * Our block as it was found in the sent params, and how intact it was.
 *
 * `text` holds the payload's own rendering of the lines we authored, in payload order,
 * and nothing else. It is therefore evidence about what the host did to our block (a
 * line dropped, a bullet renumbered, a block reflowed or emptied) while being incapable
 * of carrying content we did not write.
 *
 * `null` means not one line of ours was found in a plausible block region, which is the
 * honest artefact for a block that never reached the model: an empty receipt is not the
 * same as no receipt, and sending an empty string would be read as an exposure that
 * matched nothing.
 */
export interface ReceiptLocation {
  readonly text: string | null;
  readonly shelves: readonly ShelfFidelity[];
}

export function isReceiptPresent(receipt: ReceiptLocation): boolean {
  return receipt.text !== null;
}

/**
 * The run's fidelity, taken as the worst any shelf reported.
 *
 * Worst rather than best, and rather than an average. The reader's question is whether
 * anything went wrong on the way to the model, and a run that delivered its advice
 * verbatim while its facts vanished has something wrong with it.
 */
export function receiptOutcome(receipt: ReceiptLocation | null): string {
  if (receipt === null) return UNRESOLVED;
  const outcomes = new Set(
    receipt.shelves.filter((shelf) => shelf.linesExpected > 0).map((shelf) => shelf.outcome),
  );
  if (outcomes.size === 0) return UNRESOLVED;
  for (const candidate of [UNRESOLVED, DELIVERED_REFORMATTED, DELIVERED_VERBATIM]) {
    if (outcomes.has(candidate)) return candidate;
  }
  return UNRESOLVED;
}

export interface ShelfInput {
  readonly name: string;
  readonly text: string | null;
  readonly offeredIds: readonly string[];
}

/**
 * Find where our blocks sit in `sentPayload`, and grade each shelf.
 *
 * Matching is confined to the cluster of the payload where our lines actually
 * congregate, so a stray echo elsewhere in the message history neither credits a shelf
 * nor drags unrelated content into the receipt.
 */
export function locateReceipt(
  sentPayload: string,
  shelves: readonly ShelfInput[],
): ReceiptLocation {
  const sentLines = sentPayload.split("\n");
  const strippedSent = sentLines.map(stripMarkers);

  const expectedByShelf = shelves.map((shelf) => ({
    ...shelf,
    expected: significantLines(shelf.text),
  }));
  const ours = new Set(expectedByShelf.flatMap((shelf) => shelf.expected));

  const region = blockRegion(strippedSent, ours);
  // Only lines inside the region count, and only they may appear in the receipt. Both
  // restrictions come from the same rule: a match outside the block our own lines form is
  // somebody else repeating us, and neither credits a shelf nor belongs in the artefact.
  const present = new Set(region.map(([, line]) => line));
  const receiptLines = region.map(([index]) => sentLines[index] as string);

  const graded: ShelfFidelity[] = expectedByShelf.map((shelf) => {
    const found = shelf.expected.filter((line) => present.has(line));
    const missing = shelf.expected.filter((line) => !present.has(line));
    let outcome: string;
    if (shelf.expected.length === 0 || found.length === 0) {
      outcome = UNRESOLVED;
    } else if (missing.length > 0) {
      outcome = DELIVERED_REFORMATTED;
    } else {
      outcome = verbatimOrReformatted(sentPayload, shelf.text);
    }
    return {
      name: shelf.name,
      outcome,
      offeredIds: [...shelf.offeredIds],
      linesExpected: shelf.expected.length,
      linesFound: found.length,
      missingLines: missing,
    };
  });

  return {
    text: receiptLines.length === 0 ? null : receiptLines.join("\n"),
    shelves: graded,
  };
}

/**
 * The cluster of payload lines that is our block, as `[index, stripped]` pairs.
 *
 * Every payload line matching something we authored is a candidate. They are grouped
 * into clusters separated by more than {@link MAX_INTERLEAVE_LINES} unrelated lines, and
 * the richest cluster wins, measured by how many *distinct* lines of ours it holds
 * rather than by how many matches it has: a tool result repeating one line ten times
 * must not outrank the block itself.
 *
 * Ties go to the earlier cluster, which is arbitrary and stated so rather than left to
 * be discovered. A tie means two regions carry equally much of our block, and no
 * evidence here distinguishes them.
 */
function blockRegion(
  strippedSent: readonly string[],
  ours: ReadonlySet<string>,
): [number, string][] {
  const candidates: [number, string][] = [];
  strippedSent.forEach((line, index) => {
    if (line && ours.has(line)) candidates.push([index, line]);
  });
  if (candidates.length === 0) return [];

  const clusters: [number, string][][] = [[candidates[0] as [number, string]]];
  for (const candidate of candidates.slice(1)) {
    const current = clusters[clusters.length - 1] as [number, string][];
    const last = current[current.length - 1] as [number, string];
    if (candidate[0] - last[0] > MAX_INTERLEAVE_LINES + 1) {
      clusters.push([]);
    }
    (clusters[clusters.length - 1] as [number, string][]).push(candidate);
  }

  let best = clusters[0] as [number, string][];
  let bestSize = new Set(best.map(([, line]) => line)).size;
  for (const cluster of clusters.slice(1)) {
    const size = new Set(cluster.map(([, line]) => line)).size;
    if (size > bestSize) {
      best = cluster;
      bestSize = size;
    }
  }
  return best;
}

/**
 * Whether every line survived unchanged, or survived only after normalising.
 *
 * Every line is present either way; the difference is whether the host reflowed,
 * re-indented or renumbered on the way. Both are deliveries and neither costs credit, so
 * the distinction exists to answer the customer's own question about their stack rather
 * than to gate anything.
 */
function verbatimOrReformatted(sentPayload: string, text: string | null): string {
  return text && sentPayload.includes(text) ? DELIVERED_VERBATIM : DELIVERED_REFORMATTED;
}

/**
 * A model params object nests a few levels: messages, content parts, and the odd blob of
 * provider metadata. Bounded so a cyclic or pathologically nested object cannot turn a
 * diagnostic into a hang on the model-call hot path.
 */
const MAX_FLATTEN_DEPTH = 8;

/**
 * Best-effort flattening of a model SDK's params into searchable text.
 *
 * Model SDKs disagree about the shape of a message list and each of them changes it, so
 * this walks strings, objects and arrays rather than naming any provider's schema. It is
 * deliberately generous: a shape it cannot read contributes nothing, which reads as a
 * block that did not arrive, which is the fail-safe direction for a lane that must never
 * assert an exposure it cannot evidence.
 */
export function flattenParams(params: unknown): string {
  const collected: string[] = [];
  collect(params, collected, 0, new Set());
  return collected.join("\n");
}

function collect(
  value: unknown,
  into: string[],
  depth: number,
  seen: Set<object>,
): void {
  if (depth > MAX_FLATTEN_DEPTH) return;
  if (typeof value === "string") {
    into.push(value);
    return;
  }
  if (value === null || typeof value !== "object") return;
  // A depth cap alone still walks an exponentially wide shared subgraph; the seen set is
  // what makes the bound hold on a params object a host built by reference.
  if (seen.has(value)) return;
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) collect(item, into, depth + 1, seen);
    return;
  }
  for (const item of Object.values(value as Record<string, unknown>)) {
    collect(item, into, depth + 1, seen);
  }
}
