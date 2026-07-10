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
| `sources` | no | Up to 25 source-of-truth blocks. Each has non-empty `text` (maximum 100,000 characters), optional `id`, and optional `label`. These are the only request blocks admitted as grounding evidence. Supplying any sources activates the read-only faithfulness check. |
| `references` | no | Up to 25 exemplar/calibration blocks. Each has non-empty `text` (maximum 100,000 characters) and optional `label`. Shown to the model but never admitted as evidence. |

Use `sources` for authoritative specifications, records, transcripts, and tool
reads. Use `references` only to demonstrate desired tone, structure, style, or
format. Evidence supplied only through `context` or a reference cannot ground a
claim. If a source omits `id`, the runtime assigns `source-<index>`; explicit and
generated IDs must be unique across the source array. Source items accept only
`text`, `id`, and `label`; reference items accept only `text` and `label`.

Example:

```json
{
  "goal": "Recommend an implementation plan.",
  "context": "The caller needs a phased plan with explicit risks.",
  "sources": [
    {
      "id": "accepted-spec",
      "label": "Accepted specification",
      "text": "The migration must preserve identifiers and vectors."
    }
  ],
  "references": [
    {
      "label": "Preferred plan style",
      "text": "Milestone: ...\\nRisks: ...\\nVerification: ..."
    }
  ]
}
```

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
    "estimated_llm_cost_usd": "0",
    "estimated_total_cost_usd": "0",
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

Response `200` — a top-level `RunResponse` object. Unlike `POST /agents/{agent_id}/goals` and `POST /runs/{run_id}/resume`, this endpoint is **not** wrapped in a `run` property.

```json
{
  "id": "<uuid>",
  "agent_id": "<uuid>",
  "session_id": "<uuid>",
  "parent_run_id": null,
  "run_type": "goal",
  "status": "completed",
  "goal": "...",
  "worker_profile": "default",
  "started_at": "...",
  "ended_at": "...",
  "compute_seconds": "12.345",
  "estimated_compute_cost_usd": "0.001234",
  "estimated_llm_cost_usd": "0.012345",
  "estimated_total_cost_usd": "0.013579",
  "error": null,
  "metadata": {
    "result": {
      "success": true,
      "output": "...",
      "iterations": 3,
      "token_usage": {},
      "trace_id": "...",
      "error": null,
      "halted": false,
      "extraction_outcome": null,
      "engine_session_id": "..."
    }
  },
  "created_at": "..."
}
```

Status values: `queued`, `running`, `completed`, `failed`, `suspended`.

### Completed run — `metadata.result`

On success, expect at least:

- `output` — final user-facing string (or structured object) from the reasoning engine; **this is what orchestrators should surface** to the caller.
- `success`, `iterations`, `token_usage`, `trace_id`, `error`, `halted`, `extraction_outcome`, and `engine_session_id` when applicable.

Do **not** look for `duration_seconds` inside `metadata.result`. Worker duration is surfaced through top-level `compute_seconds` and cost fields. Internal scratchpad details are redacted from `GET /runs/{run_id}` responses.

If `output` is missing or `null`, the run did not return caller-usable guidance. Do not treat other metadata fields as a final answer.

Run response shape is unchanged by learning instance evidence. If a completed run or local caller context reveals reusable entity/outcome examples, store them later through the Learnings API `instances` field rather than expecting them on `RunResponse`.

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
