---
name: platform-learnings-recall
description: >-
  Read-heavy workflow: search + get relevant learnings before local work; reinforce after.
  API key from HYPER_API_KEY, .env, or user-supplied context.
---

# Recall learnings before acting (search-first)

## When to use

At the **start** of a complex task, before editing code or calling a hosted agent goal, retrieve what the platform already knows for this agent/tenant.

## Steps

1. **Handoff** — Run **platform-context-handoff** and derive 1–3 short **search queries** from the goal (keywords, stack names, failure modes).
2. **Search** — **GET** `/agents/{agent_id}/learnings/search?q=...&limit=10` (add filters if useful).
3. **Deep read** — For top hits, **GET** `/agents/{agent_id}/learnings/{learning_id}` when you need full fields.
4. **Integrate** — Summarize findings for the human; cite `learning_id` only (not secret).
5. **After the task** — If a learning helped or hurt, **POST** `.../reinforce` with `is_helpful`.

## Auth

`HYPER_API_KEY` resolution order: explicit user-provided → env → `.env` / `PUBLIC_INTEGRATIONS_ENV_FILE`.

## Pitfalls

- Low-quality `q` returns noise; iterate queries.
- Org scope (`scope=org`) may be forbidden on some plans (**403**).
- Newly stored learnings may not appear instantly (**async store**).

## Optional script

```bash
python public_integrations/scripts/platform_api_client.py learnings-search --query "your keywords"
```
