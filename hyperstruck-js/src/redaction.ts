/**
 * Client-side redaction, applied before any payload leaves the process.
 *
 * This is a security boundary, not an ergonomic layer, and it is why the package could
 * not ship without it: a port that carried the write queue and not this would send
 * unredacted tool arguments and results out of the customer's environment by default,
 * and would do it silently, because nothing in the customer's own code would look
 * different from the Python seat they were comparing it against.
 *
 * Two layers, matching `redaction.py` behaviour for behaviour:
 *
 * 1. **Declared-field strip.** Tool arguments the customer declared sensitive are
 *    replaced with a redaction marker, so their values never reach the platform.
 * 2. **Known-value scrub.** Because the declared values are known exactly, every one is
 *    scrubbed from the entire outbound payload (tool results, and any model text that
 *    echoed a literal secret) at any nesting depth.
 *
 * The scrub matches each value only as a whole token and skips values shorter than
 * {@link MIN_SCRUB_LENGTH}, so a short or common declared value does not corrupt
 * unrelated content. The tradeoff runs in the catch-the-echo direction: an echo that
 * glues the value inside a larger identifier is left intact rather than corrupting it,
 * while the declared argument itself is always stripped regardless.
 *
 * What is *not* redacted here, stated for integrators because the asymmetry is real:
 * only declared sensitive argument values are stripped, and only those exact values are
 * scrubbed elsewhere. Tool results and errors are not scanned for undeclared personal
 * data a tool may have fetched; that content reaches the platform, which applies its own
 * heuristic floor to undeclared fields server-side. To keep a value off the platform
 * entirely, declare the argument carrying it, or fit a content scanner.
 *
 * The Python package additionally carries a tiered free-text detector used by its editor
 * seat, which reads a transcript this package never sees. That half is deliberately not
 * ported: there is no TypeScript surface that produces the input it consumes, and a
 * detector with no caller is a maintenance cost pretending to be a control.
 */

export const REDACTION_MARKER = "[REDACTED]";

/**
 * Minimum length for a declared value to be scrubbed across the whole payload.
 *
 * A one-character value scrubbed everywhere corrupts unrelated content, so shorter
 * values are still stripped from their own declared argument and never scrubbed
 * elsewhere. Mirrors Core's server-side floor.
 */
export const MIN_SCRUB_LENGTH = 2;

type Json = unknown;

function labelledMarker(label: string): string {
  const trimmed = (label ?? "").trim();
  return trimmed ? `[REDACTED:${trimmed}]` : REDACTION_MARKER;
}

function declaredArgs(step: Record<string, unknown>): Record<string, string> {
  const declared = step["declared_sensitivity"];
  if (declared === null || typeof declared !== "object") return {};
  const args = (declared as Record<string, unknown>)["args"];
  if (args === null || typeof args !== "object" || Array.isArray(args)) return {};
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(args as Record<string, unknown>)) {
    out[key] = typeof value === "string" ? value : "";
  }
  return out;
}

function collectDeclaredValues(steps: Record<string, unknown>[]): Set<string> {
  const values = new Set<string>();
  for (const step of steps) {
    const args = step["args"];
    if (args === null || typeof args !== "object" || Array.isArray(args)) continue;
    const bag = args as Record<string, unknown>;
    for (const name of Object.keys(declaredArgs(step))) {
      const value = bag[name];
      if (value === undefined || value === null) continue;
      const rendered = String(value);
      if (rendered.length >= MIN_SCRUB_LENGTH) values.add(rendered);
    }
  }
  return values;
}

function stripDeclaredArgs(steps: Record<string, unknown>[]): void {
  for (const step of steps) {
    const args = step["args"];
    if (args === null || typeof args !== "object" || Array.isArray(args)) continue;
    const bag = args as Record<string, unknown>;
    for (const [name, label] of Object.entries(declaredArgs(step))) {
      if (bag[name] === undefined || bag[name] === null) continue;
      bag[name] = labelledMarker(label);
    }
  }
}

/**
 * Apply `replace` to every string in a payload, at any depth.
 *
 * The traversal is iterative over an explicit work stack rather than recursive, so an
 * arbitrarily deep payload is fully processed without a depth cap and cannot overflow
 * the stack into the host's run. Exposed so other adapters can layer their own string
 * pass over the same safe traversal rather than reinventing it, which is what the
 * content scanner does.
 */
export function scrubStrings(value: Json, replace: (text: string) => string): Json {
  if (typeof value === "string") return replace(value);
  if (value === null || typeof value !== "object") return value;

  const scalar = (item: unknown): unknown =>
    typeof item === "string" ? replace(item) : item;

  const root: Json = Array.isArray(value) ? [] : {};
  const stack: [unknown, Json][] = [[value, root]];
  while (stack.length > 0) {
    const frame = stack.pop();
    if (frame === undefined) break;
    const [source, target] = frame;
    const entries: [string | number, unknown][] = Array.isArray(source)
      ? source.map((item, index) => [index, item] as [number, unknown])
      : Object.entries(source as Record<string, unknown>);
    for (const [key, item] of entries) {
      let child: unknown;
      if (item !== null && typeof item === "object") {
        child = Array.isArray(item) ? [] : {};
        stack.push([item, child]);
      } else {
        child = scalar(item);
      }
      if (Array.isArray(target)) {
        (target as unknown[])[key as number] = child;
      } else {
        (target as Record<string, unknown>)[key as string] = child;
      }
    }
  }
  return root;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * A redacted copy of an episode payload, safe to send. The input is not mutated.
 *
 * Declared-sensitive arguments are stripped to markers, then their exact values are
 * scrubbed everywhere else in the payload with a single precompiled alternation, so each
 * string is scanned once however many distinct secrets there are.
 */
export function redactEpisodePayload(
  payload: Record<string, unknown>,
): Record<string, unknown> {
  const steps = payload["steps"];
  if (!Array.isArray(steps)) return payload;

  const stepsCopy = steps.map((step) => {
    const copy = { ...(step as Record<string, unknown>) };
    const args = copy["args"];
    if (args !== null && typeof args === "object" && !Array.isArray(args)) {
      copy["args"] = { ...(args as Record<string, unknown>) };
    }
    return copy;
  });

  // Longest first, so a longer secret wins over a shorter prefix of it.
  const secrets = [...collectDeclaredValues(stepsCopy)].sort(
    (left, right) => right.length - left.length,
  );
  stripDeclaredArgs(stepsCopy);

  let redacted: Record<string, unknown> = { ...payload, steps: stepsCopy };
  if (secrets.length > 0) {
    // Fenced by non-word lookarounds so each matches only as a whole token: a value like
    // "25" must not corrupt "1250".
    const alternation = secrets.map(escapeRegExp).join("|");
    const pattern = new RegExp(`(?<!\\w)(?:${alternation})(?!\\w)`, "g");
    redacted = scrubStrings(redacted, (text) =>
      text.replace(pattern, REDACTION_MARKER),
    ) as Record<string, unknown>;
  }
  return redacted;
}
