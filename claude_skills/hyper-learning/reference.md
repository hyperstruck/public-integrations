# Hyperstruck API reference (learnings)

Load this file when you need full request/response schemas or error-code details beyond what SKILL.md covers. Prefer this file during normal runs to save context. Treat this file as the contract: hosted Hyperstruck does not serve `{BASE_URL}/openapi.json`, and neither a 404 (authenticated: the route does not exist) nor a 401 (unauthenticated: the auth middleware runs before routing) means your base URL is wrong.

---

## Endpoints

### Store a learning (async)

```
POST /agents/{agent_id}/learnings
```

| Field | Required | Description |
|-------|----------|-------------|
| `content` | yes | 1–5000 chars, actionable text |
| `utility` | no | 0.0–1.0, default 0.5. Starting prior only. The value later returned in `standing.utility` is Core's derived, recency-weighted application-outcome score, updated from evidence that the learning helped or misled. Establishedness (reliability) is earned through corroboration, not set here. |
| `source_goal` | no | Goal/task that produced this insight. For local or external runs, summarize the original task that generated the compacted evidence. |
| `applicable_goals` | no | Keyword tags for search relevance. Use this to align learnings with the selected agent's purpose and task domain. |
| `applicable_tools` | no | Tool names for search relevance. Use this for learnings distilled from compacted Claude, Cursor, MCP, CLI, browser, CI, or other external tool transcripts. |
| `privacy` | no | `shareable`, `agent_specific`, `sensitive` |
| `instances` | no | Structured evidence examples. Each item requires `entity_values` and `outcome` string maps, with optional `source_context`. |

Instance evidence example:

```json
{
  "content": "qualify_lead returns cold for cybersecurity companies",
  "applicable_tools": ["qualify_lead"],
  "instances": [
    {
      "entity_values": {
        "company": "CrowdShield",
        "industry": "cybersecurity"
      },
      "outcome": {
        "tier": "cold",
        "score": "0.12"
      },
      "source_context": "claude-skill"
    }
  ]
}
```

Response `202`:

```json
{
  "request_id": "<uuid>",
  "worker_payload_version": "learning-store-worker-payload.v1"
}
```

Processing is **asynchronous**: deduplication, conflict detection, quota enforcement, and indexing happen in a background worker. The `request_id` is a correlation handle for logs. Wait a few seconds before searching.

For work completed outside hosted reasoning, store distilled insights from agent-purpose-aligned evidence rather than raw logs. Evidence may include local knowledge, repo facts, candidate learnings, errors, decisions, constraints, review feedback, and tool results. Include relevant task terms in `applicable_goals`, tool names in `applicable_tools`, and keep secrets, PII, hostnames, and unnecessary transcript details out of `content`.

### Search learnings

```
GET /agents/{agent_id}/learnings/search?q=<query>&limit=10
```

| Param | Required | Description |
|-------|----------|-------------|
| `q` | yes | 1–2000 chars, natural-language query |
| `limit` | no | 1–50, default 10 |
| `min_utility` | no | 0.0–1.0 |
| `scope` | no | `agent` or `org` (enterprise) |

Response `200`:

```json
{
  "items": [
    {
      "learning": {
        "learning_id": "<uuid>",
        "content": "...",
        "standing": {"utility": 0.7, "reliability": 0.4, "corroboration_count": 2},
        "trust_level": "unverified",
        "source_goal": "...",
        "applicable_goals": [],
        "applicable_tools": [],
        "times_applied": 0,
        "times_helpful": 0,
        "is_archived": false,
        "privacy": "shareable",
        "scope": "agent",
        "instances": [
          {
            "id": "content:...",
            "entity_values": {"company": "CrowdShield"},
            "outcome": {"tier": "cold"},
            "source_context": "claude-skill",
            "created_at": "..."
          }
        ],
        "created_at": "...",
        "updated_at": "..."
      },
      "score": 0.82
    }
  ],
  "total": 1
}
```

### Get a learning

```
GET /agents/{agent_id}/learnings/{learning_id}
```

Response `200` — full learning object (same shape as search result item's `learning` field).

### Reinforce a learning

```
POST /agents/{agent_id}/learnings/{learning_id}/reinforce
```

| Field | Required | Description |
|-------|----------|-------------|
| `is_helpful` | yes | boolean |

Response `200`:

```json
{
  "learning_id": "...",
  "standing": {"utility": 0.79, "reliability": 0.55, "corroboration_count": 3},
  "trust_level": "unverified",
  "times_applied": 1,
  "times_helpful": 1
}
```

Trust promotion: 5 consecutive positive reinforcements advance `unverified` → `agent_verified`.

`standing.utility` is an application-outcome signal, not a confidence score.
Recent outcomes carry more weight than older outcomes.

### Distill from a corpus (async)

```
POST /distill
```

Extracts grounded learnings from a corpus of evidence (docs, diffs, post-mortems, MCP/tool output) without a real run trace. Standalone — it does not participate in the resolve/observe/reinforce loop.

| Field | Required | Description |
|-------|----------|-------------|
| `agent_name` | yes | Boundary agent **name** (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`), not the `HYPER_AGENT_ID` UUID. The corpus is distilled into this agent. |
| `run_id` | yes | Must start with `distill:` (namespaced so it never collides with a loop run id). |
| `goal` | yes | The extraction intent (≤ 8000 chars). |
| `evidence` | yes | 2–50 items. Each: `id`, `content` (≤ 8000 chars), optional `label`, `role` (`support`/`contrast`/`neutral`), `status` (`completed`/`failed`), `source_ref` (a non-secret doc id or URL). |
| `outcome` | yes | `{ "is_success": bool, "summary"?: str }`. |
| `evaluation` | no | Reviewer verdict / contrast aid (≤ 8000 chars); folded into the grounding corpus. |
| `synthesis_notes` | no | Optional extra context (≤ 8000 chars). |

**Validation gates** (400 before the 202): fewer than 2 items; total non-whitespace content < 500 or > 120,000 chars; `run_id` missing the `distill:` prefix; `occurred_at` in the future; **no declared contrast signal**. Declare contrast via differing `status`, a `contrast`+`support` pairing, differing roles, or a non-empty `evaluation`. Structural violations (item > 8000 chars, > 50 items, unknown field) surface as `422`.

Response `202`:

```json
{
  "status": "accepted",
  "run_id": "distill:...",
  "worker_payload_version": "boundary-worker-payload.v1"
}
```

A corpus with no declared contrast is rejected before the `202`. A corpus that declares contrast but whose text carries no reusable contrast is accepted and yields nothing (a valid zero-yield 202). Results are searchable via the search endpoint a few seconds later.

---

## Error codes

| HTTP | Meaning | Action |
|------|---------|--------|
| 202 | Accepted (async store) | Wait before searching |
| 400 | Validation error | Fix request body |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden (scope/entitlement) | Check plan or scopes |
| 404 | Agent or learning not found | Verify ID |
| 503 | Runtime unavailable | Check provider setup |

---

## Trust lifecycle

```
unverified → agent_verified → source_verified → corroborated
```

Advanced by consecutive positive reinforcements. Negative reinforcement resets the streak but does not demote the level.
