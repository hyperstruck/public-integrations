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
- **Ingest compacted local-run evidence** when useful knowledge appears outside the platform.
- **Reinforce** past learnings to improve their ranking for future use.

## Current environment

```!
# Config resolution order: exported env > ./.env > ~/.hyperstruck/.env.
# The ~/.hyperstruck/.env fallback (written by hyper-install) survives git
# worktrees and subdirectories where a repo-local ./.env may be absent.
for f in ".env" "$HOME/.hyperstruck/.env"; do
  [ -f "$f" ] || continue
  while IFS='=' read -r k v; do
    case "$k" in ''|\#*) continue ;; esac
    k="$(printf '%s' "$k" | tr -d '[:space:]')"
    case "$k" in HYPER_*|HYPERSTRUCK_*) ;; *) continue ;; esac
    printenv "$k" >/dev/null 2>&1 && continue
    v="$(printf '%s' "$v" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    export "$k=$v"
  done < "$f"
done
echo "HYPER_BASE_URL=${HYPER_BASE_URL:-https://api.hyperstruck.com}"
echo "HYPER_LEARNING_AGENT_NAME=${HYPER_LEARNING_AGENT_NAME:-<not set>}"
echo "HYPER_AGENT_NAME=${HYPER_AGENT_NAME:-<not set>}"
echo "HYPER_AGENT_ID=${HYPER_AGENT_ID:-<not set>}"
if [ -n "$HYPER_API_KEY" ]; then echo "HYPER_API_KEY_SET=yes"; else echo "HYPER_API_KEY_SET=no"; fi
[ -f .env ] && echo "dotenv=./.env" || { [ -f "$HOME/.hyperstruck/.env" ] && echo "dotenv=~/.hyperstruck/.env" || echo "dotenv=not found"; }
```

If `HYPER_API_KEY_SET=no` above, the block already tried both `./.env` and `~/.hyperstruck/.env`. If still missing, **stop and ask the user** to set `HYPER_API_KEY`.

---

## Configuration

- **Base URL**: `HYPER_BASE_URL` from above, defaulting to `https://api.hyperstruck.com`.
- **API key**: Resolved above. **Never echo it.**
- **Agent ID**: `HYPER_AGENT_ID` from above must be the hosted agent **UUID** (from `GET /agents`), not the agent name. If `<not set>`, call `GET {BASE_URL}/agents?limit=50` and ask the user to pick an agent (learnings are scoped per agent). For the automatic IDE hook loop, use `HYPER_AGENT_NAME` (agent name) instead — see `hyperstruck-py` install docs.
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

Optional query params: `min_utility` (0.0–1.0), `scope` (`agent` or `org` — org may require enterprise; expect 403).

Response:

```json
{
  "items": [
    {
      "learning": {
        "learning_id": "...",
        "content": "...",
        "standing": {"utility": 0.7, "reliability": 0.4, "corroboration_count": 2},
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
  "utility": 0.6,
  "source_goal": "<what task produced this insight>",
  "applicable_goals": ["keyword1", "keyword2"],
  "applicable_tools": ["tool_name"],
  "privacy": "shareable",
  "instances": [
    {
      "entity_values": {"entity": "value"},
      "outcome": {"result": "value"},
      "source_context": "claude-skill"
    }
  ]
}
```

Omit `instances` unless you have concrete structured evidence. Use it when a learning describes an observed input-to-outcome pattern, a tool result, a test case, or a compacted external run with clear entities and outcome. Keep values short strings and remove secrets, PII, internal hostnames, and raw logs.

### Async store

Returns **202 Accepted** with `request_id`. Indexing is asynchronous (non-LLM deduplication and storage). **Wait a few seconds** before searching for the new learning.

### Writing good learnings

- Be **specific and actionable**: "Always include a date range filter when querying the analytics API — without it, responses exceed 30 seconds" beats "Be careful with the API."
- Prefer **multiple small learnings** over one large paragraph.
- Strip secrets, PII, and internal hostnames from `content`.
- Set `applicable_goals` and `applicable_tools` so the learning surfaces when relevant.
- Add `instances` when evidence is available, especially for learnings that describe an observed input-to-outcome pattern or a tool's behaviour. Each instance should capture the minimal `entity_values` that explain when the pattern applies and the observed `outcome`.

### Capturing from local runs

When useful knowledge appears during local work, compact the run before storing learnings. Include only what helps future agents:

- The task, outcome, and whether the approach worked.
- Important errors, fixes, constraints, review feedback, repo facts, or tool behavior.
- The precise rule or pattern future agents should apply.
- Optional structured instances: entity values, observed outcome, and `source_context` such as `claude-skill`, `cursor`, `ci`, `browser`, or `api`.

Store only distilled learnings, not raw logs. If the insight is ambiguous, ask the user whether they want to store it with `/hyper-learning`. If they need deeper analysis first, briefly mention hosted reasoning as a separate option.

---

## Distill from a referenced corpus

Use `POST /distill` when a **referenced document, an MCP result, or a tool call** brought in a corpus that holds reusable knowledge — a design doc, spec, RFC, diff, or post-mortem — and you want the learnings Core would extract, but you have no real run trace and no final learning text to store verbatim. This is the right tool when the user drops a document into the agent's context and it deserves durable learning.

- **Endpoint**: `POST {BASE_URL}/distill` — this is **not** agent-UUID scoped. Its body carries `agent_name`, which must be the configured boundary agent name (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`) — the same corpus the automatic loop learns into — **not** the `HYPER_AGENT_ID` UUID used by `/agents/{id}/...`. If the task selected a different agent, use that agent's name.
- **Contrast is required** and is what yields a learning: pair a baseline/failure with a fix/success, or supply an `evaluation` note. A single descriptive paragraph yields nothing by design.
- **`run_id` must start with `distill:`**; supply at least 2 evidence items (each ≤ 8000 chars, ≤ 50 items), with total content between 500 and 120,000 non-whitespace chars.
- **Strip secrets, PII, and internal hostnames** from evidence `content`; the server stores it verbatim as the grounding source.

```
curl -sS -X POST "${HYPER_BASE_URL:-https://api.hyperstruck.com}/distill" \
  -H "Authorization: Bearer $HYPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "'"${HYPER_LEARNING_AGENT_NAME:-$HYPER_AGENT_NAME}"'",
    "run_id": "distill:design-doc-checkout-2026-07",
    "goal": "Extract reusable design learnings from the referenced design doc",
    "evidence": [
      {"id": "baseline", "role": "contrast", "status": "failed",
       "content": "<the old approach / problem the doc describes>"},
      {"id": "chosen", "role": "support", "status": "completed",
       "content": "<the chosen approach and why it is better>"}
    ],
    "outcome": {"is_success": true, "summary": "Design finalized"},
    "evaluation": "<the general, reusable principle — not doc-specific naming>"
  }'
```

Returns **202 Accepted** after the request passes validation; extraction is asynchronous. A corpus with **no declared contrast is rejected** (fix the evidence roles/statuses or add an `evaluation`). A corpus that declares contrast but contains no reusable contrast may be accepted and later yield zero learnings (the spend reservation is released and nothing is metered) — report that outcome rather than retrying blindly. The extracted learnings are searchable via `GET /agents/{agent_id}/learnings/search` a few seconds later. Do **not** use `/distill` for a real execution trace (that is the automatic observe loop) or for a learning you already have verbatim (use the store endpoint above).

---

## Reinforce a learning

```
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce
```

```json
{ "is_helpful": true }
```

Or `false`. Updates the learning's standing (utility and reliability) and advances the trust lifecycle (`unverified` → `agent_verified` → `source_verified` → `corroborated`).

When a learning gets used, reinforce it after the outcome is known. Mark it helpful if it improved the run, or unhelpful if it misled the agent.

---

## Report what you found

Whenever this skill recalls, searches, or distills, **surface the result to the user** so it is clear how the learning layer shaped the work — do not silently fold it in:

- **What was found**: the specific learnings (quote `content`, cite `learning_id`), or "none" on an empty result.
- **From which agent**: the agent name/id the call read from or wrote to (e.g. `HYPER_LEARNING_AGENT_NAME`/`HYPER_AGENT_NAME` for distill, the resolved agent UUID for search).
- **How it affected the run**: the concrete decisions you changed (approach, ordering, a pitfall avoided). After the outcome is known, **reinforce** every learning you actually applied (helpful or unhelpful).

---

## Typical workflows

### Recall-then-act

1. **Search** for learnings relevant to the current task.
2. Incorporate findings into your plan.
3. After the task, **reinforce** every learning that was actually used as helpful or unhelpful.
4. **Store** any new insights discovered.

### Local-run capture

1. Compact the local run into a short evidence summary.
2. Ask whether to store the distilled learning.
3. Store approved learnings, then reinforce them when future use shows whether they helped or misled.

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
