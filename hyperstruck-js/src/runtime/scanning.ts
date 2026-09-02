/**
 * Content scanning as a secondary net over free text, off by default.
 *
 * Free text is where origin labelling under-delivers: a tool returning a meeting
 * transcript has one label and arbitrary content inside it. So a scan may raise a value's
 * sensitivity above what its tool declared. It may never lower it, which is the same
 * lattice join the origin propagation uses, so the two signals compose rather than
 * competing and it fails in the safe direction. A tool declared permissively whose output
 * turns out to carry personal data is the case the net exists for; a tool declared
 * restrictively whose content looks innocuous is not evidence the declaration was wrong.
 *
 * **One interface and one behaviour in both languages; only the shipped adapter differs.**
 * The Python seat bundles a Presidio adapter because Presidio is the mature free option and
 * is Python-first, and the credible Node equivalents are materially thinner: `pii-scan`
 * describes itself as development-grade, Grepture is a hosted gateway rather than a library,
 * and the zero-shot detector family needs a model runtime in process. So this half is a
 * customer-supplied hook until one exists, and shipping a thin detector as a default would
 * be worse than none because it would read as coverage while missing what the net was
 * fitted for.
 *
 * What is *not* asymmetric is the seam. Both languages take the same span shape and apply
 * the same scrubbing policy, so a customer who writes a scanner writes it once and gets the
 * same redaction from it either way. An earlier version had Python taking values and
 * TypeScript taking spans, which meant one seat scrubbed a finding's echoes across the
 * payload and the other did not, from identical detector output, while a parity test
 * asserted the two agreed.
 *
 * A finding is **redacted, not relabelled**. `declared_sensitivity` carries argument
 * labels and a finding in a *result* has nowhere to go in that field, so the span is
 * scrubbed over the package's existing safe traversal and the run reports how many went.
 */

import { scrubStrings } from "../redaction.ts";
import { join, UNDECLARED_SENSITIVITY } from "./declarations.ts";

/** Text shorter than this is not worth scanning and is skipped. */
export const MIN_SCAN_LENGTH = 3;

/**
 * One span a scanner believes is sensitive, and how sensitive it thinks it is.
 *
 * Spans, because that is what every detector produces: Presidio's `RecognizerResult` is
 * `(entity_type, start, end, score)`, and so is the output of any regex or model-based
 * detector worth fitting. The Python seat takes the identical shape, so a customer writing
 * one scanner writes it once.
 *
 * Whether a finding also reaches *other* occurrences of the same value is a separate
 * decision and not the interface's to make. See {@link scanAndScrub}.
 */
export interface Finding {
  readonly start: number;
  readonly end: number;
  /** What was found, e.g. `EMAIL_ADDRESS`. */
  readonly kind: string;
  /** How sensitive, on the boundary's own lattice. Optional, because a detector says what
   * it found and not always how restricted it is; absent, the most restrictive member is
   * assumed, which is the direction the undeclared-argument default takes and for the
   * same reason. */
  readonly label?: string | null;
}

/**
 * The hook a customer fits. Synchronous by design: it runs on the close path where the
 * episode is being assembled, and an async scanner there would either block the close or
 * turn one seam into a queue with its own failure modes.
 */
export interface ContentScanner {
  scan(text: string): readonly Finding[];
}

/** The default. Finds nothing, costs nothing, and exists so the seam is always present. */
export class NullScanner implements ContentScanner {
  scan(): readonly Finding[] {
    return [];
  }
}

/**
 * Several scanners over one text, joined by union.
 *
 * Union rather than intersection, for the same escalate-only reason: a finding one
 * scanner makes and another misses is still a finding, and requiring agreement would
 * make adding a scanner able to *reduce* what is caught.
 */
export class CompositeScanner implements ContentScanner {
  private readonly scanners: readonly ContentScanner[];

  constructor(scanners: Iterable<ContentScanner>) {
    this.scanners = [...scanners];
  }

  scan(text: string): readonly Finding[] {
    const findings: Finding[] = [];
    for (const scanner of this.scanners) {
      try {
        findings.push(...scanner.scan(text));
      } catch {
        // A customer's scanner throwing is their bug, and losing the episode over it
        // would be ours. The other scanners still run and the run reports what was found.
      }
    }
    return findings;
  }
}

export interface ScanResult {
  readonly payload: unknown;
  readonly findingCount: number;
  readonly kinds: readonly string[];
}

export function isScanClean(result: ScanResult): boolean {
  return result.findingCount === 0;
}

export function describeScan(result: ScanResult): string {
  return (
    `${result.findingCount} content scan finding(s) redacted from the result ` +
    `(${[...result.kinds].sort().join(", ")}); the labels a tool declares cover its ` +
    "arguments, so a finding in a result is scrubbed rather than relabelled"
  );
}

function marker(label: string | null | undefined): string {
  // An absent label reads as the most restrictive member rather than as unlabelled: a
  // detector that says what it found without saying how sensitive it is has licensed
  // nothing weaker.
  return `[REDACTED:${label ?? UNDECLARED_SENSITIVITY}]`;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Scan every string in a payload and scrub what was found, over the same safe traversal
 * the declared-value redaction uses.
 *
 * Spans are replaced back to front so an earlier replacement cannot shift the offsets of a
 * later one, and overlapping findings are merged rather than double-replaced. A second
 * pass then reaches the same value where it was echoed into another field, fenced exactly
 * as the declared-value scrubber fences its own.
 */
export function scanAndScrub(
  payload: unknown,
  scanner: ContentScanner | null | undefined,
): ScanResult {
  if (scanner == null || scanner instanceof NullScanner) {
    return { payload, findingCount: 0, kinds: [] };
  }
  let findingCount = 0;
  const kinds = new Set<string>();
  // What each detected span *said*, so the echo pass below knows what to look for and
  // under which label. Keyed by the value, because that is what an echo is.
  const echoes = new Map<string, string | null>();

  let scrubbed = scrubStrings(payload, (text) => {
    let findings: readonly Finding[];
    try {
      findings = scanner.scan(text);
    } catch {
      return text;
    }
    const valid = findings
      .filter(
        (finding) =>
          Number.isInteger(finding.start) &&
          Number.isInteger(finding.end) &&
          finding.start >= 0 &&
          finding.end > finding.start &&
          finding.end <= text.length,
      )
      .sort((left, right) => left.start - right.start);
    if (valid.length === 0) return text;

    const merged: Finding[] = [];
    for (const finding of valid) {
      const last = merged[merged.length - 1];
      if (last !== undefined && finding.start < last.end) {
        merged[merged.length - 1] = {
          kind: last.kind,
          start: last.start,
          end: Math.max(last.end, finding.end),
          // Escalate-only here too: two detectors overlapping resolve to the stricter.
          label: join(last.label ?? null, finding.label ?? null),
        };
        continue;
      }
      merged.push(finding);
    }

    let out = text;
    for (const finding of [...merged].reverse()) {
      const value = text.slice(finding.start, finding.end);
      if (value.length >= MIN_SCAN_LENGTH && !echoes.has(value)) {
        echoes.set(value, finding.label ?? null);
      }
      out = `${out.slice(0, finding.start)}${marker(finding.label)}${out.slice(finding.end)}`;
      findingCount += 1;
      kinds.add(finding.kind);
    }
    return out;
  });

  // **The echo pass, and why it lives here rather than in the interface.** A detector
  // reports where it looked; whether the same datum in a *different* field is also
  // sensitive is a policy about this payload, and one this package has already argued and
  // tested a module away. `redaction.ts` scrubs a declared value across the whole payload
  // fenced by non-word lookarounds and above a minimum length, precisely so a short or
  // common value cannot corrupt unrelated content. The same rule applies for the same
  // reason, and the Python seat applies it identically.
  if (echoes.size > 0) {
    const values = [...echoes.keys()].sort((a, b) => b.length - a.length);
    const pattern = new RegExp(
      `(?<!\\w)(?:${values.map(escapeRegExp).join("|")})(?!\\w)`,
      "g",
    );
    scrubbed = scrubStrings(scrubbed, (text) =>
      text.replace(pattern, (match) => marker(echoes.get(match) ?? null)),
    );
  }

  return { payload: scrubbed, findingCount, kinds: [...kinds] };
}
