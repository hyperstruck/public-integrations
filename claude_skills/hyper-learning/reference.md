# Hyperstruck API reference (learnings)

Load this file when you need full request/response schemas or error-code details beyond what SKILL.md covers. Prefer this file during normal runs to save context. Fetch `{BASE_URL}/openapi.json` only when API errors suggest schema or path drift and this file is not enough.

---

## Endpoints

### Store a learning (async)

```
POST /agents/{agent_id}/learnings
```

| Field | Required | Description |
|-------|----------|-------------|
| `content` | yes | 1–5000 chars, actionable text |
| `learning_type` | yes | `tool_usage`, `approach`, `pitfall`, `prerequisite`, `coordination_pattern`, `agent_capability`, `conflict_insight`, `debate_outcome` |
| `confidence` | no | 0.0–1.0, default 0.5 |
| `source_goal` | no | Goal/task that produced this insight. For local or external runs, summarize the original task that generated the compacted evidence. |
| `applicable_goals` | no | Keyword tags for search relevance. Use this to align learnings with the selected agent's purpose and task domain. |
| `applicable_tools` | no | Tool names for search relevance. Use this for learnings distilled from compacted Cursor, MCP, CLI, browser, CI, or other external tool transcripts. |
| `privacy` | no | `shareable`, `agent_specific`, `sensitive` |
| `scope` | no | `"agent"` (default) or `"org"` (enterprise) |

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
| `min_confidence` | no | 0.0–1.0 |
| `learning_type` | no | Filter by type |
| `scope` | no | `agent` or `org` (enterprise) |

Response `200`:

```json
{
  "items": [
    {
      "learning": {
        "learning_id": "<uuid>",
        "content": "...",
        "learning_type": "pitfall",
        "confidence": 0.7,
        "trust_level": "unverified",
        "source_goal": "...",
        "applicable_goals": [],
        "applicable_tools": [],
        "times_applied": 0,
        "times_helpful": 0,
        "is_archived": false,
        "privacy": "shareable",
        "scope": "agent",
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
  "confidence": 0.79,
  "trust_level": "unverified",
  "times_applied": 1,
  "times_helpful": 1
}
```

Trust promotion: 5 consecutive positive reinforcements advance `unverified` → `agent_verified`.

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
