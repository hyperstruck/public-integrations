# Hyperstruck

Learning for your agents. Plug in one middleware and your agent gets sharper run
over run: it remembers what worked, avoids what did not, and carries that across
runs. The learning runs on the Hyperstruck platform; this package is a thin,
swappable client.

## Table of contents

- [Why](#why)
- [Install](#install)
- [Quick start (LangGraph)](#quick-start-langgraph)
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

agent = create_agent(
    model,
    tools=tools,
    middleware=[
        HyperstruckLearningMiddleware(api_key="hsk_...", agent_id="support-bot"),
    ],
)

# Use the agent as normal. Over successive runs it gets sharper.
result = await agent.ainvoke({"messages": [("user", "refund order 1234")]})
```

The `agent_id` is your own string. The platform creates a named agent for it on
first use and scopes the learning corpus to it. Set the key from the environment
(`HYPERSTRUCK_API_KEY`) and you can drop the `api_key` argument entirely.

Watch it learn through the platform's learnings and usage APIs (see the docs);
the corpus grows as runs accrue.

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
  fail-open, so a slow or unreachable platform never stalls your agent.
- **Record** (during the run): planned tool calls and their outcomes are joined
  by tool-call id, so the platform knows which learning helped which step.
- **Observe and reinforce** (run end): the finished run is shipped for
  server-side extraction and the learnings it used are credited. Both happen in
  the background, so your `invoke()` is never blocked.

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
text that echoed them):

```python
HyperstruckLearningMiddleware(
    api_key="hsk_...",
    agent_id="support-bot",
    tool_sensitivity={"lookup_customer": {"ssn": "pii", "dob": "pii"}},
)
```

## Reliability

- Resolve is deadline-bounded and fails open: a degraded platform costs you one
  run without its learnings, never a stalled agent.
- Writes are asynchronous with bounded retry, and safe at-least-once because the
  platform dedupes by run id. There is no local disk state, so the package
  deploys unchanged in serverless, read-only, and multi-replica environments.
- A run that is cancelled or killed mid-flight is never observed (an incomplete
  run has no terminal outcome); the skip is surfaced on the middleware stats.
