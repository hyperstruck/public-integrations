# Hyperstruck

Learning for your agents. Plug in one middleware and your agent gets sharper run
over run: it remembers what worked, avoids what did not, and carries that across
runs. The learning runs on the Hyperstruck platform; this package is a thin,
swappable client.

## Table of contents

- [Why](#why)
- [Install](#install)
- [Quick start (Anthropic or OpenAI SDK)](#quick-start-anthropic-or-openai-sdk)
- [Exact run boundaries](#exact-run-boundaries)
- [Quick start (Microsoft Agent Framework)](#quick-start-microsoft-agent-framework)
- [Correlating with your traces](#correlating-with-your-traces)
- [Quick start (LangGraph)](#quick-start-langgraph)
- [Quick start (IDE: Claude Code & Cursor)](#quick-start-ide-claude-code--cursor)
- [Quick start (Claude CoWork)](#quick-start-claude-cowork)
- [Quick start (MCP host)](#quick-start-mcp-host)
- [How it works](#how-it-works)
  - [Credit follows evidence, not assertion](#credit-follows-evidence-not-assertion)
- [Configuration](#configuration)
- [Privacy: client-side redaction](#privacy-client-side-redaction)
- [Reliability](#reliability)

## Why

Most agents start every run from zero. They repeat the same dead ends and forget
the trick that worked yesterday. Hyperstruck closes that loop: every run becomes
evidence, and the next run is offered what prior runs learned. You write no
memory code, assemble no episodes, and run no stores. You install a package, set
a key and an identity, and register a middleware.

## Install

The package is distributed from this repository, not PyPI:

```
pip install --upgrade "hyperstruck[langgraph] @ git+https://github.com/hyperstruck/public-integrations.git#subdirectory=hyperstruck-py"
```

**Not yet on PyPI**, which is why the install above is a git URL. To cut the first
release, publish a GitHub Release whose tag is `py-v<version>`, matching `__version__`
in `_version.py`:

```
gh release create py-v0.8.0 --title py-v0.8.0 --notes "..."
```

The `py-v` prefix is not decoration. `release: published` reaches every publisher in
`core-platform`, so each product owns a prefix (`js-v` for `@hyperstruck/core`, a bare
`vYYYY.MM.DD` for the platform's own deploys), and a tag in none of them fails the
release rather than publishing nothing in silence.


## Quick start (Anthropic or OpenAI SDK)

The default attachment point, and the one to reach for if you are not on a framework
we ship a seat for. Wrap your model client and the loop runs itself: the experience
bound to your goal is injected into every model call, the run is assembled from what
the model planned and what your tools returned, and the run is credited or declined
when it ends.

```python
from anthropic import AsyncAnthropic
from hyperstruck import AgentIdentity, HostedLearningClient
from hyperstruck.runtime import RunSeat, wrap_anthropic

seat = RunSeat(
    client=HostedLearningClient(api_key=..., client_host="anthropic-sdk",
                                client_capabilities=("receipt", "delivery")),
    identity=AgentIdentity(agent_name="support-bot"),
)
client = wrap_anthropic(AsyncAnthropic(api_key=...), seat)

# Call it exactly as you did before. Everything else on the client passes through.
response = await client.messages.create(model=..., messages=[...], tools=[...])
```

`wrap_openai` is the same call for an `AsyncOpenAI` client. Streaming is covered too:
`wrap_anthropic` wraps `messages.stream` alongside `messages.create`, and OpenAI streams
through the same `create`, so nothing extra is needed either way. Your stream object is
handed back untouched, at its own pace; the seat reads the final message the SDK has
already accumulated rather than buffering anything.

Both wrap the **async** client only: the seat's prefetch and write-back are coroutines, and wrapping the
synchronous client would appear to work while capturing nothing, so it raises instead.

### Why this layer

This sits below every middleware you composed: after trimming, after summarisation,
after guardrails. What it sees is the prompt as it actually goes on the wire, and that
is what makes an honest receipt possible. A seat above the composition stack can only
hand back the block it built itself, which asserts the very thing a receipt exists to
prove, so our LangGraph seat sends none and earns no credit. This one returns an
artefact it did not author.

It also means the run report can tell you what *your* stack did to our block. Every
run reports, per shelf, whether the block arrived verbatim, arrived reformatted, or
never arrived, and names the lines that went missing. If your own trimming middleware
is emptying it, you can see that without opening a ticket.

### What a run is here

The hooks fire once per model call, not once per episode, so the seat has to work out
which calls belong together. It reads the key your instrumentation already sets rather
than inventing one: an active OpenTelemetry trace first, then a conversation id, then
this seat's own context, and only last does it infer from the message history. The run
report always says which rung answered, because an inferred key is a fact about that
report's reliability. Tenancy is never inferred: the API key binds at wrap time, so one
wrapped client is one tenant.

A run inferred from activity closes when the model answers without asking for another
tool. If you need an exact boundary, hold the run yourself through `seat.open(...)` and
`seat.close(...)`.

### Declaring your tools

Sensitivity is declared per tool, by origin, and everything flowing out of a tool
inherits its label. Undeclared arguments are withheld as the most restrictive label,
and every run says which tool they came from and what releases them, so a
configuration state never looks like a broken product.

```python
from hyperstruck.runtime import DeclarationRegistry, ToolDeclaration

seat = RunSeat(
    ...,
    declarations=DeclarationRegistry([
        ToolDeclaration(name="lookup_account", args={"api_token": "secret"},
                        subject="company_name"),
    ]),
)
```

`subject` names the argument carrying the entity a call's result is about, and it is
read for free from your tool's JSON Schema if you annotate that argument with
`"role": "entity"`. It matters more than it looks: without it, the same company
arriving under two spellings accumulates two separate dossiers and neither reaches the
confidence the read side requires.

Free text is where origin labelling under-delivers, so an optional content scan sits
behind it as a secondary net. It is off by default and never lowers a label, only
raises one.

```python
from hyperstruck.runtime import PresidioScanner

seat = RunSeat(..., scanner=PresidioScanner())  # needs presidio-analyzer, not installed by us
```

### When a run ends

A run ends when the model answers without asking for another tool, after a grace window
(60 seconds by default, `close_grace_seconds`) unless a further call arrives under the same
key, which continues it instead. The seat runs that timer itself.

Two honest costs, stated rather than hidden: a grace-window close posts credit up to one
window late, and a run whose last event is a tool call your loop never returned closes as
abandoned, because the seat cannot know whether the answer is still coming.

At process exit, `await seat.flush_all()` paired with `is_synchronous_writes=True` on the
client closes and delivers whatever the window still held. Without both, those episodes are
dropped at teardown with no error anywhere.

## Exact run boundaries

The model-layer seat works out which calls belong to one run from your trace context or,
failing that, from the shape of the traffic. If you would rather say so yourself:

```python
from hyperstruck.runtime import hyperstruck_run

async with hyperstruck_run(seat, "reconcile the March invoices", tools) as run:
    await agent.run()          # any model call in here joins this run
print(run.report)
```

This is the only rung that is exact in both directions. A trace context gives a key and
never an end, because the bare OpenTelemetry API sends no span-end notification, and the
traffic-shape trigger gives an end that is one grace window late. The handle closes on the
way out either way, including on an exception, because a run left neither reinforced nor
declined sits open holding its resolve reservation and is indistinguishable from a host
that stopped writing back.

`@hyperstruck/core`'s `withRun` is the same thing in TypeScript.

## Quick start (Microsoft Agent Framework)

Agent Framework's `AIContextProvider` is the same two halves this seat needs, so the
adapter is a shim over the shared core rather than a second implementation.

```python
from hyperstruck.runtime import HyperstruckContextProvider, RunSeat

agent = ChatAgent(
    chat_client=client,
    context_providers=[HyperstruckContextProvider(RunSeat(client=hyperstruck, identity=identity))],
)
```

The framework tells the provider where each invocation starts and ends, so runs are keyed
and closed exactly rather than inferred, and a thread id becomes the run's thread id so a
multi-turn session is one thread server-side.

One honest limit, stated rather than discovered. A context provider runs *above* your
composition stack: it is handed the messages the agent assembled, not the parameters the
model was sent. So it records no receipt, exactly as the LangGraph seat does not, and for
the same reason: the only artefact it could return is the block it built itself, and
echoing that back asserts the very thing a receipt exists to prove. It still reports
delivery, which is a different and weaker claim. To earn reinforcement credit as well,
attach the model seat too; the two compose, with the provider supplying the exact boundary
and the model seat supplying the receipt.

## Correlating with your traces

If your process runs the OpenTelemetry API, runs are keyed on the active trace by default,
so a Hyperstruck run report lines up against your own incident rather than sitting beside
it. No dependency is taken: the rung is a resolver, and a tracer that is not OpenTelemetry
is three lines you write.

To also read `gen_ai.conversation.id`, which keys a multi-turn session rather than one
operation:

```python
from hyperstruck.runtime import resolvers_with_conversation

seat = RunSeat(..., run_key_resolvers=resolvers_with_conversation())
```

Opt in rather than default, because reading a span's attributes back is not part of the
OpenTelemetry API's promised surface, so whether it works is a fact about your own
instrumentation. Best effort throughout: the GenAI conventions still carry the Development
stability badge and moved to their own repository in June 2026 with no stabilisation
timeline, so an attribute can be renamed without a major version bump. Losing this rung
costs correlation quality and never correctness, and no contract test depends on it.

## Quick start (LangGraph)

```python
from langchain.agents import create_agent
from hyperstruck.langgraph import HyperstruckLearningMiddleware

async with HyperstruckLearningMiddleware(api_key="hsk_...", agent_name="support-bot") as learning:
    agent = create_agent(model, tools=tools, middleware=[learning])

    # Use the agent as normal. Over successive runs it gets sharper.
    result = await agent.ainvoke({"messages": [("user", "refund order 1234")]})
```

The observe and reinforce writes run in the background so your `invoke()` is
never blocked. In a long-lived server they complete on their own; in a
short-lived process (a script, a one-shot task, a serverless handler) use the
middleware as an `async with` context (or `await learning.aclose()` before exit)
so the writes are drained before the process ends. Skip the drain and the first
run's learning is cancelled at exit before it reaches the platform.

The `agent_name` is your human-readable agent name (unique within the tenant).
If no agent with that name exists yet, a write-scoped key (`agents:write`)
**creates one automatically** on first use and scopes the corpus to it. A
read-only key can resolve an existing name but cannot mint a new agent. This is
not the hosted agent UUID used in REST paths — use `HYPER_AGENT_ID` for those.
Set the key from the environment (`HYPERSTRUCK_API_KEY`) and you can drop the
`api_key` argument entirely.

What the agent is shown is two blocks, not one. The *advice* half carries rules the
agent has learned; the *fact* half carries what it has already established about the
entities in play, so a rule arrives with the warrant that makes it apply here rather
than in general. The boundary returns them separately so a host can place each where
its model treats it best; this middleware places them adjacently in a single system
message before the model call, and keeps the halves and their id sets apart on the run
so that placement can change without a second resolve.

Watch it learn through the platform's learnings and usage APIs (see the docs);
the corpus grows as runs accrue. For how this surface places the two blocks, what it
inherits from the boundary rather than enforcing itself, and how it reports a run that
was shown nothing, see
[`src/hyperstruck/langgraph/README.md`](src/hyperstruck/langgraph/README.md).

## Quick start (IDE: Claude Code & Cursor)

The same learning loop, driven by your editor's hooks instead of a programmatic
agent. Install once and every coding turn recalls and contributes learnings with
no explicit commands:

```
pip install --upgrade "hyperstruck @ git+https://github.com/hyperstruck/public-integrations.git#subdirectory=hyperstruck-py"
python -m hyperstruck.ide.install
```

This wires the learning hooks into Claude Code and Cursor (deep-merging your hooks
config without touching your existing entries) and installs the `hyper-*` skills.
Restart your editor afterwards. See [`hyperstruck/ide/README.md`](src/hyperstruck/ide/README.md)
for the turn loop, the deferred outcome resolution, and the privacy model.

`python -m hyperstruck.ide.install` does **not** install or wire Claude CoWork.

## Quick start (Claude CoWork)

CoWork is a skill-plus-curl host, not a hooked editor. Zip the portable
[`hyper-learning`](../claude_skills/hyper-learning/) folder, upload it from
**Customize → Skills**, enable it, and start a new session. Set
`HYPER_SOURCE_FRAMEWORK=cowork`. Allowlist `api.hyperstruck.com` for CoWork
network egress (Capabilities → Code execution). The skill reads `HYPER_*`
from the attached local `.env` as well as the remote session env — an empty
sandbox environment is not a missing key. The skill must close every
`POST /resolve` with `POST /reinforce` or `POST /decline`.

Full zip, UI, auth, and reporting steps live in the
[repository README](../README.md#claude-cowork).

## Quick start (MCP host)

The same learning loop for any MCP-capable host (Claude Desktop, Cursor, Cline, CoWork),
through Hyperstruck's hosted MCP server. There is nothing to install and nothing
to run: point your host at the remote endpoint with your API key.

```json
{
  "mcpServers": {
    "hyperstruck": {
      "url": "https://mcp.hyperstruck.com/mcp/",
      "headers": {
        "Authorization": "Bearer your-hyperstruck-api-key"
      }
    }
  }
}
```

`X-Hyperstruck-Agent-Name` is optional and **unset by default**. Add it only
when you want to pin `resolve` / `complete_run` / `distill` to a specific agent
name; otherwise hosted MCP uses the shared `default` namespace. For manual
learning and claim tools, call `list_agents` first so you can pick the agent
UUID this API key can access and pull the correct learnings.

The hosted endpoint authenticates the bearer before MCP discovery, request
parsing, or SSE setup. The key must be active and include at least one MCP tool
scope: `agents:read`, `agents:write`, or `claims:read`. Admission does not grant every tool:
learning read tools require `agents:read`, write tools require `agents:write`,
and claim tools require `claims:read`.

For CoWork, paste the same JSON into **Advanced settings** / **MCP server
configuration**, then start a new session. Allowlist `mcp.hyperstruck.com` for
MCP egress. Keep `api.hyperstruck.com` allowlisted when you also use the
`hyper-learning` skill's curl fallback.

Connection failures use standard HTTP status codes:

- `401 Unauthorized`: the bearer is missing, malformed, or rejected. Check the
  configured API key; the response includes `WWW-Authenticate: Bearer`.
- `403 Forbidden`: the key is valid but has neither MCP tool scope.
- `429 Too Many Requests`: the key exceeded the hosted MCP request limit. Retry
  after the number of seconds in the `Retry-After` response header.
- `503 Service Unavailable`: authentication could not be confirmed, including
  temporary authentication-service or lookup-capacity failures. Retry later.

Successful authentication and entitlement lookups may be cached for up to 60
seconds. Rejected credentials and service failures are not cached.

The host's model calls `resolve` to read the learnings bound to a task before it
acts, and `complete_run` to report the outcome after, so the next run is sharper.
The MCP server also exposes `distill` for contrast corpora (docs, diffs,
post-mortems) and manual tools: `list_agents`, `list_learnings`,
`search_learnings`, `get_learning`, `store_learning`, `reinforce_learning`,
`list_learning_claims`, `get_claim_review_context`, `get_claim_entity`, and
`get_claim_attribute`. Use `distill` when the rule is not written yet; use
`store_learning` when you already have the final text. Redaction runs at our
edge before write payloads are forwarded, with the names/addresses tier
available on the compliance add-on.
Regulated teams that need redaction inside their own process can run the
self-host build (enterprise).

## How it works

```
  your agent run                                  Hyperstruck platform
  ┌───────────────────────────┐                  ┌──────────────────────────┐
  │ create_agent graph         │   resolve  ───▶  │ bind learnings to goal   │
  │  + middleware              │ ◀── injected     │                          │
  │   run the model + tools    │     block        │                          │
  │   record what happened     │   observe  ───▶  │ extract · store          │
  │                            │   reinforce ──▶  │ attribute · reinforce    │
  └───────────────────────────┘                  └──────────────────────────┘
```

- **Resolve** (run start): the middleware fetches the learnings bound to the
  run's goal and injects them into every model call. Deadline-bounded and
  fail-open, so a slow or unreachable platform never stalls your agent. Resolve
  uses a fast, graph-free retrieval path by default, ranking learnings by
  relevance, usefulness, and reliability with no graph round trips.
- **Record** (during the run): planned tool calls and their outcomes are joined
  by tool-call id, so the platform knows which learning helped which step.
- **Observe and reinforce** (run end): the finished run is shipped for
  server-side extraction, and the learnings the model was *shown* are credited.
  Both happen in the background, so your `invoke()` is never blocked.

### Credit follows evidence, not assertion

A learning is credited only once something confirms the model actually saw it. That
is not the same as the platform having selected it: an injected block can be trimmed
by a prompt budget, refused by an editor's hook, or dropped by compaction long after
this client hands it over, and from here every one of those looks identical.

So the run end carries an **exposure receipt**: the block as the host's own artefact
records it, never an echo of what this client emitted. An echo would match every
offered rule by construction and assert precisely the thing the receipt exists to
evidence. The platform re-derives the match itself, against what it offered.

```
   offered ──▶ rendered ──▶ shown ──▶ credited
      │            │           │
      │            │           └─ the receipt reports it  ▶ EXPOSED    earns credit
      │            └───────────── the receipt omits it    ▶ UNEXPOSED  demoted
      └────────────────────────── no receipt at all       ▶ UNVERIFIED credits nothing
```

The last two are kept apart on purpose. "We know it was not shown" and "we cannot
say" license different conclusions, and collapsing them would make a host with broken
wiring indistinguishable from a corpus with nothing left to learn.

What produces the receipt depends on the host, and today only one host can produce
one. The IDE integration under Claude Code reads the editor's own transcript record of
what it accepted, matched to the run by an identifier this client stamps into the
block, so a denied injection on one turn can never pair a verdict with another turn's
learnings.

Every other host sends nothing, deliberately. Cursor keeps no record of what it
accepted; the LangGraph middleware sees only what it emitted, and sending that back
would be the echo above wearing a receipt's name. A host that sends nothing earns no
reinforcement, which is the safe answer rather than a silent one: the platform logs
each run that offered learnings and never heard back, and names the client behind it so
an unsupported host is distinguishable from a broken one.

That is why the client declares its host in the `User-Agent`, as
`hyperstruck-py/<version> (host=claude-code)`. Whether an honest receipt can exist is a
property of the editor rather than of this library, so a version alone would report a
host that can never send one as ready for the credit rules that require it.

The `utility` value exposed in learning standing is a derived,
recency-weighted application-outcome score. Later evidence that a learning
helped or misled the agent moves the score; it is not a confidence field or a
directly maintained persistence value. When manually storing a learning, an
optional `utility` is only the starting prior.

## Configuration

`HyperstruckLearningMiddleware(...)` accepts:

- `api_key`, `agent_id`, `org_id`: the whole configuration for a single agent.
- `client`: a custom `LearningClient` to point at a different backend.
- `tool_sensitivity`: per-tool argument sensitivity declarations (see below).
- `tools`: your agent's tools (names, dicts, or tool objects) for tool-aware
  retrieval; learnings are resolved at run start, before the graph binds tools,
  so pass them here if you want retrieval to consider them.
- `max_injected_learnings`: cap on learnings injected per run.

To serve many tenants from one registered middleware, set a per-invoke
`AgentIdentity` under the `hyperstruck_identity` config key.

## Privacy: client-side redaction

Traces leave your environment, so redaction happens here, before anything is
sent. Declare which tool arguments are sensitive and their values are stripped
to a marker, then scrubbed everywhere in the outbound payload (including model
text that echoed them). The scrub matches each value only as a whole token and
skips very short values, so a short or common declared value cannot corrupt
unrelated content; it errs towards over-redaction rather than leaking:

```python
HyperstruckLearningMiddleware(
    api_key="hsk_...",
    agent_name="support-bot",
    tool_sensitivity={"lookup_customer": {"ssn": "pii", "dob": "pii"}},
)
```

The IDE host layers a privacy-forward default on top of this: it never ships raw
file contents or diffs (only tool name, path, status, error, and a clipped
result), and it scrubs known credential shapes and high-entropy tokens from every
string before it leaves the machine. Your source never leaves; only scrubbed,
pattern-level learnings do.

## Reliability

- Resolve is deadline-bounded and fails open: a degraded platform costs you one
  run without its learnings, never a stalled agent.
- Writes are asynchronous with bounded retry, and safe at-least-once because the
  platform claims each run atomically by run id, so a retried observe or reinforce
  is a single-charge server-side no-op. There is no local disk state, so the
  package deploys unchanged in serverless, read-only, and multi-replica
  environments. Drain the writes before a short-lived process exits (see the quick
  start); `writes_delivered` and `writes_failed` on the middleware report the real
  delivery outcome once drained.
- A run that is cancelled or killed mid-flight is never observed (an incomplete
  run has no terminal outcome); the skip is surfaced on the middleware stats.
- Stacking middleware? Keep this one innermost (last in the list) so an outer
  middleware cannot strip the injected learnings before the model sees them. Call
  `assert_innermost(middleware_list, learning)` to enforce it.
