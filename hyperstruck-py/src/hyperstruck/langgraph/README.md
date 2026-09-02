# The LangGraph surface

Of every host this client supports, LangGraph has the best placement available to it.
It is not reading an editor's hooks or racing a prompt that has already been sent: it
sits inside the agent loop and can put experience in front of the model as a system
message, before the model call, on every call of the run. What it does with that
position is the whole of this module.

## Contents

- [Why placement is the interesting part](#why-placement-is-the-interesting-part)
- [Two blocks, not one](#two-blocks-not-one)
- [The ledger is a join, not a log](#the-ledger-is-a-join-not-a-log)
- [Why this host earns no credit](#why-this-host-earns-no-credit)
- [What this surface inherits rather than enforces](#what-this-surface-inherits-rather-than-enforces)
- [Telling silence apart](#telling-silence-apart)

## Why placement is the interesting part

Experience that arrives after the model has decided is a record, not an input. The
value of a surface is therefore mostly a question of where in the turn it can inject,
and how reliably.

```
   abefore_agent          awrap_model_call            aafter_model / tools
        |                        |                            |
   start the run           inject, then call             join what happened
   prefetch resolve        the model                     back onto the plan
        |                        |                            |
        +---- resolve runs concurrently ----+                 |
                                                              v
                                                      invoke end: observe
```

The resolve is *prefetched* when the run starts and awaited at the first model call, so
the network round trip overlaps the work the graph was doing anyway rather than sitting
in front of it. It is resolved once and reused on every later model call of the run, so
a multi-step loop keeps the experience in view without paying for it again.

## Two blocks, not one

The boundary returns experience in two halves. The **advice** half carries rules the
agent has learned. The **fact** half carries what it has already established about the
entities this run names, which is what makes a rule apply *here* rather than in
general.

They arrive separately on purpose: a host that knows its model treats a cached prompt
prefix differently from fresh context can place the stable advice half in the prefix and
the volatile fact half elsewhere. This surface makes no such claim about its model, so
it takes the documented default and places them adjacently in one system message.

What matters is that the default is a *placement choice* rather than a structural
limit. The halves and their two id sets are held apart on the run ledger, so changing
where each goes is a rendering change here and never another resolve.

A run offered facts and no applicable rule is still a run that was offered something.
Gating injection on the advice half alone would show such a run nothing at all, and
would then report it as a corpus with nothing in it.

## The ledger is a join, not a log

A turn produces two streams that have to be matched: what the model *planned* (tool
calls on an `AIMessage`) and what actually *happened* (tool outcomes, arriving later
and possibly out of order). The ledger keys both by tool-call id and joins them at
invoke end.

Only calls present in both streams become steps in the episode. A call the model
planned and the graph never ran is not evidence about anything, and recording it as a
step would teach the corpus from an obligation rather than an outcome.

State lives in a module-level registry keyed by run id, not on the middleware instance,
so one registered middleware can serve concurrent invokes without them seeing each
other's runs.

## Why this host earns no credit

Reinforcement needs evidence that the experience actually reached the model and was
used. The only artefact this host could return is the block it built itself, and
echoing that back asserts precisely the thing a receipt exists to prove: it would
report a rendered learning just as confidently for a run that a context-trimming
middleware downstream had quietly emptied.

So this surface sends no receipt, deliberately, and earns no reinforcement credit.
Unverified is the honest state for a host with no independent record. That is a
property of the framework rather than of this code, which is why the client declares
its host in the `User-Agent` (`hyperstruck-py/<version> (host=langgraph)`) rather than
relying on a version number alone.

Declaring the host identifies this surface; it does not make it receipt-capable. That
set is `claude-code` alone, because only there can a client read the editor's own
record of what was accepted. A LangGraph run is therefore distinguishable from an
unsupported host without ever being mistaken for one that owes a receipt.

## What this surface inherits rather than enforces

Two properties are worth stating plainly, because this surface relies on the boundary
for both rather than checking locally.

**The fact block is fenced upstream, not here.** Its content originates in tool outputs
and, via cross-tenant promotion, other agents' corpora, and the boundary renders it
inside a fence for exactly that reason. This middleware places the composed block into a
system message ahead of the operator's own prompt and applies no further check. That is
the same posture as the IDE seat, which delivers the identical composed string, so the
trust boundary is the boundary's fence in both cases.

**The fact half is sized server-side.** `max_injected_learnings` caps the advice half
only. How large the fact block may be is governed entirely by the boundary's own dossier
token budget, which a customer of this package cannot reach, and the composed block
rides every model call of a multi-step loop. A client-side lever for the fact half would
need the boundary to accept one.

## Telling silence apart

A run that shows the model nothing can mean several different things, and they license
opposite repairs. The surface reports which:

| Outcome | What happened | What it means |
|---------|---------------|---------------|
| `delivered` | The block reached a model call | Working |
| `resolve_failed` | Resolve raised | A fault: network, auth, server |
| `resolve_empty` | Resolve returned neither half | The corpus had nothing to offer |
| `recall_unclaimed` | A block was built and never injected | The run ended before a model call |
| `recall_missing` | The run ended with the prefetch in flight | Not a fault; the run was too short |

One state this table cannot yet name: the **fact lane being switched off server-side**.
The boundary hard-disables it when its fact-commitment secret is unset, and a run in
that deployment reports `resolve_empty` (or `delivered`, if rules rendered) exactly as a
deployment holding no facts would. The advice half has a taxonomy precisely to stop that
collapse; the fact half does not have one yet, and this is the honest statement of the
gap rather than a claim that it is covered.

Collapsing `resolve_failed` into `resolve_empty` is the failure this taxonomy exists to
prevent: it would make a broken deployment indistinguishable from a cold corpus, and
the cold corpus is the case an operator is right to ignore.
