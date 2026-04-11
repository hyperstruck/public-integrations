---
name: platform-agent-run
description: >-
  Call hosted agent APIs: POST goals, poll GET run status (queued/running/completed/failed/suspended),
  POST resume when suspended, optional continuation on same session. Resolves HYPER_API_KEY from env or .env.
---

# Hosted agent runs (goals, polling, resume, continuation)

## Prerequisites

Run **platform-context-handoff** first so `goal`, `context`, `HYPER_BASE_URL`, and `HYPER_AGENT_ID` are explicit.

## Authentication

Resolve the API key in order:

1. Value provided in the current task (do not repeat it in output).
2. `HYPER_API_KEY` environment variable.
3. `.env` or `PUBLIC_INTEGRATIONS_ENV_FILE` with `HYPER_API_KEY=`.

Use header: `Authorization: Bearer <key>` and `Content-Type: application/json` for POST bodies.

## Endpoints (REST)

| Action | Method | Path |
|--------|--------|------|
| Start run | POST | `/agents/{agent_id}/goals` |
| Poll run | GET | `/runs/{run_id}` |
| Resume | POST | `/runs/{run_id}/resume` |
| Session messages | GET | `/sessions/{session_id}/messages?limit=...` |
| Session runs | GET | `/sessions/{session_id}/runs?limit=...` |

`{agent_id}` and `{run_id}` are UUIDs. Base URL has no trailing slash.

## Start a goal

**POST** `/agents/{agent_id}/goals`

Required JSON field:

- `goal` (non-empty string)

Optional:

- `context` — include the handoff summary and tool summaries.
- `session_id` — omit to auto-create a session; set to continue the same session after prior runs are **terminal**.
- `worker_profile`, `metadata`

Example body:

```json
{
  "goal": "<from handoff>",
  "context": "<condensed handoff + prior learnings + tool notes>",
  "metadata": { "source": "claude-code-integration" }
}
```

Parse the response for `run.id` and `run.session_id` (field names match your API schema).

## Poll until terminal

**GET** `/runs/{run_id}` repeatedly until `status` is one of: `completed`, `failed`, or handle `suspended`.

Polling guidance:

- Default interval **2 seconds**, backoff slightly if the API returns rate limits (429) or transient errors (5xx) — retry with cap.
- Stop after a **maximum wall time** (e.g. 10–30 minutes) and report last known status to the human.

### Status: `suspended` (HITL)

When status is `suspended`, read suspension metadata from the run payload (e.g. `suspension_id`). **Do not** start another goal on the same `session_id` while a run is non-terminal — the API may return **409 Conflict**.

Ask the human for a decision, then:

**POST** `/runs/{run_id}/resume`

Required JSON:

- `suspension_id`
- `decision_type` — one of: `approve`, `reject`, `modify`, `skip`, `provide_input`, `partial_approve`

Optional: `data`, `decided_by`, `reason`, `worker_profile`, `metadata`

After resume, poll the **new child run** id returned by the API (or follow your API’s pattern for child runs).

## Continuation (new goal, same session)

When the previous run is **terminal**, you may send another **POST** `/agents/{agent_id}/goals` with the same `session_id` for a new user turn.

## Optional: Python helper

From the repo that contains `public_integrations/`:

```bash
python public_integrations/scripts/platform_api_client.py goal-run \
  --goal "..." \
  --context "..." \
  --session-id "<optional>"
```

Use `poll-run`, `resume-run`, and `session-messages` subcommands as needed (`--help`).

## What to report back to the human

- Final run status and a short summary of `metadata` / messages if available.
- `session_id` and `run_id` for traceability (these are identifiers, not secrets).
