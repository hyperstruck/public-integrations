# Hyperstruck learning reference

This skill drives the hosted learning loop through the editor hooks. Load
this file when you need the request shapes or the interim manual-curation path.

---

## The learning loop (automatic)

The loop runs for you via the installed hooks; you do not call these by hand. They
are listed so you understand what is happening.

| Step | Endpoint | When | Purpose |
|------|----------|------|---------|
| resolve | `POST /resolve` | turn start | Return goal-relevant learnings to inject. Server stores the offer log keyed by `run_id`. |
| observe | `POST /observe` | deferred to next turn start | Extract new learnings from the finished episode (server-side producer + critic). |
| reinforce | `POST /reinforce` | deferred to next turn start | Credit/penalise the learnings that were offered at resolve. |

The write side is deferred one turn so the user's next prompt supplies ground
truth for the prior turn's outcome. All of this is handled by
`python -m hyperstruck.ide.hook`; the recall command in SKILL.md is the only piece
you invoke, and only on Cursor.

Auth and the configured agent come from `~/.hyperstruck/.env`
(`HYPER_API_KEY`, `HYPER_BASE_URL`, `HYPER_AGENT_ID`), written by `hyper-install`.

---

## Manual curation (interim: curation API)

Durable, human curation belongs in the Hyperstruck dashboard (coming). Until it
ships, use the curation API directly. These endpoints are supported and not
deprecated; the dashboard will be built on them.

Headers for every request:

```
Authorization: Bearer <HYPER_API_KEY>
Content-Type: application/json
Accept: application/json
```

Add a high-signal learning verbatim:

```
POST {BASE_URL}/agents/{agent_id}/learnings
```

```json
{
  "content": "<actionable, specific insight>",
  "utility": 0.6,
  "source_goal": "<task that produced it>",
  "applicable_goals": ["keyword1", "keyword2"],
  "applicable_tools": ["tool_name"],
  "privacy": "shareable"
}
```

Search, inspect, and reinforce-by-id for curation:

```
GET  {BASE_URL}/agents/{agent_id}/learnings/search?q=<keywords>&limit=10
GET  {BASE_URL}/agents/{agent_id}/learnings/{learning_id}
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce   {"is_helpful": true}
```

The `utility` supplied when adding a learning is only its starting prior.
The value later returned in `standing.utility` is Core's derived,
recency-weighted application-outcome score, updated as the learning helps or
misleads later work. It is not a confidence score.

Strip secrets, PII, and internal hostnames from any content you add by hand.

---

## Errors

- **401 / 403**: bad key or missing scopes. Check `HYPER_API_KEY`.
- **404**: agent or learning not found. Verify the id.
- **Network errors**: the automatic loop fails open (silently skips). For manual
  curation, retry once after a few seconds, then report.
