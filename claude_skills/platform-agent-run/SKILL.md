---
name: platform-agent-run
description: >-
  Dispatch a goal to a Hyperstruck hosted agent for deeper cognitive reasoning,
  then poll for results. Use only when local work would benefit from remote
  planning, multi-step analysis, or cross-domain reasoning — NOT for simple edits
  or lookups you can handle directly.
argument-hint: "[optional goal text]"
effort: high
allowed-tools:
  - Bash(curl *)
  - WebFetch
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          once: true
          statusMessage: "Validating Hyperstruck API key..."
          command: |
            curl -sf -o /dev/null -w '' "${HYPER_BASE_URL:-https://api.core.hyperstruck.com}/agents?limit=1" \
              -H "Authorization: Bearer ${HYPER_API_KEY}" \
              -H "Accept: application/json" \
            || { echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Hyperstruck API key validation failed. Set HYPER_API_KEY or check HYPER_BASE_URL."}}'; exit 0; }
---

# Hyperstruck agent run

Use this skill when the current task needs **deeper reasoning, multi-step planning, or cross-domain analysis** that would benefit from a hosted Hyperstruck agent. Do **not** invoke for straightforward edits, lookups, or tasks you can complete directly.

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

---

## Step 2 — Discover the API (first use only)

Fetch the OpenAPI spec to confirm endpoints and adapt to schema changes:

```
GET {BASE_URL}/openapi.json
```

Look for these paths: `/agents`, `/agents/{agent_id}/goals`, `/runs/{run_id}`, `/runs/{run_id}/resume`, `/sessions/{session_id}/messages`. Note any new fields or endpoints.

If this fails, fall back to the paths hardcoded in [reference.md](reference.md).

---

## Step 3 — List agents and match to the task

```
GET {BASE_URL}/agents?limit=50
```

For each agent, inspect `name`, `core_config.description`, and `status`. Only `active` agents can run goals.

**If no agent's description fits the current task → stop early.** Tell the user:
> "None of your Hyperstruck agents match this task. Create one at your dashboard, or I'll continue without remote reasoning."

If one agent clearly matches, use it. If several match, list them briefly and ask the user to pick (or choose the best fit by description). Store the chosen `agent_id`.

---

## Step 4 — Build rich context (critical)

The user is already mid-session. A bare one-line goal is nearly useless. Assemble a **structured context block** before dispatching.

### Goal

If the user passed `$ARGUMENTS`, use that as the starting point. Otherwise, synthesize a clear, self-contained goal paragraph from the conversation so far. Include success criteria.

### Context (passed as the `context` JSON field)

Build a markdown block with these sections:

1. **Task background** — What the user is working on: repo, branch, project, deployment targets, environment constraints.
2. **Work done so far** — Summarize files read/written, commands run, data fetched from integrations (MCP tools, web searches, DB queries, etc.). Include key **findings and data**, not just tool names — the hosted agent cannot call your local tools.
3. **Learnings & pitfalls** — Anything discovered in this session: error patterns, API quirks, performance constraints, edge cases found.
4. **Open questions** — What needs deeper analysis, trade-off evaluation, or planning that you cannot resolve locally.
5. **Constraints** — Deadlines, compliance, tech-stack limits, performance budgets, cost concerns.

> **Tip:** Paste summarized MCP/integration results. The remote agent has no access to your local tools, Jira, Linear, Slack, or databases.

---

## Step 5 — Dispatch the goal

```
POST {BASE_URL}/agents/{agent_id}/goals
```

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
- `session_id` — set only to continue a previous Hyperstruck session whose last run is **terminal** (completed/failed). Omit to auto-create.
- `worker_profile` — `"default"` unless you need `"large"`.

Parse the response for `run.id` and `run.session_id`.

---

## Step 6 — Poll until terminal

```
GET {BASE_URL}/runs/{run_id}
```

### Polling strategy

- **3 s** intervals for the first 30 s.
- **5 s** intervals from 30 s to 2 min.
- **10 s** intervals after 2 min.
- **Stop after 10 min** and report last known status.

### On `completed`

Report the run output to the user. Look at `metadata.result` for structured output — present actionable next steps.

### On `failed`

Report `error` and `metadata`. Ask whether to retry or proceed without.

### On `suspended` (HITL)

1. Read `metadata.result.suspension.suspension_id`.
2. Present the suspension context to the user.
3. Ask for a decision: `approve`, `reject`, `modify`, `skip`, `provide_input`, or `partial_approve`.
4. Send:

```
POST {BASE_URL}/runs/{run_id}/resume
```

```json
{
  "suspension_id": "<from above>",
  "decision_type": "<user choice>",
  "decided_by": "claude-code-user",
  "reason": "<optional>"
}
```

After resume, poll the **child run id** from the response.

> Do **not** dispatch a new goal on the same `session_id` while any run is non-terminal — the API returns **409**.

---

## Step 7 — Use the results

1. Optionally fetch the full reasoning trace: `GET {BASE_URL}/sessions/{session_id}/messages?limit=50`
2. Integrate findings into the current task.
3. If you discovered reusable insights, invoke `/platform-learnings` to store them.

---

## When NOT to use this skill

- Simple file edits, renames, or lookups.
- You already have all the information you need.
- No Hyperstruck agents match the task (step 3).
- The user explicitly says to skip remote reasoning.

## Error handling

See [reference.md](reference.md) for full endpoint schemas and error codes. Summary:

- **Network errors**: retry twice with 5 s gap, then report and continue without.
- **401/403**: invalid key or insufficient scopes. Ask the user to check `HYPER_API_KEY`.
- **404**: stale agent or run ID. Re-list agents or confirm the run ID.
- **409**: session has a non-terminal run. Poll it first or omit `session_id`.
- **5xx**: retry once after 5 s; if still failing, report and continue.
