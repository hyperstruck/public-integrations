"""The package version, in a leaf module so anything may import it.

``__init__`` imports the client, so the client cannot import the version back from
``__init__`` without a cycle. It lives here instead, and ``__init__`` re-exports it
as the public ``__version__``.
"""

from __future__ import annotations

# 0.5.0 is the first release that posts an exposure receipt, and the server's adoption
# gate reads exactly that boundary out of the User-Agent. Shipping the receipt code
# without moving this would leave every capable and incapable client reporting the same
# string, which is what made the gate read 100% safe on a fleet that could send nothing.
# 0.5.1 is the first release that parses the recalled-fact block a resolve now returns
# separately from the advice block. Additive only: it changes nothing about the receipt the
# 0.5.0 gate reads, and an older client against the new server simply never sees the facts.
# 0.5.2 is the first release that reports whether the recall it was handed ever reached
# the model. A turn that was never shown its recall owes no receipt, so without this the
# server can only read the missing receipt as a client defect. Moving the version is what
# lets a fleet still running 0.5.1 be told apart from one that can answer the question.
# 0.5.3 hardens the rendezvous key a turn's three hook processes share when the host
# supplies no session id of its own. No host the installer wires is in that state today,
# so this moves no production number; the version moves because the User-Agent is the only
# way a fleet is segmented, and a wheel that reports the version below it cannot be told
# apart from one without the change.
# 0.5.4 is the first release that names a read-only recall's close as its own decline
# reason rather than borrowing the recording path's. Nothing gates on this value, but the
# User-Agent is the only way a fleet is segmented, so a wheel that reports the version
# below it cannot be told apart from one that still sends the borrowed reason, which is
# exactly what the alert's shrinking loss line has to be read against.
# 0.5.5 changes four things a fleet must be able to tell apart, and they land together
# because one wheel is one shipped artefact and one version names it.
#   * A failed tool call is recognised as one. The main host reports a failure by returning
#     its result as a plain string rather than an object, so every structured check missed
#     it and real failures were recorded as successes; a command that merely wrote to stderr
#     was meanwhile recorded as a failure. Both directions at once meant the failure-recovery
#     signal, the one turn class always observed, fired on noise and missed every genuine
#     recovery. Every turn-outcome and failure-count series is read against this boundary.
#   * A failed step now carries the name it failed under, under the single field the server
#     derives a gate from. Every offered rule before this one carried no gate predicate at
#     all, so the gate-derivation rate is read against this boundary or against nothing.
#   * The prompt hook emits the project's previous resolve, so experience reaches the model
#     before it plans rather than after its first tool call. It is deliberately uncreditable
#     and reports itself as such, so a fleet below this version is the control group for
#     whether earlier placement moves the yield at all.
#   * A resolve from the IDE path sends a tool palette and a context window from a
#     registration store that also replaces the tool-name matching which decided what could
#     ever be learned from. The palette-populated ratio and the material-step rate for
#     server-contributed tools are only interpretable per version.
# 0.6.0 stops this client refusing a corpus the boundary accepts. Two local gates outlived
# the server rules they mirrored: a floor of two evidence items, and a requirement that the
# corpus declare contrast. Both refused before a request existed, so the discarded corpus is
# invisible to every server-side series, and a fleet below this version is exactly the
# population whose fact corpora never arrived. Measured against production, one contrast-free
# two-item corpus the old client skipped yields facts from both of its items once sent.
# It also carries `subject` and `declared_sensitivity` through for the first time, which are
# what decide whether those facts accumulate against one entity or scatter, so the
# corroboration rate on caller-declared corpora is only interpretable at or above this
# version. The minor bump is the behaviour change; nothing gates on the value, but the
# User-Agent is the only way a fleet is segmented.
# 0.6.1 withholds the gate operand on every path. The 0.5.5 note above says a failed step
# now carries the name it failed under, and that is no longer true of any host: both routes
# to an operand read an identifier off a line nobody has established the host or a language
# runtime wrote, and both returned an internal hostname, a username and an environment
# variable name for ordinary input. Nothing is emitted until a provenance tier licenses a
# path. The version moves because the User-Agent is the only way a fleet is segmented, and a
# 0.5.5 wheel that sends operands cannot otherwise be told apart from one that sends none:
# the gate-derivation rate goes to zero fleet-wide, and without this boundary the only
# record available says the client is still sending, so a deliberate withholding reads as a
# boundary defect.
# 0.6.2 is the first release that sends a gate operand again, and it is the boundary the
# 0.6.1 note above has to be read against: that note says nothing is emitted on any path,
# and from this version that is false. Two provenance tiers now license a read, a language
# runtime's traceback and a host's own protocol frame, and on the measured corpus 27.8% of
# the failures the client reaches derive an operand where 0.6.1 derived none. The
# gate-derivation rate is therefore only interpretable per version: without this boundary a
# fleet still on 0.6.1 and one on this wheel are byte-indistinguishable in the User-Agent,
# and the rate lifting off zero would read as a boundary change rather than a client one.
# 0.6.3 is the first release that records the editor process on the turn it starts, which
# is what lets the backstop sweep decline a dead session's unevidenced turn now instead of
# in two days. The version moves because the per-client breakdown is the only way to tell a
# fleet that can supply a pid from one that cannot, and the change is deliberately inert
# without it: a turn carrying no pid takes the old age gate.
# 0.7.0 names the run seat, which shipped without a version of its own and should not
# have. The host-neutral runtime arrived whole in core-platform #550: the run-scoped core
# and its ledger, the wrapped Anthropic and OpenAI clients, per-tool sensitivity
# declaration, the receipt located in the params as sent, the durable write queue and
# breaker, the explicit run handle, the Agent Framework context provider and the
# OpenTelemetry adapter. `__version__` stayed at 0.6.2 through all of it, and then moved
# to 0.6.3 for the editor pid. By the rule every note above states, that is backwards: a
# fleet that can attach at the model layer and one that cannot are byte-indistinguishable
# in the User-Agent, so every series that asks how the neutral seat behaves in production
# is being read across a boundary that was never drawn. The minor bump is the new
# attachment point; nothing gates on the value, and the receipt gate reads the declared
# capability rather than this number.
#
# It is also the number `@hyperstruck/core` takes for its first npm release, and that is
# deliberate rather than cosmetic. The two packages are one product in two languages and
# the same minor now means the same capability generation, which is the only version
# question a customer choosing between them actually has. Patch numbers stay per language,
# because a fix in one says nothing about the other.
# 0.7.1 publishes `stash_emitted` and `recall_no_injection_point`, which this client has
# set since 0.5.5 and could not send: `wire_value` degraded both to `recall_unclaimed`
# until the boundary's contract named them. Nothing in the code changes, which is exactly
# why the version has to. A wheel that reports 0.7.0 either degrades both to
# `recall_unclaimed` or does not, depending only on which vendored JSON file it shipped
# with, and the User-Agent is the only way a fleet is segmented. Measured on one machine
# before this: 17 of 22 runs emitted a warm stash and all 21 recall statuses read
# `recall_unclaimed`, so the series this change exists to create would otherwise be read
# across an undrawn boundary, with the old and new populations reporting the same string
# under the same version. Patch rather than minor: no attachment point moves and no
# capability is added, one diagnostic stops being collapsed into another.
#
# `no_goal` is deliberately NOT published here. The client has named it since 0.5.5 and
# still withholds it. Publishing it flips `_is_goalless_decline` on, which routes a
# goalless turn away from observe, and observe is the only leg that harvests the
# own-output lane, so a turn that composed an answer would lose the promise it spoke.
# That trade needs the goalless population measured first; the local records put it at
# 1 of 23, which is a floor rather than a size, because the hook deletes a turn once
# reported.

# long-comment: this file is a version log by design, and each entry states why the number
# moved. An entry trimmed to one sentence stops answering that.
# 0.8.0 publishes `render_brief`, and `@hyperstruck/core` publishes `renderBrief` at the same
# minor, because the two packages are one product and the same minor means the same capability
# generation. It turns a structured brief into the prose a person or a host model reads, and it
# is the first thing either package exports that produces text rather than moving it. Minor
# rather than patch: a name a customer can import is new, and a fleet that has it cannot be told
# apart in the User-Agent from one that does not unless this number moves.
# 0.9.0 removes `render_brief`, and `@hyperstruck/core` removes `renderBrief` at the same minor.
# The structured brief route became `POST /agents/{id}/answer`, which writes its own prose, so
# nothing returns the shape either renderer read.
# 0.9.0 also stops the IDE hook refusing a boolean or an integer inside a declared-sensitivity
# section. The boundary admits `attacker_reachable` only as a bool and citation offsets only as
# ints, so a wheel below this version can send neither: its corpora are never held untrusted
# and never cite a passage, and the citation rate on hook corpora is only readable at or above it.
# 0.10.0 publishes loop-level obligation closure, and `@hyperstruck/core` publishes it at the
# same minor, because the two packages are one product and the same minor means the same
# capability generation. `reinforce` and `decline` both accept `obligation_outcomes` and both
# return a `ReinforceResult` carrying the presence verdicts and a disposition per reported id;
# `decline` returned nothing at all before. Minor rather than patch: the port grew a parameter
# and two return types changed, so a client a customer wrote against 0.9.0 no longer
# structurally satisfies `LearningClient`, and a fleet that can report a closure cannot
# otherwise be told apart in the User-Agent from one that cannot.
# 0.11.0 adds the hosted answer: `HostedLearningClient.answer` asks a hosted agent a question at
# one level of detail, typed to that level, and `Answer.more` fetches the same answer at a higher
# level. `@hyperstruck/core` adds it at the same minor. Nothing existing changed shape.
# 0.12.0 follows the answer contract: a section whose step did not run is null, so the
# typed answer bodies admit null there, and `@hyperstruck/core` moves at the same minor.
# 0.13.0 tells a host how many of its agent's keys hold a changed value for a person to review:
# `observe` returns an `ObserveResult` (it returned nothing) and `ReinforceResult` carries
# `keys_awaiting_review`, and `@hyperstruck/core` moves at the same minor. A fleet on this version
# can show a host that its agent is serving an earlier value while a change waits.
# 0.13.1 reads who started a turn from the host's own record of the prompt, and sends a turn
# nobody started (a subagent's report, a task notification) as host text with no principal
# words. A fleet below it sends a subagent's report as the person's goal, so the share of
# learnings grounded in a report is only readable per version. No exported name changed.
# 0.13.2 keeps an instruction typed straight after a pasted subagent report as the person's
# words. A fleet on 0.13.1 sends it as host text, so the instruction is lost to learning there.
# 0.14.0 waits and asks again when the answer is refused: a 429 or 503 is retried after the wait
# `Retry-After` names, up to five times, and `answer` takes `max_retries`. `@hyperstruck/core`
# moves at the same minor and exports `HostedAnswerError`. A fleet below it fails a batch on the
# first refusal, so refusal rates per version are only comparable from here.
# 0.14.1 records a tool call that failed, which Claude Code and Cursor each report on a separate
# event this client was not registered for. Cursor shell calls are now recorded from its tool
# events, by call id. A fleet below it sends no failed command at all, so a count of failed
# steps is only readable per version. No exported name changed.
# 0.14.2 changes only the installer: an install that runs the hook through a person's own
# wrapper script is recognised, rewired through that script, and uninstalled. A fleet below it
# double-wires such a machine on re-install. No exported name changed.
# 0.15.0 tells a host whether its agent has ever reported a run's outcome: `ResolvedContext`
# carries `has_reported_outcomes`, None when the server is older or recall failed open, and
# `@hyperstruck/core` moves at the same minor. A host that never reinforces can never see a
# learning recommended, and from here it is told so.
# 0.16.0 sends every `answer` call under an `Idempotency-Key`, making one when the caller gives
# none, and waits out a 409 that carries `Retry-After` (the call's own key still being answered).
# `@hyperstruck/core` moves at the same minor. A fleet below it can be charged twice for one call.
# 0.17.0 asks a question as a plain read: `answer(agent_id=, question=, as_of=, since=, detail=)`
# returns the Answer object (text, claims, shape, as_of, more) and takes no `idempotency_key` or
# `max_retries`, because nothing is stored or billed. `Answer.more`, the stored-answer fetch and the
# level bodies are gone, and `@hyperstruck/core` moves at the same minor. A fleet below it calls a
# route that no longer exists.
# 0.17.0 also reads resolve's two blocks, advice and claims, with the claims as Claim items; what
# the agent owes arrives as claims in that block, so the obligation block and its ids are gone.
# 0.18.0 removes the Obligations surface: `ObligationClosureResult` and `ReportedObligationOutcome`
# are gone from `hyperstruck`, and `CLOSURE_APPLIED`, `CLOSURE_BUSY`, `ObligationClosureResult` and
# `ReportedObligationOutcome` from `@hyperstruck/core`, which moves at the same minor. A fleet
# below it can still import them and report an obligation's closure.
# 0.19.0 names the claims read a search: `answer` becomes `search_claims`, posting to
# `/agents/{id}/claims/search`, and `Answer` and its literals become `ClaimSearch` and
# `ClaimSearchDetail`, `ClaimSearchShape`, `ClaimSearchState` and `ClaimSearchKind`.
# `@hyperstruck/core` moves at the same minor. A fleet below it calls a route that no longer exists.
# 0.20.0 renames `CompiledIngestSpec.distill_goal` to `collection_note` and removes `mode`, which nothing read:
# a watch's spec now names the note that steers which pages the crawl follows first. `@hyperstruck/core` moves at
# the same minor. A client below it fails to read a watch's spec.
# 0.21.0 makes the channel compulsory on a record: an evidence item always sends the `channel`
# it came through, and a corpus parked by an older client replays as `unknown`. The IDE hook
# states the host (`claude_code` or `cursor`) for an item that names none. `@hyperstruck/core`
# moves at the same minor. A fleet below it sends no channel, and a server that requires one
# refuses its distills, which the client drops without telling the person.
__version__ = "0.21.0"
