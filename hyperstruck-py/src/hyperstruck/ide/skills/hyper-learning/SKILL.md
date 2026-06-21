---
name: hyper-learning
description: >-
  Explicitly recall relevant Hyperstruck learnings for a goal, so prior experience
  informs the work. Recall, capture, and reinforcement already run automatically
  through the learning hooks on both Claude Code and Cursor; use this only to force
  an extra, read-only recall for a specific goal.
argument-hint: "[optional goal text]"
allowed-tools:
  - Bash(python3 *)
  - Bash(python *)
  - WebFetch
---

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
python3 -m hyperstruck.ide.hook prompt --readonly --emit text --goal "$ARGUMENTS"
```

- If `$ARGUMENTS` is empty, pass a one-line summary of the goal you want recall for.
- The command prints a block of relevant learnings (or nothing, on a cold corpus
  or if no agent is configured). **Treat the printed text as guidance and apply
  it** to your plan before editing.
- `--readonly` means it only reads: it resolves and prints, without touching the
  current turn's automatic capture/reinforce, so it never disrupts the live loop.
- It is fail-open: any error prints nothing and you simply proceed without recall.

The agent the loop reads from and writes to is the one configured at install
(`HYPER_AGENT_ID`), or your single agent. For deeper, explicit reasoning that
selects the most appropriate agent for a task, use the `hyper-reasoning` skill.

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
