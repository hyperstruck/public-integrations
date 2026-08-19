---
name: hyper-learning
description: >-
  Recall, search, store, and reinforce Hyperstruck learnings and claims. Use
  before complex work; curl fallback supports CoWork, Codex, CI, and unwired
  IDEs.
argument-hint: "[search query or 'store' or 'reinforce']"
allowed-tools:
  - Bash(curl *)
  - Bash(python3 *)
  - WebFetch
---

<!-- GENERATED FILE — do not edit directly. Edit the templates under
scripts/skill_templates/hyper-learning/ in the core-platform repo, then run:
python3 scripts/render_skills.py -->

# Hyperstruck learnings management

Recall, store, search, and reinforce learnings on the Hyperstruck platform — the practical learning layer that accumulates knowledge to support structured reasoning. Use this to:

- **Recall** learnings *and claims* (established entity facts) matched to the caller's current task before starting complex work.
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
echo "HYPER_LEARNING_AGENT_NAME=${HYPER_LEARNING_AGENT_NAME:-<not set>}"
echo "HYPER_AGENT_NAME=${HYPER_AGENT_NAME:-<not set>}"
echo "HYPER_AGENT_ID=${HYPER_AGENT_ID:-<not set>}"
if [ -n "$HYPER_API_KEY" ]; then echo "HYPER_API_KEY_SET=yes"; else echo "HYPER_API_KEY_SET=no"; fi
if [ -x "$HOME/.hyperstruck/venv/bin/python" ] && "$HOME/.hyperstruck/venv/bin/python" -c "import hyperstruck.ide.hook" >/dev/null 2>&1; then echo "HYPER_VENV=available"; else echo "HYPER_VENV=missing"; fi
if [ -f "$HOME/.claude/settings.json" ] && grep -q "hyperstruck.ide.hook" "$HOME/.claude/settings.json" 2>/dev/null; then echo "HYPER_CLAUDE_HOOKS=wired"; else echo "HYPER_CLAUDE_HOOKS=unwired"; fi
if [ -f "$HOME/.cursor/hooks.json" ] && grep -q "hyperstruck.ide.hook" "$HOME/.cursor/hooks.json" 2>/dev/null; then echo "HYPER_CURSOR_HOOKS=wired"; else echo "HYPER_CURSOR_HOOKS=unwired"; fi
[ -f .env ] && echo "dotenv=./.env" || { [ -f "$HOME/.hyperstruck/.env" ] && echo "dotenv=~/.hyperstruck/.env" || echo "dotenv=not found"; }
```

If `HYPER_API_KEY_SET=no` above, the block already tried the **session** `./.env` and `$HOME/.hyperstruck/.env`. That is enough on Claude Code and Cursor. On **Claude CoWork** it is not: the preamble often runs in a remote sandbox whose cwd and `$HOME` are not the user's machine. An empty remote session env is **not** proof the user has no key.

On CoWork, also read `HYPER_*` / `HYPERSTRUCK_*` from the **local filesystem** the user attached (the project or folder CoWork is working in):

1. Open `.env` at that folder root, then parent folders, with the host file tools if the sandbox shell cannot see the file.
2. If this session can see the user's home directory, also open `~/.hyperstruck/.env` on that **local** filesystem — do not treat the sandbox `$HOME` as the user's Mac unless they are the same path.
3. Apply the same quote and comment stripping as the block above. **Never echo values.**
4. Only then **stop and ask** the user for `HYPER_API_KEY`.

On other hosts, if the key is still missing after the block, **stop and ask** the user to set `HYPER_API_KEY`.

`HYPER_VENV` only means the hook command can run; it does **not** mean this host owns the live loop. Claude Code owns the loop only when `HYPER_CLAUDE_HOOKS=wired`, Cursor only when `HYPER_CURSOR_HOOKS=wired`. CoWork, Codex, and CI never own the loop — use curl there even if the venv exists.

If the environment block above did not run at all (some hosts do not execute dynamic skill preambles), run its body manually in your shell before continuing — every call below needs `HYPER_API_KEY` and `HYPER_BASE_URL`. On CoWork, still check the attached local `.env` first.

---

## Hooks installed vs curl fallback

The hooks, `~/.hyperstruck/venv`, and `.env` files remain fully supported. Prefer the live hook loop only when **this host** has them wired; the curl path is how the same skill stays portable everywhere else.

- **This host's hooks are wired** (`HYPER_CLAUDE_HOOKS=wired` in Claude Code, or `HYPER_CURSOR_HOOKS=wired` in Cursor) — the Hyperstruck learning hooks (installed by `hyper-install` from `hyperstruck-py`) own the live resolve/observe/reinforce loop for normal turns. Do **not** hand-drive that loop in parallel (double-driving distorts attribution). Use this skill for explicit search, store, distill, curation, or an extra read-only recall the user asked for. `HYPER_VENV=available` only chooses the hook executable (`~/.hyperstruck/venv/bin/python`).
- **This host does not own the loop** (CoWork, Codex, CI, or unwired Claude/Cursor) — everything in this skill works with plain `curl`; **you** are the loop. Recall with [`POST /resolve`](#recall-for-the-callers-task--learnings--claims) at the start of substantive work, and close every resolve with [reinforce or decline](#close-the-loop--reinforce-or-decline). Do this even when `HYPER_VENV=available`.

---

## Configuration

- **Base URL**: `HYPER_BASE_URL` from above, defaulting to `https://api.hyperstruck.com`.
- **API key**: Resolved above. **Never echo it.**
- **Boundary agent name**: `/resolve`, `/observe`, `/reinforce`, `/decline`, and `/distill` take `agent_name` — a human-readable, tenant-unique name (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`). If no agent with that name exists, one is created automatically on first use. This is **not** a UUID.
- **REST agent UUID**: `/agents/{agent_id}/...` paths use the hosted agent **UUID** in `HYPER_AGENT_ID` (from `GET /agents`), not the agent name. If `<not set>`, call `GET {BASE_URL}/agents?limit=50` and ask the user to pick an agent (learnings are scoped per agent).
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
- `/hyper-learning` (no arguments) → ask what they want to do, or default to **recall** for the current task context (`/resolve` when `HYPER_HOOKS=missing`, search otherwise).

---

## Recall for the caller's task — learnings + claims

Use this as the recall path when `HYPER_HOOKS=missing`. When hooks are installed they already resolve per prompt — only call this manually if the user explicitly asks for an extra recall, and still close the loop.

`POST /resolve` returns the learnings **and claims** bound to a goal. Claims are facts the agent has already established about entities it investigated; they are matched to the goal text, so **write `goal` as the caller's actual task in its own words** — not generic keywords. A vague goal returns vague claims.

Mint a unique `run_id` once per run (date + slug + a UUID). Reuse that exact value for every resolve, reinforce, and decline of this run. A date+slug alone collides if the same task runs twice in one day, and a second resolve is then treated as a retry.

Build the body with a JSON encoder so apostrophes and quotes in the goal cannot break the shell:

```bash
export RUN_ID="skill:$(date +%Y%m%d)-<short-task-slug>-$(python3 -c 'import uuid; print(uuid.uuid4())')"
export HYPER_GOAL="<the caller's current task, specific and in context>"
# Optional: set HYPER_SOURCE_FRAMEWORK to the producing host (cowork, codex, ci,
# mcp:cursor, claude-skill). Omit it to let the server backfill. Use the same
# value on reinforce/decline. Do not hardcode claude-skill on every host.
# resolve_purpose defaults to agent_loop on the server; omit it unless this
# is human inspection (then send explicit_recall).
python3 -c '
import json, os
body = {
    "agent_name": os.environ.get("HYPER_LEARNING_AGENT_NAME") or os.environ.get("HYPER_AGENT_NAME"),
    "run_id": os.environ["RUN_ID"],
    "goal": os.environ["HYPER_GOAL"],
    "max_learnings": 8,
}
key = os.environ.get("HYPER_RESOLVE_KEY")
if key:
    body["resolve_idempotency_key"] = key
host = os.environ.get("HYPER_SOURCE_FRAMEWORK")
if host:
    body["source_framework"] = host
print(json.dumps(body))
' | curl -sS -X POST "${HYPER_BASE_URL:-https://api.hyperstruck.com}/resolve" \
  -H "Authorization: Bearer $HYPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d @-
```

Response (`200`):

```json
{
  "injected_text": "<advice: rules and annotations compiled from learnings>",
  "injected_facts_text": "<fenced block of claim facts about entities relevant to the goal>",
  "offered_learning_ids": ["..."],
  "offered_claim_ids": ["..."]
}
```

How to use it:

- **`injected_text`** is the advice half — treat it as rules that shape your plan.
- **`injected_facts_text`** is the claims half — established facts about entities (repos, services, APIs, tools) the agent already investigated. Trust them as prior knowledge; they save re-investigation. `offered_claim_ids` mirrors the fact block in order — a fact cut by trust floor or token budget appears in neither.
- Both halves may be `null` on an empty corpus — that is a valid empty recall, not an error.
- **Every manual resolve must be closed** with reinforce or decline (below) using the same `run_id`. An unclosed resolve is indistinguishable from a broken host.

---

## Recall per component on large tasks

A single recall on one big blended goal dilutes retrieval: matching runs on the goal text, so component-specific learnings and claims get crowded out by generic ones. When the task is large — a design-document review, a large corpus of text, or work with clearly separable components or milestones — recall **per key component**, not once on the main goal:

1. Split the task into its key components (milestones, subsystems, document sections).
2. Recall once per component with a short, focused goal for that component.
   - **This host's hooks are wired**: run the read-only hook recall once per component goal: `PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook prompt --readonly --resolve-purpose agent_loop --emit text --goal "<component goal>"` (use `~/.hyperstruck/venv/bin/python` when `HYPER_VENV=available`). Each invocation mints its own throwaway `run_id` and the hook **declines it immediately** after printing — do not reinforce or decline these yourself, and do not treat them as one shared run.
   - **curl fallback**: call `POST /resolve` once per component, reusing the **same `run_id`** and passing a **distinct `resolve_idempotency_key`** (set `HYPER_RESOLVE_KEY` to a component or milestone id). The server accumulates the offer log per run, and offers from every recall are credited at reinforce.
3. On the curl path, close the run **once** at the end — a single reinforce or decline for the whole run, not one per component. On the wired-hook path, the automatic loop already closes the live turn; the extra read-only recalls are already closed.
4. Surface per component what each recall returned and how it shaped that component's work.

---

## Close the loop — reinforce or decline

After the work finishes, tell the platform what happened so the offered learnings and claims are credited or corrected. Build these bodies with a JSON encoder too.

**Something was learned or applied** → `POST /reinforce` with a compacted episode (same `run_id`):

```bash
python3 -c '
import json, os
episode = {
    "run_id": os.environ["RUN_ID"],
    "goal": os.environ["HYPER_GOAL"],
    "outcome": {"is_success": True, "total_steps": 3, "completed_steps": 3, "failed_steps": 0},
    "steps": [
        {"id": "step-1", "name": "<tool or action>", "status": "completed",
         "result": "<short, redacted result>"}
    ],
}
host = os.environ.get("HYPER_SOURCE_FRAMEWORK")
if host:
    episode["source_framework"] = host
body = {
    "agent_name": os.environ.get("HYPER_LEARNING_AGENT_NAME") or os.environ.get("HYPER_AGENT_NAME"),
    "episode": episode,
}
print(json.dumps(body))
' | curl -sS -X POST "${HYPER_BASE_URL:-https://api.hyperstruck.com}/reinforce" \
  -H "Authorization: Bearer $HYPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d @-
```

Keep steps compact and **pre-redact secrets, PII, and internal hostnames** from `args`/`result` — no automatic scrubbing runs on this manual path. If the model was actually shown the injected text, you may pass the rendered block as `context_receipt` (top-level field, next to `episode`) so attribution can confirm what was displayed.

**Nothing worth learning this turn** → `POST /decline` (same `run_id`):

```bash
python3 -c '
import json, os
body = {
    "agent_name": os.environ.get("HYPER_LEARNING_AGENT_NAME") or os.environ.get("HYPER_AGENT_NAME"),
    "run_id": os.environ["RUN_ID"],
    "reason": "below_material_threshold",
    "is_delivered": True,
}
host = os.environ.get("HYPER_SOURCE_FRAMEWORK")
if host:
    body["source_framework"] = host
print(json.dumps(body))
' | curl -sS -X POST "${HYPER_BASE_URL:-https://api.hyperstruck.com}/decline" \
  -H "Authorization: Bearer $HYPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d @-
```

`reason` is a closed set: `no_tool_calls`, `below_material_threshold`, `empty_offer`, `unevidenced_outcome`. Set `is_delivered` to whether the injected text actually reached the model this turn. Both endpoints return **202** — processing is asynchronous.

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

`utility` is a starting prior only; the platform later derives `standing.utility` from application outcomes. Omit `instances` unless you have concrete structured evidence. Use it when a learning describes an observed input-to-outcome pattern, a tool result, a test case, or a compacted external run with clear entities and outcome. Keep values short strings and remove secrets, PII, internal hostnames, and raw logs.

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

Returns **202 Accepted** after the request passes validation; extraction is asynchronous. A corpus with **no declared contrast is rejected** (fix the evidence roles/statuses or add an `evaluation`). A corpus that declares contrast but contains no reusable contrast may be accepted and later yield zero learnings (the spend reservation is released and nothing is metered) — report that outcome rather than retrying blindly. The extracted learnings are searchable via `GET /agents/{agent_id}/learnings/search` a few seconds later. Do **not** use `/distill` for a real execution trace (that is the automatic observe loop or the manual reinforce above) or for a learning you already have verbatim (use the store endpoint above).

---

## Reinforce a single learning

```
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce
```

```json
{ "is_helpful": true }
```

Or `false`. Updates the learning's standing (utility and reliability) and advances the trust lifecycle (`unverified` → `agent_verified` → `source_verified` → `corroborated`).

When a learning gets used, reinforce it after the outcome is known. Mark it helpful if it improved the run, or unhelpful if it misled the agent. Use this REST endpoint for learnings found via **search**; for learnings offered by a manual **resolve**, prefer the boundary `POST /reinforce` above so the whole run is attributed at once.

---

## Report what you found

Whenever this skill recalls, searches, or distills, **surface the result to the user** so it is clear how the learning layer shaped the work — do not silently fold it in:

- **What was found**: the specific learnings (quote `content`, cite `learning_id`) and claims (summarize `injected_facts_text`, cite `offered_claim_ids`), or "none" on an empty result.
- **From which agent**: the agent name/id the call read from or wrote to (e.g. `HYPER_LEARNING_AGENT_NAME`/`HYPER_AGENT_NAME` for resolve/distill, the resolved agent UUID for search).
- **How it affected the run**: the concrete decisions you changed (approach, ordering, a pitfall avoided, an entity fact you did not re-investigate). After the outcome is known, **close the loop** for every learning and claim you actually applied.

---

## Typical workflows

### Recall-then-act (hooks missing — CoWork, Codex, CI)

1. **Resolve** learnings + claims for the caller's task (`POST /resolve`, goal = the actual task). On a large task, resolve per key component instead (see above).
2. Fold `injected_text` (advice) and `injected_facts_text` (entity facts) into your plan; report them to the user.
3. Do the work.
4. **Close the loop**: `POST /reinforce` with a compacted episode, or `POST /decline` if the turn taught nothing.
5. **Store** any new standalone insights discovered.

### Recall-then-act (hooks installed)

1. The hooks already resolve per prompt — read what they surfaced. On a large task, add read-only hook recalls per key component (see above).
2. Use **search** for extra targeted lookups; do not hand-drive resolve/reinforce for normal turns.
3. **Store** genuinely new insights; **reinforce** search-found learnings you applied via the per-learning REST endpoint.

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

- **401/403**: invalid key or lacking scopes → ask user to check `HYPER_API_KEY`. On CoWork, re-read the attached local `.env` before asking; an empty remote session env is not a missing key.
- **403 `blocked-by-allowlist` / `host_not_allowed`**: CoWork (or the org) has not allowlisted the API host for code-execution egress. Ask the user to add `api.hyperstruck.com` (or their `HYPER_BASE_URL` host) under Settings or Organization settings → **Capabilities → Code execution → Allow network egress → Additional allowed domains**, then start a **new** session.
- **404**: agent or learning not found → verify ID.
- **403 on `scope=org`**: requires enterprise entitlement.
- **400/422 validation errors, or a field in this doc looks renamed**: the contract may have moved — run the self-check below before retrying.
- **Network errors**: retry once after 3 s; if still failing, report and stop.

---

## Contract self-check (when this doc and the API disagree)

The canonical API contract is the published `openapi.json` in the public integrations repo:

```
https://raw.githubusercontent.com/hyperstruck/public-integrations/main/openapi.json
```

The spec is large — **never read it whole**. Fetch it once and extract only the operation you need:

```bash
curl -sSL https://raw.githubusercontent.com/hyperstruck/public-integrations/main/openapi.json \
  -o /tmp/hyper_openapi.json
python3 - '/resolve' 'post' <<'EOF'
import json, sys
path, method = sys.argv[1], sys.argv[2]
spec = json.load(open("/tmp/hyper_openapi.json"))

def deref(node: dict) -> dict:
    while isinstance(node, dict) and "$ref" in node:
        target = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node

try:
    op = spec["paths"][path][method]
except KeyError:
    print(f"{method.upper()} {path} not in spec; known paths:")
    print("\n".join(sorted(spec["paths"])))
    sys.exit(1)
print(method.upper(), path, "—", op.get("summary", ""))
for prm in op.get("parameters", []):
    print(" param:", prm["name"], f"({prm['in']}, required={prm.get('required', False)})")
body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
if body:
    model = deref(body)
    print(" request:", json.dumps(model, indent=1)[:4000])
for code, resp in op.get("responses", {}).items():
    schema = resp.get("content", {}).get("application/json", {}).get("schema")
    if schema:
        print(f" response {code}:", json.dumps(deref(schema), indent=1)[:4000])
EOF
```

Swap the two arguments for any endpoint (e.g. `'/agents/{agent_id}/learnings/search' 'get'`). Use this whenever a request 400s/422s unexpectedly, a documented field is rejected, or a response is missing a field this doc promises — then follow what the spec says over what this doc says, and tell the user this skill needs updating.
