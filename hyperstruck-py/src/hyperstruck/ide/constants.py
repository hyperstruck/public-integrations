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
ACTIVE_FILE = "active.json"
PENDING_FILE = "pending.json"
RECALL_FILE = "recall.json"
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


# Resolve is detached from the prompt hook, so it can afford to wait out the
# production boundary without adding latency to prompt submission.
DETACHED_RESOLVE_TIMEOUT = 20.0

# A turn is only observed if it has at least this many material steps. This also
# subsumes the rapid-tiny-turn debounce: a trivial burst cannot clear it.
MIN_MATERIAL_STEPS = 2

# Bound on a single tool result shipped to the platform. We never ship raw file
# contents or diffs; this caps even the summarised/echoed result string.
MAX_RESULT_CHARS = 2000

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

# Native terminal statuses an editor may report at stop that mean failure.
NATIVE_FAILURE_STATUSES = frozenset({"aborted", "error", "cancelled", "failed"})
