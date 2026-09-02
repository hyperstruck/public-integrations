# @hyperstruck/core

Run-scoped middleware for Hyperstruck. Recall goes in, the episode comes out, and the
receipt proves what the model was actually shown.

One core, three ways to attach, in descending order of how automatic they are: model-layer
middleware (the documented default), a context-provider adapter, and an explicit run
handle. All three share the same object and produce the same run report.

**Server-side only.** Tenancy rides entirely on your API key, with the organisation
resolved server-side. This package ships no browser entry point and its `exports` declare
no browser condition, so a bundler targeting the browser fails to resolve it rather than
quietly putting your tenant boundary in a bundle.

## Install

**Not yet on npm.** `publish-hyperstruck-js.yml` is wired and no release has been cut, so
`npm install @hyperstruck/core` returns a 404 today. Until the first release, install from a
packed tarball built out of this repository:

```
cd public_integrations/hyperstruck-js && npm ci && npm run build && npm pack
npm install /path/to/hyperstruck-core-0.8.0.tgz
```

To cut the first release, publish a GitHub Release whose tag is `js-v<version>`,
matching the version in `package.json`:

```
gh release create js-v0.8.0 --title js-v0.8.0 --notes "..."
```

The `js-v` prefix is not decoration. `release: published` reaches every publisher in
`core-platform`, so each product owns a prefix (`py-v` for the Python package, a bare
`vYYYY.MM.DD` for the platform's own deploys), and a tag in none of them fails the
release rather than publishing nothing in silence. A release marked prerelease goes to
the `next` dist-tag, never to `latest`.

Once the first release is published this becomes `npm install @hyperstruck/core`, and this
section changes in the same commit as that release rather than ahead of it. Documenting an
install that 404s is worse than documenting an awkward one that works.

Node 20.11 or newer.

## Quick start (Vercel AI SDK)

```ts
import { wrapLanguageModel } from "ai";
import { openai } from "@ai-sdk/openai";
import {
  DeclarationRegistry,
  HostedLearningClient,
  RunSeat,
  hyperstruckMiddleware,
} from "@hyperstruck/core";

const client = new HostedLearningClient({
  apiKey: process.env.HYPERSTRUCK_API_KEY,
  clientHost: "ai-sdk",
});

const seat = new RunSeat({
  client,
  identity: { agentName: "invoice-reconciler" },
  // Optional, and the thing most worth doing: declare what your tools return.
  declarations: new DeclarationRegistry([
    { name: "crm_lookup", args: { email: "user_data" }, subject: "company" },
  ]),
  // Optional: route the run report into your own observability.
  onReport: (report) => logger.info({ hyperstruck: report }),
});

const model = wrapLanguageModel({
  model: openai("gpt-5"),
  middleware: hyperstruckMiddleware({ seat }),
});
```

That is the whole integration. Every call through `model` now recalls what the corpus
knows, injects it, and writes the episode back with a receipt.

### Why the model layer

The middleware runs below every other middleware you composed: after trimming, after
summarisation, after guardrails. What it sees is the prompt as it actually goes on the
wire.

That is what makes an honest receipt possible. A seat attached above your composition
stack can only hand back the block it built itself, which asserts the very thing a receipt
exists to prove; it would report a delivered learning just as confidently for a run whose
trimming middleware had emptied the block on the way to the model. This seat searches the
sent parameters for the lines it authored, so what comes back is an observation rather than
an echo, and your run earns reinforcement credit for it.

The receipt carries only lines this package wrote, never the content between them, so its
disclosure cost is zero by construction rather than by promise.

### What a run is here

The middleware hooks fire once per model call, not once per episode, so the seat has to
work out which calls belong together. It reads the key you already have rather than
inventing one, best available first:

1. An active OpenTelemetry trace context, if your process registered the API.
2. `gen_ai.conversation.id`, if your instrumentation sets it (opt in with `otelResolvers`).
3. This package's own `withRun` wrapper.
4. Inference from the message history, last and always reported as inferred.

The run report always names the rung that answered, because an inferred key is a fact about
that report's reliability that you are entitled to.

A run ends when the model answers without asking for another tool, after a grace window
(60 seconds by default, `closeGraceMs`) unless a further call arrives under the same key.
The seat runs that timer itself, so you need do nothing. Two honest costs, stated rather
than hidden: a grace-window close posts credit up to one window late, and a run whose last
event is a tool call you never returned closes as abandoned, because the seat cannot know
whether the answer is still coming.

The one thing worth wiring yourself is `await seat.flushAll()` at process exit, paired with
`isSynchronousWrites: true`. The pending timers are unrefed so they never hold your process
open, which means a process exiting inside a grace window would otherwise drop those runs.

### Exact boundaries

If you would rather say where a run starts and stops:

```ts
import { withRun } from "@hyperstruck/core";

const report = await withRun(seat, "reconcile the March invoices", async () => {
  return await generateText({ model, prompt });
});
```

This is the only rung that is exact in both directions. A trace context supplies a key and
never an end, because the OpenTelemetry API gives no span-end notification.

## Declaring your tools

The seat fills `declared_sensitivity` for you, by origin rather than by inspecting content.
A tool is declared once and every value flowing out of it inherits the label.

```ts
new DeclarationRegistry([
  { name: "crm_lookup", args: { email: "user_data" }, subject: "company" },
]);
```

`subject` names the argument carrying the entity the result is about. Declaring it is what
stops `Northwind Clinics` and `Northwind Clinics Pty Ltd` becoming two entities with separate
dossiers, neither of which ever accumulates enough corroboration to be read back. If your tool schemas already
carry a JSON Schema `role: "entity"` annotation, `registerTools` reads it and you declare
nothing.

**Undeclared means most restrictive**, for sensitivity only and never for the subject. The
seat never withholds silently: every run reports how many fields went undeclared, which
tools they came from, and the configuration that would release them.

## What is redacted before anything leaves your process

Declared-sensitive argument values are replaced with a marker, and then those exact values
are scrubbed from the whole outbound payload, at any depth, matching only as whole tokens.

Tool results and errors are *not* scanned for undeclared personal data a tool may have
fetched. To keep a value off the platform entirely, declare the argument carrying it, or
fit a content scanner:

```ts
const seat = new RunSeat({ client, identity, scanner: myScanner });
```

The interface is `scan(text) => Finding[]`, off by default. This is where the two seats are
deliberately asymmetric and the reason is worth stating plainly: the Python package ships a
Presidio adapter, because Presidio is the mature free option and is Python-first, and the
credible Node equivalents are materially thinner. A thin detector shipped as a default
would be worse than none, because it would read as coverage while missing the cases the net
was fitted for. A customer-supplied hook is the honest shape until that changes.

A finding is redacted, not relabelled: the label field carries argument declarations, and a
finding inside a *result* has nowhere to go there, so the span is scrubbed and the run
reports how many went.

## Failure behaviour

- **Resolve fails or times out.** Your run proceeds with no context and reports
  `resolve_failed`. Never `resolve_empty`, which is what a cold corpus reports: collapsing
  the two makes a broken deployment indistinguishable from an agent with nothing to recall.
- **A degraded boundary.** A process-wide circuit breaker over resolve means a degraded
  deployment costs your host one timeout rather than one per run.
- **Write-back fails.** Retried with equal-jitter backoff. A 4xx is not retried, because it
  fails identically forever.
- **Durability, opt in.** `durableQueueDir` parks writes on disk so an outage that outlives
  the process is drained by the next start, via `client.replayDurableQueue()`. Off by
  default, and it refuses a read-only location rather than degrading: a store that silently
  fails to write is a corpus that silently never fills. The store holds episode content, so
  it inherits the same redaction the wire does.
- **No event loop to outlive the call.** `isSynchronousWrites: true` delivers inline. Use it
  in a serverless host, where a scheduled write is cancelled at teardown and the episode is
  lost with no error anywhere.

## The run report

The same report reaches three channels, and is never a subset on any of them: a structured
log line on every close, the `onReport` callback, and `run.report` on a handle you hold.

It names the rung that keyed the run, what closed it, whether the recall reached the model
and why not if it did not, how intact the block was on arrival, what was withheld and how
to release it, and the boundary's own per-offered-id verdict once the queued reinforce
drains. The seat's local check is a cheap verbatim substring test and is labelled a
heuristic; the authoritative three-way relation comes from the server, which owns the
matcher, so a local report can never disagree with the credit verdict.

## Dependencies

One runtime dependency, `p-queue`, for the bounded write queue.

The Python client ships exactly one runtime dependency as a stated design property, and
this package is close to the same discipline but not identical, which is deliberate. Jitter
and the circuit breaker are written by hand here as they are there, because their policy is
pinned to the Python seat's by a parity test and wrapping a library to reproduce that policy
exactly would be more code than stating it. Boundary calls go through `fetch` with the
schema types generated by `openapi-typescript`, not through the generated `@hyperstruck/sdk`:
the middleware needs five endpoints, and 19,743 lines of generated client to reach them
would buy nothing the type checker does not already give us.

The AI SDK itself is not a dependency. The middleware contract is a plain object of hooks,
described structurally, so your own `ai` version supplies the real types at your call site
and an SDK release that adds a field cannot break your build.

## Contributing

Edits are made in the `core-platform` repository, under `public_integrations/`. A commit
made on the public mirror leaves the sync unable to reach it, so every later sync is
rejected silently and the trees drift.

```
npm install
npm run typecheck
npm test
npm run schema     # regenerate src/schema.ts from ../openapi.json
```
