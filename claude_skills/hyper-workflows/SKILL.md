---
name: hyper-workflows
description: >-
  Find, run, draft and save Hyperstruck workflows (saved request-to-answer graphs
  with evals). Use when a task may already be a workflow, or the user asks to build
  one.
argument-hint: "[goal, or 'draft <goal>', or 'run <workflow>']"
allowed-tools:
  - Bash(curl *)
  - Bash(python3 *)
  - WebFetch
---

<!-- GENERATED FILE — do not edit directly. Edit the templates under
scripts/skill_templates/hyper-workflows/ in the core-platform repo, then run:
python3 scripts/render_skills.py -->

# Hyperstruck workflows

A **workflow** is a saved request-to-answer graph on the Hyperstruck platform. A caller
sends one request body; a **trigger** step summarises it, an optional **insight** step
runs a standing question over the account's agents, up to three **evals** judge it
(a label, a score, or a yes/no probability) on a trained evaluator, and an **answer**
step writes the reply. Every run is logged, metered and fed back into the workflow's
own learning agent (`workflow:<name>`), so it improves with use.

Use this skill to:

- **Find** a workflow that already does the user's task, with what its agents learned.
- **Run** it on a request body and read the answer and eval results.
- **Draft** a new workflow from a plain-language goal, check it, and **save** it.

Do not use it to manage evals or train evaluators; that is the portal's job.

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

## MCP tools first

When the Hyperstruck MCP server is connected (`mcp.hyperstruck.com/mcp`), use its six
workflow tools rather than curl. They carry auth, redaction and status mapping
(`accepted`, `invalid_request`, `not_found`, `quota_exceeded`, ...).

| Tool | Does | REST |
| --- | --- | --- |
| `list_workflows(goal?, q?, include_context=false, limit?, cursor?)` | Find workflows; with `goal`, best fit first. `include_context=true` recalls `context` (billed, at most six resolves) | `GET /workflows` |
| `get_workflow(workflow)` | Full definition, by id or exact name | `GET /workflows/{id}` |
| `run_workflow(workflow, input, wait_seconds=30, idempotency_key?)` | Run on one request body | `POST /workflows/{id}/runs` |
| `get_workflow_run(run_id)` | Poll a run | `GET /workflow-runs/{run_id}` |
| `draft_workflow(goal, sample_input?, constraints?, install_starter_evals=true)` | Draft a definition; saves nothing but a missing starter eval | `POST /workflows/compose` |
| `save_workflow(definition, workflow_id?, dry_run=false)` | Validate (`dry_run`), create, or save a new version | `POST /workflows/validate`, `POST /workflows`, `PATCH /workflows/{id}` |

Without MCP, call the REST routes below with `HYPER_API_KEY`. Either way, a `404` on
every workflow route means workflows are not enabled for the account; say so and stop.

---

## 1. Find a workflow for the task

Pass the user's task in their own words as `goal`. Only workflows that fit come back,
best first, each with `match` (`score` 0-1, `matched_terms`, `matched_in`). On MCP,
`include_context` defaults false so listing does not bill. Pass `include_context=true`
to recall `context` for the top matches: one block per learning agent (the workflow's
own, then the agents its insight consults) with `learnings_text` and `facts_text`. That
is a billed resolve per agent (at most six). Read those blocks before running; they are
what earlier runs taught.

```bash
curl -sS -G "$HYPER_BASE_URL/workflows" \
  -H "Authorization: Bearer $HYPER_API_KEY" \
  --data-urlencode "goal=Triage this support ticket and tell me which queue it belongs in"
```

- A goal-ranked list is one page (no `cursor`). REST `include_context` still defaults
  true; pass `false` on curl to skip recall.
- Each item already holds `purpose`, `input_schema`, `important_fields`, `output` and
  `example_input`: everything you need to call it. No match means no workflow does the
  task yet; offer to draft one (step 3).

## 2. Run it

Build `input` from the item's `input_schema`: field name to a string, number or
boolean, every `required` field present. Values are not parsed: `"42"` is not a number.

```bash
curl -sS -X POST "$HYPER_BASE_URL/workflows/$WORKFLOW_ID/runs?wait_seconds=30" \
  -H "Authorization: Bearer $HYPER_API_KEY" -H "Content-Type: application/json" \
  -d '{"input": {"subject": "Login broken for every user", "arr_usd": 250000},
       "idempotency_key": "ticket-2048"}'
```

- `200`: finished. `status` is `succeeded` with `answer` and `eval_outputs`, or
  `failed` with `error_code`.
- `202`: still going; poll `GET /workflow-runs/{run_id}` until `status` is
  `succeeded`, `failed` or `cancelled`.
- `422` lists input problems by `/input/<field>`; fix them and retry.
- `403` with `reason` `spend_limit`, or `429` with `Retry-After`: the account is out
  of budget or rate; tell the user, do not loop.
- Reuse `idempotency_key` when retrying, so a retry never runs twice.

Report the answer and each eval's result to the user. Do not invent eval values a run
did not return.

## 3. Draft a new workflow

Only when the user asks for one, or agrees after step 1 found nothing.

```bash
curl -sS -X POST "$HYPER_BASE_URL/workflows/compose" \
  -H "Authorization: Bearer $HYPER_API_KEY" -H "Content-Type: application/json" \
  -d '{"goal": "Triage inbound support tickets by urgency; route enterprise customers to a human",
       "sample_input": {"subject": "Login broken", "body": "Nobody can sign in", "arr_usd": 250000},
       "constraints": {"max_evals": 2, "answer_format": "json"}}'
```

The response holds `definition`, `suggested_evals` (each with `reason`, `source`
`existing` or `starter`, and `installed_now`), `rationale`, `warnings` and `problems`.
It is one small model call held against the spend limit. It saves nothing except a
suggested starter eval the account does not have yet; send
`"install_starter_evals": false` to avoid that (the draft then leaves those evals out).

Show the user the draft in plain terms: what it takes in, what each eval judges and
why, what it answers. Edit what they ask for in `definition` directly.

## 4. Check, then save

```bash
# Check only; saves nothing. 200 means valid.
curl -sS -X POST "$HYPER_BASE_URL/workflows/validate" \
  -H "Authorization: Bearer $HYPER_API_KEY" -H "Content-Type: application/json" \
  -d "{\"definition\": $(cat definition.json)}"

# Save a new workflow (201) ...
curl -sS -X POST "$HYPER_BASE_URL/workflows" \
  -H "Authorization: Bearer $HYPER_API_KEY" -H "Content-Type: application/json" \
  -d @definition.json

# ... or a new version of an existing one.
curl -sS -X PATCH "$HYPER_BASE_URL/workflows/$WORKFLOW_ID" \
  -H "Authorization: Bearer $HYPER_API_KEY" -H "Content-Type: application/json" \
  -d @definition.json
```

To edit a saved workflow over REST, fetch it and drop the fields the server added before
sending it back, or the save is a `422` for unknown fields (`save_workflow` does this
for you):

```bash
curl -sS "$HYPER_BASE_URL/workflows/$WORKFLOW_ID" -H "Authorization: Bearer $HYPER_API_KEY" \
  | jq 'del(.id, .short_id, .version, .schema_hash, .is_enabled, .created_at, .updated_at)' \
  > definition.json
```

A `422` carries every problem at once, each with a `code` and a JSON `pointer` into the
definition (`/nodes/2/config/evaluator`). Fix all of them in one pass and check again.
Common ones:

| `code` | Fix |
| --- | --- |
| `unknown_eval` | The eval id does not exist; draft again or pick one from `GET /evals` |
| `eval_output_differs` | Copy the eval's current `output` into the node's `config.output` |
| `eval_input_missing`, `eval_input_type_differs` | The eval judges an input field the trigger lacks or types differently; add or retype `input_schema.fields.<name>` to match the eval's `input_schema` |
| `eval_limit_exceeded` | The eval's output is over a limit some evaluator family sets (`GET /evals/limits`); use fewer labels or levels, or shorter labels |
| `unsupported_output_type` | Pick an evaluator that judges that output type (`GET /evals/evaluators`) |
| `unknown_insight` | The insight is missing or one of its agents is unreadable; drop the node or pick another |
| `unknown_template_field` | `{{ field }}` in the insight objective must be an input field or `trigger.summary` / `trigger.insight_objective` |
| `answer_unreachable`, `node_dead_end` | Every node needs a path from the trigger to the answer |

Saving needs `agents:write`; running needs `agents:execute`. Then run it (step 2) on
the sample the user gave, and show the result.

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
