# Hyperstruck learning reference

This skill drives the hosted learning loop through the editor hooks. Load
this file when you need the request shapes or the interim manual-curation path.

---

## The learning loop (automatic)

The loop runs for you via the installed hooks; you do not call these by hand. They
are listed so you understand what is happening.

| Step | Endpoint | When | Purpose |
|------|----------|------|---------|
| resolve | `POST /resolve` | turn start (or any decision point) | Return goal-relevant learnings to inject. Server accumulates the offer log keyed by `run_id`; a run may recall more than once by passing a distinct `resolve_idempotency_key` per recall, and offers from every recall are credited at reinforce. |
| observe | `POST /observe` | deferred to next turn start | Extract new learnings from the finished episode (server-side producer + critic). |
| reinforce | `POST /reinforce` | deferred to next turn start | Credit/penalise the learnings that were offered at resolve. |

The write side is deferred one turn so the user's next prompt supplies ground
truth for the prior turn's outcome. All of this is handled by
`python -m hyperstruck.ide.hook`; the recall command in SKILL.md is the only piece
you invoke, and only on Cursor.

Auth and the configured agent come from `~/.hyperstruck/.env`
(`HYPER_API_KEY`, `HYPER_BASE_URL`, `HYPER_LEARNING_AGENT_NAME`,
`HYPER_AGENT_NAME`, `HYPER_AGENT_ID`), written by `hyper-install`. The hook reads
this file at start regardless of the current working directory, so both recall
and distill behave identically across git worktrees where a repo-local `.env` may
be absent. Agent-name precedence is `HYPER_LEARNING_AGENT_NAME` first, then
`HYPER_AGENT_NAME`.

---

## Distill (caller-driven, outside the loop)

`POST /distill` extracts grounded learnings from a corpus of evidence (a design
doc, an MCP result, a diff, a post-mortem) without a real run trace. It sits
outside the resolve → observe → reinforce loop. The IDE skill drives it through
the hook so identity, namespacing, and secret-scrubbing are handled for you:

```
echo '<spec json>' | PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook distill --emit text
```

The spec is `{goal, evidence: [{id, content, role, status, label?, source_ref?}],
outcome?, evaluation?, run_id?}`. The command:

- Uses the configured boundary agent name (`HYPER_LEARNING_AGENT_NAME` when set,
  otherwise `HYPER_AGENT_NAME`) as the distill `agent_name` (never a repo-derived
  agent, never the `HYPER_AGENT_ID` UUID — distill is name-scoped like
  observe/resolve).
- Requires at least 2 evidence items and a declared contrast (differing `status`,
  a `contrast`/`support` pair, or a non-empty `evaluation`); the server rejects a
  no-contrast corpus.
- Namespaces `run_id` with `distill:` (minted if omitted) so it never collides
  with a loop run id.
- Secret-scrubs caller-supplied *descriptive* distill strings before sending:
  `goal`, `evaluation`, evidence `label`/`content`, and outcome `summary`; the
  server stores evidence text verbatim as the grounding source.
- Never rewrites an *identifier*. The run id and each evidence `id`/`source_ref`
  are sent exactly as given, or the corpus is refused naming the field, because a
  rewritten identifier collides rather than degrading.

A corpus with no declared contrast is skipped locally (and would be rejected by
the server). A delivered corpus that declares contrast can still yield zero
learnings if the text contains no reusable contrast; extracted learnings are
searchable via `GET /agents/{id}/learnings/search` a few seconds later.

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
