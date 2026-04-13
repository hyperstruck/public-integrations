---
name: hyper-learning
description: >-
  Manage Hyperstruck learnings: store reusable insights, search existing knowledge,
  retrieve by ID, and reinforce with feedback. Use to capture or recall experience
  during local work and to feed the platform learning layer that improves reasoning
  over time.
argument-hint: "[search query or 'store' or 'reinforce']"
allowed-tools:
  - Bash(curl *)
  - WebFetch
---

# Hyperstruck learnings management

Store, search, and reinforce learnings on the Hyperstruck platform — the practical learning layer that accumulates knowledge to support structured reasoning. Use this to:

- **Recall** relevant knowledge before starting complex work.
- **Capture** insights discovered during local coding.
- **Reinforce** past learnings to improve their ranking for future use.

## Current environment

```!
echo "HYPER_BASE_URL=${HYPER_BASE_URL:-https://api.core.hyperstruck.com}"
echo "HYPER_AGENT_ID=${HYPER_AGENT_ID:-<not set>}"
echo "HYPER_API_KEY_SET=$([ -n \"$HYPER_API_KEY\" ] && echo yes || echo no)"
if [ -f .env ]; then echo "dotenv=found (.env)"; else echo "dotenv=not found"; fi
```

If `HYPER_API_KEY_SET=no` above, check `.env` for a `HYPER_API_KEY=` line. If still missing, **stop and ask the user** to set `HYPER_API_KEY`.

---

## Configuration

- **Base URL**: `HYPER_BASE_URL` from above, defaulting to `https://api.core.hyperstruck.com`.
- **API key**: Resolved above. **Never echo it.**
- **Agent ID**: `HYPER_AGENT_ID` from above. If `<not set>`, call `GET {BASE_URL}/agents?limit=50` and ask the user to pick an agent (learnings are scoped per agent).
- **Headers**:
  ```
  Authorization: Bearer <API_KEY>
  Content-Type: application/json
  Accept: application/json
  ```

---

## How to interpret `$ARGUMENTS`

The user may invoke this skill as:

- `/hyper-learning retry backoff strategies` → treat as a **search** query.
- `/hyper-learning store` → the user wants to **store** a new learning (ask for content or derive from chat).
- `/hyper-learning reinforce <learning_id>` → reinforce a specific learning.
- `/hyper-learning` (no arguments) → ask what they want to do, or default to **search** for the current task context.

---

## Search learnings

```
GET {BASE_URL}/agents/{agent_id}/learnings/search?q=<keywords>&limit=10
```

Optional query params: `min_confidence` (0.0–1.0), `learning_type`, `scope` (`agent` or `org` — org may require enterprise; expect 403).

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
        "trust_level": "unverified"
      },
      "score": 0.82
    }
  ],
  "total": 1
}
```

Cite `learning_id` for traceability (not a secret). To get full fields: `GET {BASE_URL}/agents/{agent_id}/learnings/{learning_id}`.

---

## Store a learning

```
POST {BASE_URL}/agents/{agent_id}/learnings
```

```json
{
  "content": "<actionable, specific — 1 to 5000 chars>",
  "learning_type": "<type>",
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

### Async store

Returns **202 Accepted** with `request_id`. Indexing is asynchronous (deduplication, conflict detection). **Wait a few seconds** before searching for the new learning.

### Writing good learnings

- Be **specific and actionable**: "Always include a date range filter when querying the analytics API — without it, responses exceed 30 seconds" beats "Be careful with the API."
- Prefer **multiple small learnings** over one large paragraph.
- Strip secrets, PII, and internal hostnames from `content`.
- Set `applicable_goals` and `applicable_tools` so the learning surfaces when relevant.

---

## Reinforce a learning

```
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce
```

```json
{ "is_helpful": true }
```

Or `false`. Updates confidence and advances trust lifecycle (`unverified` → `agent_verified` → `source_verified` → `corroborated`).

Always reinforce when you can — it improves future search ranking.

---

## Typical workflows

### Recall-then-act

1. **Search** for learnings relevant to the current task.
2. Incorporate findings into your plan.
3. After the task, **reinforce** learnings that helped (or mark unhelpful).
4. **Store** any new insights discovered.

### Quick capture

1. Notice a pitfall or effective pattern while coding.
2. **Store** it immediately. Continue working.

### Batch review

1. **Search** broadly (`q=api+best+practices&limit=50`).
2. Review for accuracy. **Reinforce** each (helpful/unhelpful).

---

## Error handling

- **401/403**: invalid key or lacking scopes → ask user to check `HYPER_API_KEY`.
- **404**: agent or learning not found → verify ID.
- **403 on `scope=org`**: requires enterprise entitlement.
- **Network errors**: retry once after 3 s; if still failing, report and stop.

For full endpoint schemas, see [reference.md](reference.md).
