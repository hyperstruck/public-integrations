---
name: hyper-learning
description: >-
  Explicitly recall relevant Hyperstruck learnings for a goal, so prior experience
  informs the work, and distill durable learnings from a referenced corpus (a
  design document, MCP result, or tool output) that the automatic loop cannot see.
  Recall, capture, and reinforcement already run automatically through the learning
  hooks on both Claude Code and Cursor; use this to force an extra read-only recall
  for a specific goal, or to distill a referenced document into the configured
  agent's corpus.
argument-hint: "[optional goal text]"
allowed-tools:
  - Bash(python3 *)
  - Bash(python *)
  - WebFetch
---

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
`postToolUse` hooks. So you rarely need this skill. Use it only to deliberately
pull learnings for a *specific* goal (for example a different sub-task than the
prompt that started the turn).

## Recall learnings for a goal

Print the learnings relevant to a goal and apply them:

```!
PYTHONSAFEPATH=1 python3 -m hyperstruck.ide.hook prompt --readonly --emit text --goal "$ARGUMENTS"
```

- If `$ARGUMENTS` is empty, pass a one-line summary of the goal you want recall for.
- The command prints a block of relevant learnings (or nothing, on a cold corpus
  or if no agent is configured). **Treat the printed text as guidance and apply
  it** to your plan before editing.
- `--readonly` means it only reads: it resolves and prints, without touching the
  current turn's automatic capture/reinforce, so it never disrupts the live loop.
- It is fail-open: any error prints nothing and you simply proceed without recall.

The agent the loop reads from and writes to is the configured boundary agent
**name**, not UUID: `HYPER_LEARNING_AGENT_NAME` when set, otherwise
`HYPER_AGENT_NAME` (or your single agent when install auto-wires both name and
REST id). Config (`HYPER_API_KEY`, `HYPER_BASE_URL`, and the agent name vars) is
read from `~/.hyperstruck/.env`, so recall works identically from any worktree or
subdirectory. For deeper, explicit reasoning that selects the most appropriate
agent for a task, use the `hyper-reasoning` skill.

## Report what you recalled

Whenever you run this skill, **surface the result to the user** so it is clear the
loop shaped the work — do not silently fold it in:

- **What was found**: the learnings text the command printed (quote the key lines,
  not a vague "applied prior learnings").
- **From which agent**: the boundary agent name (`HYPER_LEARNING_AGENT_NAME` when
  set, otherwise `HYPER_AGENT_NAME`) the recall read from.
- **How it affected the run**: the concrete decisions you changed because of it
  (approach, ordering, a pitfall you avoided). If nothing was returned (cold
  corpus or no agent configured), say so in one line and proceed.

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
- Use distill for corpus text, **not** for a real agent run trace (that is the
  automatic observe loop) and **not** for a final learning you already have
  verbatim (that is the curation API in [reference.md](reference.md)).

## Manual curation

Curating the corpus by hand (adding a high-signal learning verbatim, fixing,
pruning, or promoting) is **not** part of this skill. That is the job of the
Hyperstruck dashboard, which is coming. In the interim, use the curation API
directly (see [reference.md](reference.md)); it stays live and supported, so no
capability is lost, only its home moves.

## What changed

Earlier versions of this skill called the manual learning endpoints to store,
search, and reinforce by hand. That is gone: the hosted resolve/observe/reinforce loop
(resolve / observe / reinforce) now runs automatically through the hooks, and
durable manual curation lives in the dashboard (curation API in the interim).
