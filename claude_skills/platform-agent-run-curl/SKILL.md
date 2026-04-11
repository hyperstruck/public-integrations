---
name: platform-agent-run-curl
description: >-
  Same as platform-agent-run but using curl only: POST goals, GET poll runs,
  POST resume. For environments without Python. API key from env or .env.
---

# Hosted agent runs using curl only

The examples below use **`jq`** to parse JSON (`brew install jq`, `apt install jq`, etc.). If `jq` is unavailable, parse `RESP` with Python or copy IDs manually from the printed JSON.

## Setup (shell)

```bash
export HYPER_BASE_URL="https://your-api-host"   # no trailing slash
export HYPER_AGENT_ID="your-agent-uuid"
# Prefer: export HYPER_API_KEY from your secure store
export HYPER_API_KEY="..."   # NEVER commit this line

AUTH="Authorization: Bearer $HYPER_API_KEY"
JSON="Content-Type: application/json"
```

If using a `.env` file, `source` it or export variables manually — do not commit `.env`.

## Start goal

```bash
RESP="$(curl -sS -X POST "$HYPER_BASE_URL/agents/$HYPER_AGENT_ID/goals" \
  -H "$AUTH" -H "$JSON" \
  -d "{\"goal\":\"YOUR_GOAL\",\"context\":\"YOUR_CONTEXT\"}")"
echo "$RESP"
RUN_ID="$(echo "$RESP" | jq -r '.run.id')"
SESSION_ID="$(echo "$RESP" | jq -r '.run.session_id')"
```

## Poll run

```bash
curl -sS "$HYPER_BASE_URL/runs/$RUN_ID" -H "$AUTH"
```

Repeat until `status` is terminal or `suspended`.

## Resume (after human decision)

```bash
curl -sS -X POST "$HYPER_BASE_URL/runs/$RUN_ID/resume" \
  -H "$AUTH" -H "$JSON" \
  -d "{\"suspension_id\":\"$SUSPENSION_ID\",\"decision_type\":\"approve\",\"decided_by\":\"local\",\"reason\":\"approved\"}"
```

## Session messages

```bash
curl -sS "$HYPER_BASE_URL/sessions/$SESSION_ID/messages?limit=20" -H "$AUTH"
```

## Rules

- Apply **platform-context-handoff** before composing `goal` and `context`.
- Never print the raw API key in chat logs or scripts checked into public repos.
