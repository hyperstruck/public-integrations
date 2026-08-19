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
- [Distilling a referenced corpus](#distilling-a-referenced-corpus)
- [Outcome: what a turn can show for itself](#outcome-what-a-turn-can-show-for-itself)
- [Proving the model was shown it](#proving-the-model-was-shown-it)
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
  detach resolve         first tool injects recall          label + deliver
  (read path)            + capture each outcome              (detached write)
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
pip install --upgrade "hyperstruck @ git+https://github.com/hyperstruck/public-integrations.git#subdirectory=hyperstruck-py"
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

This installer does **not** wire Claude CoWork. CoWork never owns the live hook
loop — zip and upload the portable skill instead (see the
[repository README](../../../../README.md#claude-cowork)).

Wired commands also keep your project directory off the interpreter's import path.
Without that, a file in your repo named after a standard library module (a
`types.py`, a `json.py`) shadows the real one, the interpreter cannot start, and
every hook event fired from that directory is lost with no sign that anything went
wrong. Detached work is insulated the same way, by running from the loop's own
state directory rather than yours. This is why the package requires Python 3.11 or
later: the interpreter flag that provides the isolation does not exist before it,
and wiring a command an older interpreter refuses to start is worse than the
problem it solves.

## What gets learned, and when

Not every turn is worth learning from, so capture is gated to the informative
ones: a turn that recovered from a failure (the highest-signal moment), or a turn
that materially changed code or ran a command. Pure reading, searching, and chat
are skipped. The platform critic is the final precision backstop.

Because the loop captures tool *names, paths, and commands* only — never file
bodies, diffs, or tool results (see [Privacy](#privacy)) — it deliberately does
**not** learn from the contents of a referenced document, an MCP result, or a tool
call's output. That corpus is often exactly where reusable knowledge lives (a
design doc, a spec, a post-mortem). Distill closes that gap on demand.

## Distilling a referenced corpus

When a turn pulls in a corpus worth learning from, the `hyper-learning` skill can
distill it into the same boundary agent, out of band from the automatic loop:

```
echo '{"goal":"...","evidence":[{"id":"a","role":"contrast","status":"failed","content":"..."},
{"id":"b","role":"support","status":"completed","content":"..."}],"evaluation":"..."}' \
  | PYTHONSAFEPATH=1 python -m hyperstruck.ide.hook distill --emit text
```

It targets the configured boundary agent name (`HYPER_LEARNING_AGENT_NAME` when
set, otherwise `HYPER_AGENT_NAME`; never a repo-derived agent), namespaces the run
id with `distill:`, and secret-scrubs the caller-supplied *descriptive* strings
before they leave the machine (the identifiers are handled differently, see below).
Distillation needs **declared contrast** (a baseline vs a fix, or an
`evaluation` note); a corpus without that signal is skipped locally and would be
rejected by the server. A delivered corpus can still yield zero learnings if the
text contains no reusable contrast. Use it for corpus text only — a real run trace
is the automatic loop, and a final learning you already have verbatim belongs in
the curation API.

**Your `run_id` is never rewritten, only ever accepted or refused.** It is the
dedup key, so a distil is idempotent on it: if two distils arrive under one id,
all but the first do nothing. That makes silently altering an id the worst
available outcome, because every altered id collapses onto the same value and the
work is discarded while the client still reports success. So an accepted id is
preserved exactly, and one carrying a recognised credential shape is refused
outright with a reason rather than sanitised. Descriptive ids are safe to use and
are the point: pass something you can correlate with your own run.

One class of ordinary id is refused anyway, so it is worth knowing rather than
discovering: an id that reads as a credential *key* followed by a value, such as
`auth-token:refresh-flow-2026` or `api-key:rotation-runbook`. Nothing can tell that
from a real leaked key at a glance, so it fails loudly rather than quietly. Rename
it, or omit `run_id` and take a minted one.

**The same rule governs each evidence item's `id` and `source_ref`**, and for the
same reason: an `id` keys a step, and `source_ref` is the provenance a distilled
learning cites. Both mean what they *are*, so both are passed through exactly or
refused, never rewritten. Redaction maps many inputs onto one marker, and a
many-to-one map over a key manufactures collisions: two evidence items whose ids
were rewritten would arrive sharing one id, and a rewritten `source_ref` is a
citation pointing nowhere.

By contrast `content` and `label` mean what they *say*, so a redacted span still
reads as what it was. Those stay fully scrubbed, and are where a secret in your
corpus is handled.

**A credential in any identifier refuses the whole corpus, not just that item.**
That is deliberate. Dropping the offending item silently would change what is
learned, and can invert it: drop the only `failed` item and the remaining evidence
asserts the opposite of what you meant. The refusal names the exact field and
index, such as `evidence[3].source_ref`, so it is a one-line fix and a free retry.
Nothing was delivered and no run id was consumed.

Two mechanical details if you correlate by exact match: surrounding whitespace is
trimmed, and your id is namespaced under `distill:` unless it already carries that
prefix. So `my-run`, `  my-run  ` and `distill:my-run` are all stored as
`distill:my-run`, and are the same run as far as dedup is concerned. That is the
one way two ids you thought were distinct can still meet, so pick ids that differ
by more than whitespace or the prefix. Omit `run_id` entirely and a clean one is
minted for you, which is also the escape hatch if an id of yours is ever refused.

## Outcome: what a turn can show for itself

Whether a turn *succeeded* is the crux of learning, and the honest answer is
sometimes that nobody knows. Coding turns fail transiently on the way to a fix, so
a turn is scored on its final state rather than on any failure en route, and it is
scored from evidence the turn itself produced:

```
  turn ends ──► did its trailing test or command pass?      ──► success / failure
                     │ nothing ran
                     ▼
                did the host report a status it declares?   ──► success / failure
                     │ no status, or one it never declared
                     ▼
                unevidenced ──► the run is declined: closed, crediting nothing
```

There is no third rung. An absent signal is its own answer, not a reason to assume
the best. That matters because assuming the best is a *fabrication*, and the sole
purpose of the retired design was to retract fabrications one turn later, by asking
whether the next turn re-edited the same files. Remove the fabrication and there is
nothing left to retract, which is what lets a turn be written once, at its own stop.

Three consequences follow, and the first is the reason for the change:

- **A turn with no successor still closes its loop.** A headless one-shot run is
  always its own last turn, and so is the final turn of every interactive session.
  Waiting for a successor meant those never closed at all.
- **A status the host does not declare is not a pass.** Statuses are host protocol
  values, so each host declares which of its own mean success and which mean failure,
  and anything else abstains. Under the old shared failure list, membership decided
  failure and non-membership decided success, so a run killed by a CI `timeout` was
  credited for it.
- **Fewer turns are credited than before, deliberately.** Turns that used to pass on
  the assumption now decline instead, and the counts fall to what the evidence supports.

The trade taken knowingly: a turn whose tests pass but whose work is rejected keeps its
credit, because there is no longer a later turn to take it away. In an interactive
session the signal is re-attributed rather than lost, since the next turn is offered the
same learnings and its own outcome feeds their reinforcement. In a headless run there is
no principal to do the rejecting in the first place, so its exit code *is* the acceptance
criterion rather than a proxy for one.

## Proving the model was shown it

A learning earns credit only once something confirms the model was actually shown it.
Offering is not showing: an injected block can be refused by a hook, trimmed by a prompt
budget, or evicted by compaction, and from inside this client every one of those looks
identical to success.

The evidence has to be the *editor's* artefact, never this client's. Echoing back the
block we emitted would match every offered rule by construction and assert exactly the
thing the evidence exists to establish. That failure is not hypothetical: Cursor's prompt
hook cannot inject at all, so recall rides on a tool event, and a Cursor turn that calls
no tool resolves learnings and never shows them.

```
  block emitted ──stamped with this run's id──▶ editor decides
                                                     │
                          accepted ──▶ recorded in the transcript ──▶ receipt
                          denied   ──▶ nothing recorded            ──▶ no receipt
```

Under Claude Code the editor writes each accepted hook context into its transcript as its
own record, distinct from the record of what the hook printed. The stop hook reads back
the records carrying this run's marker, and that becomes the receipt. The marker leads the
block so a truncated tail still resolves to the right run, and the truncation then shows
up honestly as the missing rules being absent.

Under every other host nothing is sent, and those runs credit nothing. That is the safe
answer rather than a silent one: the platform logs each run that offered learnings and
heard nothing back, and names the client behind it, so a host that structurally cannot
report is distinguishable from one that should have and did not.

Two things follow that are easy to get backwards:

- **A turn that never injected sends no receipt at all**, rather than an empty one. It
  stamped no marker, so there is nothing in the transcript to find.
- **An oversized receipt is clipped ABOVE the boundary's own ceiling, not below it.** The
  server treats a receipt it had to clip as an incomplete account and demotes nothing. A
  client that clipped to fit under that ceiling would hand over a truncated receipt
  looking complete, and every rule past the cut would be recorded as never shown, which
  is permanent.

## Privacy

Redaction happens on your machine, before anything leaves it.

- **No raw file contents or diffs are shipped.** A step carries the tool name, the
  path, the status, the error, and a clipped result. Learnings are about patterns,
  not literal code.
- **Your prompt leaves this machine once, as its own turn's goal.** It used to leave
  twice, because a turn was held back until your next message arrived and that message
  was attached to it as the principal's own words. Turns are no longer held, so there is
  no moment at which a later message could honestly speak for an earlier turn, and
  nothing of the kind is sent. The platform still accepts such a message from callers
  that have a human-input channel to supply one; this client is not one of them.
- **Secrets are scrubbed from descriptive text**: known credential shapes and
  high-entropy tokens are removed from every descriptive string that ships, on both
  paths. The goal is scrubbed at capture, before recall ever sees it, and the
  episode is scrubbed again on its way to the write.
- **Identifiers are never scrubbed**, because replacing many of them with one
  marker makes them collide rather than degrade. What happens instead depends on
  whether the path is allowed to stop. Distil is something you invoke, so it
  **refuses** and tells you which field to fix. The automatic turn loop must never
  block your editing, so it cannot refuse: a step id that looks like a credential
  is **re-minted** to a fresh unique id instead. Both keep identifiers distinct;
  neither ever collapses them onto a shared value.
- **Oversized text is clipped to the boundary's bounds**, results at capture and
  the goal at both capture and after the scrub, because scrubbing can lengthen a
  string. A goal past the bound is rejected by *recall* as well as by the write, so
  an unclipped long prompt would cost the turn its learnings and then its episode,
  silently on both counts. An overlong turn is clipped to the boundary's step cap
  the same way, keeping the trailing steps that carry the outcome.
- **The exposure receipt is scrubbed like everything else.** It is a slice of your
  editor's transcript, and the platform matches it rather than storing it, which is a
  reason to keep it out of a column and never a reason to put a credential on the wire.

Your source never leaves; only scrubbed, pattern-level learnings do.

## Identity

The agent a turn reads from and writes to is *your configured boundary agent
name* (`HYPER_LEARNING_AGENT_NAME` when set, otherwise `HYPER_AGENT_NAME`), never
anything derived from the repo, because editors are general agent platforms, not
just code tools. If you have one agent, install writes both `HYPER_AGENT_NAME` and
`HYPER_AGENT_ID` (REST UUID) automatically. If you have several, pick a name with
`--agent-name` at install; REST skills still use `HYPER_AGENT_ID` or `GET /agents`.

## Fail-open by design

The loop is strictly additive. A missing API key, a network error, a malformed
config, a timeout: every one degrades to a silent no-op. The learning loop can
never block or slow your editing.

Detached write flushes are retried on later sweeps. A *terminal* rejection (a
4xx: the boundary refuses the payload as invalid) is what counts toward the cap,
so a permanently invalid local episode is dropped after three such rejections
rather than retrying forever. A *transient* failure (the boundary is down, a
network blip) does not count: it keeps retrying until the eviction window, so a
passing outage never discards a still-deliverable episode. Set
`HYPER_FLUSH_MAX_ATTEMPTS` to a positive integer to change the terminal-retry cap.

Recall has its own deadline, set by `HYPER_RESOLVE_TIMEOUT` (seconds). It governs
both the detached resolver and the explicit `/hyper-learning` recall, and it is
floored, because a budget too small to clear a real boundary round trip turns
recall off rather than tuning it: every call times out and fails open as though
the corpus were empty.

Because a dropped flush is the one place a learning is lost for good, and the
detached flush process has no reachable stderr, each drop is appended as one JSON
line to `~/.hyperstruck/dropped.jsonl` (run id, agent, attempts, and a cause tag,
never the prompt), so the loss leaves a trace.

When the boundary rejects a payload as invalid, the cause names the field it
refused: `HTTP 422 (body.episode.goal:string_too_long)`. Only the *location* and
*type* of each rejection are kept, never the server's message or the value it
rejected, because that value is the prompt or command this log must not hold. A
bare `HTTP 422` says a payload was discarded but not what was wrong with it, and
the payload is deleted along with it, so the drop would otherwise be impossible to
diagnose after the fact.

## Diagnosing a quiet hook

The flip side of failing open is that a hook producing no output is ambiguous: it
could have never fired, fired with no agent configured, resolved zero learnings,
overran its recall deadline, or hit a network error. A hook that died before it could report anything at all,
for instance because a file in your project shadowed a standard library module,
appends to `~/.hyperstruck/hook-failures.log` (rotated once past a megabyte), so
start there: an entry names the working directory the failure came from. In a cloud or remote agent (for example a Cursor
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
