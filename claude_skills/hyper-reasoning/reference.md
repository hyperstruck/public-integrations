# Hyperstruck API reference (goals & reasoning runs)

Load this file when you need full request/response schemas or error-code details beyond what SKILL.md covers. Prefer this file during normal runs to save context. Fetch `{BASE_URL}/openapi.json` only when API errors suggest schema or path drift and this file is not enough.

---

## Endpoints

### List agents

```
GET /agents?limit=50&cursor=<optional>
```

Response `200`:

```json
{
  "items": [
    {
      "id": "<uuid>",
      "name": "...",
      "status": "active",
      "model_provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "reasoning_profile": "full",
      "memory_profile": "default",
      "knowledge_scope": "agent",
      "core_config": {
        "instructions": "...",
        "description": "...",
        "temperature": null,
        "max_tokens": null,
        "hitl_enabled": false,
        "hitl_autonomy_level": 5,
        "hitl_policy_preset": "autonomy",
        "metadata": {}
      },
      "llm_credential": null,
      "created_at": "..."
    }
  ],
  "next_cursor": null
}
```

Key fields for agent selection:
- `name` — human-readable label.
- `core_config.description` — what the agent is designed to do.
- `status` — must be `active` to run goals.

### Dispatch a goal

```
POST /agents/{agent_id}/goals
```

Request body:

| Field | Required | Description |
|-------|----------|-------------|
| `goal` | yes | Non-empty string |
| `context` | no | Additional context for the reasoning runtime. Include agent-purpose-aligned local knowledge, candidate learnings, compacted external-run evidence, files changed, tool inputs/results, errors, tests, review feedback, decisions, constraints, and final outcome when work happened outside hosted reasoning. |
| `session_id` | no | Omit to auto-create; set to continue an existing session (must have no non-terminal runs) |
| `worker_profile` | no | `"default"` or `"large"` |
| `metadata` | no | Arbitrary dict persisted on the run |

Response `202`:

```json
{
  "run": {
    "id": "<uuid>",
    "agent_id": "<uuid>",
    "session_id": "<uuid>",
    "parent_run_id": null,
    "run_type": "goal",
    "status": "queued",
    "goal": "...",
    "worker_profile": "default",
    "started_at": null,
    "ended_at": null,
    "compute_seconds": "0",
    "estimated_compute_cost_usd": "0",
    "error": null,
    "metadata": {},
    "created_at": "..."
  },
  "worker_payload_version": "run-worker-payload.v1"
}
```

### Poll a run

```
GET /runs/{run_id}
```

Response `200` — same `RunResponse` shape as above (inside `run` or at top level depending on wrapper).

Status values: `queued`, `running`, `completed`, `failed`, `suspended`.

### Completed run — `metadata.result`

On success, expect at least:

- `output` — final user-facing string (or structured object) from the reasoning engine; **this is what orchestrators should surface** to the caller.
- `success`, `iterations`, `token_usage`, `error`, and `duration_seconds` when applicable.

If `output` is missing or `null`, the run did not return caller-usable guidance. Do not treat other metadata fields as a final answer.

When `status == "suspended"`, look for:

```json
{
  "metadata": {
    "result": {
      "suspension": {
        "id": "..."
      }
    }
  }
}
```

### Resume a suspended run

```
POST /runs/{run_id}/resume
```

| Field | Required | Description |
|-------|----------|-------------|
| `suspension_id` | yes | From `metadata.result.suspension.id` on the suspended run |
| `decision_type` | yes | `approve`, `reject`, `modify`, `skip`, `provide_input`, `partial_approve` |
| `data` | no | Dict for `modify` or `provide_input` |
| `decided_by` | no | Identifier for audit trail |
| `reason` | no | Human-readable reason |
| `worker_profile` | no | `"default"` |
| `metadata` | no | Arbitrary dict for the child run |

Response `202` — returns a new child `RunResponse`.

### Session messages

```
GET /sessions/{session_id}/messages?limit=50
```

### Session runs

```
GET /sessions/{session_id}/runs?limit=20
```

---

## Error codes

| HTTP | Meaning | Action |
|------|---------|--------|
| 400 | Validation error | Fix request body |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden (scope/entitlement) | Check scopes or plan |
| 404 | Agent/run/session not found | Verify IDs |
| 409 | Session has a non-terminal run | Poll/resume existing run first |
| 5xx | Server error | Retry once after 5 s |

---

## Pagination

All list endpoints return `next_cursor`. Pass it as `?cursor=<value>` for the next page. When `next_cursor` is `null`, you are on the last page.
