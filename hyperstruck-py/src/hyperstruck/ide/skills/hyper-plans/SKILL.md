---
name: hyper-plans
description: >-
  Search similar Hyperstruck plans and review candidate learnings returned with
  similar-plan results.
argument-hint: "[search query] [--agents <id1,id2,...>]"
allowed-tools:
  - Bash(curl *)
  - WebFetch
---

# Hyperstruck plans management

Inspect prior plans captured by Hyperstruck so you can reuse successful decompositions,
compare strategies across agents, and review candidate learnings surfaced with similar-plan hits.

## Current environment

```!
# Config resolution order: exported env > ./.env > ~/.hyperstruck/.env.
# Strip matching quotes and trailing " # comment" so Bearer auth does not
# send literal "…" (that yields HTTP 401 Invalid API key).
for f in ".env" "$HOME/.hyperstruck/.env"; do
  [ -f "$f" ] || continue
  while IFS='=' read -r k v; do
    case "$k" in ''|\#*) continue ;; esac
    k="$(printf '%s' "$k" | tr -d '[:space:]')"
    case "$k" in HYPER_*|HYPERSTRUCK_*) ;; *) continue ;; esac
    printenv "$k" >/dev/null 2>&1 && continue
    v="$(printf '%s' "$v" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    # dotenv: strip matching quotes and trailing " # comment" so Bearer auth
    # does not send literal "…" (that yields HTTP 401 Invalid API key).
    case "$v" in
      \"*)
        rest="${v#\"}"
        case "$rest" in
          *\"*) v="${rest%%\"*}" ;;
        esac
        ;;
      \'*)
        rest="${v#\'}"
        case "$rest" in
          *\'*) v="${rest%%\'*}" ;;
        esac
        ;;
      *)
        case "$v" in
          *" #"*) v="${v%% #*}" ;;
        esac
        v="$(printf '%s' "$v" | sed -e 's/[[:space:]]*$//')"
        ;;
    esac
    export "$k=$v"
  done < "$f"
done
echo "HYPER_BASE_URL=${HYPER_BASE_URL:-https://api.hyperstruck.com}"
echo "HYPER_AGENT_ID=${HYPER_AGENT_ID:-<not set>}"
if [ -n "$HYPER_API_KEY" ]; then echo "HYPER_API_KEY_SET=yes"; else echo "HYPER_API_KEY_SET=no"; fi
[ -f .env ] && echo "dotenv=./.env" || { [ -f "$HOME/.hyperstruck/.env" ] && echo "dotenv=~/.hyperstruck/.env" || echo "dotenv=not found"; }
```

If `HYPER_API_KEY_SET=no` above, the block already tried both `./.env` and `~/.hyperstruck/.env`. If still missing, stop and ask the user to set `HYPER_API_KEY`.

---

## Configuration

- Base URL: `HYPER_BASE_URL` from above, default `https://api.hyperstruck.com`
- API key: resolved above; never echo it
- Agent ID: use `HYPER_AGENT_ID` unless the user supplies `--agents`

Headers:

```
Authorization: Bearer <API_KEY>
Content-Type: application/json
Accept: application/json
```

---

## Commands

### `/hyper-plans search <query>`

Single-agent search:

```
GET {BASE_URL}/agents/{agent_id}/plans/similar?q=<query>&limit=10
```

Multi-agent search:

```
POST {BASE_URL}/plans/similar
```

```json
{
  "agent_ids": ["<uuid>", "<uuid>"],
  "q": "<query>",
  "limit": 10
}
```

If the user supplies `--agents <id1,id2,...>`, call the multi-agent endpoint. Otherwise call the single-agent route.

Summarize each hit with:

- `plan.plan_id`
- `plan.goal`
- `plan.summary` when present
- `similarity_score`
- top candidate learnings with `trust_level`
- if a candidate learning looks evidence-backed and the user needs details, fetch it with `GET /agents/{agent_id}/learnings/{learning_id}` to inspect full `instances`

Also mention `partial_failures` when present.

---

## Error handling

- `401/403`: invalid key, missing scope, or unauthorized agent ids
- `503`: plan runtime unavailable
- Network error: retry once after 3 s, then report failure

For detailed response shapes, see [reference.md](reference.md).
