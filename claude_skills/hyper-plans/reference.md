# Hyperstruck API reference (plans)

Load this file when you need full request/response schemas or error-code details beyond what `SKILL.md` covers. Fetch `{BASE_URL}/openapi.json` only when this file and the inline skill instructions are insufficient.

---

## Endpoints

### Search similar plans for one agent

```
GET /agents/{agent_id}/plans/similar?q=<query>&limit=10
```

| Param | Required | Description |
|-------|----------|-------------|
| `q` | yes | 1-2000 chars, natural-language query |
| `limit` | no | Requested max results; capped at 10 per agent |

Response `200`:

```json
{
  "items": [
    {
      "plan": {
        "plan_id": "plan-123",
        "agent_id": "00000000-0000-0000-0000-000000000000",
        "goal": "Investigate flaky retries",
        "summary": null,
        "reasoning": null,
        "is_success": true,
        "executed_at": "2026-04-21T08:00:00Z",
        "num_steps": 0,
        "milestones": null,
        "steps": null
      },
      "similarity_score": 0.83,
      "candidate_learnings": [
        {
          "learning_id": "learning-1",
          "content": "Cap retries at 3 with jitter.",
          "score": 0.71,
          "trust_level": "agent_verified"
        }
      ]
    }
  ],
  "retrieved_at": "2026-04-21T08:00:00Z",
  "partial_failures": []
}
```

Candidate learnings stay compact in plan-search responses. To inspect structured instance evidence for a candidate, call `GET /agents/{agent_id}/learnings/{learning_id}` from the Learnings API.

### Search similar plans across multiple agents

```
POST /plans/similar
```

```json
{
  "agent_ids": [
    "00000000-0000-0000-0000-000000000000",
    "11111111-1111-1111-1111-111111111111"
  ],
  "q": "retry strategy",
  "limit": 10
}
```

Response `200`: same shape as single-agent search, but `partial_failures` may contain degraded agents.

---

## Error codes

| HTTP | Meaning | Action |
|------|---------|--------|
| 422 | Validation error | Fix params/body |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden | Missing `agents:read` or unauthorized agent ids |
| 503 | Runtime unavailable | Memory runtime or retrieval dependency missing |
