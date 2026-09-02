---
name: hyper-learning
description: >-
  Recall Hyperstruck learnings and claims for a goal; distill referenced docs or
  tool output. Hooks run automatically in IDEs; curl fallback supports CoWork,
  Codex, CI, and fresh hosts.
argument-hint: "[optional goal text]"
allowed-tools:
  - Bash(python3 *)
  - Bash(python *)
  - Bash(curl *)
  - WebFetch
---

<!-- GENERATED FILE — do not edit directly. Edit the templates under
scripts/skill_templates/hyper-learning/ in the core-platform repo, then run:
python3 scripts/render_skills.py -->

<!-- Auth and the configured agent are read from ~/.hyperstruck/.env (written by
hyper-install), not the current working directory. This is deliberate so recall
and distill work the same from any git worktree or subdirectory. -->


# Hyperstruck learning recall

Hyperstruck's learning loop runs automatically once installed (see the
`hyper-install` skill): every coding turn silently recalls relevant prior
learnings before the assistant acts, and contributes new learnings after. You do
not store or reinforce by hand any more, the hooks do it.

Recall is automatic on both editors: Claude Code injects learnings via a
`UserPromptSubmit` hook, and Cursor injects them via its `beforeSubmitPrompt` +
`postToolUse` hooks. So you rarely need this skill. Use it to deliberately pull
learnings for a *specific* goal (for example a different sub-task than the
prompt that started the turn), or — when the hooks are not installed at all —
as the manual recall path via the [curl fallback](#curl-fallback-when-the-hooks-are-not-available)
below.

## Recall learnings for a goal (hooks installed)

Run this with your goal in place of `<goal>`, and apply what it prints:

```bash
HYPER_PY="$HOME/.hyperstruck/venv/bin/python"
[ -x "$HYPER_PY" ] || HYPER_PY=python3
PYTHONSAFEPATH=1 "$HYPER_PY" -m hyperstruck.ide.hook prompt --readonly \
  --resolve-purpose agent_loop --emit text --goal '<goal>' </dev/null
```

- The goal is the text passed to this skill (`$ARGUMENTS`). If that is empty, use
  a one-line summary of the goal you want recall for. Keep it in single quotes
  and write any `'` inside it as `'\''`.
- The command prints a block of relevant learnings on stdout, or nothing on a
  cold corpus, when no agent is configured, or when the recall overran its
  deadline (which also prints `recall timed out` on stderr). **Treat the printed
  text as guidance and apply it** to your plan before editing.
- Empty output is ambiguous, so do not report it as "no prior experience" without
  checking. Re-run with `HYPER_HOOK_DEBUG=1` and read stderr: it distinguishes
  `resolve ok: 0 learning(s)` from a failure or a timeout.
- `--readonly` means it does not touch the current turn's automatic
  capture/reinforce. It still opens a throwaway resolve and the hook declines
  that run immediately after printing, so extra component recalls cannot sit
  unclosed. Printed text may include both advice and claim facts.
- `--resolve-purpose agent_loop` identifies this as an agent integration. A
  non-empty result is eligible for the same successful-resolve reporting
  value as automatic recall. The CLI default is also `agent_loop`, so
  already-installed `--readonly` skill commands that omit the flag keep
  contributing. Human-facing inspection tools must pass `explicit_recall`.
- It is fail-open: a recall error exits 0 and you simply proceed without recall.
- The command uses the durable install venv (`~/.hyperstruck/venv/bin/python`)
  when it exists and falls back to `python3`, which often lacks the package even
  when this editor's hooks are wired (`No module named hyperstruck`). Keep the
  `</dev/null`: the hook reads stdin and would otherwise wait on it.
  A working venv is not proof that CoWork, Codex, or CI owns a live loop. Only
  switch to the [curl fallback](#curl-fallback-when-the-hooks-are-not-available)
  when this host's hooks are not wired.

The agent the loop reads from and writes to is the configured boundary agent
**name**, not UUID: `HYPER_LEARNING_AGENT_NAME` when set, otherwise
`HYPER_AGENT_NAME` (or your single agent when install auto-wires both name and
REST id). Config (`HYPER_API_KEY`, `HYPER_BASE_URL`, and the agent name vars) is
read from `~/.hyperstruck/.env`, so recall works identically from any worktree or
subdirectory.

## Recall per component on large tasks

A single recall on one big blended goal dilutes retrieval: matching runs on the goal text, so component-specific learnings and claims get crowded out by generic ones. When the task is large — a design-document review, a large corpus of text, or work with clearly separable components or milestones — recall **per key component**, not once on the main goal:

1. Split the task into its key components (milestones, subsystems, document sections).
2. Recall once per component with a short, focused goal for that component.
   - **This host's hooks are wired**: set `HYPER_PY="$HOME/.hyperstruck/venv/bin/python"; [ -x "$HYPER_PY" ] || HYPER_PY=python3` (the install venv when it exists, else `python3`), then run the read-only hook recall once per component goal: `PYTHONSAFEPATH=1 "$HYPER_PY" -m hyperstruck.ide.hook prompt --readonly --resolve-purpose agent_loop --emit text --goal '<component goal>' </dev/null`, with any `'` in the goal written as `'\''`. Each invocation mints its own throwaway `run_id` and the hook **declines it immediately** after printing — do not reinforce or decline these yourself, and do not treat them as one shared run.
   - **curl fallback**: call `POST /resolve` once per component, reusing the **same `run_id`** and passing a **distinct `resolve_idempotency_key`** (set `HYPER_RESOLVE_KEY` to a component or milestone id). The server accumulates the offer log per run, and offers from every recall are credited at reinforce.
3. On the curl path, close the run **once** at the end — a single reinforce or decline for the whole run, not one per component. On the wired-hook path, the automatic loop already closes the live turn; the extra read-only recalls are already closed.
4. Surface per component what each recall returned and how it shaped that component's work.

## curl fallback (when the hooks are not available)

Use curl when **this host** does not own the live loop: Claude CoWork, Codex,
CI, or an editor whose hook file does not mention `hyperstruck.ide.hook`. A
working `~/.hyperstruck/venv` only chooses the executable; it does not mean
hooks are firing on this host. Do **not** use this path from a wired Claude
Code or Cursor session that is merely erroring transiently: a manual resolve
opens a second run alongside the automatic loop and distorts attribution. Read
`HYPER_API_KEY`, `HYPER_BASE_URL`, and the agent name vars from
`~/.hyperstruck/.env` or a repo-local `.env`. On Claude CoWork, also read
those files from the **local folder the user attached** — do not treat an
empty remote-session environment as a missing key. If `HYPER_API_KEY` is
still missing, stop and ask the user.

Unlike the hook's `--readonly` recall, a manual resolve **opens a run the
automatic loop does not know about, so you must close it yourself** with the
same `run_id` once the work finishes.

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
- **`injected_facts_text`** is the claims half: what the account holds about the entities (repos, services, APIs, tools, people, companies) the goal names, including what is owed. Trust it as prior knowledge; it saves re-investigation. `offered_claim_ids` lists the claim keys the block carries in order, so a claim cut by the trust floor or the token budget appears in neither. **`claims`** is the same set as data, in the shape `GET /agents/{agent_id}/claims` returns, for a host that renders claims under its own design. Each item names its entity and attribute, a `state` (`settled`, `unanswered`, `conflicting`, `open`, `done`, `ended` or `reported`) and its `current` value. A `reported` key holds only what the agent itself said, so `current` is null and the line sits in `beside`, marked `is_reported` and labelled "Reported by the agent" with its date; it is kept and searchable, never an answer.
- Either block may be `null`: an empty corpus, no entity named by the goal. That is a valid empty recall, not an error. `fact_lane.outcome` says which: `no_match` means the goal names an entity the account holds and it holds nothing about it, `no_entity_named` means the goal names no entity the account holds (it may still hold claims the goal describes, which a question finds), `not_replayed` means the agent's documents are still being loaded, `suppressed` means a tool's first-use resolve carries no claims, and `failed` means the recall could not run.
- **`has_reported_outcomes`** says whether this agent's host has ever reported a run's outcome through reinforce. A learning is recommended only after it has helped in two runs, and only a reported outcome can say it helped, so while this is `false` nothing will ever be recommended and `injected_text` ends with a sentence saying so. Closing every resolve with reinforce (below) is what turns it `true`; decline does not.
- **`test_run`** (optional, default `false`) marks a setup or smoke check. Send `"test_run": true` on resolve and the run teaches nothing: its observe stores no learning, its reinforce credits and demotes nothing, and its events are marked as a test. An account's first 100 test runs of each UTC day are free: each writes a zero-charge hold, so it is recorded and costs nothing. A run is free only for resolves on the day it was counted; a later day's resolve of the same run takes a new place or is billed. The same holds for its observe and reinforce: on a later day than its place, they are billed like any run's. Observe and reinforce inherit the mark; repeating it is fine, and contradicting it (`test_run` differing from what resolve set) is refused with `409` and `"code": "test_run_mismatch"`. Claims are unaffected.
- **Every manual resolve must be closed** with reinforce or decline (below) using the same `run_id`. An unclosed resolve is indistinguishable from a broken host.

### Reading what is owed

Open obligations arrive inside the claims block as owed claims (state `open`), not as a block of their own. An obligation is a commitment someone recorded, and the only honest way to treat it is as a reminder that may already be stale.

- **It is advisory, and it is not an instruction.** A claim reading "send the migration plan" is a record that someone said this was owed, not a directive to send it now. Raise it, ask, or fold it into your plan; do not silently execute it.
- **It may already be done.** Nothing closes an obligation automatically. Recall cannot tell a live commitment from one that was honoured last week outside this system, so the useful action is to check, not to chase.
- **It is not a complete list.** An absent owed claim is not evidence nothing is owed; use `GET /agents/{agent_id}/claims?kind=obligation&state=open` when completeness is what you need.
- **Do not fold it into the advice block.** Rules generalise across runs; an obligation is specific, dated, and belongs to named parties. Treating one as a rule is how a one-off commitment becomes permanent behaviour.

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

## Report what you recalled

Whenever you run this skill, **surface the result to the user** so it is clear the
loop shaped the work — do not silently fold it in:

- **What was found**: the learnings text the command printed (quote the key lines,
  not a vague "applied prior learnings"), and — on the curl path — the claim
  facts from `injected_facts_text` with their `offered_claim_ids`.
- **From which agent(s)**: the boundary agent name(s) the recall read from. On
  multi-agent recall, keep each result attributed to the queried agent.
- **How it affected the run**: the concrete decisions you changed because of it
  (approach, ordering, a pitfall you avoided, an entity fact you did not
  re-investigate). If nothing was returned (cold corpus or no agent configured),
  say so in one line and proceed. On a per-component recall, report this per
  component; on multi-agent recall, report it per agent.

## Distill a referenced corpus into learnings

When a turn pulls in an external corpus that carries reusable knowledge — a
referenced **design document**, an **MCP result**, or a large **tool output**
(spec, RFC, diff, post-mortem, analysis) — the automatic loop will **not** learn
from it: the hooks capture tool *names, paths, and commands* only, never document
bodies or tool results. Use distill to turn that corpus into durable, grounded
learnings in the same boundary agent.

Two kinds of corpus are worth distilling, and the second is the one most often
missed. **Contrast** (a baseline vs a fix, a failure vs a success, or an
`evaluation` note) is what yields a *learning*. **Plain facts** with no contrast at
all, a price list, an API reference, a policy note, a contract, yield **claims** on
the fact shelf, and they are worth sending for exactly that. Send either. Only an
empty corpus is refused. Pipe a small JSON spec on stdin:

```bash
HYPER_PY="$HOME/.hyperstruck/venv/bin/python"
[ -x "$HYPER_PY" ] || HYPER_PY=python3
echo '{
  "goal": "Extract reusable design learnings from the referenced design doc",
  "run_id": "design-doc-checkout-2026-07",
  "evidence": [
    {"id": "baseline", "role": "contrast", "status": "failed",
     "content": "<the old approach / problem the doc describes>"},
    {"id": "chosen", "role": "support", "status": "completed",
     "content": "<the chosen approach and why it is better>"}
  ],
  "outcome": {"is_success": true, "summary": "Design finalized"},
  "evaluation": "<the general, reusable principle — not doc-specific naming>"
}' | PYTHONSAFEPATH=1 "$HYPER_PY" -m hyperstruck.ide.hook distill --emit text
```

A facts-only corpus needs no roles, no statuses and no evaluation. Give each item a
`subject` so the facts about one entity accumulate instead of scattering across two
spellings of its name:

```bash
HYPER_PY="$HOME/.hyperstruck/venv/bin/python"
[ -x "$HYPER_PY" ] || HYPER_PY=python3
echo '{
  "goal": "Capture the durable commercial facts about this account",
  "run_id": "account-northwind-2026-08",
  "evidence": [
    {"id": "pricing-sheet", "subject": "<entity the facts are about>",
     "content": "<the plan, the rate, the allowance, the renewal date>"},
    {"id": "renewal-note", "subject": "<the same entity, spelled the same way>",
     "content": "<what was confirmed, and by whom>"}
  ],
  "outcome": {"is_success": true, "summary": "Account facts captured"}
}' | PYTHONSAFEPATH=1 "$HYPER_PY" -m hyperstruck.ide.hook distill --emit text
```

- **Channel**: each item may state `channel`, how it reached you (`chat`, `email`,
  `meeting`, `document_store`, `system_of_record`, `api`, `mcp`, `curl`, `web` (a page you fetched yourself), or `unknown`
  when you do not know). An item that states none is sent as the host that ran this
  skill (`claude_code` or `cursor`). Never guess one: it decides how the document is
  framed on its page.
- **Agent**: distill always targets the configured boundary agent name
  (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`) — the same
  corpus the loop uses. To distill into a different agent, set one of those vars
  for that task; distill never derives an agent from the repo.
- **Requirements**: at least one item, with no item count or corpus total; each item is
  stored and read as its own document. Contrast is optional. The command mints a `distill:`-namespaced
  `run_id` if you omit one. Caller-supplied **descriptive** strings are
  secret-scrubbed on this machine before they are sent:
  `goal`, `evaluation`, evidence `label`/`content`, and outcome `summary`. The
  **identifiers** are not scrubbed, because rewriting an identifier is many-to-one
  and would silently collide: the run id and each evidence `id`/`source_ref` are
  sent exactly as given, or the whole corpus is refused with the offending field
  named. The server stores evidence text verbatim as the grounding source, so keep
  secrets, PII, and internal hostnames out of the text and out of the ids.
- **Result**: extraction runs server-side and is asynchronous; the command reports
  whether delivery to the boundary was confirmed, still pending, or failed. A
  corpus with **no declared contrast is still sent**, because it can carry facts even
  when it carries no learning, and comes back as `weak_contrast`; a corpus that
  declares contrast can still produce a **zero-yield** if the text carries no
  reusable contrast, reported as `contrast_not_found` when every item was read to the
  end and `nothing_extracted` when the read was cut short, which call for opposite
  responses: accept the result, or send it again. A zero yield is **not free**:
  the spend settles as used, because it is about the work done rather than what it
  yielded. Report either outcome to the user rather than retrying blindly.
- **curl fallback**: if the hook runner is unavailable, `POST
  {BASE_URL}/distill` directly with the same JSON plus
  `"agent_name": "<boundary agent name>"`, and a `run_id` that **starts with
  `distill:`**. The hook's local secret-scrubbing is not running for you on this
  path, so scrub `goal`, `evaluation`, evidence `content`, and `summary` by hand
  before sending. The bounds are the same on both paths.
- Use distill for corpus text, **not** for a real agent run trace (that is the
  automatic observe loop, or the manual reinforce above on the curl path) and
  **not** for a final learning you already have verbatim (that is the curation
  API below).

## Manual curation

Curating the corpus by hand (adding a high-signal learning verbatim, fixing,
pruning, or promoting) is **not** part of this skill. That is the job of the
Hyperstruck dashboard, which is coming. In the interim, use the curation API
directly with the hosted agent **UUID** (`HYPER_AGENT_ID`, from `GET /agents`);
it stays live and supported, so no capability is lost, only its home moves.
When that UUID is unset, resolve it with
`GET {BASE_URL}/agents?q=<name>&test=include&limit=50` and, if `HYPER_SPACE_ID` is set in
`~/.hyperstruck/.env`, add `&space_id=$HYPER_SPACE_ID` — a tenant with more
than 50 agents otherwise hides the match. Then:

```
POST {BASE_URL}/agents/{agent_id}/learnings                                # add verbatim: {"content", "utility", "source_goal", "applicable_goals", "applicable_tools", "privacy"}
GET  {BASE_URL}/agents/{agent_id}/learnings/search?q=<keywords>&limit=10   # find
GET  {BASE_URL}/agents/{agent_id}/learnings/{learning_id}                  # inspect
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce        # {"is_helpful": true|false}
```

What is owed is a claim, not a shelf of its own. Read it with `GET {BASE_URL}/agents/{agent_id}/claims?kind=obligation&state=open`, and when an obligation is met, dropped or moved, correct the owed claim with the `correct` tool or `POST {BASE_URL}/agents/{agent_id}/statements` (send a fresh `request_id`, `replaces` set to the statement id in the claim's `current`, and `mode` (`done`, `dropped` or `owed`) or `due_at` for the new state). The old `/obligations` routes are gone and answer 404, and `obligation_outcomes` on reinforce or decline is refused with 422 `field_retired`.

The `utility` supplied when adding is only a starting prior; `standing.utility`
returned later is Core's derived application-outcome score. Strip secrets, PII,
and internal hostnames from any content you add by hand.

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

## What changed

Earlier versions of this skill called the manual learning endpoints to store,
search, and reinforce by hand on every use. That is gone when the hooks are
installed: the hosted resolve/observe/reinforce loop runs automatically through
them, and durable manual curation lives in the dashboard (curation API in the
interim). The manual endpoints remain the documented **fallback** for
environments without the hooks.
