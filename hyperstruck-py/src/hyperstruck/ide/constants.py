"""Shared constants for the IDE learning adapter.

Values only, no logic (see :mod:`hyperstruck.ide.config` for behaviour).
Centralised so the hook, installer, state, and gating modules cannot drift on a
path, a window, or a marker.
"""

from __future__ import annotations

# Re-exported from the neutral gate so the two hosts cannot come to disagree about what
# counts as a finished step or how many material ones a turn needs.
from hyperstruck import turn_gate as _turn_gate

import os
from collections.abc import Sequence
from pathlib import Path

# -- filesystem layout -------------------------------------------------------

# Root for all loop state on a machine. Overridable so tests (and exotic homes)
# can redirect every path with one env var.
HYPER_HOME_ENV = "HYPER_HOME"


# Where a detached child's stderr is appended when it dies before the fail-open
# contract in ``main`` can record anything. Kept beside the loop state it explains.
HOOK_FAILURES_LOG = "hook-failures.log"

# One traceback per hook event accrues forever on a machine stuck in the broken
# state, so the trail is rotated once rather than allowed to grow without bound.
HOOK_FAILURES_LOG_MAX_BYTES = 1_000_000


def hyper_home() -> Path:
    """The root directory for loop state (``~/.hyperstruck`` by default)."""
    override = os.environ.get(HYPER_HOME_ENV)
    return Path(override).expanduser() if override else Path.home() / ".hyperstruck"


def sessions_dir() -> Path:
    return hyper_home() / "sessions"


def env_file() -> Path:
    return hyper_home() / ".env"


# Durable venv that holds the IDE hook runtime. Hooks must not use a project
# ``.venv`` interpreter: ``uv sync`` / recreates drop undeclared packages and
# silently break hooks. Overridable for tests.
IDE_VENV_ENV = "HYPER_IDE_VENV"


def ide_venv_dir() -> Path:
    """Directory of the durable IDE venv (``~/.hyperstruck/venv`` by default)."""
    override = os.environ.get(IDE_VENV_ENV)
    return Path(override).expanduser() if override else hyper_home() / "venv"


# Per-session subpaths, relative to ``sessions_dir() / <session_id>``.
# The rendezvous key a turn's hooks share when the host names no session of its own.
# Prefixed so a derived key stays distinguishable from a host-supplied id on sight.
DERIVED_KEY_PREFIX = "derived-"
DERIVED_KEY_DIGEST_CHARS = 12

# The warm stash lives here, beside the sessions rather than inside one. It has to
# outlive the turn that produced it, and every per-session path is cleared at both the
# start and the end of a turn.
STASH_SUBDIR = "stash"

ACTIVE_FILE = "active.json"
PENDING_FILE = "pending.json"
RECALL_FILE = "recall.json"
# The detached resolver's own verdict on whether it published a stash, so a turn that
# was never shown its recall can say why instead of looking like a lost receipt.
RECALL_STATUS_FILE = "recall-status.json"
# Written by the hook that can show a turn's recall, the first time it fires. A file rather
# than a field on the active turn: tool hooks are parallel processes with no lock, so a
# read-modify-write from one can clobber another's injection record between read and write.
INJECTION_POINT_FILE = "injection-point"
# Written by whichever parallel tool hook first observes a checkpoint's threshold, so
# exactly one of them spawns that checkpoint's resolve. A file for the same reason as the
# marker above: tool hooks race, and a read-modify-write of active.json loses a writer.
CHECKPOINT_CLAIM_FILE = "checkpoint"
# One file per block a run has already put in front of the model, named after that block's
# own digest and holding the ids it offered. A file, and created exclusively, because it is
# what makes "never the same advice twice" true rather than likely: the test and the record
# are a single atomic act, so two parallel hooks holding two different stashes cannot both
# read "not shown yet" and both show it. A field on the active turn could do neither half
# safely, since each hook reads it before the other has written.
SHOWN_BLOCK_FILE = "shown-block"
STEPS_SUBDIR = "steps"  # under active/, one append-only file per tool call
ACTIVE_SUBDIR = "active"
FLUSHING_SUBDIR = "flushing"  # handed-off episodes a detached flush is delivering

# -- identity ----------------------------------------------------------------

# Boundary loop: human-readable agent name (``upsert_learning_agent`` key).
# ``HYPER_LEARNING_AGENT_NAME`` wins over ``HYPER_AGENT_NAME`` for backward compat
# with the old ``HYPER_LEARNING_AGENT_ID`` name-only pin.
AGENT_NAME_ENV_VARS = ("HYPER_LEARNING_AGENT_NAME", "HYPER_AGENT_NAME")

# REST skills: hosted agent UUID for ``/agents/{agent_id}/...`` paths.
AGENT_ID_ENV_VARS = ("HYPER_AGENT_ID",)

# Optional home-space UUID that narrows ``GET /agents`` when a tenant has more
# agents than one list page. Skills and install read the same key.
SPACE_ID_ENV_VARS = ("HYPER_SPACE_ID",)

# -- provenance --------------------------------------------------------------

SOURCE_CLAUDE_CODE = "claude-code"
SOURCE_CURSOR = "cursor"
SOURCE_OPENHANDS = "openhands"

# -- timing / gating ---------------------------------------------------------

# A pending turn left longer than this without a next prompt is flushed on its
# provisional label. Chosen to sit well under the server's offer-log retention
# (~7 days) so a deferred reinforce still finds its offer log.
EVICTION_WINDOW_SECONDS = 48 * 60 * 60

# How old an orphan must be before its recorded editor process is consulted at all.
# A floor, never a threshold: being wrong about it only delays a decline, never causes
# one. It guards the case where the pid recorded at turn start is a short-lived shell
# wrapper rather than the editor, which would otherwise read as dead almost immediately.
LIVENESS_FLOOR_SECONDS = 30 * 60

# A staged flush file older than this is presumed orphaned (its detached process
# died before delivering) and is re-spawned by the sweep. Younger files are left
# to their in-flight flush, so a freshly-staged episode is not double-spawned.
FLUSH_STALE_SECONDS = 5 * 60

# Far above git's millisecond cost, so this fires only on a hang.
GIT_LOCATOR_TIMEOUT_SECONDS = 10

# Failed staged flushes are retried by later sweeps. This caps how many terminal
# (4xx) rejections a permanently-invalid payload gets before it is dropped, so one
# bad episode cannot reappear forever. Transient outages do not count against it.
DEFAULT_FLUSH_MAX_ATTEMPTS = 3
FLUSH_MAX_ATTEMPTS_ENV = "HYPER_FLUSH_MAX_ATTEMPTS"
FLUSH_ATTEMPT_SUFFIX = ".attempts"

# Dropping a flush is the one place a learning is lost for good, and the detached
# flush process has no reachable stderr, so each drop is appended (one JSON line)
# to this log under the loop root for an operator to inspect.
DROPPED_FLUSH_LOG = "dropped.jsonl"

# Every checkpoint appends one JSON line here, on every ending it can have: the tool-set
# drift behind it and whether the block it resolved actually differed from one already shown.
# Both halves, because either alone answers nothing, and the second is free since the digest
# comparison computes it anyway.
#
# On EVERY ending is the load-bearing part, and it is why the turn's own stop hook writes the
# line for a checkpoint that published and was never claimed. Line count is the only thing on
# this machine that says how many checkpoints a turn actually spent, and CHECKPOINT_MATERIAL_STEPS
# is the only thing bounding that spend, so a count missing its most common ending cannot
# answer whether the bound held.
#
# A local debugging aid and nothing more. Nothing collects this file and no transport off
# the machine exists: the boundary publishes no field the pair could travel on, and a
# client that sends an unpublished one costs the run its whole episode. It is here so that
# someone asking why a long turn did or did not show a second block can read the answer on
# the machine where the question came up.
CHECKPOINT_DRIFT_LOG = "checkpoint-drift.jsonl"

# Endings only a checkpoint can have, and deliberately not members of ``RecallOutcome``.
# That vocabulary answers a turn-level question and travels on the wire against a closed
# enum the boundary publishes; these two never leave the machine, so putting them in it
# would grow a published contract for a local diagnostic. They are kept apart from
# ``RECALL_UNCLAIMED`` for the reason that value was split once already: a stash that was
# published and shown to nobody is a different event from one that was never published, and
# reported under one name they read as a single drop rate.
CHECKPOINT_SLOT_OCCUPIED = "checkpoint_slot_occupied"
CHECKPOINT_SPAWN_FAILED = "checkpoint_spawn_failed"
# The turn ended between the tool hook spawning this checkpoint and the checkpoint starting.
# Nothing synchronises the two, so a threshold crossed on a turn's last tool call reaches a
# session the stop hook has already retired. No resolve was sent and nothing was charged, but
# the ordinal was spent, which is what the line is here to count.
CHECKPOINT_TURN_GONE = "checkpoint_turn_gone"


def dropped_flush_log() -> Path:
    return hyper_home() / DROPPED_FLUSH_LOG


def checkpoint_drift_log() -> Path:
    return hyper_home() / CHECKPOINT_DRIFT_LOG


# How long a project's warm stash stays useful. Working-set reasoning (Denning, 1968):
# what a session needs is defined by a recency window, not a static partition. Eight
# hours covers a session resumed after a meeting and excludes yesterday's context.
#
# TODO(ceiling): uncalibrated. The age rides on every emission, so the band that is
# actually useful is measurable from real data; revisit once there is a fortnight of it.
STASH_FRESHNESS_SECONDS = 8 * 60 * 60

# Where a host's declared tool set is stored, and how long a declaration is believed.
# Far longer than the stash's window because a tool set changes rarely, and it is
# refreshed on install and on upgrade. A tool that has been *removed* degrades safely,
# since unregistered already means material; a tool whose declaration *changed* is the
# residual risk, and this is what bounds it.
REGISTRATION_SUBDIR = "registrations"
REGISTRATION_TTL_SECONDS = 14 * 24 * 60 * 60

# The boundary caps a resolve's tool list, and an over-cap request is refused outright, so
# the whole recall is lost rather than the surplus tools. Mirrored from the boundary's own
# bound like the goal and episode ceilings above.
MAX_PALETTE_TOOLS = 200

# A registration is written from a local payload any shell-capable process can send, so its
# inputs are bounded here rather than trusted. A tool name longer than this is not a tool
# name, and a context window outside these is not a window.
MAX_REGISTERED_TOOL_NAME_CHARS = 128
MIN_MODEL_CONTEXT_WINDOW = 1_000
MAX_MODEL_CONTEXT_WINDOW = 100_000_000

# A floor under HYPER_RESOLVE_TIMEOUT: an override below this cannot clear a real
# hosted resolve, so honouring it would silently turn recall off.
MIN_RECALL_TIMEOUT = 5.0

# A turn is only observed if it has at least this many material steps. This also
# subsumes the rapid-tiny-turn debounce: a trivial burst cannot clear it.
MIN_MATERIAL_STEPS = _turn_gate.MIN_MATERIAL_STEPS

# Bound on a single tool result shipped to the platform. We never ship raw file
# contents or diffs; this caps even the summarised/echoed result string.
MAX_RESULT_CHARS = 2000

TRUNCATION_MARKER = " [TRUNCATED]"

# The boundary's own bounds, mirrored from api/models/learning_boundary.py, which
# stays authoritative. Exceeding one is not a soft failure: the request 422s, and
# for the goal that costs the turn its recall (ResolveRequest) and then its whole
# episode (EpisodeModel), silently on both counts. So values are clipped to fit
# rather than sent and lost. Not to be confused with the hosted-run goal bound in
# api/models/payload_bounds.py, which is a different limit for a different path.
MAX_BOUNDARY_GOAL_CHARS = 8000
MAX_EPISODE_STEPS = 500

# Deliberately ABOVE the boundary's own ceiling (CONTEXT_RECEIPT_MAX_CHARS, 200k), not
# below it. The server clips an over-cap body rather than refusing it, and treats what
# it had to clip as no account of what the model was NOT shown: it confirms only, and
# demotes nothing. Clipping first, under that ceiling, would hand the server a truncated
# receipt that looks complete, and every rule that fell off the end would be recorded
# UNEXPOSED, which is terminal and unrepairable. So this cap only bounds the request
# body; the decision about truncated evidence stays with the side that can act on it.
MAX_RECEIPT_CHARS = 220_000
MAX_STEP_FIELD_CHARS = 200

# The boundary's own bound on the run's composed answer, mirrored so an over-long one is clipped
# here rather than rejected there: a 4xx is terminal to the flush retry, so it would cost the whole
# episode and not just this field. `api/pin_shared_bounds_test.py` holds this against the API's
# `MAX_FINAL_OUTPUT_CHARS` and Core's `MAX_OWN_OUTPUT_CHARS`, which is what stops the three drifting.
#
# Declared HERE, beside the other wire bounds, rather than in the transcript reader that happens to
# apply it. It is a fact about the boundary and it is read by the redaction pass as well, and having
# it live in `ide/final_output` meant redaction imported a file reader to learn a number.
MAX_FINAL_OUTPUT_CHARS = 32_000

# -- distil run ids ----------------------------------------------------------

# The server keys distil idempotency on the run id, so this prefix decides whether
# two distils are the same run. A run id is never scrubbed or rewritten: the secret
# scrubber keys on high entropy, which is what makes an identifier an identifier,
# so a suspect id is refused rather than transformed (see _distill_run_id_rejection).
DISTILL_RUN_ID_PREFIX = "distill:"
MINTED_RUN_ID_TOKEN = "ide-"
MINTED_RUN_ID_CHARS = 12

# How much of a refused run id's credential match is quoted back to the caller.
# Enough to identify the shape (ghp_, AKIA, xoxb, pass), never enough to be key
# material, so a refusal can say what it objected to without echoing the secret.
CREDENTIAL_HEAD_CHARS = 4

# -- step classification -----------------------------------------------------

# What a tool call did, used by gating (material vs read-only) and outcome
# resolution (the execution oracle reads the trailing command/test result).
STEP_KIND_EDIT = "edit"  # changed code/files
STEP_KIND_COMMAND = "command"  # ran a shell command or test
STEP_KIND_READ = "read"  # read/search/lookup only
# Acted on something outside this machine's files: an API call, a browser, a message.
# Distinct from ``command`` on purpose. The execution oracle reads the trailing ``command``
# step as the turn's verdict, so folding a declared side-effectful tool in there would let
# an unrelated call decide whether the turn succeeded.
#
# It carries two situations that are worth keeping apart in the reading even though they are
# gated the same way: a tool *declared* side-effectful, and a tool nobody classified. Both
# are material, because nothing backstops over-exclusion; the second is also the signal that
# a registration is missing, which is otherwise invisible.
STEP_KIND_ACT = "act"

# A material step changed something or executed something.
MATERIAL_KINDS = frozenset({STEP_KIND_EDIT, STEP_KIND_COMMAND, STEP_KIND_ACT})

# Accumulated material steps at which a turn re-resolves its recall mid-flight, so a
# long turn is not still holding the block its opening goal earned. Front-loaded rather
# than evenly spaced: most drift happens once, so the second checkpoint is insurance for
# a turn that changed direction twice and is worth less than the first.
#
# The bound is on RESOLVES, not injections. A resolve has to happen before the digest
# test can say whether the block changed, so it is charged whether or not anything is
# re-injected, and resolve spend reserves against the run cap while that cap sums
# reserved rather than actual. Two is therefore the ceiling: worst case three resolves
# against one today. The server's own MAX_RESOLVE_KEYS_PER_RUN is structural rather than
# cost-aware and will not intervene.
#
# TODO(ceiling): a step count is the weak baseline and is known to be. Fixed-interval
# retrieval loses to need-triggered retrieval (FLARE, Self-RAG, IRCoT), and a PostToolUse
# subprocess sees neither token probabilities nor a model-emitted retrieval token. The two
# arguments above are the whole case for these numbers; nothing else is holding them up.
# Replacing the interval with a threshold on the recorded tool-set drift would need
# readings from many machines, which would need a boundary field to carry them that does
# not exist and has not been specced. Revisit if that field is ever built.
CHECKPOINT_MATERIAL_STEPS = (8, 24)

# Material steps on EACH side of the drift comparison. Fixed, and the same on every
# checkpoint, because a measure whose window grows with the checkpoint index does not mean
# the same thing at 8 as it does at 24 and the two cannot go in one sample. Derived from
# the first interval rather than chosen separately: it is the largest window that fits
# inside every gap between resolves, so no comparison reaches back past the resolve before
# the one it is measuring against.
CHECKPOINT_DRIFT_WINDOW = CHECKPOINT_MATERIAL_STEPS[0]

# How many distinct work locations a checkpoint's query may carry beside the opening goal.
#
# A checkpoint that re-sent the opening goal unchanged would ask the same question of the
# same corpus and get the same block back, which the digest test then suppresses: the
# feature would be two billed resolves and nothing else. So the query is rewritten against
# what the turn has since done, which is the established shape for a follow-up question
# that has to stand on its own (Yu et al., few-shot generative conversational query
# rewriting, SIGIR 2020).
#
# Bounded because the established failure of that rewrite is topic drift: a query that is
# neither the old task nor the new one retrieves worse than either would alone. Paths are
# high-entropy tokens and enough of them stop expanding the goal and start replacing it, so
# the anchor keeps the majority of the query. Eight is the drift window's worth of work:
# every term comes from a step inside it, and no term can come from before the resolve this
# checkpoint is measured against.
CHECKPOINT_GOAL_TERMS = 8

# Introduces the expansion so the reader (a retrieval model, then a language model) can see
# where the opening prompt ends and the recent work begins.
CHECKPOINT_GOAL_PREFIX = "Recent work in this turn: "

# Characters of MAX_BOUNDARY_GOAL_CHARS held for the expansion, so the ANCHOR is what gets
# clipped when the two together will not fit.
#
# Appending the expansion and clipping the whole is the wrong way round, and silently: an
# opening prompt already at the bound loses every character of the expansion, so the
# checkpoint re-sends a truncated copy of the goal it was supposed to move away from, which
# is the inert case this whole mechanism exists to cure. Just under the bound is no better,
# because the clip lands mid-path and the query carries half a filename.
#
# A thousand holds the eight terms comfortably at any realistic path length while leaving
# seven eighths of the bound to the anchor, so an ordinary prompt is never touched at all.
CHECKPOINT_GOAL_RESERVED_CHARS = 1000

# -- step / turn status ------------------------------------------------------

# The wire status of a step or a turn (matches the server StepModel literals).
STATUS_COMPLETED = _turn_gate.STATUS_COMPLETED
# The runtime declined to carry the act out. Only a refusal when paired with
# ``is_refused`` and no error; on its own it means the step simply did not run.
STATUS_SKIPPED = "skipped"
STATUS_FAILED = _turn_gate.STATUS_FAILED

# Statuses a host may put on a single tool result that mean that call failed. This
# is a per-step signal, not a verdict on the turn: a turn's terminal status is read
# against the vocabulary its own host declares (see host_vocabularies). Membership
# here decides failure and non-membership decides nothing, because a step's outcome
# is corroborated by an exit code, stderr and an error field alongside it.
STEP_FAILURE_STATUSES = frozenset({"aborted", "error", "cancelled", "failed"})


# The hosted boundary's distil bounds, restated because this client ships separately and
# cannot import ``api.models.learning_boundary``. A restatement that drifts is worse than a
# duplicate: these are checked before the request leaves the machine, so a floor of two here
# refused one-item corpora the platform admits, for months, while every published description
# said otherwise. api/openapi_contract_test.py pins these against the server's own values.
DISTILL_MIN_EVIDENCE = 1
DISTILL_MAX_EVIDENCE = 200
DISTILL_MAX_ITEM_CHARS = 240000
DISTILL_MAX_TOTAL_CHARS = 240000


def distill_cut_point(contents: Sequence[str], limit: int) -> int:
    """The last index whose running trimmed total is within ``limit``, in the caller's order.

    ``-1`` when even the first item is over. A copy of the server's ``cut_point`` in
    ``api/models/learning_boundary.py``, restated for the same reason as the numbers above,
    and pinned against it by ``api/openapi_contract_test.py`` on shared fixtures so a caller
    sees the same index whichever side refuses.
    """
    running = 0
    last_fitting = -1
    for index, content in enumerate(contents):
        running += len(content.strip())
        if running > limit:
            break
        last_fitting = index
    return last_fitting
