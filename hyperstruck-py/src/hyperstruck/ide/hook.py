"""The IDE learning hooks: the editor-driven analogue of the LangGraph middleware.

Where the middleware runs the resolve/observe/reinforce loop inside one
``ainvoke``, these hooks run it across three separate OS processes fired by the
editor, sharing per-turn state on disk (see :mod:`hyperstruck.ide.state`):

* ``prompt`` (Claude Code ``UserPromptSubmit``; the Cursor skill calls it too):
  flushes the previous turn now that this prompt is its ground truth, sweeps
  stale sessions, records the new active turn, and detaches its resolve.
* ``resolve`` (internal, detached): resolves the active goal into a recall stash.
* ``tool`` (``PostToolUse`` / Cursor tool hooks): appends one redacted step and,
  on the first eligible hook, atomically claims and injects the recall stash.
* ``stop`` (``Stop`` / Cursor ``stop``): finalises the turn with a provisional
  outcome and holds it as pending. No write to the platform yet.
* ``flush`` (internal, detached): delivers one turn's observe then reinforce.

Every command fails open: any error exits 0 with no output, so the learning loop
can never block or break the user's editing. The deferred write for turn N runs
at the *start* of turn N+1 (or at stale eviction), once the next prompt supplies
ground truth, and is handed to a detached ``flush`` process so it never delays the
prompt the user is waiting on.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import re

# Used only for fixed-argv detached processes; never a shell.
import subprocess  # nosec B404
import sys
import time
import uuid
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import Any

from hyperstruck._wire import (
    REASON_BELOW_MATERIAL_THRESHOLD,
    REASON_NO_TOOL_CALLS,
    EvidenceItem,
)
from hyperstruck.client import DEFAULT_RECALL_TIMEOUT, HostedLearningClient
from hyperstruck.env import RESOLVE_TIMEOUT_ENV, env_float
from hyperstruck.identity import AgentIdentity
from hyperstruck.ide import outcome, state
from hyperstruck.ide.config import configured_agent_name, load_env
from hyperstruck.ide.constants import (
    CREDENTIAL_HEAD_CHARS,
    DEFAULT_FLUSH_MAX_ATTEMPTS,
    DISTILL_RUN_ID_PREFIX,
    EVICTION_WINDOW_SECONDS,
    FLUSH_MAX_ATTEMPTS_ENV,
    FLUSH_STALE_SECONDS,
    HOOK_DEBUG_ENV,
    HOOK_DEBUG_OFF_VALUES,
    HOOK_FAILURES_LOG,
    HOOK_FAILURES_LOG_MAX_BYTES,
    MAX_EPISODE_STEPS,
    MAX_STEP_FIELD_CHARS,
    MIN_RECALL_TIMEOUT,
    MINTED_RUN_ID_CHARS,
    MINTED_RUN_ID_TOKEN,
    NATIVE_FAILURE_STATUSES,
    SOURCE_CLAUDE_CODE,
    SOURCE_CURSOR,
    STATUS_COMPLETED,
    STATUS_FAILED,
    hyper_home,
)
from hyperstruck.ide.gating import classify_tool, should_observe
from hyperstruck.ide.redaction import (
    clip_goal,
    clip_result,
    redact_ide_episode,
    scrub_secrets,
)
from hyperstruck.ide.state import ActiveTurn, PendingTurn
from hyperstruck.redaction import REDACTION_MARKER, known_credential_match

# Wire fields of a step (the rest of a stored step, e.g. ``kind``, is client-only).
_WIRE_STEP_FIELDS = ("id", "name", "args", "status", "result", "error")
_DISTILL_EMBEDDED_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])("
    r"sk-[A-Za-z0-9_\-]{16,}"
    r"|[sr]k_(?:live|test)_[A-Za-z0-9]{10,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r")"
)


# -- command: prompt (turn start) --------------------------------------------


def cmd_prompt(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Turn start: record and detach resolve; recover any interrupted turn."""
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    # Scrubbed here, not just in redact_ide_episode: this goal also goes to
    # resolve, which the episode redaction never touches.
    # --goal is honoured only for read-only recall. On the recording path the goal must come
    # from the host's prompt payload and nothing else, because it becomes the principal's
    # utterance on the previous turn, and a non-empty utterance is what authorises a rule that
    # is frozen against outcomes and rendered at the top of every future prompt. The installed
    # hooks already pass stdin, but this CLI is invocable by any agent with a shell, including
    # one under prompt injection, so the restriction has to live in the code rather than in
    # which argv the installer happens to write.
    raw_goal = (args.goal if args.readonly else payload.get("prompt")) or ""
    goal = clip_goal(scrub_secrets(raw_goal.strip()))
    agent_name = configured_agent_name()

    # Read-only recall (the hyper-learning skill): resolve and print for this goal,
    # without touching any turn state, so an explicit recall never disturbs the
    # automatic loop. A throwaway run id keeps the offer un-reinforced.
    if args.readonly:
        if agent_name:
            text, _ = _resolve(agent_name, _new_run_id(agent_name, session_id), goal)
            _emit_injection(text, args)
        else:
            _debug("prompt(readonly): no agent configured")
        return

    # 1. Orphan recovery: a turn interrupted before its stop hook fired never
    #    finalised. Treat it as a completed turn now (it really happened): it
    #    resolves the prior pending and becomes pending itself.
    orphan = state.read_active(session_id)
    if orphan is not None:
        _finalise(session_id, orphan, state.read_steps(session_id), native_status=None)
    # 2. Sweep stale sessions on their provisional label (backstop delivery).
    _sweep_stale(exclude=session_id)
    # 3. No configured agent means nothing to learn into: fail open, no injection.
    if not agent_name:
        _debug("prompt: no agent configured; loop idle, nothing to resolve")
        return
    # 4. Begin the new turn, then resolve outside the editor's prompt hook.
    run_id = _new_run_id(agent_name, session_id)
    state.write_active(
        session_id,
        ActiveTurn(
            run_id=run_id,
            agent_name=agent_name,
            goal=goal,
            source_framework=_source(args),
            started_at=time.time(),
        ),
    )
    _spawn_resolve(session_id)


# -- command: tool (capture a step) ------------------------------------------


def cmd_tool(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Append one redacted step. Lazily starts a turn if none is active.

    The lazy start keeps the write path robust on Cursor, where the resolve skill
    may not have run for this turn: steps are still captured and the turn can be
    observed at stop even without an injection.
    """
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    if args.inject:
        # Cursor postToolUse: atomically claim the detached recall, once per turn.
        # This hook does not capture a step (afterFileEdit/afterShellExecution do),
        # so injection and capture never double-count the same tool call.
        _inject_pending(session_id, SOURCE_CURSOR)
        return
    if state.read_active(session_id) is None:
        agent_name = configured_agent_name()
        if not agent_name:
            _debug("tool: no agent configured; step not captured")
            return  # no agent configured: nothing to capture into, fail open
        run_id = _new_run_id(agent_name, session_id)
        # reset_steps=False: a parallel tool hook may already have written a step
        # for this turn; resetting the steps dir would drop it.
        state.write_active(
            session_id,
            ActiveTurn(
                run_id=run_id,
                agent_name=agent_name,
                goal="",
                source_framework=_source(args),
                started_at=time.time(),
            ),
            reset_steps=False,
        )
    state.append_step(session_id, _step_from_payload(payload, args))
    if _source(args) == SOURCE_CLAUDE_CODE:
        _inject_pending(session_id, SOURCE_CLAUDE_CODE)


# -- command: stop (finalise provisional) ------------------------------------


def cmd_stop(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Turn end: resolve the prior turn with this turn's evidence, hold this one."""
    cwd = _cwd(payload, args)
    session_id = resolve_session_id(payload, cwd, args)
    active = state.read_active(session_id)
    if active is None:
        _debug("stop: no active turn for session; nothing to finalise")
        return
    steps = state.read_steps(session_id)
    native_status = args.native_status or payload.get("status")
    _finalise(session_id, active, steps, native_status=native_status)


# -- command: resolve (detached recall) --------------------------------------


def cmd_resolve(session_id: str) -> None:
    """Resolve one active turn into a tool-hook stash; fail open on every error."""
    try:
        load_env()
        active = state.read_active(session_id)
        if active is None:
            _debug("resolve: no active turn for session")
            return
        if not active.goal:
            _debug("resolve skipped: empty goal")
            return
        text, offered = asyncio.run(
            _aresolve(active.agent_name, active.run_id, active.goal)
        )
        if not text:
            # An empty stash can never validate for injection; publishing it
            # would only leave dead weight for the tool hooks to skip.
            _debug("resolve dropped: no learnings to inject")
            return
        current = state.read_active(session_id)
        if current is None or current.run_id != active.run_id:
            _debug("resolve dropped: active turn changed before recall was ready")
            return
        state.write_recall(
            session_id,
            {
                "run_id": active.run_id,
                "injected_text": text,
                "offered_learning_ids": list(offered),
            },
        )
        _debug(f"resolve ok: {len(offered)} learning(s) for agent {active.agent_name}")
    except Exception as exc:  # noqa: BLE001 - detached recall always fails open
        _debug(f"resolve failed ({type(exc).__name__}): {exc}")


# -- command: distill (caller-driven corpus extraction) ----------------------


def cmd_distill(payload: dict[str, Any], args: argparse.Namespace) -> None:
    """Distill durable learnings from a referenced corpus into the boundary agent.

    Unlike the automatic loop this is skill-driven: a referenced document, an MCP
    result, or a large tool output that carries reusable, *contrasting* knowledge
    (a design doc, a spec, a diff, a post-mortem) is handed in as a small JSON spec
    on stdin ``{goal, evidence: [{id, content, role, status, label?, source_ref?}],
    outcome?, evaluation?, run_id?}``. Identity is the configured boundary agent
    name (``HYPER_LEARNING_AGENT_NAME`` then ``HYPER_AGENT_NAME``) so a distilled
    learning lands in the same corpus the loop reads from; there is no
    repo-derived agent here.

    All caller-supplied strings are secret-scrubbed before they leave the machine
    because the server stores evidence verbatim as the grounding source. Contrast
    is required (differing ``status``, a ``contrast``/``support`` pair, or an
    ``evaluation`` note); a corpus without declared contrast is rejected locally.
    """
    parse_error = payload.get("_hyper_parse_error")
    if parse_error:
        _emit_distill_result({"status": "skipped", "reason": str(parse_error)}, args)
        return
    agent_name = configured_agent_name()
    if not agent_name:
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": (
                    "no agent configured (set HYPER_LEARNING_AGENT_NAME or "
                    "HYPER_AGENT_NAME)"
                ),
            },
            args,
        )
        return
    raw_goal = args.goal if args.goal is not None else payload.get("goal")
    goal = raw_goal.strip() if isinstance(raw_goal, str) else ""
    if not goal:
        _emit_distill_result(
            {"status": "skipped", "reason": "distill requires a non-empty goal"},
            args,
        )
        return
    evidence, complaints = _evidence_from_spec(payload.get("evidence"))
    if complaints:
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": (
                    "distill refused a corpus it could not use as given: "
                    + "; ".join(complaints)
                    + ". Nothing was sent, so fix these and retry on the same run id."
                ),
            },
            args,
        )
        return
    if len(evidence) < 2:
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": "distill needs at least 2 contrasting evidence items",
            },
            args,
        )
        return
    rejection = _distill_run_id_rejection(
        payload.get("run_id")
    ) or _evidence_credential_rejection(evidence)
    if rejection:
        _emit_distill_result({"status": "skipped", "reason": rejection}, args)
        return
    run_id = _distill_run_id(payload.get("run_id"))
    outcome_spec = (
        payload.get("outcome") if isinstance(payload.get("outcome"), dict) else {}
    )
    evaluation = payload.get("evaluation")
    scrubbed_evaluation = (
        _scrub_distill_string(evaluation.strip())
        if isinstance(evaluation, str) and evaluation.strip()
        else None
    )
    if not _has_distill_contrast(evidence, scrubbed_evaluation):
        _emit_distill_result(
            {
                "status": "skipped",
                "reason": (
                    "distill requires declared contrast (different statuses, "
                    "contrast/support roles, or evaluation)"
                ),
            },
            args,
        )
        return
    try:
        result = asyncio.run(
            _adistill(
                agent_name=agent_name,
                run_id=run_id,
                goal=_scrub_distill_string(goal),
                evidence=evidence,
                outcome_spec=outcome_spec,
                evaluation=scrubbed_evaluation,
            )
        )
    except Exception as exc:  # noqa: BLE001 - caller-driven, fail with a clear message
        _debug(f"distill failed ({type(exc).__name__}): {exc}")
        result = {
            "status": "error",
            "reason": f"{type(exc).__name__}: {exc}",
            "agent": agent_name,
            "run_id": run_id,
        }
    _emit_distill_result(result, args)


def _evidence_from_spec(raw: Any) -> tuple[list[EvidenceItem], list[str]]:
    """Build ``EvidenceItem``s from the skill's spec, plus what could not be used.

    Returns the complaints rather than swallowing them. A dropped item changes
    what is learned and a coerced ``status`` can invert it, since status is one of
    the three signals establishing contrast, so neither may pass silently: that is
    the same silent-discard failure this whole path was rewritten to end.
    """
    if not isinstance(raw, list):
        return [], ["evidence must be a list"]
    items: list[EvidenceItem] = []
    complaints: list[str] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            complaints.append(f"evidence[{index}] is not an object")
            continue
        content = entry.get("content")
        if not isinstance(content, str) or not content.strip():
            complaints.append(f"evidence[{index}] has no content")
            continue
        role = entry.get("role")
        status = entry.get("status")
        if role is not None and role not in ("support", "contrast", "neutral"):
            complaints.append(
                f"evidence[{index}].role {role!r} is not "
                "'support', 'contrast' or 'neutral'"
            )
        if status is not None and status not in ("completed", "failed"):
            complaints.append(
                f"evidence[{index}].status {status!r} is not 'completed' or 'failed'"
            )
        source_ref = entry.get("source_ref")
        items.append(
            EvidenceItem(
                # id and source_ref are identifiers and are never rewritten; they
                # are refused instead, by _evidence_credential_rejection.
                id=str(entry.get("id") or f"e{index + 1}"),
                content=_scrub_distill_string(content),
                label=_scrub_distill_string(str(entry.get("label") or "")),
                role=role if role in ("support", "contrast", "neutral") else "neutral",
                status=status if status in ("completed", "failed") else "completed",
                source_ref=str(source_ref) if source_ref else None,
            )
        )
    return items, complaints


def _scrub_distill_string(text: str) -> str:
    """Scrub distill corpus strings, including secrets embedded in labels/URLs."""
    return _DISTILL_EMBEDDED_SECRET_PATTERN.sub("[REDACTED]", scrub_secrets(text))


def _has_distill_contrast(evidence: list[Any], evaluation: str | None) -> bool:
    """Whether the corpus declares enough contrast for the server to accept it."""
    if evaluation:
        return True
    statuses = {item.status for item in evidence}
    if len(statuses) > 1:
        return True
    roles = {item.role for item in evidence}
    return {"contrast", "support"}.issubset(roles)


def _distill_run_id_rejection(provided: Any) -> str | None:
    """Why this run id cannot be accepted, or ``None`` when it is fine.

    A run id is an opaque identifier, never free text, so it is never rewritten.
    The secret scrubber keys on high entropy in a long token, which is precisely
    the property a descriptive identifier has by design, so it cannot separate a
    leaked credential from one: measured, ``sk-proj-AbCdEf0123456789AbCdEf0123456789AbCdEf``
    is 4.43 bits/char and ``pr-305-review-round-2-fixes-and-followups`` is 4.09,
    both over the 3.5 gate.
    Running it over identifiers is a category error, and the episode path already
    says so, scrubbing only goal and steps and "never identifiers" because a
    corrupted ``run_id`` silently breaks the server's dedup.

    Refusing is stronger than rewriting on every axis that matters. Nothing
    suspect egresses at all rather than egressing in derived form, the caller
    keeps an id they can correlate with their own run, and the failure is loud
    instead of silent.

    The judgement is ``known_credential_match``, not the full scrubber. Asking the
    scrubber "would you change this?" reinstates the entropy arm that this
    docstring rejects, one layer down: it refuses every descriptive id of 32+
    characters, which is the population the refusal exists to serve.
    """
    return _identifier_credential_rejection(
        provided,
        "run id",
        "Pass a run id carrying no secret, or omit run_id entirely and one will "
        "be minted for you.",
    )


def _identifier_credential_rejection(
    provided: Any, field: str, remedy: str
) -> str | None:
    """Why this identifier cannot be accepted, or ``None`` when it is fine.

    Shared by every field whose meaning *is* its value. Redaction replaces many
    inputs with one marker, and a many-to-one map over a key manufactures
    collisions, which is the whole of the 2026-07-24 incident rather than a
    property of that one field. So an identifier is judged and refused, never
    rewritten, and the caller keeps something they can correlate.
    """
    if not (isinstance(provided, str) and provided.strip()):
        return None
    match = known_credential_match(provided.strip())
    if match is None:
        return None
    return (
        f"{field} contains {_describe_credential_match(match)}, which reads as a "
        "credential, so it was refused rather than rewritten (rewriting an "
        f"identifier is many-to-one, so it would silently collide). {remedy}"
    )


def _evidence_credential_rejection(evidence: list[EvidenceItem]) -> str | None:
    """Why this corpus cannot be accepted, or ``None`` when it is fine.

    ``id`` and ``source_ref`` are identifiers, not prose: the first keys a step
    and the second is documented in the API as "non-secret provenance: a doc id or
    URL". Scrubbing them collapsed distinct ids onto one marker and shredded the
    citation a distilled learning rests on. ``label`` and ``content`` stay
    scrubbed, because a redacted span still reads as what it was.
    """
    for index, item in enumerate(evidence):
        for field, value in (
            (f"evidence[{index}].id", item.id),
            (f"evidence[{index}].source_ref", item.source_ref),
        ):
            reason = _identifier_credential_rejection(
                value, field, "Pass provenance carrying no secret."
            )
            if reason:
                return reason
    return None


def _describe_credential_match(match: str) -> str:
    """Name the offending run-id substring without echoing a real secret.

    Only the prefix is shown, which is the part that identifies the shape and
    carries no key material. Never widen this, and never add a branch that returns
    the match whole: the argument is the suspect text itself.
    """
    return f"'{match[:CREDENTIAL_HEAD_CHARS]}...' ({len(match)} characters)"


def _distill_run_id(provided: Any) -> str:
    """Namespace the caller's run id with ``distill:`` (minted if absent).

    Deliberately never scrubbed; see :func:`_distill_run_id_rejection`.
    """
    original = provided.strip() if isinstance(provided, str) else ""
    if not original:
        return f"{DISTILL_RUN_ID_PREFIX}{MINTED_RUN_ID_TOKEN}{uuid.uuid4().hex[:MINTED_RUN_ID_CHARS]}"
    return original if original.startswith(DISTILL_RUN_ID_PREFIX) else f"{DISTILL_RUN_ID_PREFIX}{original}"


def _distill_success(value: Any) -> bool:
    """Coerce an optional JSON success flag without treating "false" as truthy."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    return True


async def _adistill(
    *,
    agent_name: str,
    run_id: str,
    goal: str,
    evidence: list[Any],
    outcome_spec: dict[str, Any],
    evaluation: str | None,
) -> dict[str, Any]:
    """Ship one distill job and drain it; return a compact, printable result."""
    from hyperstruck._wire import DistillOutcome
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    try:
        client = HostedLearningClient()
    except ValueError:
        return {
            "status": "skipped",
            "reason": "no API key configured",
            "agent": agent_name,
        }
    summary = outcome_spec.get("summary")
    outcome_obj = DistillOutcome(
        is_success=_distill_success(outcome_spec.get("is_success", True)),
        summary=_scrub_distill_string(str(summary)) if summary else None,
    )
    closed = False
    try:
        await client.distill(
            identity=AgentIdentity(agent_name=agent_name),
            run_id=run_id,
            goal=goal,
            evidence=evidence,
            outcome=outcome_obj,
            evaluation=evaluation,
        )
        await client.drain()
        await client.aclose()
        closed = True
        if client.writes_duplicated:
            return {
                "status": "skipped",
                "reason": (
                    "this run id was already distilled, so nothing was extracted; "
                    "use a new run id to distil this corpus again"
                ),
                "agent": agent_name,
                "run_id": run_id,
            }
        if client.writes_delivered:
            return {
                "status": "delivered",
                "agent": agent_name,
                "run_id": run_id,
                "evidence_count": len(evidence),
            }
        if client.writes_failed:
            return {
                "status": "error",
                "reason": client.last_write_error or "delivery failed",
                "agent": agent_name,
                "run_id": run_id,
            }
        return {
            "status": "pending",
            "reason": "write still in flight after the drain timeout",
            "agent": agent_name,
            "run_id": run_id,
            "evidence_count": len(evidence),
        }
    finally:
        if not closed:
            await client.aclose(drain_timeout=0)


def _emit_distill_result(result: dict[str, Any], args: argparse.Namespace) -> None:
    """Print the distill result: human text for the skill, JSON otherwise."""
    if args.emit != "text":
        json.dump(result, sys.stdout)
        return
    if result.get("status") == "delivered":
        sys.stdout.write(
            f"Distill delivered for agent '{result['agent']}' "
            f"(run {result['run_id']}, {result['evidence_count']} evidence items). "
            "Extraction runs server-side and may still yield zero learnings if "
            "the accepted corpus has no real reusable contrast.\n"
        )
        return
    if result.get("status") == "pending":
        sys.stdout.write(
            f"Distill pending for agent '{result['agent']}' "
            f"(run {result['run_id']}): {result.get('reason', '')}.\n"
        )
        return
    sys.stdout.write(f"Distill {result.get('status')}: {result.get('reason', '')}\n")


# -- command: flush (detached delivery) --------------------------------------


class FlushOutcome(Enum):
    """What one delivery attempt established about a staged flush.

    DELIVERED and UNRECOVERABLE (malformed payload / no key) both mean drop now.
    TERMINAL (a 4xx: the payload is bad) counts toward the retry cap; TRANSIENT
    (5xx / network) is retried later without counting, so a passing outage never
    drops a still-deliverable episode.
    """

    DELIVERED = "delivered"
    UNRECOVERABLE = "unrecoverable"
    TERMINAL = "terminal"
    TRANSIENT = "transient"


def cmd_flush(args: argparse.Namespace) -> None:
    """Deliver one staged turn: observe (if gated in) then reinforce.

    The staged file is removed on success, on an unrecoverable payload, and once a
    *terminal* (4xx) rejection has recurred up to the retry cap. A *transient*
    failure (boundary down, network error) leaves the file in place so the next
    sweep retries it, bounded only by the eviction window: this keeps the staging
    dir a real outbox that never discards a still-deliverable episode over a blip.
    """
    payload = state.read_flush(args.flush_path)
    if not payload:
        state.remove_flush(args.flush_path)
        return
    try:
        outcome_, cause = asyncio.run(_deliver(payload))
    except Exception as exc:  # noqa: BLE001 - fail open; treat as transient and retry
        outcome_, cause = FlushOutcome.TRANSIENT, f"{type(exc).__name__}: {exc}"
    if outcome_ in (FlushOutcome.DELIVERED, FlushOutcome.UNRECOVERABLE):
        state.remove_flush(args.flush_path)
        return
    if outcome_ is FlushOutcome.TRANSIENT:
        return  # leave staged for a later sweep; eviction is the ultimate backstop
    attempts = state.record_flush_attempt(args.flush_path)
    if attempts is None:
        return  # another flush process delivered and removed the staged file
    if attempts >= _max_flush_attempts():
        state.record_dropped_flush(
            args.flush_path,
            run_id=_staged_run_id(payload),
            agent_name=payload.get("agent_name") or payload.get("agent_id", ""),
            attempts=attempts,
            cause=cause,
        )
        state.remove_flush(args.flush_path)


# -- turn finalisation / flush staging ---------------------------------------


# A stated standard is short. Measured over real sessions: 18 messages that actually state
# one run 30 to 368 characters, while the typed-prompt distribution has a median of 46 and a
# maximum near 20,000. The long tail is pasted logs, code and documents, which are the least
# likely to be a standard and the most expensive to ship a second time. This is a data
# minimisation bound, NOT a quality gate: irrelevant utterances were measured not to become
# norms, so nothing here is protecting precision. Drops are counted, never truncated: half a
# stated norm can mean the opposite of the whole one.
MAX_UTTERANCE_CHARS = 500


def _principal_utterance(goal: str, session_id: str) -> str:
    """The successor's message, when it can honestly be offered as the principal's own words.

    Returns "" rather than a best effort, because downstream a non-empty value is what
    authorises a rule that is frozen against outcomes, never decays, and renders at the top
    of every future prompt. Anything we cannot stand behind must be absent, not approximate.

    Suppressed when the session id is derived rather than supplied by the host: two
    conversations in one terminal and working directory collapse onto one session, so the
    turn this message belongs to is not established, and attributing it to the pending turn
    asserts an authority we do not have. That is the same confused-deputy reasoning the
    field-level guarantee rests on, applied one layer up. It lifts on its own once a host
    supplies real session ids.
    """
    if not goal or session_id.startswith("derived-"):
        return ""
    if REDACTION_MARKER in goal:
        # The scrub already fired on this message. A message carrying a credential is strong
        # evidence it is not a stated standard, and a placeholder frozen into a rule would
        # render at primacy forever. Reading our own marker, not guessing at content.
        return ""
    if len(goal) > MAX_UTTERANCE_CHARS:
        _count_dropped_utterance(len(goal))
        return ""
    return goal


def _count_dropped_utterance(length: int) -> None:
    """Record a message the bound refused, so a real standard lost to it is not invisible.

    The spec's own rule: no cap ships without logging what it drops.
    """
    _debug(
        f"utterance not attached: {length} chars exceeds the {MAX_UTTERANCE_CHARS} bound"
    )


def _finalise(
    session_id: str,
    current: ActiveTurn,
    current_steps: list[dict[str, Any]],
    *,
    native_status: str | None,
) -> None:
    """Resolve the prior turn using this turn's evidence, then hold this turn.

    The prior pending turn's outcome is decided here, now that this (its
    successor) turn's actions exist: rework against the prior turn's files marks it
    failed, otherwise its objective provisional label stands. This turn then
    becomes the pending turn, resolved when the *following* turn ends.
    """
    prior = state.read_pending(session_id)
    if prior is not None:
        final_is_success = outcome.resolve_prior_outcome(
            prior.is_success,
            reworked=outcome.reworked(prior.steps, current_steps),
        )
        # The objection is typed on this turn but is about the prior one, and this is the
        # only moment both are in scope: the prior turn is resolved here precisely because
        # its successor now exists. No buffering, no re-observe, no idempotency problem.
        prior = replace(
            prior,
            principal_utterance=_principal_utterance(current.goal, session_id),
        )
        _stage_and_flush(session_id, prior, final_is_success)
        state.clear_pending(session_id)
    state.write_pending(
        session_id,
        PendingTurn(
            run_id=current.run_id,
            agent_name=current.agent_name,
            goal=current.goal,
            steps=tuple(current_steps),
            is_success=outcome.provisional_outcome(current_steps, native_status),
            source_framework=current.source_framework,
            ended_at=time.time(),
            offered_learning_ids=current.offered_learning_ids,
            is_injected=current.is_injected,
        ),
    )


def _stage_and_flush(
    session_id: str, pending: PendingTurn, final_is_success: bool
) -> None:
    """Gate, stage the redacted episode with its final label, detach a flush."""
    if not pending.agent_name:
        return  # nothing to deliver to (turn captured before an agent was set)
    steps = list(pending.steps)
    do_observe = should_observe(steps)
    # An observed turn that offered nothing still closes its loop server-side, so
    # reinforce it too; skipping empty offers is what left those runs half-open. A
    # trivial turn (no material steps, no offer) still short-circuits below.
    do_reinforce = do_observe or bool(pending.offered_learning_ids)
    if not (do_observe or do_reinforce):
        # Not worth learning from, but the run it opened is still open server-side,
        # and going quiet made a deliberate skip look identical to a broken host.
        # Staged like any other write so it inherits retry and drop accounting.
        staged_decline = {
            "agent_name": pending.agent_name,
            "decline": {
                "run_id": pending.run_id,
                "reason": _decline_reason(steps),
                "is_delivered": pending.is_injected,
                "source_framework": pending.source_framework,
            },
        }
        _spawn_flush(state.stage_flush(session_id, pending.run_id, staged_decline))
        return
    episode = _build_episode(pending, final_is_success)
    staged = {
        "agent_name": pending.agent_name,
        "episode": redact_ide_episode(episode),
        "do_observe": do_observe,
        "do_reinforce": do_reinforce,
    }
    path = state.stage_flush(session_id, pending.run_id, staged)
    _spawn_flush(path)


def _staged_run_id(payload: dict[str, Any]) -> str:
    """The run a staged payload belongs to, whichever kind of write it carries.

    A dropped write is the one record that survives the loss, so it is worthless
    without the run id: an unattributable drop is exactly the silent hole a decline
    exists to close. Episodes and declines nest the id differently, so read both.
    """
    for block in ("episode", "decline"):
        nested = payload.get(block)
        if isinstance(nested, dict) and nested.get("run_id"):
            return str(nested["run_id"])
    return ""


def _decline_reason(steps: list[dict[str, Any]]) -> str:
    """Why this turn was not worth learning from, from the gate that decided it.

    Derived rather than invented, so the reported cause and the gate can never
    disagree. This is what makes the gate measurable: until now it fired silently,
    so how often it skipped a turn, and why, was invisible.

    The wire contract also carries ``empty_offer`` for callers whose recall returned
    nothing to apply. This host cannot reach it: an empty offer with material steps
    still observes, and one without them is already described by the step count.
    """
    return REASON_NO_TOOL_CALLS if not steps else REASON_BELOW_MATERIAL_THRESHOLD


def _build_episode(pending: PendingTurn, is_success: bool) -> dict[str, Any]:
    """Project stored steps onto the wire episode shape (drops client-only fields)."""
    # Keep the tail when a turn overruns the boundary's cap: the trailing steps
    # carry the outcome the producer reads. The counts stay over the full turn.
    wire_steps = [
        {field: step.get(field) for field in _WIRE_STEP_FIELDS}
        for step in pending.steps[-MAX_EPISODE_STEPS:]
    ]
    completed = sum(
        1 for step in pending.steps if step.get("status") == STATUS_COMPLETED
    )
    failed = sum(1 for step in pending.steps if step.get("status") == STATUS_FAILED)
    return {
        "run_id": pending.run_id,
        "goal": pending.goal,
        "steps": wire_steps,
        "outcome": {
            "is_success": is_success,
            "total_steps": len(pending.steps),
            "completed_steps": completed,
            "failed_steps": failed,
        },
        "source_framework": pending.source_framework,
        "principal_utterance": pending.principal_utterance or None,
        "thread_id": None,
    }


def _sweep_stale(*, exclude: str) -> None:
    """Flush turns left longer than the eviction window, on their provisional label.

    A session abandoned with no successor turn never gets behavioural ground
    truth, so its pending (and any interrupted active) is delivered on the
    provisional label rather than lost.
    """
    now = time.time()
    for session_id in state.all_session_ids():
        if session_id == exclude:
            continue
        pending = state.read_pending(session_id)
        if pending is not None and now - pending.ended_at > EVICTION_WINDOW_SECONDS:
            _stage_and_flush(session_id, pending, pending.is_success)
            state.clear_pending(session_id)
            state.clear_recall(session_id)
        orphan = state.read_active(session_id)
        if orphan is not None and now - orphan.started_at > EVICTION_WINDOW_SECONDS:
            _finalise(
                session_id, orphan, state.read_steps(session_id), native_status=None
            )
        elif orphan is None:
            state.clear_recall(session_id)
        _recover_flushes(session_id, now)
        state.remove_session_if_empty(session_id)


def _recover_flushes(session_id: str, now: float) -> None:
    """Re-deliver or evict flush files orphaned by a killed flush process.

    A detached flush removes its file on completion; one left behind means its
    process died (sleep, OOM, reboot) before delivering. Re-spawn a flush for it
    (at-least-once is safe, the platform dedups by run id), but evict files past
    the eviction window so a permanently-failing delivery cannot pin the session.
    """
    for path in state.iter_flush_files(session_id):
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age > EVICTION_WINDOW_SECONDS:
            state.remove_flush(path)  # never delivered in time; drop it
        elif age > FLUSH_STALE_SECONDS:
            _spawn_flush(path)  # presumed orphaned; retry. Younger files are in flight.


def _max_flush_attempts() -> int:
    """Configured outer flush attempts; the HTTP client still retries per attempt."""
    raw = os.environ.get(FLUSH_MAX_ATTEMPTS_ENV)
    if raw is None:
        return DEFAULT_FLUSH_MAX_ATTEMPTS
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_FLUSH_MAX_ATTEMPTS
    return max(1, parsed)


# -- network (resolve / deliver) ---------------------------------------------


def _recall_timeout() -> float:
    """Seconds a hook recall waits.

    Floored, because a zero or negative override reproduces the original defect:
    every recall times out and fails open as though the corpus were empty.
    """
    return max(MIN_RECALL_TIMEOUT, env_float(RESOLVE_TIMEOUT_ENV, DEFAULT_RECALL_TIMEOUT))


def _resolve(
    agent_name: str, run_id: str, goal: str
) -> tuple[str | None, tuple[str, ...]]:
    """Resolve the goal's learnings. Returns (injected_text, offered_ids); fails open."""
    if not goal:
        _debug("resolve skipped: empty goal")
        return None, ()
    try:
        text, offered = asyncio.run(_aresolve(agent_name, run_id, goal))
        _debug(f"resolve ok: {len(offered)} learning(s) for agent {agent_name}")
        return text, offered
    except TimeoutError:
        print(
            f"[hyperstruck] recall timed out after {_recall_timeout():g}s; "
            "proceeding without learnings",
            file=sys.stderr,
        )
        return None, ()
    except Exception as exc:  # noqa: BLE001 - explicit recall always fails open
        _debug(f"resolve failed ({type(exc).__name__}): {exc}")
        return None, ()


async def _aresolve(
    agent_name: str,
    run_id: str,
    goal: str,
    *,
    resolve_timeout: float | None = None,
) -> tuple[str | None, tuple[str, ...]]:
    client = HostedLearningClient(
        resolve_timeout=(
            _recall_timeout() if resolve_timeout is None else resolve_timeout
        )
    )
    try:
        context = await client.resolve(
            identity=AgentIdentity(agent_name=agent_name), run_id=run_id, goal=goal
        )
        return context.injected_text, tuple(context.offered_learning_ids)
    finally:
        await client.aclose()


async def _deliver_decline(
    agent_name: str, decline: dict[str, Any]
) -> tuple[FlushOutcome, str | None]:
    """Close a run the gate declined. Same outcome taxonomy as an episode write."""
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    run_id = decline.get("run_id")
    reason = decline.get("reason")
    if not run_id or not reason:
        return FlushOutcome.UNRECOVERABLE, "malformed staged decline"
    try:
        client = HostedLearningClient()
    except ValueError:
        return FlushOutcome.UNRECOVERABLE, "no API key configured"
    try:
        await client.decline(
            identity=AgentIdentity(agent_name=agent_name),
            run_id=run_id,
            reason=reason,
            is_delivered=bool(decline.get("is_delivered")),
            source_framework=decline.get("source_framework", SOURCE_CLAUDE_CODE),
        )
        await client.drain()
        if client.writes_failed == 0:
            return FlushOutcome.DELIVERED, None
        if client.writes_terminal_failed:
            return FlushOutcome.TERMINAL, client.last_write_error
        return FlushOutcome.TRANSIENT, client.last_write_error
    finally:
        await client.aclose()


async def _deliver(payload: dict[str, Any]) -> tuple[FlushOutcome, str | None]:
    """Observe (awaited to completion) then reinforce, so the wire order holds.

    Returns the outcome plus a coarse cause tag. A 4xx rejection is TERMINAL (the
    payload is bad, so it counts toward the retry cap); a 5xx/network failure is
    TRANSIENT (retry later, uncounted); a malformed payload or missing key is
    UNRECOVERABLE (drop now, retrying cannot help).
    """
    from hyperstruck._wire import Episode, StepRecord, TerminalOutcome
    from hyperstruck.client import HostedLearningClient
    from hyperstruck.identity import AgentIdentity

    agent_name = payload.get("agent_name") or payload.get("agent_id")
    decline_data = payload.get("decline")
    if agent_name and decline_data:
        return await _deliver_decline(agent_name, decline_data)
    episode_data = payload.get("episode") or {}
    if not agent_name or not episode_data:
        return FlushOutcome.UNRECOVERABLE, "malformed staged payload"
    identity = AgentIdentity(agent_name=agent_name)
    outcome_data = episode_data.get("outcome") or {}
    episode = Episode(
        run_id=episode_data.get("run_id", ""),
        goal=episode_data.get("goal", ""),
        steps=tuple(
            StepRecord(**_wire_step(step)) for step in episode_data.get("steps") or []
        ),
        outcome=TerminalOutcome(
            is_success=bool(outcome_data.get("is_success", True)),
            total_steps=int(outcome_data.get("total_steps", 0)),
            completed_steps=int(outcome_data.get("completed_steps", 0)),
            failed_steps=int(outcome_data.get("failed_steps", 0)),
        ),
        source_framework=episode_data.get("source_framework", SOURCE_CLAUDE_CODE),
        # Rebuilt field by field, so anything omitted here is staged, scrubbed, written to
        # disk and then silently dropped at the moment of delivery. That is how the utterance
        # came to be plumbed through five layers and never transmitted; thread_id had the same
        # omission already. Keep this list in step with _build_episode.
        principal_utterance=episode_data.get("principal_utterance"),
        thread_id=episode_data.get("thread_id"),
    )
    try:
        client = HostedLearningClient()
    except ValueError:
        return FlushOutcome.UNRECOVERABLE, "no API key configured"
    try:
        if payload.get("do_observe"):
            await client.observe(identity=identity, episode=episode)
            await client.drain()  # land observe before reinforce reads its offer log
        if payload.get("do_reinforce"):
            # IDE tool calls are undeclared, so an IDE turn never auto-promotes.
            await client.reinforce(
                identity=identity, episode=episode, is_org_promotion_allowed=False
            )
            await client.drain()
        # The client retries internally then drops with a counter rather than
        # raising. A terminal (4xx) failure means the payload is bad and will fail
        # every retry, so it counts toward the cap; a transient failure keeps the
        # staged file for the next sweep without counting.
        if client.writes_failed == 0:
            return FlushOutcome.DELIVERED, None
        if client.writes_terminal_failed:
            return FlushOutcome.TERMINAL, client.last_write_error
        return FlushOutcome.TRANSIENT, client.last_write_error
    finally:
        await client.aclose()


def _wire_step(step: dict[str, Any]) -> dict[str, Any]:
    """Keep only StepRecord's fields, with a non-empty id (StepRecord requires it)."""
    wire = {field: step.get(field) for field in _WIRE_STEP_FIELDS}
    if not wire.get("id"):
        wire["id"] = uuid.uuid4().hex
    if not wire.get("name"):
        wire["name"] = "tool"
    for field in ("id", "name"):
        wire[field] = str(wire[field])[:MAX_STEP_FIELD_CHARS]
    if wire.get("status") not in (STATUS_COMPLETED, STATUS_FAILED):
        wire["status"] = STATUS_COMPLETED
    if not isinstance(wire.get("args"), dict):
        wire["args"] = {}
    return wire


# -- step capture ------------------------------------------------------------


def _step_from_payload(
    payload: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Build a redacted, no-raw-content step from a tool-hook payload.

    Spans Claude Code (``tool_name``/``tool_input``/``tool_response``) and Cursor
    (``command``/``file_path``/``exit_code``) shapes. Only safe-to-ship inputs go
    in ``args`` (path, command); no file body, diff, or tool output is ever
    captured. The result is always dropped (it would be source); only the tool
    name, path/command, status, and a clipped, scrubbed error survive.
    """
    name = (
        args.name
        or payload.get("tool_name")
        or payload.get("tool")
        or payload.get("name")
        or "tool"
    )
    kind = args.kind or classify_tool(name)

    safe_args: dict[str, Any] = {}
    path = (
        payload.get("file_path")
        or payload.get("path")
        or (payload.get("tool_input") or {}).get("file_path")
    )
    if path:
        safe_args["path"] = scrub_secrets(str(path))
    command = payload.get("command") or (payload.get("tool_input") or {}).get("command")
    if command:
        safe_args["command"] = scrub_secrets(clip_result(command))

    is_error = _is_error(payload)
    # No tool result is ever shipped. A read or edit result is file contents or a
    # diff, and a command's stdout can be source too (git diff, grep, cat). The
    # only execution signal we need is pass/fail (the status); the failure detail
    # rides in `error`, clipped and scrubbed. So `result` is always dropped.
    raw_error = payload.get("error") or payload.get("stderr")
    response = payload.get("tool_response")
    if not raw_error and isinstance(response, dict):
        raw_error = response.get("stderr") or response.get("error")

    return {
        "id": payload.get("tool_call_id") or payload.get("id") or uuid.uuid4().hex,
        "name": str(name),
        "args": safe_args,
        "status": STATUS_FAILED if is_error else STATUS_COMPLETED,
        "result": None,
        "error": (
            scrub_secrets(clip_result(raw_error)) if (is_error and raw_error) else None
        ),
        "kind": kind,
    }


def _is_error(payload: dict[str, Any]) -> bool:
    """Whether a tool call failed, across Claude Code and Cursor payload shapes.

    Claude Code's ``Bash`` failures surface inside ``tool_response`` (stderr /
    interrupted / a nested exit code), not as a top-level field, so the nested
    dict is inspected as well as the top level.
    """
    if _failed_exit(payload.get("exit_code")):
        return True
    if payload.get("is_error") or payload.get("error") or payload.get("stderr"):
        return True
    if str(payload.get("status") or "").lower() in NATIVE_FAILURE_STATUSES:
        return True
    response = payload.get("tool_response")
    if isinstance(response, dict):
        if (
            response.get("error")
            or response.get("stderr")
            or response.get("interrupted")
        ):
            return True
        if _failed_exit(
            response.get("exit_code")
            or response.get("exitCode")
            or response.get("returnCode")
        ):
            return True
        if str(response.get("status") or "").lower() in NATIVE_FAILURE_STATUSES:
            return True
    return False


def _failed_exit(code: Any) -> bool:
    return isinstance(code, int) and code != 0


# -- process plumbing --------------------------------------------------------


def _debug(message: str) -> None:
    """Write one diagnostic breadcrumb to stderr when ``HYPER_HOOK_DEBUG`` is set.

    stderr, never stdout: stdout carries the injection JSON and must stay clean.
    Guarded so it can never raise and break the loop's fail-open contract.
    """
    if (os.environ.get(HOOK_DEBUG_ENV) or "").strip().lower() in HOOK_DEBUG_OFF_VALUES:
        return
    try:
        sys.stderr.write(f"[hyperstruck-hook] {message}\n")
        sys.stderr.flush()
    except (OSError, ValueError):
        pass


def _new_run_id(agent_name: str, session_id: str) -> str:
    """Mint a run id namespaced by agent and session; the uuid tail is the unique part."""
    return f"{agent_name}:{session_id}:{uuid.uuid4().hex}"


def _child_env() -> dict[str, str]:
    """Environment for a detached child, keeping the session's cwd off ``sys.path``.

    A child is a fresh interpreter, so the parent's ``-P`` does not reach it:
    ``sys.flags.safe_path`` is not inherited and ``PYTHONSAFEPATH`` is not set by
    the flag. Without this, a project file named after a stdlib module shadows the
    real one and the child cannot boot ``runpy``, so flush and resolve die in
    exactly the directories the wired flag protects the parent from. The variable
    is honoured from 3.11 and ignored before it, which ``-P`` is not, so it is
    safe on every interpreter this package supports.
    """
    return {**os.environ, "PYTHONSAFEPATH": "1"}


def _spawn_stderr(home: Path) -> Any:
    """Append handle for child stderr, so a child that dies leaves a trace.

    Discarding it is why this class of failure stayed invisible: the child died
    before reaching the fail-open contract in ``main``, so nothing anywhere
    recorded that it had run. Truncated past a bound, because a machine stuck in
    the broken state writes one traceback per hook event forever. Falls back to
    ``DEVNULL``: a diagnostic must never itself be the reason the loop breaks.
    """
    try:
        home.mkdir(parents=True, exist_ok=True)
        log = home / HOOK_FAILURES_LOG
        if log.exists() and log.stat().st_size > HOOK_FAILURES_LOG_MAX_BYTES:
            log.replace(log.with_suffix(log.suffix + ".1"))
        return log.open("ab")
    except OSError:
        return subprocess.DEVNULL


def _spawn_detached(*args: str) -> None:
    """Start a detached hook subprocess, insulated from the session's directory.

    ``cwd`` is the loop's own state directory rather than the editor's, so a
    project file named after a stdlib module cannot shadow it however the child
    interpreter resolves imports. ``PYTHONSAFEPATH`` says the same thing to 3.11
    and later; this says it to every version, which is what the 3.10 floor needs.
    Neither detached command reads the working directory: ``resolve`` is keyed by
    session id and ``flush`` by an absolute path.
    """
    home = hyper_home()
    stderr = _spawn_stderr(home)
    try:
        # Fixed argv from sys.executable, never a shell: not an injection surface.
        subprocess.Popen(  # nosec B603
            [sys.executable, "-m", "hyperstruck.ide.hook", *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            start_new_session=True,
            close_fds=True,
            env=_child_env(),
            cwd=str(home),
        )
    finally:
        if stderr is not subprocess.DEVNULL:
            with contextlib.suppress(OSError):
                stderr.close()


def _spawn_flush(path: str | os.PathLike[str]) -> None:
    """Spawn a detached flush process so delivery never delays the prompt."""
    try:
        _spawn_detached("flush", str(path))
    except (OSError, ValueError):
        pass


def _spawn_resolve(session_id: str) -> None:
    """Spawn a detached resolve process so recall never delays prompt submission."""
    try:
        _spawn_detached("resolve", session_id)
        _debug(f"resolve spawned: session {session_id}")
    except (OSError, ValueError) as exc:
        _debug(f"resolve spawn failed ({type(exc).__name__}): {exc}")


def _emit_injection(injected_text: str | None, args: argparse.Namespace) -> None:
    """Emit the resolved learnings for the editor to inject before the model acts."""
    if not injected_text:
        return
    if args.emit == "text":
        sys.stdout.write(injected_text)
        return
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": injected_text,
            }
        },
        sys.stdout,
    )


def _emit_tool_context(injected_text: str | None, source: str) -> bool:
    """Emit one tool-hook context payload, returning whether context was emitted."""
    if not injected_text:
        return False
    if source == SOURCE_CURSOR:
        json.dump({"additional_context": injected_text}, sys.stdout)
    else:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": injected_text,
                }
            },
            sys.stdout,
        )
    return True


def _inject_pending(session_id: str, source: str) -> None:
    """Emit detached recall exactly once, claiming it only after it validates."""
    try:
        recall = state.peek_recall(session_id)
        if recall is None or not recall.get("injected_text"):
            return
        active = state.read_active(session_id)
        if (
            active is None
            or active.is_injected
            or recall.get("run_id") != active.run_id
        ):
            return
        claimed = state.claim_recall(session_id)
        if claimed is None:
            return  # a parallel hook won the claim
        if not _emit_tool_context(claimed.get("injected_text"), source):
            return
        offered = tuple(str(item) for item in claimed.get("offered_learning_ids") or ())
        merged = tuple(dict.fromkeys((*active.offered_learning_ids, *offered)))
        state.write_active(
            session_id,
            replace(active, is_injected=True, offered_learning_ids=merged),
            reset_steps=False,
        )
    except Exception as exc:  # noqa: BLE001 - context injection always fails open
        _debug(f"inject failed ({type(exc).__name__}): {exc}")


def resolve_session_id(
    payload: dict[str, Any], cwd: str, args: argparse.Namespace
) -> str:
    """The editor's session id from argv or the hook payload, else a stable fallback.

    The fallback (terminal session leader + repo digest) is stable across the
    three hook processes of one turn when they share a terminal and repo, so they
    still rendezvous when the editor omits a session id.
    """
    explicit = args.session or _first(
        payload, ("session_id", "conversation_id", "sessionId", "threadId", "thread_id")
    )
    if explicit:
        return str(explicit)
    try:
        sid = os.getsid(0)
    except OSError:
        sid = 0
    digest = hashlib.sha1(
        cwd.encode("utf-8", "ignore"), usedforsecurity=False
    ).hexdigest()[:12]
    return f"derived-{sid}-{digest}"


def _source(args: argparse.Namespace) -> str:
    return args.source or SOURCE_CLAUDE_CODE


def _cwd(payload: dict[str, Any], args: argparse.Namespace) -> str:
    return args.cwd or payload.get("cwd") or os.getcwd()


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value:
            return value
    return None


def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return {"_hyper_parse_error": f"invalid JSON on stdin: {exc}"}
    return data if isinstance(data, dict) else {}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hyperstruck.ide.hook", add_help=False)
    parser.add_argument(
        "command", choices=["prompt", "tool", "stop", "resolve", "flush", "distill"]
    )
    parser.add_argument("flush_path", nargs="?", default=None)
    parser.add_argument(
        "--source", choices=[SOURCE_CLAUDE_CODE, SOURCE_CURSOR], default=None
    )
    parser.add_argument("--session", default=None)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--kind", default=None)
    parser.add_argument("--native-status", dest="native_status", default=None)
    parser.add_argument("--emit", choices=["json", "text"], default="json")
    parser.add_argument("--inject", action="store_true")
    parser.add_argument("--readonly", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Dispatch one hook command. Always returns 0: the loop must fail open."""
    try:
        args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit:
        return 0
    try:
        load_env()  # bring ~/.hyperstruck/.env (auth + configured agent) into env
        _debug(
            f"fired command={args.command} source={args.source or SOURCE_CLAUDE_CODE}"
        )
        if args.command == "resolve":
            if args.flush_path:
                cmd_resolve(args.flush_path)
            return 0
        if args.command == "flush":
            cmd_flush(args)
            return 0
        payload = _read_stdin()
        if args.command == "prompt":
            cmd_prompt(payload, args)
        elif args.command == "tool":
            cmd_tool(payload, args)
        elif args.command == "stop":
            cmd_stop(payload, args)
        elif args.command == "distill":
            cmd_distill(payload, args)
    except BaseException:  # noqa: BLE001 - the loop must never break the editor, even on cancellation/interrupt
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
