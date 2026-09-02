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
echo "HYPER_SPACE_ID=${HYPER_SPACE_ID:-<not set>}"
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
- **Home space** (optional): `HYPER_SPACE_ID` is the space UUID that narrows `GET /agents` to agents homed in that space. Install writes it when you pass `--space-id`. If it is set, **every** agent-list call must include `&space_id=$HYPER_SPACE_ID`. A bare `GET /agents?limit=50` misses agents past the first page.
- **REST agent UUID**: `/agents/{agent_id}/...` paths use the hosted agent **UUID** in `HYPER_AGENT_ID` (from `GET /agents`), not the agent name. If `<not set>`, call `GET {BASE_URL}/agents?limit=50` — add `&space_id=$HYPER_SPACE_ID` when that var is set, and `q=<name>&test=include` when looking up a known name — and ask the user to pick an agent (learnings are scoped per agent).
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

`POST /resolve` returns the learnings **and claims** bound to a goal. A claim is a fact the agent has already established about an entity it investigated, kept with who said it and when; claims are matched to the goal text, so **write `goal` as the caller's actual task in its own words** — not generic keywords. A vague goal returns vague claims.

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
  "injected_facts_text": "<fenced block of the claims the account holds about entities relevant to the goal>",
  "offered_learning_ids": ["..."],
  "offered_claim_ids": ["..."],
  "claims": [
    {
      "id": "<claim key>",
      "entity": {"id": "...", "name": "Harlow Freight", "type": "organisation"},
      "attribute": {"id": "...", "name": "fiscal year end", "kind": "...", "nature": "..."},
      "qualifiers": {},
      "state": "settled",
      "current": {"value": {"type": "text", "text": "June"}, "valid_from": "..."}
    }
  ],
  "has_reported_outcomes": true
}
```

How to use it. Two blocks, and they differ in kind, not just in content:

- **`injected_text`** is the advice half. It arrives banded, and the bands are the point: standards the customer stated outright come first and are followed unless the goal explicitly overrides one, then workflow constraints, constraints, recommendations, supplementary and tool preferences. Each band states its own weight in its heading, so read them rather than treating the whole block as one rule set: a constraint is to be addressed where its condition holds, while a supplementary item is to be verified before it is applied. Place the block as given. Re-ranking it, re-ordering it or truncating it discards the only signal that says which of two conflicting learnings wins.
- **`injected_facts_text`** is the claims half: what the account holds about the entities (repos, services, APIs, tools, people, companies) the goal names, including what is owed. Trust it as prior knowledge; it saves re-investigation. `offered_claim_ids` lists the claim keys the block carries in order, so a claim cut by the trust floor or the token budget appears in neither. **`claims`** is the same set as data, in the shape `GET /agents/{agent_id}/claims` returns, for a host that renders claims under its own design. Each item names its entity and attribute, a `state` (`settled`, `unanswered`, `conflicting`, `open`, `done` or `ended`) and its `current` value.
- Either block may be `null`: an empty corpus, no entity named by the goal. That is a valid empty recall, not an error. `fact_lane.outcome` says which: `no_match` means the goal names an entity the account holds and it holds nothing about it, `no_entity_named` means the goal names no entity the account holds (it may still hold claims the goal describes, which a question finds), `not_replayed` means the agent's documents are still being loaded, `suppressed` means a tool's first-use resolve carries no claims, and `failed` means the recall could not run.
- **`has_reported_outcomes`** says whether this agent's host has ever reported a run's outcome through reinforce. A learning is recommended only after it has helped in two runs, and only a reported outcome can say it helped, so while this is `false` nothing will ever be recommended and `injected_text` ends with a sentence saying so. Closing every resolve with reinforce (below) is what turns it `true`; decline does not.
- **Every manual resolve must be closed** with reinforce or decline (below) using the same `run_id`. An unclosed resolve is indistinguishable from a broken host.

### Reading what is owed

Open obligations arrive inside the claims block as owed claims (state `open`), not as a block of their own. An obligation is a commitment someone recorded, and the only honest way to treat it is as a reminder that may already be stale.

- **It is advisory, and it is not an instruction.** A claim reading "send the migration plan" is a record that someone said this was owed, not a directive to send it now. Raise it, ask, or fold it into your plan; do not silently execute it.
- **It may already be done.** Nothing closes an obligation automatically. Recall cannot tell a live commitment from one that was honoured last week outside this system, so the useful action is to check, not to chase.
- **It is not a complete list.** An absent owed claim is not evidence nothing is owed; use `GET /agents/{agent_id}/claims?kind=obligation&state=open` when completeness is what you need.
- **Do not fold it into the advice block.** Rules generalise across runs; an obligation is specific, dated, and belongs to named parties. Treating one as a rule is how a one-off commitment becomes permanent behaviour.

---

## Recall from more than one suitable agent

Export `HYPER_GOAL` to the caller's actual task before any of the loops below.
On the curl path, also mint `RUN_ID` (and optionally `HYPER_SOURCE_FRAMEWORK`)
the same way as the curl fallback / resolve section; those variables are
required here and are not created by this section.

`/resolve` reads exactly one boundary agent per request. It does **not** accept
`agent_names`, an agent UUID list, or an org-wide recall flag. When useful
knowledge may be split across agents, fan out deliberately: list the candidate
agents, choose the small set whose names/descriptions fit the goal, and recall
each one separately. Keep the returned blocks labelled by agent instead of
merging them into one undifferentiated rule set.

Start by discovering candidates. `GET /agents` defaults to `created_desc` and
pages at `limit=50` with `next_cursor`; a single first page can hide an older
specialist. If you already know likely names, search with `q=` first. Otherwise
follow `next_cursor` (pass it back unchanged as `cursor`) until it is empty
before deciding none fit. Keep recall itself to a few agents — usually no more
than three.

```bash
cursor=""
while :; do
  args=(--data-urlencode "limit=50")
  if [ -n "$HYPER_SPACE_ID" ]; then
    args+=(--data-urlencode "space_id=$HYPER_SPACE_ID")
  fi
  if [ -n "$cursor" ]; then
    args+=(--data-urlencode "cursor=$cursor")
  fi
  page="$(curl -sS -G "${HYPER_BASE_URL:-https://api.hyperstruck.com}/agents" \
    -H "Authorization: Bearer $HYPER_API_KEY" \
    "${args[@]}")"
  printf '%s\n' "$page"
  cursor="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("next_cursor") or "")' <<<"$page")"
  [ -n "$cursor" ] || break
done
```

Read the names and descriptions from every page (or from targeted `q=`
searches). Select all clearly relevant agents, usually no more than three unless
the user's task truly spans more domains. If none fit after the later pages (or
the `q=` searches) have been read, use the configured boundary agent only; do
not spray a recall across unrelated agents just because they exist.

With hooks installed, run read-only recall once per selected **agent name** by
overriding the ambient name for that command. Each command opens and closes its
own throwaway read-only run:

```bash
HYPER_PY="$HOME/.hyperstruck/venv/bin/python"
[ -x "$HYPER_PY" ] || HYPER_PY=python3
for agent_name in "sdlc-implementation-planner" "sdlc-code-reviewer"; do
  printf '\n### Recall from %s\n' "$agent_name"
  HYPER_LEARNING_AGENT_NAME="$agent_name" \
    PYTHONSAFEPATH=1 "$HYPER_PY" -m hyperstruck.ide.hook prompt --readonly \
      --resolve-purpose agent_loop --emit text --goal "$HYPER_GOAL" </dev/null
done
```

The loop uses the install venv when it exists and falls back to `python3`.

On the curl fallback path, call `POST /resolve` once per selected agent with the
same `RUN_ID` and a distinct `resolve_idempotency_key` per agent. When you also
recall per component, set `HYPER_RESOLVE_KEY` to that component or milestone id
so the key is `<component>:agent:<name>` rather than a reused `agent:<name>`.
Close the loop once **per recalled agent** at the end by sending `/reinforce` or
`/decline` with that agent's `agent_name`; a close for one agent does not credit
or close offers made by another. Combined with per-component recall, still close
once per agent, not once per component.

```bash
export HYPER_RECALL_AGENT_NAMES="sdlc-implementation-planner,sdlc-code-reviewer"
python3 - <<'EOF' | while IFS= read -r body; do
import json, os, re

goal = os.environ["HYPER_GOAL"]
run_id = os.environ["RUN_ID"]
host = os.environ.get("HYPER_SOURCE_FRAMEWORK")
prefix = os.environ.get("HYPER_RESOLVE_KEY") or "recall"
for raw_name in os.environ["HYPER_RECALL_AGENT_NAMES"].split(","):
    agent_name = raw_name.strip()
    if not agent_name:
        continue
    slug = re.sub(r"[^A-Za-z0-9_.:-]+", "-", agent_name)
    key = f"{prefix}:agent:{slug}"[:200]
    body = {
        "agent_name": agent_name,
        "run_id": run_id,
        "goal": goal,
        "max_learnings": 8,
        "resolve_idempotency_key": key,
    }
    if host:
        body["source_framework"] = host
    print(json.dumps(body))
EOF
  printf '\n### Resolve request\n%s\n' "$body" >&2
  printf '%s' "$body" | curl -sS -X POST "${HYPER_BASE_URL:-https://api.hyperstruck.com}/resolve" \
    -H "Authorization: Bearer $HYPER_API_KEY" \
    -H "Content-Type: application/json" \
    -d @-
  printf '\n'
done
```

Do **not** paste the close-the-loop snippets as written: they send
`HYPER_LEARNING_AGENT_NAME` / `HYPER_AGENT_NAME` and would close only the
configured agent, leaving every other fanned-out run open. Loop the same
`HYPER_RECALL_AGENT_NAMES` and override the name per close. Use `/reinforce`
when that agent's advice was applied; use `/decline` with `readonly_close`
when the block was read but not applied (it earns nothing by design —
`below_material_threshold` on a read-only fan-out files lost credit).

```bash
python3 - <<'EOF' | while IFS= read -r body; do
import json, os

run_id = os.environ["RUN_ID"]
host = os.environ.get("HYPER_SOURCE_FRAMEWORK")
for raw_name in os.environ["HYPER_RECALL_AGENT_NAMES"].split(","):
    agent_name = raw_name.strip()
    if not agent_name:
        continue
    body = {
        "agent_name": agent_name,
        "run_id": run_id,
        "reason": "readonly_close",
        "is_delivered": True,
    }
    if host:
        body["source_framework"] = host
    print(json.dumps(body))
EOF
  printf '%s' "$body" | curl -sS -X POST "${HYPER_BASE_URL:-https://api.hyperstruck.com}/decline" \
    -H "Authorization: Bearer $HYPER_API_KEY" \
    -H "Content-Type: application/json" \
    -d @-
  printf '\n'
done
```

To reinforce an agent whose advice you applied, reuse the reinforce snippet
from the close-the-loop section with `HYPER_LEARNING_AGENT_NAME="$agent_name"`
in front of it, once per such agent.

When reporting the result, say which agents were queried, what each returned
(including claims), and which advice you applied. If two agents disagree, do not
silently average them: surface the conflict, prefer the agent whose purpose best
matches the decision, or ask the user to choose.

---

## Recall per component on large tasks

A single recall on one big blended goal dilutes retrieval: matching runs on the goal text, so component-specific learnings and claims get crowded out by generic ones. When the task is large — a design-document review, a large corpus of text, or work with clearly separable components or milestones — recall **per key component**, not once on the main goal:

1. Split the task into its key components (milestones, subsystems, document sections).
2. Recall once per component with a short, focused goal for that component.
   - **This host's hooks are wired**: set `HYPER_PY="$HOME/.hyperstruck/venv/bin/python"; [ -x "$HYPER_PY" ] || HYPER_PY=python3` (the install venv when it exists, else `python3`), then run the read-only hook recall once per component goal: `PYTHONSAFEPATH=1 "$HYPER_PY" -m hyperstruck.ide.hook prompt --readonly --resolve-purpose agent_loop --emit text --goal '<component goal>' </dev/null`, with any `'` in the goal written as `'\''`. Each invocation mints its own throwaway `run_id` and the hook **declines it immediately** after printing — do not reinforce or decline these yourself, and do not treat them as one shared run.
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
         "result": "<short, redacted result>",
         # Names where this step happened, the same shape the wired hooks stamp
         # automatically. Omit it and the example is stored unsourced, still
         # counted, just with no session, repository or commit to check it against.
         "declared_sensitivity": {
             "provenance": {
                 "channel": "curl",
                 "genre": "coding_session",
                 "source_id": os.environ["RUN_ID"],
                 "source_time": "2026-01-01T00:00:00Z",  # replace with the real UTC instant
             }
         }}
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

**`"final_output"` does not belong on this call.** The composed answer is read on `POST /observe`, which is the only leg that harvests it; reinforce is about crediting what was offered, and an answer sent here is dropped and counted rather than recorded. If you want the commitments you make in your own answers on the shelf, send the episode to `/observe` with `"final_output"` in its `outcome` object, carrying **the answer you actually gave the person**, verbatim. It is the composed answer only, never a tool result or your reasoning: a tool result put there is stored as a promise you made. Omit it and nothing else changes.

What lands is a row **held for review**, not a line in your recall block. Your own answer has no external source vouching for it, so the shelf treats it as untrusted and keeps it where a person looks rather than offering it back to you automatically: read those rows with `GET /agents/{agent_id}/claims?kind=obligation&state=open`. They are not returned by `/resolve`.

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

`reason` is a closed set: `no_tool_calls`, `below_material_threshold`, `empty_offer`, `unevidenced_outcome`, `readonly_close`. Use `readonly_close` for a read-only recall that closes with no outcome to reinforce against: it earns nothing by design, and reporting it as one of the others files it as lost credit on the daily alert. Set `is_delivered` to whether the injected text actually reached the model this turn. Both endpoints return **202** — processing is asynchronous.

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
  "total": 1,
  "conflicts": [{"learning_id_a": "...", "learning_id_b": "...", "conflict_type": "contradiction"}]
}
```

`conflicts` names pairs the corpus has already recorded as contradicting each other, and is usually empty. An entry is kept when either side is in `items`, so a pair can name an id you did not get back: fetch it with `GET {BASE_URL}/agents/{agent_id}/learnings/{learning_id}`. When the list is not empty, say so rather than quoting one side as settled. Empty is not proof of a clean corpus.

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

## Obligations are claims now

Learnings remember what works and claims remember what is true. What is owed (a commitment with a party and a due date) is a claim too, held on the claim shelf and returned in the claims block of a recall as an owed claim. There are no separate obligation routes any more: the old `/obligations`, `/obligation-credit` and `/org/obligations` routes answer 404.

Read what is owed through the claims routes, filtering on the obligation kind:

```
GET {BASE_URL}/agents/{agent_id}/claims?kind=obligation&state=open
```

`owner` narrows to the obligations one entity holds and `due_before` to those due before an instant (with a UTC offset).

When an obligation is met, dropped or moved, correct the owed claim with the `correct` tool, or with the route behind it:

```
POST {BASE_URL}/agents/{agent_id}/statements
```

Send a fresh `request_id` (a UUID, the same one on a retry), `replaces` set to the statement id from the owed claim's `current`, and the new state in `mode` (`done` when it was met, `dropped` when it no longer applies, `owed` to reopen it), or a new `due_at` when the date moved. A correction needs the `claims:correct` scope. The `settle` tool and `POST {BASE_URL}/agents/{agent_id}/verdicts` choose between two claims that disagree. A change to a protected attribute from an agent is held beside the standing value and waits for a person.

A request that still sends `obligation_outcomes` to `/reinforce` or `/decline` is refused with 422 `field_retired`: report the met obligation with `POST /agents/{agent_id}/statements` instead.

---

## Distill from a referenced corpus

Use `POST /distill` when a **referenced document, an MCP result, or a tool call** brought in a corpus worth keeping, and you have no real run trace and no final learning text to store verbatim. Two kinds of corpus are worth sending, and the second is the one most often missed. A corpus carrying **contrast** — a design doc, spec, RFC, diff, or post-mortem, where a baseline sits against a fix — yields a *learning*. A corpus of **plain facts** with no contrast at all — a price list, an API reference, a policy note, a contract — yields *claims* on the fact shelf, and is worth sending for exactly that. Send either.

- **Endpoint**: `POST {BASE_URL}/distill` — this is **not** agent-UUID scoped. Its body carries `agent_name`, which must be the configured boundary agent name (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`) — the same corpus the automatic loop learns into — **not** the `HYPER_AGENT_ID` UUID used by `/agents/{id}/...`. If the task selected a different agent, use that agent's name.
- **Contrast decides which shelf, not whether to send.** Pair a baseline/failure with a fix/success, or supply an `evaluation` note, and the learning extractor has something to compare. Omit all of that and the corpus still carries facts, which reach the claim shelf; the run reports `weak_contrast` for the learning count it could not fill.
- **Give each item a `subject`** when the facts are about a named entity (an account, a product, a company). It is the name the facts are filed under, so without it two spellings of one company become two entities that never corroborate each other. Optionally add `declared_sensitivity.provenance` with `source_class` and `source_id` to say where the item came from. Both are sent verbatim, so they must carry no secret.
- **Every item states its `channel`**, how it reached you: `chat`, `email`, `meeting`, `document_store`, `system_of_record`, `api`, `claude_code`, `cursor`, `mcp`, `curl`, `web` (a page you fetched yourself), or `unknown` when you do not know. A missing channel is refused with a 422. Never guess one: it decides how the document is framed on its page.
- **`run_id` must start with `distill:`**; supply at least one item, with no item count or corpus total, since each item is stored and read as its own document.
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
      {"id": "baseline", "role": "contrast", "status": "failed", "channel": "document_store",
       "content": "<the old approach / problem the doc describes>"},
      {"id": "chosen", "role": "support", "status": "completed", "channel": "document_store",
       "content": "<the chosen approach and why it is better>"}
    ],
    "outcome": {"is_success": true, "summary": "Design finalized"},
    "evaluation": "<the general, reusable principle — not doc-specific naming>"
  }'
```

Returns **202 Accepted** after the request passes validation; extraction is asynchronous. A corpus with **no declared contrast is still accepted**: contrast is what the learning extractor compares against, so a corpus without it can still be full of facts, and a run that yields nothing for that reason reports `weak_contrast` on `GET /learning-runs/{run_id}/status`. A corpus that declares contrast but contains no reusable contrast may likewise yield zero learnings, reported as `contrast_not_found` when every item was read to the end, which means resending the same documents meets the same result, or `nothing_extracted` when the read was cut short or a pass failed, where silence is not evidence of absence and resending is worthwhile. The status also carries `items`, one entry per document you sent with what became of it, and `learnings_dropped_over_cap`, which counts learnings that passed every gate and were withheld because the `max_learnings` you asked for was already met. A zero yield is **not free**: the spend reservation settles as used, because it is about the work done rather than what it yielded, so report the outcome rather than retrying blindly. The extracted learnings are searchable via `GET /agents/{agent_id}/learnings/search` a few seconds later. Do **not** use `/distill` for a real execution trace (that is the automatic observe loop or the manual reinforce above) or for a learning you already have verbatim (use the store endpoint above).

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
- **From which agent(s)**: the agent name/id each call read from or wrote to (e.g. `HYPER_LEARNING_AGENT_NAME`/`HYPER_AGENT_NAME` for resolve/distill, the resolved agent UUID for search). On multi-agent recall, keep the result attributed to each queried agent.
- **How it affected the run**: the concrete decisions you changed (approach, ordering, a pitfall avoided, an entity fact you did not re-investigate). After the outcome is known, **close the loop** for every learning and claim you actually applied, once per recalled agent when you used curl fan-out.

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
