---
name: platform-learnings
description: >-
  Learnings API: POST store (202 async), GET search, GET by id, POST reinforce.
  Uses HYPER_API_KEY from env, .env, or explicit context. Reminds to wait after store.
---

# Learnings lifecycle (store, search, get, reinforce)

## Prerequisites

Use **platform-context-handoff** so `content` is grounded in real experience (goal, tools, outcomes), not generic advice.

## Authentication

Same as agent runs: `HYPER_API_KEY` (env → `.env` / `PUBLIC_INTEGRATIONS_ENV_FILE` → explicit). Header: `Authorization: Bearer <key>`.

## Endpoints

| Action | Method | Path |
|--------|--------|------|
| Store (async) | POST | `/agents/{agent_id}/learnings` |
| Search | GET | `/agents/{agent_id}/learnings/search?q=...` |
| Get | GET | `/agents/{agent_id}/learnings/{learning_id}` |
| Reinforce | POST | `/agents/{agent_id}/learnings/{learning_id}/reinforce` |

## Store

**POST** `/agents/{agent_id}/learnings`

Required JSON:

- `content` (1–5000 chars, actionable and specific)
- `learning_type` — one of: `tool_usage`, `approach`, `pitfall`, `prerequisite`, `coordination_pattern`, `agent_capability`, `conflict_insight`, `debate_outcome`

Optional: `confidence`, `source_goal`, `applicable_goals`, `applicable_tools`, `privacy`, `scope` (where supported)

**Important:** Successful dispatch often returns **202 Accepted**. Processing is **asynchronous** — deduplication, quotas, and indexing happen later. **Wait** (e.g. a few seconds) before expecting `search` to return the new item.

## Search

**GET** `/agents/{agent_id}/learnings/search?q=<query>&limit=<1-50>&min_confidence=<0-1>&learning_type=...&scope=agent|org`

- `q` is required (short natural-language query).
- `scope=org` may require an enterprise entitlement (otherwise **403**).

## Get by ID

Use `learning_id` from search results.

## Reinforce

**POST** `/agents/{agent_id}/learnings/{learning_id}/reinforce` with JSON `{"is_helpful": true|false}`.

Call this after you applied the learning in a real task so the system can adjust confidence and trust.

## Python helper examples

```bash
python public_integrations/scripts/platform_api_client.py learnings-store \
  --content "..." \
  --learning-type pitfall \
  --source-goal "..."

python public_integrations/scripts/platform_api_client.py learnings-search \
  --query "retry backoff"

python public_integrations/scripts/platform_api_client.py learnings-reinforce \
  --learning-id "<uuid>" --helpful
```

## Agent checklist

1. Strip secrets and customer data from `content`.
2. Prefer several **small** learnings over one huge paragraph.
3. After store, **sleep or poll search** lightly; do not assume immediate consistency.
