/**
 * What the package promises about itself, asserted rather than documented.
 *
 * The server-side-only property in particular is a security requirement, not a
 * preference: tenancy rides entirely on the API key with `org_id` resolved server-side,
 * so a browser entry point would put the tenant boundary in a bundle. The spec says the
 * package must say so "in its packaging, not only in its docs", and this is what makes
 * that true rather than asserted.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const PACKAGE_ROOT = fileURLToPath(new URL("..", import.meta.url));

const manifest = JSON.parse(readFileSync(`${PACKAGE_ROOT}package.json`, "utf8")) as {
  name: string;
  version: string;
  type: string;
  engines?: Record<string, string>;
  exports: Record<string, unknown>;
  files: string[];
  dependencies?: Record<string, string>;
  browser?: unknown;
  scripts: Record<string, string>;
};

test("there is no browser entry point, and a browser condition cannot resolve", () => {
  assert.equal(manifest.browser, undefined);
  const root = manifest.exports["."] as Record<string, string>;
  // Omitting `default` is what makes this structural: a bundler resolving for the browser
  // finds no condition it can take and fails at build time, rather than silently shipping
  // the tenant boundary into a bundle.
  assert.ok("node" in root);
  assert.ok(!("browser" in root));
  assert.ok(!("default" in root));
  assert.ok(manifest.engines?.["node"] !== undefined);
});

test("the runtime dependency list stays short and is not the generated SDK", () => {
  const dependencies = Object.keys(manifest.dependencies ?? {});
  // The asymmetry with the Python package is deliberate and stated in both READMEs, but
  // it is an asymmetry rather than a licence: a dependency has to earn its place.
  assert.ok(dependencies.length <= 2, `unexpected dependencies: ${dependencies.join(", ")}`);
  assert.ok(!dependencies.includes("@hyperstruck/sdk"));
  assert.ok(!dependencies.includes("ai"));
  assert.ok(!dependencies.includes("openai"));
  assert.ok(!dependencies.includes("@anthropic-ai/sdk"));
});

test("the vendored contracts ship inside the package", () => {
  // Read at use rather than compiled in, so a boundary vocabulary is data both sides can
  // read. A published package that left them behind would degrade every decline to
  // silence at the customer's, and nowhere else.
  assert.ok(manifest.files.some((entry) => entry.startsWith("contracts/")));
});

test("publishing runs the type check and the tests first", () => {
  assert.match(manifest.scripts["prepublishOnly"] ?? "", /typecheck/);
  assert.match(manifest.scripts["prepublishOnly"] ?? "", /test/);
});

test("the package is ESM, which is what the node-only exports assume", () => {
  assert.equal(manifest.type, "module");
});

const FORBIDDEN_GLOBAL = /\b(window|document|localStorage|sessionStorage|navigator)\b/;

/**
 * One file's executable text: comments and string literals removed.
 *
 * String literals are stripped for the same reason comments always were, and the reason is worth
 * writing down because the guard read as coverage without it. The property being checked is "this
 * source reaches for a browser global IDENTIFIER". The word inside a string is prose, and a renderer
 * that has to tell a customer whether a source is "a registered document" trips a bare word match
 * while executing nothing at all. A predicate that matches the NAME rather than the property fails
 * in both directions, and this one was failing in the direction that blocks correct code.
 *
 * A template literal keeps its `${...}` bodies, and dropping them was a real hole: those are
 * executable code, and this package's two renderers are written almost entirely in template
 * literals, so a stripper that removed them wholesale could not see the very files it was added for.
 */
export function executableText(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
    .replace(/`(?:\\.|[^`\\])*`/g, (template) => "`" + interpolations(template) + "`")
    .replace(/"(?:\\.|[^"\\\n])*"/g, '""')
    .replace(/'(?:\\.|[^'\\\n])*'/g, "''");
}

/** Every `${...}` body of one template literal, brace-balanced so a nested object survives. */
function interpolations(template: string): string {
  const body = template.slice(1, -1);
  let kept = "";
  let at = 0;
  while (at < body.length) {
    const start = body.indexOf("${", at);
    if (start < 0) break;
    let depth = 1;
    let end = start + 2;
    for (; end < body.length && depth > 0; end += 1) {
      if (body[end] === "{") depth += 1;
      else if (body[end] === "}") depth -= 1;
    }
    kept += body.slice(start, end);
    at = end;
  }
  return kept;
}

test("nothing in the source reaches for a browser global", async () => {
  const { readdirSync, statSync } = await import("node:fs");
  const walk = (directory: string): string[] =>
    readdirSync(directory).flatMap((entry) => {
      const path = `${directory}/${entry}`;
      if (statSync(path).isDirectory()) return walk(path);
      return path.endsWith(".ts") && !path.endsWith("_test.ts") ? [path] : [];
    });
  for (const path of walk(`${PACKAGE_ROOT}src`)) {
    // The generated schema types name whatever the API document names and execute nothing.
    if (path.endsWith("schema.ts")) continue;
    assert.ok(
      !FORBIDDEN_GLOBAL.test(executableText(readFileSync(path, "utf8"))),
      `${path} reaches for a browser global`,
    );
  }
});

test("stripping the strings does not disarm the browser-global guard", () => {
  // The positive control the guard above cannot supply for itself: it passes on every file in the
  // package by design, so nothing there distinguishes a working guard from one the new stripping
  // has turned off. A guard that cannot fail is worse than none.
  assert.ok(FORBIDDEN_GLOBAL.test(executableText('const x = document.title;')));
  assert.ok(FORBIDDEN_GLOBAL.test(executableText('if (typeof window !== "undefined") {}')));
  assert.ok(!FORBIDDEN_GLOBAL.test(executableText('const label = "a registered document";')));
  assert.ok(!FORBIDDEN_GLOBAL.test(executableText("const label = `asserted in the same document`;")));
  // The case the widening created: an interpolation is executable code, and stripping the template
  // wholesale took it with the prose.
  assert.ok(FORBIDDEN_GLOBAL.test(executableText("const s = `${document.title}`;")));
  assert.ok(FORBIDDEN_GLOBAL.test(executableText("const s = `href=${window.location.href}`;")));
  assert.ok(FORBIDDEN_GLOBAL.test(executableText("const s = `${format({ at: document.title })}`;")));
  assert.ok(!FORBIDDEN_GLOBAL.test(executableText("const s = `a registered document: ${reference}`;")));
});
