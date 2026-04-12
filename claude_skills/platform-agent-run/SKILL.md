---
name: platform-agent-run
description: >-
  Dispatch a goal to a Hyperstruck hosted agent for deeper cognitive reasoning,
  then poll for results. Use only when local Claude Code work would benefit from
  a remote planning/reasoning pass — do NOT invoke for simple, well-scoped tasks.
---

# Hyperstruck agent run

Use this skill when the current task needs **deeper reasoning, multi-step planning, or cross-domain analysis** that would benefit from a hosted agent. Do **not** invoke it for straightforward edits, lookups, or tasks you can complete directly.

---

## 1. Resolve configuration

### API key

Try each source in order; stop at the first hit. **Never echo the key.**

1. A value the user explicitly provided in the current conversation.
2. The environment variable `HYPER_API_KEY`.
3. A `.env` file in the project root (or the path in `PUBLIC_INTEGRATIONS_ENV_FILE`).
   Look for a line `HYPER_API_KEY=<value>`.

If none found → **stop and ask the user to set one of the above.**

### Base URL

Default: `https://api.core.hyperstruck.com`

Override via (in order): explicit user instruction → `HYPER_BASE_URL` env var → `.env` file (`HYPER_BASE_URL=...`).

Strip any trailing slash.

### Headers for every request

```
Authorization: Bearer <API_KEY>
Content-Type: application/json
Accept: application/json
```

---

## 2. Discover the API (optional, on first use)

Fetch the OpenAPI spec so you can adapt if endpoints or schemas change:

```
GET {BASE_URL}/openapi.json
```

Parse the JSON and note:
- The `paths` object — confirm `/agents`, `/agents/{agent_id}/goals`, `/runs/{run_id}`, `/runs/{run_id}/resume`, `/sessions/{session_id}/messages` exist.
- Schema names for request/response bodies (`GoalRunRequest`, `RunResponse`, `AgentResponse`, etc.).
- Any new endpoints or fields not covered below.

If the fetch fails (network error, 404, auth error), **fall back to the hardcoded paths in this skill** — they are stable.

---

## 3. List agents and choose the right one

```
GET {BASE_URL}/agents?limit=50
```

Response shape (JSON):

```json
{
  "items": [
    {
      "id": "<uuid>",
      "name": "...",
      "status": "active",
      "core_config": {
        "description": "...",
        "instructions": "..."
      },
      ...
    }
  ],
  "next_cursor": null
}
```

For each agent inspect:
- `name` and `core_config.description` — does it match the user's current task domain?
- `status` — only `active` agents can run goals.

**If no agent's description fits the task → stop early.** Tell the user:
> "None of your Hyperstruck agents seem suited to this task. You can create one at your dashboard or skip the remote reasoning step."

If there is exactly one suitable agent, use it. If multiple match, briefly list them and ask the user to confirm (or pick the best match by description).

Store the chosen `agent_id`.

---

## 4. Build rich context (critical)

The user is already in the middle of a Claude Code session. A bare one-line goal is nearly useless. You **must** assemble a structured context block:

### Goal (required)

Write a clear, self-contained goal paragraph. It should make sense to someone who has never seen this chat. Include success criteria.

### Context (required — pass as the `context` field)

Build a markdown block containing:

1. **Task background** — What the user is working on, the repo/project, the branch, any deployment or environment constraints.
2. **Work done so far** — Summarize what you have already accomplished in this session: files read/written, commands run, data fetched from integrations (MCP tools, web searches, etc.). Include key **findings and outputs**, not just tool names.
3. **Learnings & pitfalls** — Anything you discovered that matters: error patterns, API quirks, performance constraints, edge cases.
4. **Open questions** — What needs deeper analysis, trade-off evaluation, or multi-step planning.
5. **Constraints** — Deadlines, compliance, tech stack limits, performance budgets.

> **Tip:** If you used MCP integrations (Jira, Linear, Slack, DB queries, etc.) paste summarized results — the hosted agent cannot call your local tools.

---

## 5. Dispatch the goal

```
POST {BASE_URL}/agents/{agent_id}/goals
```

Body:

```json
{
  "goal": "<structured goal from step 4>",
  "context": "<full context block from step 4>",
  "metadata": {
    "source": "claude-code-skill",
    "task_summary": "<one-line description>"
  }
}
```

Optional fields:
- `session_id` — set only when continuing a previous Hyperstruck session whose last run is **terminal** (completed/failed). Omit to auto-create a new session.
- `worker_profile` — `"default"` unless you need `"large"`.

Parse the response:

```json
{
  "run": {
    "id": "<run_id>",
    "session_id": "<session_id>",
    "status": "queued",
    ...
  }
}
```

Save `run_id` and `session_id`.

---

## 6. Poll until terminal

```
GET {BASE_URL}/runs/{run_id}
```

Repeat until `status` is one of: `completed`, `failed`, `suspended`.

### Polling strategy

- Start at **3-second** intervals.
- After 30 seconds, slow to **5-second** intervals.
- After 2 minutes, slow to **10-second** intervals.
- **Stop after 10 minutes** maximum and report the last known status to the user.

### On `completed`

Report the run summary to the user. Look at `metadata.result` for structured output — present it as actionable next steps for the current task.

### On `failed`

Report `error` and any details from `metadata`. Ask the user whether to retry or proceed without the remote reasoning.

### On `suspended` (HITL)

The agent hit a human-in-the-loop checkpoint and is waiting for a decision.

1. Read `metadata.result.suspension.suspension_id` from the run response.
2. Present the suspension context to the user: what gate was hit and why.
3. Ask for a decision: **approve**, **reject**, **modify**, **skip**, **provide_input**, or **partial_approve**.
4. Send:

```
POST {BASE_URL}/runs/{run_id}/resume
```

Body:

```json
{
  "suspension_id": "<from step 1>",
  "decision_type": "<user choice>",
  "decided_by": "claude-code-user",
  "reason": "<optional user reason>"
}
```

Optional: `data` (dict, for `modify` or `provide_input`), `worker_profile`, `metadata`.

After resume, parse the response for the **child run id** and go back to polling (step 6) with that new run id.

> **Do not** start a new goal on the same `session_id` while any run is non-terminal — the API returns **409 Conflict**.

---

## 7. Use the results

After the run completes:

1. Optionally fetch session messages for the full reasoning trace:
   ```
   GET {BASE_URL}/sessions/{session_id}/messages?limit=50
   ```
2. Integrate findings into your current task — update code, plans, or recommendations.
3. If you discovered reusable insights, consider using the **platform-learnings** skill to store them.

---

## When NOT to use this skill

- The task is a simple file edit, rename, or lookup.
- You already have all the information you need.
- The user has not set up any Hyperstruck agents (step 3 found none).
- The user explicitly says to skip remote reasoning.

## Error handling

- **Network errors** (connection refused, DNS failure, timeout): report to the user; do not retry more than twice with a 5-second gap.
- **401/403**: API key is invalid or lacks scopes. Ask the user to check their key.
- **404 on agent or run**: the ID is stale. Re-list agents or ask for the correct run ID.
- **409 on goal dispatch**: a non-terminal run exists on that session. Poll the existing run first or omit `session_id` to start a fresh session.
- **5xx**: transient server error. Retry once after 5 seconds; if still failing, report and continue without.
