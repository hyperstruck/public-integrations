# Hyperstruck

Learning for your agents. Plug in one middleware and your agent gets sharper run
over run: it remembers what worked, avoids what did not, and carries that across
runs. The learning runs on the Hyperstruck platform; this package is a thin,
swappable client.

## Table of contents

- [Why](#why)
- [Install](#install)
- [Quick start (LangGraph)](#quick-start-langgraph)
- [Quick start (IDE: Claude Code & Cursor)](#quick-start-ide-claude-code--cursor)
- [Quick start (MCP host)](#quick-start-mcp-host)
- [How it works](#how-it-works)
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

```
pip install hyperstruck[langgraph]
```

## Quick start (LangGraph)

```python
from langchain.agents import create_agent
from hyperstruck.langgraph import HyperstruckLearningMiddleware

async with HyperstruckLearningMiddleware(api_key="hsk_...", agent_id="support-bot") as learning:
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

The `agent_id` is your own string. The platform creates a named agent for it on
first use and scopes the learning corpus to it. Set the key from the environment
(`HYPERSTRUCK_API_KEY`) and you can drop the `api_key` argument entirely.

Watch it learn through the platform's learnings and usage APIs (see the docs);
the corpus grows as runs accrue.

## Quick start (IDE: Claude Code & Cursor)

The same learning loop, driven by your editor's hooks instead of a programmatic
agent. Install once and every coding turn recalls and contributes learnings with
no explicit commands:

```
pip install hyperstruck
python -m hyperstruck.ide.install
```

This wires the learning hooks into Claude Code and Cursor (deep-merging your hooks
config without touching your existing entries) and installs the `hyper-*` skills.
Restart your editor afterwards. See [`hyperstruck/ide/README.md`](src/hyperstruck/ide/README.md)
for the turn loop, the deferred outcome resolution, and the privacy model.

## Quick start (MCP host)

The same learning loop for any MCP-capable host (Claude Desktop, Cursor, Cline),
through Hyperstruck's hosted MCP server. There is nothing to install and nothing
to run: point your host at the remote endpoint with your key and an agent name.

```json
{
  "mcpServers": {
    "hyperstruck": {
      "url": "https://mcp.hyperstruck.com/mcp/",
      "headers": {
        "Authorization": "Bearer your-hyperstruck-api-key",
        "X-Hyperstruck-Agent-Id": "support-bot"
      }
    }
  }
}
```

The hosted endpoint authenticates the bearer before MCP discovery, request
parsing, or SSE setup. The key must be active and include at least one MCP tool
scope: `agents:read` or `agents:write`. Admission does not grant every tool:
`resolve` still requires `agents:read`, while `complete_run` requires
`agents:write`.

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

The host's model calls two tools: `resolve` to read the learnings bound to a task
before it acts, and `complete_run` to report the outcome after, so the next run
is sharper. Redaction runs at our edge before anything is persisted, with the
names/addresses tier available on the compliance add-on. Regulated teams that need
redaction inside their own process can run the self-host build (enterprise).

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
  server-side extraction and the learnings it used are credited. Both happen in
  the background, so your `invoke()` is never blocked.

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
    agent_id="support-bot",
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
