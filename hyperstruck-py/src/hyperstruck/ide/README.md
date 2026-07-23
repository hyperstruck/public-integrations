# Hyperstruck IDE learning

Your coding assistant gets sharper the more you use it. Install once, and every
coding turn in Claude Code or Cursor silently recalls the lessons of past turns
before the assistant acts, and contributes new ones after, with no explicit
commands in the common case. The learning runs on the Hyperstruck platform; this
is the thin, fail-open client that wires it into your editor.

## Table of contents

- [Why](#why)
- [The turn loop](#the-turn-loop)
- [Install](#install)
- [What gets learned, and when](#what-gets-learned-and-when)
- [Outcome: scoring a turn on what happened next](#outcome-scoring-a-turn-on-what-happened-next)
- [Privacy](#privacy)
- [Identity](#identity)
- [Fail-open by design](#fail-open-by-design)
- [Diagnosing a quiet hook](#diagnosing-a-quiet-hook)

## Why

A coding assistant treats every task as a first attempt. It rediscovers the same
build quirk, the same flaky test, the same "this repo wants imports grouped that
way" correction, over and over. Hyperstruck closes the loop: what worked (and what
did not) on past turns is recalled the next time it is relevant, so the assistant
stops repeating itself.

The programmatic path to this is the LangGraph middleware. The IDE path delivers
the *same* learning loop without writing any code, by riding the editor's own
hooks.

## The turn loop

A **turn** is one user prompt and everything the assistant does until it stops and
hands back. It is the editor analogue of one agent invocation, and it maps onto a
platform episode: the goal is the prompt, the steps are the tool calls.

```
            one TURN  =  one run  =  one episode
  prompt ───────────►  assistant acts (edits, shell) ───────────► stop
     │                        │  │  │                               │
  detach resolve         first tool injects recall             finalise
  (read path)            + capture each outcome                (deferred)
```

Three editor hooks fire as three separate processes, so they share per-turn state
on disk:

| Moment | Claude Code | Cursor |
|--------|-------------|--------|
| recall (inject) | `UserPromptSubmit` spawns a detached resolve; the first `PostToolUse` injects it | `hyper-learning` starts resolve; the first `postToolUse` injects it |
| capture a step | the same `PostToolUse` hook | file-edit / shell hooks (capture only) |
| turn end | `Stop` hook | `stop` hook |

Both recall and the write side (observe + reinforce) are handed to detached
processes, so network work never delays the prompt you are waiting on.

## Install

The package is distributed from this repository, not PyPI:

```
pip install "hyperstruck @ git+https://github.com/hyperstruck/public-integrations.git#subdirectory=hyperstruck-py"
python -m hyperstruck.ide.install
```

Prefer `python -m hyperstruck.ide.install` after pip install so the installer runs
from the same package you just installed. The installer creates a durable venv at
`~/.hyperstruck/venv`, installs/upgrades `hyperstruck` into it, copies the
`hyper-*` skills into each editor, deep-merges the learning hooks into your editor
config *without touching your existing hooks*, and records auth. Hook commands
always use that durable interpreter (not a project `.venv`), so a later
`uv sync` / project venv recreate will not silently break hooks. It is idempotent:
re-running upgrades the durable venv and replaces Hyperstruck hook entries in
place. Restart your editor afterwards. Uninstall with
`python -m hyperstruck.ide.install --uninstall` (hooks and skills only; the
durable venv is left in place).

## What gets learned, and when

Not every turn is worth learning from, so capture is gated to the informative
ones: a turn that recovered from a failure (the highest-signal moment), or a turn
that materially changed code or ran a command. Pure reading, searching, and chat
are skipped. The platform critic is the final precision backstop.

## Outcome: scoring a turn on what happened next

Whether a turn *succeeded* is the crux of learning, and it is a delayed-feedback
problem: the truest signal arrives on the **next** turn. Coding turns fail
transiently on the way to a fix, so a turn is scored on its final state, not on
any failure en route, and resolved one turn later when the evidence is in:

```
  turn N ends ──► provisional label (did its tests/commands pass?)
                        │
  turn N+1 acts ──► did N+1 rework the SAME files N touched?
                        │           (the strong, language-agnostic signal)
                        ▼
               final label, written once
```

The decisive signal is **behavioural**: if the next turn re-edits the files the
prior turn just changed, the prior turn did not land, even if its tests passed
(the classic false-green). The wording of the next prompt is only a weak
corroborator. When the evidence is weak or conflicting, the provisional label
stands, because abstaining beats a confident-wrong flip. Each turn's learning is
therefore written exactly once, with no need to retract a label later.

## Privacy

Redaction happens on your machine, before anything leaves it.

- **No raw file contents or diffs are shipped.** A step carries the tool name, the
  path, the status, the error, and a clipped result. Learnings are about patterns,
  not literal code.
- **Secrets are scrubbed**: known credential shapes and high-entropy tokens are
  removed from every string that does ship.

Your source never leaves; only scrubbed, pattern-level learnings do.

## Identity

The agent a turn reads from and writes to is *your configured boundary agent
name* (`HYPER_AGENT_NAME`), never anything derived from the repo, because editors
are general agent platforms, not just code tools. If you have one agent, install
writes both `HYPER_AGENT_NAME` and `HYPER_AGENT_ID` (REST UUID) automatically. If
you have several, pick a name with `--agent-name` at install; REST skills still
use `HYPER_AGENT_ID` or `GET /agents`.

## Fail-open by design

The loop is strictly additive. A missing API key, a network error, a malformed
config, a timeout: every one degrades to a silent no-op. The learning loop can
never block or slow your editing.

## Diagnosing a quiet hook

The flip side of failing open is that a hook producing no output is ambiguous: it
could have never fired, fired with no agent configured, resolved zero learnings,
or hit a network error. In a cloud or remote agent (for example a Cursor
background agent) the hooks do not run at all, because they are local processes
wired into your editor and reading local config; only a local editing session
fires them.

To tell these apart, set `HYPER_HOOK_DEBUG=1`. Each hook then writes one status
breadcrumb to stderr on exit (which command fired, whether an agent was
configured, and whether the detached resolver was spawned). The resolver itself
also records success, failure, and stale-result breadcrumbs when run directly,
while stdout stays clean for injection payloads. Debugging is off by default, so
normal runs stay silent; the values `0`,
`false`, `no`, and `off` also count as off.
