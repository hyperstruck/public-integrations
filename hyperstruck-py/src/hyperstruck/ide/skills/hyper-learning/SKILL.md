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

Print the learnings relevant to a goal and apply them:

```!
PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook prompt --readonly \
  --resolve-purpose agent_loop --emit text --goal "$ARGUMENTS"
```

- If `$ARGUMENTS` is empty, pass a one-line summary of the goal you want recall for.
- The command prints a block of relevant learnings (or nothing, on a cold corpus,
  if no agent is configured, or if the recall overran its deadline). **Treat the
  printed text as guidance and apply it** to your plan before editing.
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
- It is fail-open: any error prints nothing and you simply proceed without recall.
- If the command cannot run (`No module named hyperstruck`,
  `python3: command not found`), first retry with the durable install venv:
  `~/.hyperstruck/venv/bin/python -m hyperstruck.ide.hook prompt --readonly --resolve-purpose agent_loop …` —
  bare `python3` often lacks the package even when this editor's hooks are wired.
  A working venv is not proof that CoWork, Codex, or CI owns a live loop. Only
  switch to the [curl fallback](#curl-fallback-when-the-hooks-are-not-available)
  when this host's hooks are not wired.

The agent the loop reads from and writes to is the configured boundary agent
**name**, not UUID: `HYPER_LEARNING_AGENT_NAME` when set, otherwise
`HYPER_AGENT_NAME` (or your single agent when install auto-wires both name and
REST id). Config (`HYPER_API_KEY`, `HYPER_BASE_URL`, and the agent name vars) is
read from `~/.hyperstruck/.env`, so recall works identically from any worktree or
subdirectory. For deeper, explicit reasoning that selects the most appropriate
agent for a task, use the `hyper-reasoning` skill.

## Recall per component on large tasks

A single recall on one big blended goal dilutes retrieval: matching runs on the goal text, so component-specific learnings and claims get crowded out by generic ones. When the task is large — a design-document review, a large corpus of text, or work with clearly separable components or milestones — recall **per key component**, not once on the main goal:

1. Split the task into its key components (milestones, subsystems, document sections).
2. Recall once per component with a short, focused goal for that component.
   - **This host's hooks are wired**: run the read-only hook recall once per component goal: `PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook prompt --readonly --resolve-purpose agent_loop --emit text --goal "<component goal>"` (use `~/.hyperstruck/venv/bin/python` when `HYPER_VENV=available`). Each invocation mints its own throwaway `run_id` and the hook **declines it immediately** after printing — do not reinforce or decline these yourself, and do not treat them as one shared run.
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
  "injected_obligations_text": "<block of open obligations bearing on this moment>",
  "offered_learning_ids": ["..."],
  "offered_claim_ids": ["..."],
  "offered_obligation_ids": ["..."]
}
```

How to use it. Three blocks, and they differ in kind, not just in content:

- **`injected_text`** is the advice half. It arrives banded, and the bands are the point: standards the customer stated outright come first and are followed unless the goal explicitly overrides one, then workflow constraints, constraints, recommendations, supplementary and tool preferences. Each band states its own weight in its heading, so read them rather than treating the whole block as one rule set: a constraint is to be addressed where its condition holds, while a supplementary item is to be verified before it is applied. Place the block as given. Re-ranking it, re-ordering it or truncating it discards the only signal that says which of two conflicting learnings wins.
- **`injected_facts_text`** is the claims half — established facts about entities (repos, services, APIs, tools) the agent already investigated. Trust them as prior knowledge; they save re-investigation. `offered_claim_ids` mirrors the fact block in order — a fact cut by trust floor or token budget appears in neither.
- **`injected_obligations_text`** is the obligations half — what is *owed*, by whom, to whom, and by when. This is the block most easily misread, so read the rules below before acting on it.
- Any of the three may be `null` — an empty corpus, no bound entity, nothing due. That is a valid empty recall, not an error.
- **Every manual resolve must be closed** with reinforce or decline (below) using the same `run_id`. An unclosed resolve is indistinguishable from a broken host.

### Using the obligations block

An obligation is neither a fact nor a rule. It is a commitment someone recorded, and the only honest way to treat it is as a reminder that may already be stale.

- **It is advisory, and it is not an instruction.** Every line says so. A line reading "send the migration plan" is a record that someone said this was owed, not a directive to send it now. Raise it, ask, or fold it into your plan; do not silently execute it.
- **It may already be done.** Nothing closes an obligation automatically. Recall cannot tell a live commitment from one that was honoured last week outside this system, and a marker asking you to close or confirm is the shelf telling you exactly that: the useful action is to check, not to chase.
- **It is capped and it is small.** A handful of lines, ranked, with the rank stated in each line rather than implied by order. An absent obligation is not evidence there is none — it may have been below the cap, past the horizon, or cut by the block's token budget. Never read this block as a complete list of what is owed; use `GET /agents/{agent_id}/obligations?status=open` when completeness is what you need.
- **A marker saying what it rested on has changed** means a fact this obligation was premised on has since been superseded. The obligation may still stand; the reasoning behind it no longer does. Verify the premise before acting.
- **Do not fold it into the advice block.** Rules generalise across runs; an obligation is specific, dated, and belongs to named parties. Treating one as a rule is how a one-off commitment becomes permanent behaviour.

Optional request fields shape this block, all omitted by default:

- `timezone` — an IANA zone (`Australia/Sydney`). Dates render in it, and a date-only due is overdue only after end of day in it, so this changes which obligations are late rather than merely how they read. Falls back to the agent's own zone, then to UTC with a marker on the block saying so.
- `obligation_horizon_days` — how far ahead to look. Defaults from `resolve_purpose`: `0` for `agent_loop` and `7` for `explicit_recall` (a human planning the week). The horizon governs obligations whose actionability window has not opened yet: one already inside its window is returned whatever the horizon, so `0` means overdue, due today, and anything already actionable, not overdue and due today alone.
- `max_obligations` — how many lines the block may carry. `0` turns it off for this call.
- `as_of` — the moment the set is computed against, offset required. Defaults to now.

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

What lands is a row **held for review**, not a line in your recall block. Your own answer has no external source vouching for it, so the shelf treats it as untrusted and keeps it where a person looks rather than offering it back to you automatically: read those rows with `GET /agents/{agent_id}/obligations?needs_review=true`. They are not returned by `/resolve`.

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
- **From which agent**: the boundary agent name (`HYPER_LEARNING_AGENT_NAME` when
  set, otherwise `HYPER_AGENT_NAME`) the recall read from.
- **How it affected the run**: the concrete decisions you changed because of it
  (approach, ordering, a pitfall you avoided, an entity fact you did not
  re-investigate). If nothing was returned (cold corpus or no agent configured),
  say so in one line and proceed. On a per-component recall, report this per
  component.

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

```!
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
}' | PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook distill --emit text
```

A facts-only corpus needs no roles, no statuses and no evaluation. Give each item a
`subject` so the facts about one entity accumulate instead of scattering across two
spellings of its name:

```!
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
}' | PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook distill --emit text
```

- **Agent**: distill always targets the configured boundary agent name
  (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`) — the same
  corpus the loop uses. To distill into a different agent, set one of those vars
  for that task; distill never derives an agent from the repo.
- **Requirements**: up to 200 items; the corpus is capped at 240,000 non-whitespace
  characters in total; a single item may be the whole corpus. The command checks those
  bounds itself, so an oversized corpus is refused here with the reason and the item the
  next job should start at, rather than remotely as a bare status code.
  Contrast is optional. The command mints a `distill:`-namespaced
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
`GET {BASE_URL}/agents?q=<name>&limit=50` and, if `HYPER_SPACE_ID` is set in
`~/.hyperstruck/.env`, add `&space_id=$HYPER_SPACE_ID` — a tenant with more
than 50 agents otherwise hides the match. Then:

```
POST {BASE_URL}/agents/{agent_id}/learnings                                # add verbatim: {"content", "utility", "source_goal", "applicable_goals", "applicable_tools", "privacy"}
GET  {BASE_URL}/agents/{agent_id}/learnings/search?q=<keywords>&limit=10   # find
GET  {BASE_URL}/agents/{agent_id}/learnings/{learning_id}                  # inspect
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce        # {"is_helpful": true|false}
```

A fourth shelf, obligations, holds what is owed rather than what is true or what works:

```
POST {BASE_URL}/agents/{agent_id}/obligations   # {"statement", "owed_by", "owed_to", "due": {"at", "tz", "precision"}}
GET  {BASE_URL}/agents/{agent_id}/obligations?status=open&timezone=<iana zone>
GET  {BASE_URL}/agents/{agent_id}/obligations/open-count                  # {"open_count"}: this agent's open, unexpired obligations
GET  {BASE_URL}/agents/{agent_id}/obligations/{obligation_id}
POST {BASE_URL}/agents/{agent_id}/obligations/{obligation_id}/close        # {"outcome": "kept"|"dropped", "kept_basis"|"dropped_reason", "expected_version"}
POST {BASE_URL}/agents/{agent_id}/obligations/{obligation_id}/cancel       # {"note", "expected_version"} — withdraws the RECORD
POST {BASE_URL}/agents/{agent_id}/obligations/{obligation_id}/supersede    # {"successor": {…obligation body…}, "expected_version"}
POST {BASE_URL}/agents/{agent_id}/obligations/{obligation_id}/reschedule   # {"due": {"at", "tz", "precision"}, "expected_version"}
GET  {BASE_URL}/agents/{agent_id}/obligation-credit                        # how reliable each harvesting source has proved
```

The write is 202 with `{"id", "outcome"}`; a capacity or dedupe refusal is a 202 outcome, never an error. `due.at` must carry a UTC offset. Two outcomes (`suppressed`, `evicted_then_written`) are reserved for now — they need a harvested write, and this endpoint always writes `user_directed`. A date-precision due (`"precision": "date"`) lists back with `due_local` as the day itself (`YYYY-MM-DD`), not an instant.

The list also filters on `q` (text contained in the statement), `provenance_class` (what a person asked for versus what was read off a note), and `needs_review` (the open rows waiting on a person rather than on a due date, each returned with `review_reasons`). Pages are cursored: pass `next_cursor` back verbatim as `after`.

Nothing closes an obligation by itself. `close` decides the commitment and needs `kept_basis` (`reported`, `evidenced`, `declared`) when kept or `dropped_reason` (`not_an_obligation`, `no_longer_applies`, `wont_do`, `duplicate`) when dropped, and only `not_an_obligation` counts against the source. `cancel` withdraws the record instead — a test write, a bad import — taking no reason, writing no suppression key, and moving no source's credit. `supersede` closes this row and writes its linked successor in one step, returning the successor, or changes nothing at all. `reschedule` moves the due and keeps the identity. Each of the four takes an optional `expected_version`, and a stale one is a 409 whose body carries `current_version`.

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
