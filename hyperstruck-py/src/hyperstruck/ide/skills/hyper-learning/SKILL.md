---
name: hyper-learning
description: >-
  Explicitly recall relevant Hyperstruck learnings and claims for a goal, so
  prior experience informs the work, and distill durable learnings from a
  referenced corpus (a design document, MCP result, or tool output) that the
  automatic loop cannot see. Recall, capture, and reinforcement already run
  automatically through the learning hooks on both Claude Code and Cursor; when
  the hooks are not installed or not working (Claude CoWork, Codex, CI, a fresh
  machine), this skill falls back to direct curl calls against the API. On large
  tasks, recall per key component rather than once on the main goal.
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
`~/.hyperstruck/.env` or a repo-local `.env`; if `HYPER_API_KEY` is missing
from both, stop and ask the user.

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
  "offered_learning_ids": ["..."],
  "offered_claim_ids": ["..."]
}
```

How to use it:

- **`injected_text`** is the advice half — treat it as rules that shape your plan.
- **`injected_facts_text`** is the claims half — established facts about entities (repos, services, APIs, tools) the agent already investigated. Trust them as prior knowledge; they save re-investigation. `offered_claim_ids` mirrors the fact block in order — a fact cut by trust floor or token budget appears in neither.
- Both halves may be `null` on an empty corpus — that is a valid empty recall, not an error.
- **Every manual resolve must be closed** with reinforce or decline (below) using the same `run_id`. An unclosed resolve is indistinguishable from a broken host.

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

Distill needs **contrast** (that is what yields a learning): a baseline vs a fix,
a failure vs a success, or an `evaluation` note. A single descriptive paragraph
yields nothing by design. Pipe a small JSON spec on stdin:

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

- **Agent**: distill always targets the configured boundary agent name
  (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`) — the same
  corpus the loop uses. To distill into a different agent, set one of those vars
  for that task; distill never derives an agent from the repo.
- **Requirements**: at least 2 evidence items with a declared contrast; the
  command mints a `distill:`-namespaced `run_id` if you omit one. Caller-supplied
  **descriptive** strings are secret-scrubbed on this machine before they are sent:
  `goal`, `evaluation`, evidence `label`/`content`, and outcome `summary`. The
  **identifiers** are not scrubbed, because rewriting an identifier is many-to-one
  and would silently collide: the run id and each evidence `id`/`source_ref` are
  sent exactly as given, or the whole corpus is refused with the offending field
  named. The server stores evidence text verbatim as the grounding source, so keep
  secrets, PII, and internal hostnames out of the text and out of the ids.
- **Result**: extraction runs server-side and is asynchronous; the command reports
  whether delivery to the boundary was confirmed, still pending, or failed. A
  corpus with **no declared contrast is skipped locally**; a delivered corpus with
  declared contrast can still produce a **zero-yield** if the text carries no
  reusable contrast — report that outcome to the user rather than retrying
  blindly.
- **curl fallback**: if the hook runner is unavailable, `POST
  {BASE_URL}/distill` directly with the same JSON plus
  `"agent_name": "<boundary agent name>"`, and a `run_id` that **starts with
  `distill:`**. The hook's local secret-scrubbing is not running for you on this
  path, so scrub `goal`, `evaluation`, evidence `content`, and `summary` by hand
  before sending. A no-contrast corpus is rejected by the server.
- Use distill for corpus text, **not** for a real agent run trace (that is the
  automatic observe loop, or the manual reinforce above on the curl path) and
  **not** for a final learning you already have verbatim (that is the curation
  API below).

## Manual curation

Curating the corpus by hand (adding a high-signal learning verbatim, fixing,
pruning, or promoting) is **not** part of this skill. That is the job of the
Hyperstruck dashboard, which is coming. In the interim, use the curation API
directly with the hosted agent **UUID** (`HYPER_AGENT_ID`, from `GET /agents`);
it stays live and supported, so no capability is lost, only its home moves:

```
POST {BASE_URL}/agents/{agent_id}/learnings                                # add verbatim: {"content", "utility", "source_goal", "applicable_goals", "applicable_tools", "privacy"}
GET  {BASE_URL}/agents/{agent_id}/learnings/search?q=<keywords>&limit=10   # find
GET  {BASE_URL}/agents/{agent_id}/learnings/{learning_id}                  # inspect
POST {BASE_URL}/agents/{agent_id}/learnings/{learning_id}/reinforce        # {"is_helpful": true|false}
```

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
