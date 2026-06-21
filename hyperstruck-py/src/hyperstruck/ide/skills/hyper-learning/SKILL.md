---
name: hyper-learning
description: >-
  Recall relevant Hyperstruck learnings for the current coding task before acting,
  so prior experience informs the work. Capture and reinforcement happen
  automatically through the learning hooks; this skill is the recall entry point
  (and on Cursor, the way learnings get injected, since hooks cannot inject there).
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

This skill is the **recall** entry point. On Claude Code recall is automatic (a
`UserPromptSubmit` hook injects learnings), so you rarely invoke this directly. On
**Cursor**, hooks cannot inject context, so this skill is how recall happens:
invoke it at the start of a task to pull in relevant learnings.

## Recall learnings for the current task

Run the loop's resolve step for the current goal and apply what it returns:

```!
python3 -m hyperstruck.ide.hook prompt --source cursor --emit text --goal "$ARGUMENTS"
```

- If `$ARGUMENTS` is empty, pass a one-line summary of the current task as the
  goal instead.
- The command prints a block of relevant learnings (or nothing, on a cold corpus
  or if no agent is configured). **Treat the printed text as guidance and apply
  it** to your plan before editing.
- It is fail-open: any error prints nothing and you simply proceed without recall.
- It also records the run so the automatic capture at turn end can credit the
  learnings it offered. You do not need to do anything further; capture and
  reinforcement are handled by the hooks.

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
