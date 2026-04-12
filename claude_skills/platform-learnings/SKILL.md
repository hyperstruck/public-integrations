---
name: platform-learnings
description: >-
  Manually manage Hyperstruck learnings: store reusable insights, search existing
  knowledge, retrieve by ID, and reinforce with feedback. Use when you want to
  persist or recall experience without going through a full agent run.
---

# Hyperstruck learnings management

Use this skill to **directly** store, search, and reinforce learnings on the Hyperstruck platform — independent of running a hosted agent goal. Useful for:

- Capturing insights discovered during local work so future agent runs (or your own sessions) benefit.
- Searching for relevant knowledge before starting a complex task.
- Giving feedback on past learnings to improve their ranking.

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

### Agent ID

Learnings are scoped to an agent. Resolve agent ID via:

1. Explicit user-provided value.
2. `HYPER_AGENT_ID` env var or `.env` (`HYPER_AGENT_ID=...`).
3. If not set, call `GET {BASE_URL}/agents?limit=50` and ask the user to pick an agent.

### Headers for every request

```
Authorization: Bearer <API_KEY>
Content-Type: application/json
Accept: application/json
```

---

## 2. Discover the API (optional, on first use)

```
GET {BASE_URL}/openapi.json
```

Confirm the learnings paths exist:
- `POST /agents/{agent_id}/learnings`
- `GET  /agents/{agent_id}/learnings/search`
- `GET  /agents/{agent_id}/learnings/{learning_id}`
- `POST /agents/{agent_id}/learnings/{learning_id}/reinforce`

If the fetch fails, fall back to the paths hardcoded below.

---

## 3. Search existing learnings (recall before acting)

Before starting complex work, check what the platform already knows:

```
GET {BASE_URL}/agents/{agent_id}/learnings/search?q=<keywords>&limit=10
```

Optional query params:
- `min_confidence` (0.0–1.0)
- `learning_type` (e.g. `pitfall`, `approach`, `tool_usage`)
- `scope` (`agent` or `org` — org may require enterprise entitlement; expect 403 if unavailable)

Response:

```json
{
  "items": [
    {
      "learning": {
        "learning_id": "...",
        "content": "...",
        "learning_type": "pitfall",
        "confidence": 0.7,
        "trust_level": "unverified",
        ...
      },
      "score": 0.82
    }
  ],
  "total": 1
}
```

Use the results to inform your plan. Cite `learning_id` for traceability (it is not a secret).

### Get a learning by ID

```
GET {BASE_URL}/agents/{agent_id}/learnings/{learning_id}
```

Use when you need full fields from a search hit.

---

## 4. Store a learning

When you discover something reusable — a pitfall, a working approach, a tool quirk — persist it:

```
POST {BASE_URL}/agents/{agent_id}/learnings
```

Body:

```json
{
  "content": "<actionable, specific text — 1 to 5000 chars>",
  "learning_type": "<see types below>",
  "confidence": 0.6,
  "source_goal": "<what task produced this insight>",
  "applicable_goals": ["keyword1", "keyword2"],
  "applicable_tools": ["tool_name"],
  "privacy": "shareable"
}
```

### Learning types

| Type | When to use |
|------|-------------|
| `tool_usage` | How to use a specific tool effectively |
| `approach` | A strategy or pattern that worked |
| `pitfall` | Something to avoid (common failure mode) |
| `prerequisite` | Something that must be true before an approach works |
| `coordination_pattern` | Effective coordination strategies |
| `agent_capability` | What agents are good or bad at |
| `conflict_insight` | How conflicts were resolved |
| `debate_outcome` | What debates concluded and why |

### Important: store is asynchronous

The API returns **202 Accepted** with a `request_id`. The learning is processed in the background (deduplication, conflict detection, indexing). **Wait a few seconds** before searching for it.

### Writing good learnings

- Be **specific and actionable**: "When querying the analytics API, always include a date range filter — without it responses exceed 30 seconds" is better than "Be careful with the API."
- Prefer **multiple small learnings** over one large paragraph.
- Strip secrets, PII, and internal hostnames from `content`.
- Set `applicable_goals` and `applicable_tools` so the learning surfaces when relevant.

---

## 5. Reinforce a learning

After applying a learning in real work, report whether it helped:

```
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce
```

Body:

```json
{ "is_helpful": true }
```

or `false`. This updates confidence and advances the trust lifecycle (`unverified` → `agent_verified` → `source_verified` → `corroborated` after consecutive positive reinforcements).

Always reinforce when you can — it improves future search ranking.

---

## Typical workflows

### Recall-then-act

1. **Search** for learnings relevant to the current task (step 3).
2. Incorporate findings into your plan.
3. After the task, **reinforce** any learnings that helped (or mark unhelpful).
4. If you discovered new insights, **store** them (step 4).

### Capture during work

1. While coding, notice a pitfall or effective pattern.
2. **Store** it immediately so it is indexed before you forget.
3. Continue working.

### Batch review

1. **Search** broadly (e.g. `q=api+best+practices&limit=50`).
2. Review returned learnings for accuracy.
3. **Reinforce** each (helpful or unhelpful) to tune the corpus.

---

## Error handling

- **401/403**: invalid key or lacking scopes. Ask the user to check credentials.
- **404**: agent or learning not found. Verify the ID.
- **403 on `scope=org`**: org-scope requires enterprise entitlement.
- **Network errors**: retry once after 3 seconds; if still failing, report and stop.
