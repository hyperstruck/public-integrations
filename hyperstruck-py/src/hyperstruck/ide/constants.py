"""Shared constants for the IDE learning adapter.

Values only, no logic (see :mod:`hyperstruck.ide.config` for behaviour).
Centralised so the hook, installer, state, and gating modules cannot drift on a
path, a window, or a marker.
"""

from __future__ import annotations

import os
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

ACTIVE_FILE = "active.json"
PENDING_FILE = "pending.json"
RECALL_FILE = "recall.json"
# The detached resolver's own verdict on whether it published a stash, so a turn that
# was never shown its recall can say why instead of looking like a lost receipt.
RECALL_STATUS_FILE = "recall-status.json"
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

# -- diagnostics -------------------------------------------------------------

# When set to a truthy value, each hook writes one status breadcrumb to stderr on
# exit. Off by default so the loop stays silent and fails open; on, it lets a user
# tell "hook never fired" apart from "fired but no agent / empty resolve / network
# down", which otherwise all produce identical empty output.
HOOK_DEBUG_ENV = "HYPER_HOOK_DEBUG"

# Values of HOOK_DEBUG_ENV that count as "off" (anything else enables debug).
HOOK_DEBUG_OFF_VALUES = frozenset({"", "0", "false", "no", "off"})

# -- provenance --------------------------------------------------------------

SOURCE_CLAUDE_CODE = "claude-code"
SOURCE_CURSOR = "cursor"
SOURCE_OPENHANDS = "openhands"

# -- timing / gating ---------------------------------------------------------

# A pending turn left longer than this without a next prompt is flushed on its
# provisional label. Chosen to sit well under the server's offer-log retention
# (~7 days) so a deferred reinforce still finds its offer log.
EVICTION_WINDOW_SECONDS = 48 * 60 * 60

# A staged flush file older than this is presumed orphaned (its detached process
# died before delivering) and is re-spawned by the sweep. Younger files are left
# to their in-flight flush, so a freshly-staged episode is not double-spawned.
FLUSH_STALE_SECONDS = 5 * 60

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


def dropped_flush_log() -> Path:
    return hyper_home() / DROPPED_FLUSH_LOG


# A floor under HYPER_RESOLVE_TIMEOUT: an override below this cannot clear a real
# hosted resolve, so honouring it would silently turn recall off.
MIN_RECALL_TIMEOUT = 5.0

# A turn is only observed if it has at least this many material steps. This also
# subsumes the rapid-tiny-turn debounce: a trivial burst cannot clear it.
MIN_MATERIAL_STEPS = 2

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
STEP_KIND_OTHER = "other"

# A material step changed something or executed something.
MATERIAL_KINDS = frozenset({STEP_KIND_EDIT, STEP_KIND_COMMAND})

# -- step / turn status ------------------------------------------------------

# The wire status of a step or a turn (matches the server StepModel literals).
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Statuses a host may put on a single tool result that mean that call failed. This
# is a per-step signal, not a verdict on the turn: a turn's terminal status is read
# against the vocabulary its own host declares (see host_vocabularies). Membership
# here decides failure and non-membership decides nothing, because a step's outcome
# is corroborated by an exit code, stderr and an error field alongside it.
STEP_FAILURE_STATUSES = frozenset({"aborted", "error", "cancelled", "failed"})
