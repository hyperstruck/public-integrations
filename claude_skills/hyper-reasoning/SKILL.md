---
name: hyper-reasoning
description: >-
  Use Hyperstruck Core hosted reasoning for structured plans, milestones, and
  steps when local work needs deeper analysis. The platform applies memory,
  knowledge, and accumulated learnings so outcomes improve over time. Do not use
  for simple edits or lookups you can handle directly — poll until the
  reasoning session completes (including human-in-the-loop when required).
argument-hint: "[optional goal text]"
effort: high
allowed-tools:
  - Bash(curl *)
  - WebFetch
---

# Hyperstruck hosted reasoning

Use this skill when the current task needs **structured reasoning**: richer plans, milestones, trade-off analysis, or cross-domain thinking that benefits from Hyperstruck Core — where reasoning is **grounded, auditable**, and informed by **memory, knowledge, and learnings** so results get **more valuable over time**. The underlying service runs as a hosted workflow; what matters for you is **better planning and evidence-backed output**, not the transport details.

Do **not** invoke for straightforward edits, lookups, or tasks you can complete locally.

## How this skill fits the caller workflow

- **The skill is HTTP orchestration:** env -> `GET /agents` -> `POST /agents/{id}/goals` with **`goal`** + **`context`** -> poll **`GET /runs/{run_id}`** -> return **`metadata.result.output`** to the user.
- **Choose enough reasoning depth:** `fast` is only for compact results that can be planned and executed in one or two steps. If the answer may need several synthesis steps, richer milestones, validation, reflection, or trade-off analysis, pick **`balanced`** or **`full`** so the engine has enough iterations to execute the plan and emit final `output`.
- **Compressed `context`:** put session facts, goal-relevant caller capabilities, tool findings, constraints, and success criteria here. Hosted reasoning has **no** access to Claude Code, Cursor, the repo, local subagents, MCP, or external integrations unless you summarize them in **`goal`** and **`context`**.
- **Tool-aware output:** the hosted reasoning result should tell the caller what to do next using the caller's own relevant skills, subagents, tools, and integrations. The reasoning service cannot run those capabilities itself.
- **Caller-usable result:** treat **`metadata.result.output`** as the only final answer to pass back. Do not expose raw run metadata to the user as a substitute for a missing final answer.

## Current environment

```!
echo "HYPER_BASE_URL=${HYPER_BASE_URL:-https://api.core.hyperstruck.com}"
echo "HYPER_AGENT_ID=${HYPER_AGENT_ID:-<not set>}"
echo "HYPER_API_KEY_SET=$([ -n \"$HYPER_API_KEY\" ] && echo yes || echo no)"
if [ -f .env ]; then echo "dotenv=found (.env)"; else echo "dotenv=not found"; fi
```

If `HYPER_API_KEY_SET=no` above, check `.env` for a `HYPER_API_KEY=` line. If still missing, **stop and ask the user** to set `HYPER_API_KEY`.

---

## Step 1 — Resolve configuration

- **Base URL**: Use `HYPER_BASE_URL` from the environment block above, defaulting to `https://api.core.hyperstruck.com`.
- **API key**: Already resolved above. **Never echo it.**
- **Headers** for every HTTP request:
  ```
  Authorization: Bearer <API_KEY>
  Content-Type: application/json
  Accept: application/json
  ```
- **Paths and JSON shapes**: Follow [reference.md](reference.md). **Do not** fetch `GET {BASE_URL}/openapi.json` up front — the document is large and wastes context. Rely on `reference.md` unless you hit errors that suggest API drift (see **Error handling**).

---

## Step 2 — Choose the Hyperstruck profile for this task

The API exposes this as **agents**; each one is a configured reasoning profile (instructions, model, memory, knowledge, learnings, safety settings).

**This step’s first request is also your auth check** — do not issue a separate `GET /agents?limit=1` beforehand. One round trip is enough.

```
GET {BASE_URL}/agents?limit=50
```

On **401** or **403**, stop and tell the user to verify `HYPER_API_KEY` and `HYPER_BASE_URL` (same outcome as a dedicated key-validation call, without the extra request).

For each item, inspect `name`, `core_config.description`, and `status`. Only `active` profiles can accept a new goal.

**If no profile fits the current task → stop early.** Tell the user:
> "None of your Hyperstruck setups match this task. Configure one in your Hyperstruck dashboard, or I'll continue without hosted reasoning."

If one profile clearly matches, use it. If several match, list them briefly and ask the user to pick (or choose the best fit by description). Store the chosen `agent_id` for API calls.

---

## Step 3 — Build rich context (critical)

The user is already mid-session. A bare one-line goal is nearly useless. Assemble a **structured context block** before dispatching.

### Goal

If the user passed `$ARGUMENTS`, use that as the starting point. Otherwise, synthesize a clear, self-contained goal paragraph from the conversation so far.

Before dispatching, make sure the goal describes something the caller can **act on** with the reasoning result. Include:

- The desired outcome.
- Success criteria or acceptance criteria.
- The decision, plan, implementation order, or next action the caller needs from hosted reasoning.

If the actionable goal is unclear, **stop and ask the user for the goal** instead of sending a vague prompt.

### Context (passed as the `context` JSON field)

Build a markdown block with these sections:

1. **Task background** — What the user is working on: repo, branch, project, deployment targets, environment constraints.
2. **Work done so far** — Summarize files read/written, commands run, data fetched from integrations (MCP tools, web searches, DB queries, etc.). Include key **findings and data**, not just tool names — the hosted agent cannot call your local tools.
3. **Relevant caller capabilities** — List only the skills, subagents, tools, MCP servers, CLIs, integrations, databases, browsers, test runners, deployment targets, and permissions that could realistically affect this goal. Do not include a full tool inventory. Also list relevant unavailable capabilities or permissions when they constrain the plan.
4. **Requested output shape** — Ask the hosted agent to produce a complete caller-executable final answer that maps each meaningful step to the appropriate relevant caller-run skill, subagent, tool, or integration. If no tool is needed for a step, say so.
5. **Learnings & pitfalls** — Anything discovered in this session: error patterns, API quirks, performance constraints, edge cases found (this feeds the same learning ecosystem the platform uses long term).
6. **Open questions** — What needs deeper analysis, trade-off evaluation, or planning that you cannot resolve locally.
7. **Constraints** — Deadlines, compliance, tech-stack limits, performance budgets, cost concerns.

> **Tip:** Paste summarized MCP/integration results. The hosted reasoning runtime has no access to your local tools, Jira, Linear, Slack, databases, browser session, local filesystem, or subagents.

---

## Step 4 — Submit the goal for hosted reasoning

```
POST {BASE_URL}/agents/{agent_id}/goals
```

```json
{
  "goal": "<structured goal from step 3>",
  "context": "<full context block from step 3>",
  "metadata": {
    "source": "claude-code-skill",
    "task_summary": "<one-line description>"
  }
}
```

Optional fields:
- `session_id` — set only to continue a previous Hyperstruck session whose last run is **terminal** (completed/failed). Omit to auto-create.
- `worker_profile` — infrastructure sizing only: `"default"` unless you need `"large"`.

Tier guidance:
- `full` — maximal hosted reasoning depth.
- `balanced` — middle tier for most hosted reasoning tasks.
- `fast` — lower-latency path for narrow, caller-usable answers. It intentionally caps plan size; a fast run still needs enough iterations for planning, each generated step, and the final completion pass that emits `metadata.result.output`. If the hosted planner may create more than 1-2 steps, use `balanced` or `full`.

Reasoning profiles live on the agent (`reasoning_profile` = `full` / `balanced` / `fast`). `worker_profile` is not a reasoning profile.

Choose an agent whose configured `reasoning_profile` matches the task instead of trying to change reasoning behavior per run.

Parse the response for `run.id` and `run.session_id` (the API names this a “run”; it is the lifecycle handle for the reasoning job).

---

## Step 5 — Poll until the reasoning job is finished

```
GET {BASE_URL}/runs/{run_id}
```

### Polling strategy

- Poll every **10 s**. Do not poll more frequently unless you are debugging a transient API problem.
- **Stop after 10 min** and report last known status.

### On `completed`

Read `metadata.result.output`.

- If `output` is present, report it to the user as the hosted reasoning result. Present actionable plans, milestones, and next steps.
- If `output` is missing or `null`, do **not** show raw run metadata. Tell the user hosted reasoning completed without a caller-usable final answer, then ask whether to retry with a clearer goal, richer context, or a deeper reasoning profile.

### On `failed`

Report `error` and `metadata`. Ask whether to retry or proceed without.

### On `suspended` (HITL)

1. Read `metadata.result.suspension.id`.
2. Present the suspension context to the user.
3. Ask for a decision: `approve`, `reject`, `modify`, `skip`, `provide_input`, or `partial_approve`.
4. Send:

```
POST {BASE_URL}/runs/{run_id}/resume
```

```json
{
  "suspension_id": "<from suspension.id>",
  "decision_type": "<user choice>",
  "decided_by": "claude-code-user",
  "reason": "<optional>"
}
```

After resume, poll the **child run id** from the response.

> Do **not** dispatch a new goal on the same `session_id` while any run is non-terminal — the API returns **409**.

---

## Step 6 — Use the results

1. Optionally fetch persisted session messages: `GET {BASE_URL}/sessions/{session_id}/messages?limit=50`
2. Integrate plans and findings into the current task.
3. If you discovered reusable insights, invoke `/hyper-learning` so the learning layer can improve future reasoning.

---

## When NOT to use this skill

- Simple file edits, renames, or lookups.
- You already have all the information you need.
- No Hyperstruck profile matches the task (step 2).
- The user explicitly says to skip hosted reasoning.

## Error handling

See [reference.md](reference.md) for full endpoint schemas and error codes. Summary:

- **Network errors**: retry twice with 5 s gap, then report and continue without.
- **401/403**: invalid key or insufficient scopes. Ask the user to check `HYPER_API_KEY`.
- **404**: stale agent or run ID. Re-list agents or confirm the run ID.
- **409**: session has a non-terminal run. Poll it first or omit `session_id`.
- **5xx**: retry once after 5 s; if still failing, report and continue.

### When to fetch `openapi.json` (troubleshooting only)

After a failed or confusing API call, if fixing IDs/payloads using [reference.md](reference.md) does not help, fetch once:

```
GET {BASE_URL}/openapi.json
```

Use it only to reconcile paths, methods, or fields — **do not** paste the whole spec into the user thread. Extract the minimum fragment needed, then continue. If `openapi.json` is unreachable, stay with `reference.md` and ask the user to confirm `HYPER_BASE_URL` and API version.
