/**
 * Values a receiving side publishes, mirrored here rather than assumed.
 *
 * Three boundary fields are closed sets validated behind `extra="forbid"`, and a name
 * this client sends that the deployed boundary cannot parse is not a degraded
 * diagnostic: it costs the run its whole episode. A refused decline in particular leaves
 * the run open holding its resolve reservation, which is worse than saying less.
 *
 * So each set is vendored as a JSON artefact read at use, exactly as `contracts.py` does
 * it, and never as a generated union type. A generated union is the shape that looks
 * safest and is not: it makes the vocabulary a compile-time fact about the version of
 * the schema the package was built against, while the boundary the customer's process
 * actually talks to is deployed on a different schedule. The failure then lands as a
 * runtime rejection with a type system that said the value was fine.
 *
 * Empty is the safe degradation in both directions by construction. Every caller asks
 * "may I send this value", so an unreadable contract withholds the value and keeps the
 * behaviour the client had before that value existed.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** The vendored copy shipped inside the package, resolved relative to the built file
 * rather than to the working directory, so a host that starts elsewhere still finds it. */
const CONTRACT_ROOT = new URL("../contracts/", import.meta.url);

const cache = new Map<string, Record<string, unknown>>();

function published(name: string): Record<string, unknown> {
  const cached = cache.get(name);
  if (cached !== undefined) return cached;
  let parsed: Record<string, unknown> = {};
  try {
    const raw = readFileSync(fileURLToPath(new URL(name, CONTRACT_ROOT)), "utf8");
    const loaded: unknown = JSON.parse(raw);
    // Checked rather than trusted, because the degradation is only safe when a bad
    // contract yields empty. An array or a string would pass a looser guard and yield a
    // non-empty set matching nothing a caller will ever ask about, and the
    // empty-means-unknown escape hatch would never fire.
    if (loaded !== null && typeof loaded === "object" && !Array.isArray(loaded)) {
      parsed = loaded as Record<string, unknown>;
    }
  } catch {
    // A missing or corrupt file is a packaging fault. Taking the run down with it would
    // turn one unreadable diagnostic into lost learning with nothing to see.
  }
  cache.set(name, parsed);
  return parsed;
}

export function publishedNames(contract: string, key: string): ReadonlySet<string> {
  const value = published(contract)[key];
  if (!Array.isArray(value)) return new Set();
  return new Set(value.filter((name): name is string => typeof name === "string"));
}

/** The decline reasons the boundary accepts, as published by it. */
export function publishedDeclineReasons(): ReadonlySet<string> {
  return publishedNames("published_decline_reasons.json", "reasons");
}
