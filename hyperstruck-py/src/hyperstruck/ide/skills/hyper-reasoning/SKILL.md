---
name: hyper-reasoning
description: >-
  Use Hyperstruck Core hosted reasoning for structured plans, milestones, and
  steps when local work needs deeper analysis. The platform applies memory,
  knowledge, and accumulated learnings so outcomes improve over time. Do not use
  for simple edits or lookups you can handle directly — poll until the
  reasoning session completes (including human-in-the-loop when required).
argument-hint: "[optional goal text]"
effort: high
allowed-tools:
  - Bash(curl *)
  - WebFetch
---

# Hyperstruck hosted reasoning

Use this skill when the current task needs **structured reasoning**: richer plans, milestones, trade-off analysis, or cross-domain thinking that benefits from Hyperstruck Core — where reasoning is **grounded, auditable**, and informed by **memory, knowledge, and learnings** so results get **more valuable over time**. The underlying service runs as a hosted workflow; what matters for you is **better planning and evidence-backed output**, not the transport details.

Do **not** invoke for straightforward edits, lookups, or tasks you can complete locally.

## How this skill fits the caller workflow

- **The skill is HTTP orchestration:** env -> `GET /agents` -> `POST /agents/{id}/goals` with **`goal`**, **`context`**, and any relevant **`sources`** / **`references`** -> poll **`GET /runs/{run_id}`** -> use **`metadata.result.output`** to inform the caller's next actions.
- **Choose enough reasoning depth:** `fast` is only for compact results that can be planned and executed in one or two steps. If the answer may need several synthesis steps, richer milestones, validation, reflection, or trade-off analysis, pick **`balanced`** or **`full`** so the engine has enough iterations to execute the plan and emit final `output`.
- **Compressed `context`:** put session facts, goal-relevant caller capabilities, tool findings, constraints, and success criteria here. Hosted reasoning has **no** access to Claude Code, Cursor, the repo, local subagents, MCP, or external integrations unless you summarize them in **`goal`** and **`context`**.
- **Local/tool evidence for learning:** if meaningful work already happened outside Hyperstruck (for example Claude or Cursor edits, MCP calls, shell output, browser testing, CI failures, review comments, or external tool results), compact those results into **`context`**. The hosted run can only reason over and learn from tool evidence that is included in the run context or produced by tools available to the hosted agent.
- **Agent-purpose context:** after choosing an agent, use its `name`, `core_config.description`, and `core_config.instructions` to infer what information it is meant to use. Include relevant local knowledge, candidate learnings from the caller's run, errors, decisions, constraints, domain facts, repo facts, and review outcomes that match that purpose. Do not include unrelated session noise just because it exists.
- **Tool-aware use:** the hosted reasoning result can mention relevant caller-side skills, subagents, tools, and integrations, but the reasoning service cannot run those capabilities itself.
- **Caller-usable result:** treat **`metadata.result.output`** as the only caller-facing result. Use it to decide the next local actions; do not expose raw run metadata to the user as a substitute for a missing final answer.

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

If `HYPER_API_KEY_SET=no` above, the block already tried both `./.env` and `~/.hyperstruck/.env`. If still missing, **stop and ask the user** to set `HYPER_API_KEY`.

---

## Step 1 — Resolve configuration

- **Base URL**: Use `HYPER_BASE_URL` from the environment block above, defaulting to `https://api.hyperstruck.com`.
- **API key**: Already resolved above. **Never echo it.**
- **Headers** for every HTTP request:
  ```
  Authorization: Bearer <API_KEY>
  Content-Type: application/json
  Accept: application/json
  ```
- **Paths and JSON shapes**: Follow [reference.md](reference.md). **Do not** fetch `GET {BASE_URL}/openapi.json` up front — the document is large and wastes context. Rely on `reference.md` unless you hit errors that suggest API drift (see **Error handling**).

---

## Step 2 — Choose the Hyperstruck profile for this task

The API exposes this as **agents**; each one is a configured reasoning profile (instructions, model, memory, knowledge, learnings, safety settings).

**This step’s first request is also your auth check** — do not issue a separate `GET /agents?limit=1` beforehand. One round trip is enough.

```
GET {BASE_URL}/agents?limit=50
```

On **401** or **403**, stop and tell the user to verify `HYPER_API_KEY` and `HYPER_BASE_URL` (same outcome as a dedicated key-validation call, without the extra request).

For each item, inspect `name`, `core_config.description`, `core_config.instructions`, and `status`. Only `active` profiles can accept a new goal.

**If no profile fits the current task → stop early.** Tell the user:
> "None of your Hyperstruck setups match this task. Configure one in your Hyperstruck dashboard, or I'll continue without hosted reasoning."

If one profile clearly matches, use it. If several match, list them briefly and ask the user to pick (or choose the best fit by description). Store the chosen `agent_id` for API calls. Keep the selected agent's apparent purpose in mind when building `context`: include information that helps that agent do its job, and omit unrelated facts.

---

## Step 3 — Build rich context (critical)

The user is already mid-session. A bare one-line goal is nearly useless. Assemble a **structured context block** before dispatching.

### Goal

If the user passed `$ARGUMENTS`, use that as the starting point. Otherwise, synthesize a clear, self-contained goal paragraph from the conversation so far.

Before dispatching, make sure the goal describes something the caller can **act on** with the reasoning result. Include:

- The desired outcome.
- Success criteria or acceptance criteria.
- The decision, plan, implementation order, or next action the caller needs from hosted reasoning.

If the actionable goal is unclear, **stop and ask the user for the goal** instead of sending a vague prompt.

### Context (passed as the `context` JSON field)

Build a markdown block with these sections:

1. **Task background** — What the user is working on: repo, branch, project, deployment targets, environment constraints.
2. **Selected agent purpose** — Briefly state which agent was chosen and what its name/description/instructions imply it should care about. Use this as the filter for the rest of the context.
3. **Work done so far** — Summarize files read/written, commands run, data fetched from integrations (MCP tools, web searches, DB queries, etc.). Include key **findings and data**, not just tool names — the hosted agent cannot call your local tools.
4. **Relevant knowledge and learnings** — Include local domain facts, repo facts, accepted patterns, prior caller-run insights, candidate learnings, known pitfalls, user preferences, and review feedback that are relevant to the selected agent's purpose. Distinguish proven facts from hypotheses.
5. **Relevant caller capabilities** — List only the skills, subagents, tools, MCP servers, CLIs, integrations, databases, browsers, test runners, deployment targets, and permissions that could realistically affect this goal. Do not include a full tool inventory. Also list relevant unavailable capabilities or permissions when they constrain the plan.
6. **Compacted external-run evidence** — When local execution happened before this hosted run, include concise evidence: tool name, inputs or parameters that matter, observed outputs or errors, files changed, tests run, CI/browser results, review feedback, retry/fix sequence, and final outcome. Omit secrets and noisy logs. This gives hosted reasoning enough evidence to extract approach, pitfall, prerequisite, and tool-usage learnings from work it did not execute directly.
7. **Result-use guidance** — Do not request a response schema, machine-readable structure, or any specific format. The API response is the response; interpret `metadata.result.output` as returned.
8. **Open questions** — What needs deeper analysis, trade-off evaluation, or planning that you cannot resolve locally.
9. **Constraints** — Deadlines, compliance, tech-stack limits, performance budgets, cost concerns.

> **Tip:** Paste summarized MCP/integration results, compacted local tool transcripts, relevant knowledge, and candidate learnings from Claude, Cursor, or other caller runs. The hosted reasoning runtime has no access to your local tools, Jira, Linear, Slack, databases, browser session, local filesystem, or subagents unless you pass their relevant results in `context`.

### Sources and references

Keep these distinct from general `context`:

- **`sources`** are source-of-truth text blocks and the only request text that the grounding gate admits as evidence. Use them for authoritative records, transcripts, specifications, or tool reads. Supplying one or more also activates the read-only faithfulness check. Each item accepts non-empty `text`, optional `id`, and optional `label`; omitted IDs become `source-<index>`, and all explicit and generated IDs must be unique.
- **`references`** are exemplar or calibration material shown to the model for tone, structure, style, or output conventions. Each item accepts `text` and optional `label`. References are never admitted as evidence.

Do not place factual evidence only in `references` or rely on `context` as grounding evidence; put evidence that must ground claims in `sources`. Do not present a style example as a source. Omit both arrays when no suitable material exists. The API accepts at most 25 items per array and 100,000 characters of non-empty `text` per item.

---

## Step 4 — Submit the goal for hosted reasoning

```
POST {BASE_URL}/agents/{agent_id}/goals
```

```json
{
  "goal": "<structured goal from step 3>",
  "context": "<full context block from step 3>",
  "sources": [
    {
      "id": "accepted-spec",
      "label": "Accepted specification",
      "text": "<authoritative source text>"
    }
  ],
  "references": [
    {
      "label": "Preferred response style",
      "text": "<example used only to calibrate tone or format>"
    }
  ],
  "metadata": {
    "source": "claude-code-skill",
    "task_summary": "<one-line description>"
  }
}
```

Optional fields:
- `session_id` — set only to continue a previous Hyperstruck session whose last run is **terminal** (completed/failed). Omit to auto-create.
- `worker_profile` — infrastructure sizing only: `"default"` unless you need `"large"`.
- `sources` — authoritative source-of-truth blocks that may ground claims; omit when none are available.
- `references` — exemplar/calibration blocks for tone, structure, or format; never treat them as evidence.

Tier guidance:
- `full` — maximal hosted reasoning depth.
- `balanced` — middle tier for most hosted reasoning tasks.
- `fast` — lower-latency path for narrow, caller-usable answers. It intentionally caps plan size; a fast run still needs enough iterations for planning, each generated step, and the final completion pass that emits `metadata.result.output`. If the hosted planner may create more than 1-2 steps, use `balanced` or `full`.

Reasoning profiles live on the agent (`reasoning_profile` = `full` / `balanced` / `fast`). `worker_profile` is not a reasoning profile.

Choose an agent whose configured `reasoning_profile` matches the task instead of trying to change reasoning behavior per run.

Parse the response for `run.id` and `run.session_id` (the API names this a “run”; it is the lifecycle handle for the reasoning job).

---

## Step 5 — Poll until the reasoning job is finished

```
GET {BASE_URL}/runs/{run_id}
```

### Polling strategy

- Poll every **10 s**. Do not poll more frequently unless you are debugging a transient API problem.
- **Stop after 10 min** and report last known status.

### On `completed`

Read `metadata.result.output`.

- If `output` is present, interpret it as returned, use it to inform the next local actions, and share the relevant conclusion, plan, or next steps with the user.
- If `output` is missing or `null`, do **not** show raw run metadata. Tell the user hosted reasoning completed without a caller-usable final answer, then ask whether to retry with a clearer goal, richer context, or a deeper reasoning profile.

### On `failed`

Report `error` and `metadata`. Ask whether to retry or proceed without.

### On `suspended` (HITL)

1. Read `metadata.result.suspension.id`.
2. Present the suspension context to the user.
3. Ask for a decision: `approve`, `reject`, `modify`, `skip`, `provide_input`, or `partial_approve`.
4. Send:

```
POST {BASE_URL}/runs/{run_id}/resume
```

```json
{
  "suspension_id": "<from suspension.id>",
  "decision_type": "<user choice>",
  "reason": "<optional>"
}
```

After resume, poll the **child run id** from the response.

> If the agent's `hitl_required_approvals` is greater than 1, the run stays suspended until that many **distinct** people have approved (the dispatcher is excluded, and any `reject` vetoes). Poll `output.approvals_recorded` to see progress. See `reference.md`.

> Do **not** dispatch a new goal on the same `session_id` while any run is non-terminal — the API returns **409**.

---

## Step 6 — Use the results

1. Optionally fetch persisted session messages: `GET {BASE_URL}/sessions/{session_id}/messages?limit=50`
2. Integrate plans and findings into the current task.
3. If you discovered reusable insights, invoke `/hyper-learning` so the learning layer can improve future reasoning. When the run or local caller evidence includes concrete entity/outcome examples, preserve them as learning `instances` instead of only storing a prose summary.

---

## When NOT to use this skill

- Simple file edits, renames, or lookups.
- You already have all the information you need.
- No Hyperstruck profile matches the task (step 2).
- The user explicitly says to skip hosted reasoning.

## Error handling

See [reference.md](reference.md) for full endpoint schemas and error codes. Summary:

- **Network errors**: retry twice with 5 s gap, then report and continue without.
- **401/403**: invalid key or insufficient scopes. Ask the user to check `HYPER_API_KEY`.
- **404**: stale agent or run ID. Re-list agents or confirm the run ID.
- **409**: session has a non-terminal run. Poll it first or omit `session_id`.
- **5xx**: retry once after 5 s; if still failing, report and continue.

### When to fetch `openapi.json` (troubleshooting only)

After a failed or confusing API call, if fixing IDs/payloads using [reference.md](reference.md) does not help, fetch once:

```
GET {BASE_URL}/openapi.json
```

Use it only to reconcile paths, methods, or fields — **do not** paste the whole spec into the user thread. Extract the minimum fragment needed, then continue. If `openapi.json` is unreachable, stay with `reference.md` and ask the user to confirm `HYPER_BASE_URL` and API version.
